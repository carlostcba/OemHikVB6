#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Queue Manager para Facial Sync Service
Maneja cola de tareas de sincronización facial con prioridades
"""

import threading
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from queue import PriorityQueue, Empty
import heapq

class TaskItem:
    """Item de tarea con prioridad para la cola"""
    
    def __init__(self, priority: int, task_id: int, task_data: Dict[str, Any]):
        self.priority = priority
        self.task_id = task_id
        self.task_data = task_data
        self.timestamp = datetime.now()
    
    def __lt__(self, other):
        # Prioridad menor = mayor urgencia
        if self.priority != other.priority:
            return self.priority < other.priority
        # Si misma prioridad, FIFO por timestamp
        return self.timestamp < other.timestamp
    
    def __repr__(self):
        return f"TaskItem(priority={self.priority}, id={self.task_id}, type={self.task_data.get('task_type')})"

class TaskQueue:
    """Gestor de cola de tareas con prioridades"""
    
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config
        
        # Cola de prioridades en memoria
        self.priority_queue = PriorityQueue()
        self.queue_lock = threading.Lock()
        
        # Configuración
        self.max_retries = config.get('MAX_RETRY_ATTEMPTS', 3)
        self.retry_delay = config.get('RETRY_DELAY_SECONDS', 60)
        self.batch_size = config.get('BATCH_SIZE', 10)
        
        # Estado
        self.is_running = False
        self.worker_thread = None
        
        # Estadísticas
        self.stats = {
            'tasks_processed': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_retried': 0,
            'start_time': None
        }
        
        # Cache de tareas en proceso
        self.processing_tasks = {}
        
        logging.info("TaskQueue inicializado")
    
    def start(self):
        """Inicia el procesador de cola de tareas"""
        if self.is_running:
            logging.warning("TaskQueue ya está ejecutándose")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        # Cargar tareas pendientes desde BD
        self._load_pending_tasks()
        
        # Iniciar worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logging.info("✅ TaskQueue iniciado")
    
    def stop(self):
        """Detiene el procesador de cola"""
        if not self.is_running:
            return
        
        logging.info("🛑 Deteniendo TaskQueue...")
        self.is_running = False
        
        # Esperar que termine el worker
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        logging.info("✅ TaskQueue detenido")
    
    def enqueue_task(self, task_type: str, facial_id: int = None, 
                    persona_id: int = None, task_data: Dict = None, 
                    priority: int = 1) -> int:
        """Encola una nueva tarea de sincronización"""
        try:
            # Guardar en BD primero
            task_id = self.db_manager.enqueue_sync_task(
                task_type=task_type,
                facial_id=facial_id,
                persona_id=persona_id,
                task_data=task_data,
                priority=priority
            )
            
            if task_id:
                # Agregar a cola en memoria
                full_task_data = {
                    'id': task_id,
                    'task_type': task_type,
                    'facial_id': facial_id,
                    'persona_id': persona_id,
                    'task_data': task_data or {},
                    'priority': priority,
                    'attempts': 0
                }
                
                task_item = TaskItem(priority, task_id, full_task_data)
                
                with self.queue_lock:
                    self.priority_queue.put(task_item)
                self.stats['tasks_retried'] += 1
        
        # Ejecutar reintento en thread separado
        retry_thread = threading.Thread(target=delayed_retry, daemon=True)
        retry_thread.start()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Obtiene estado actual de la cola"""
        return {
            'is_running': self.is_running,
            'pending_tasks': self.get_pending_count(),
            'processing_tasks': len(self.processing_tasks),
            'stats': self.stats.copy(),
            'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        }
    
    def get_processing_tasks(self) -> List[Dict[str, Any]]:
        """Obtiene lista de tareas actualmente en procesamiento"""
        processing = []
        
        for task_id, info in self.processing_tasks.items():
            task_info = {
                'task_id': task_id,
                'task_type': info['task_data']['task_type'],
                'facial_id': info['task_data']['facial_id'],
                'persona_id': info['task_data']['persona_id'],
                'start_time': info['start_time'].isoformat(),
                'duration_seconds': (datetime.now() - info['start_time']).total_seconds()
            }
            processing.append(task_info)
        
        return processing
    
    def clear_failed_tasks(self) -> int:
        """Limpia tareas fallidas de la base de datos"""
        try:
            query = "DELETE FROM sync_queue WHERE Status = 'FAILED'"
            deleted_count = self.db_manager.execute_non_query(query)
            
            logging.info(f"🧹 {deleted_count} tareas fallidas eliminadas")
            return deleted_count
            
        except Exception as e:
            logging.error(f"Error limpiando tareas fallidas: {e}")
            return 0
    
    def clear_completed_tasks(self, days_old: int = 7) -> int:
        """Limpia tareas completadas antiguas"""
        try:
            query = "DELETE FROM sync_queue WHERE Status = 'COMPLETED' AND CompletedAt < DATEADD(DAY, -?, GETDATE())"
            deleted_count = self.db_manager.execute_non_query(query, [days_old])
            
            logging.info(f"🧹 {deleted_count} tareas completadas antiguas eliminadas")
            return deleted_count
            
        except Exception as e:
            logging.error(f"Error limpiando tareas completadas: {e}")
            return 0
    
    def retry_failed_tasks(self) -> int:
        """Reintenta todas las tareas fallidas que no han excedido el límite"""
        try:
            # Obtener tareas fallidas con intentos < max_retries
            query = """
            SELECT ID, TaskType, FacialID, PersonaID, TaskData, Priority, Attempts
            FROM sync_queue 
            WHERE Status = 'FAILED' AND Attempts < ?
            """
            
            results = self.db_manager.execute_query(query, [self.max_retries])
            
            retried_count = 0
            for row in results:
                # Resetear a PENDING
                self.db_manager.update_task_status(row[0], 'PENDING', None)
                
                # Agregar a cola
                task_data = {
                    'id': row[0],
                    'task_type': row[1],
                    'facial_id': row[2],
                    'persona_id': row[3],
                    'task_data': json.loads(row[4]) if row[4] else {},
                    'priority': row[5],
                    'attempts': row[6]
                }
                
                task_item = TaskItem(row[5], row[0], task_data)
                
                with self.queue_lock:
                    self.priority_queue.put(task_item)
                
                retried_count += 1
            
            logging.info(f"🔄 {retried_count} tareas fallidas reencoladas para reintento")
            return retried_count
            
        except Exception as e:
            logging.error(f"Error reintentando tareas fallidas: {e}")
            return 0
    
    def get_task_details(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene detalles específicos de una tarea"""
        try:
            query = """
            SELECT ID, TaskType, Status, FacialID, PersonaID, TaskData, Priority, 
                   Attempts, CreatedAt, ProcessedAt, CompletedAt, LastError
            FROM sync_queue 
            WHERE ID = ?
            """
            
            results = self.db_manager.execute_query(query, [task_id])
            
            if results:
                row = results[0]
                return {
                    'id': row[0],
                    'task_type': row[1],
                    'status': row[2],
                    'facial_id': row[3],
                    'persona_id': row[4],
                    'task_data': json.loads(row[5]) if row[5] else {},
                    'priority': row[6],
                    'attempts': row[7],
                    'created_at': row[8].isoformat() if row[8] else None,
                    'processed_at': row[9].isoformat() if row[9] else None,
                    'completed_at': row[10].isoformat() if row[10] else None,
                    'last_error': row[11]
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error obteniendo detalles de tarea {task_id}: {e}")
            return None
    
    def cancel_task(self, task_id: int) -> bool:
        """Cancela una tarea pendiente"""
        try:
            # Verificar que la tarea esté pendiente
            task_details = self.get_task_details(task_id)
            if not task_details:
                return False
            
            if task_details['status'] not in ['PENDING', 'PROCESSING']:
                logging.warning(f"No se puede cancelar tarea {task_id} con estado {task_details['status']}")
                return False
            
            # Actualizar estado a CANCELLED
            self.db_manager.update_task_status(task_id, 'CANCELLED', 'Cancelada por usuario')
            
            # Remover de cola en memoria si está ahí
            # (No hay forma directa de remover de PriorityQueue, pero se ignorará al procesarse)
            
            logging.info(f"❌ Tarea {task_id} cancelada")
            return True
            
        except Exception as e:
            logging.error(f"Error cancelando tarea {task_id}: {e}")
            return False
    
    def pause_queue(self):
        """Pausa el procesamiento de la cola"""
        self.is_running = False
        logging.info("⏸️ Cola de tareas pausada")
    
    def resume_queue(self):
        """Reanuda el procesamiento de la cola"""
        if not self.is_running:
            self.is_running = True
            if not self.worker_thread or not self.worker_thread.is_alive():
                self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self.worker_thread.start()
            logging.info("▶️ Cola de tareas reanudada")
    
    def set_device_manager(self, device_manager):
        """Establece referencia al device manager para sincronización real"""
        self.device_manager = device_manager
        logging.info("📱 DeviceManager conectado al TaskQueue")
    
    def force_process_task(self, task_id: int) -> bool:
        """Fuerza el procesamiento inmediato de una tarea específica"""
        try:
            task_details = self.get_task_details(task_id)
            if not task_details:
                return False
            
            if task_details['status'] != 'PENDING':
                logging.warning(f"Tarea {task_id} no está pendiente (estado: {task_details['status']})")
                return False
            
            # Crear TaskItem con prioridad máxima
            task_item = TaskItem(0, task_id, task_details)  # Prioridad 0 = máxima urgencia
            
            # Agregar al frente de la cola
            with self.queue_lock:
                self.priority_queue.put(task_item)
            
            logging.info(f"⚡ Tarea {task_id} marcada para procesamiento inmediato")
            return True
            
        except Exception as e:
            logging.error(f"Error forzando procesamiento de tarea {task_id}: {e}")
            return False

def main():
    """Función principal para testing"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import get_config
    from database_manager import DatabaseManager
    
    # Configuración de prueba
    config = get_config()
    config.initialize()
    
    # Database manager
    db_manager = DatabaseManager(config.get('DB_UDL_PATH'))
    
    # Crear task queue
    task_queue = TaskQueue(db_manager, config)
    
    print("Task Queue iniciado")
    print("Comandos disponibles:")
    print("  start - Iniciar procesamiento")
    print("  stop - Detener procesamiento")
    print("  status - Ver estado de la cola")
    print("  add <type> <facial_id> - Agregar tarea de prueba")
    print("  processing - Ver tareas en proceso")
    print("  clear failed - Limpiar tareas fallidas")
    print("  retry failed - Reintentar tareas fallidas")
    print("  quit - Salir")
    
    try:
        while True:
            try:
                command = input("\ntask> ").strip().split()
                
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == "start":
                    task_queue.start()
                    print("Task Queue iniciado")
                
                elif cmd == "stop":
                    task_queue.stop()
                    print("Task Queue detenido")
                
                elif cmd == "status":
                    status = task_queue.get_queue_status()
                    print("Estado de la cola:")
                    for key, value in status.items():
                        print(f"  {key}: {value}")
                
                elif cmd == "add" and len(command) >= 3:
                    task_type = command[1].upper()
                    facial_id = int(command[2])
                    
                    task_id = task_queue.enqueue_task(
                        task_type=task_type,
                        facial_id=facial_id,
                        persona_id=1,  # Dummy persona ID
                        task_data={'test': True},
                        priority=1
                    )
                    
                    if task_id:
                        print(f"Tarea {task_id} agregada: {task_type} para facial {facial_id}")
                    else:
                        print("Error agregando tarea")
                
                elif cmd == "processing":
                    processing = task_queue.get_processing_tasks()
                    if processing:
                        print(f"Tareas en proceso: {len(processing)}")
                        for task in processing:
                            print(f"  {task['task_id']}: {task['task_type']} (facial {task['facial_id']}) - {task['duration_seconds']:.1f}s")
                    else:
                        print("No hay tareas en proceso")
                
                elif cmd == "clear" and len(command) > 1 and command[1] == "failed":
                    deleted = task_queue.clear_failed_tasks()
                    print(f"{deleted} tareas fallidas eliminadas")
                
                elif cmd == "retry" and len(command) > 1 and command[1] == "failed":
                    retried = task_queue.retry_failed_tasks()
                    print(f"{retried} tareas fallidas reencoladas")
                
                elif cmd in ["quit", "exit"]:
                    break
                
                elif cmd == "help":
                    print("Comandos: start, stop, status, add <type> <facial_id>, processing, clear failed, retry failed, quit")
                
                else:
                    print(f"Comando desconocido: {cmd}")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except ValueError as e:
                print(f"Error en parámetros: {e}")
    
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando Task Queue...")
        task_queue.stop()

if __name__ == "__main__":
    main()queue.put(task_item)
                
                logging.info(f"📋 Tarea {task_id} encolada: {task_type} (prioridad {priority})")
                return task_id
            else:
                logging.error("Error: No se pudo guardar tarea en BD")
                return None
                
        except Exception as e:
            logging.error(f"Error encolando tarea: {e}")
            return None
    
    def get_pending_count(self) -> int:
        """Obtiene número de tareas pendientes"""
        with self.queue_lock:
            return self.priority_queue.qsize()
    
    def _load_pending_tasks(self):
        """Carga tareas pendientes desde la base de datos"""
        try:
            logging.info("📂 Cargando tareas pendientes desde BD...")
            
            # Obtener tareas pendientes ordenadas por prioridad
            query = """
            SELECT ID, TaskType, FacialID, PersonaID, TaskData, Priority, Attempts
            FROM sync_queue 
            WHERE Status = 'PENDING' AND Attempts < ?
            ORDER BY Priority ASC, CreatedAt ASC
            """
            
            results = self.db_manager.execute_query(query, [self.max_retries])
            
            loaded_count = 0
            for row in results:
                task_data = {
                    'id': row[0],
                    'task_type': row[1],
                    'facial_id': row[2],
                    'persona_id': row[3],
                    'task_data': json.loads(row[4]) if row[4] else {},
                    'priority': row[5],
                    'attempts': row[6]
                }
                
                task_item = TaskItem(row[5], row[0], task_data)
                self.priority_queue.put(task_item)
                loaded_count += 1
            
            logging.info(f"📂 {loaded_count} tareas pendientes cargadas")
            
        except Exception as e:
            logging.error(f"Error cargando tareas pendientes: {e}")
    
    def _worker_loop(self):
        """Loop principal del worker que procesa tareas"""
        logging.info("🔄 Worker TaskQueue iniciado")
        
        while self.is_running:
            try:
                # Obtener siguiente tarea con timeout
                try:
                    with self.queue_lock:
                        if self.priority_queue.empty():
                            # No hay tareas, esperar un poco
                            time.sleep(1)
                            continue
                        
                        task_item = self.priority_queue.get_nowait()
                
                except Empty:
                    time.sleep(1)
                    continue
                
                # Procesar tarea
                self._process_task(task_item)
                
                # Pausa breve entre tareas
                time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error en worker loop: {e}")
                time.sleep(5)  # Pausa más larga en caso de error
        
        logging.info("🔄 Worker TaskQueue finalizado")
    
    def _process_task(self, task_item: TaskItem):
        """Procesa una tarea específica"""
        task_data = task_item.task_data
        task_id = task_data['id']
        
        try:
            # Marcar como en proceso
            self.processing_tasks[task_id] = {
                'start_time': datetime.now(),
                'task_data': task_data
            }
            
            # Actualizar estado en BD
            self.db_manager.update_task_status(task_id, 'PROCESSING', None)
            
            logging.info(f"⚙️ Procesando tarea {task_id}: {task_data['task_type']}")
            
            # Aquí se conectaría con el DeviceManager para ejecutar la sincronización
            # Por ahora simularemos el procesamiento
            success = self._execute_sync_task(task_data)
            
            if success:
                # Tarea completada exitosamente
                self.db_manager.update_task_status(task_id, 'COMPLETED', None)
                self.stats['tasks_completed'] += 1
                logging.info(f"✅ Tarea {task_id} completada exitosamente")
                
            else:
                # Tarea falló, decidir si reintentar
                attempts = task_data['attempts'] + 1
                
                if attempts < self.max_retries:
                    # Reintentar
                    self._retry_task(task_item, attempts)
                else:
                    # Marcar como fallida definitivamente
                    self.db_manager.update_task_status(task_id, 'FAILED', "Máximo de reintentos alcanzado")
                    self.stats['tasks_failed'] += 1
                    logging.error(f"❌ Tarea {task_id} falló definitivamente después de {attempts} intentos")
            
            self.stats['tasks_processed'] += 1
            
        except Exception as e:
            # Error en procesamiento
            error_msg = f"Error procesando tarea: {str(e)}"
            logging.error(f"❌ Error en tarea {task_id}: {e}")
            
            attempts = task_data.get('attempts', 0) + 1
            if attempts < self.max_retries:
                self._retry_task(task_item, attempts, error_msg)
            else:
                self.db_manager.update_task_status(task_id, 'FAILED', error_msg)
                self.stats['tasks_failed'] += 1
        
        finally:
            # Limpiar del cache de procesamiento
            if task_id in self.processing_tasks:
                del self.processing_tasks[task_id]
    
    def _execute_sync_task(self, task_data: Dict[str, Any]) -> bool:
        """Ejecuta la sincronización real con dispositivos"""
        try:
            task_type = task_data['task_type']
            facial_id = task_data['facial_id']
            persona_id = task_data['persona_id']
            
            # Aquí se integraría con DeviceManager
            # Por ahora simulamos el trabajo
            
            if task_type == 'CREATE':
                # Obtener datos faciales de BD
                facial_data = self.db_manager.get_facial_data(facial_id)
                if not facial_data:
                    logging.error(f"No se encontraron datos faciales para ID {facial_id}")
                    return False
                
                # TODO: Usar DeviceManager para sincronizar con dispositivos
                # results = device_manager.sync_face_to_all_devices(facial_data, 'create')
                # return results['successful'] > 0
                
                # Simulación
                time.sleep(2)  # Simular trabajo
                return True
                
            elif task_type == 'UPDATE':
                # Similar a CREATE pero para actualización
                facial_data = self.db_manager.get_facial_data(facial_id)
                if not facial_data:
                    logging.error(f"No se encontraron datos faciales para ID {facial_id}")
                    return False
                
                # TODO: DeviceManager sync
                time.sleep(2)
                return True
                
            elif task_type == 'DELETE':
                # Eliminar de dispositivos
                # TODO: DeviceManager delete
                time.sleep(1)
                return True
                
            else:
                logging.error(f"Tipo de tarea desconocido: {task_type}")
                return False
                
        except Exception as e:
            logging.error(f"Error ejecutando sincronización: {e}")
            return False
    
    def _retry_task(self, task_item: TaskItem, attempts: int, error_msg: str = None):
        """Programa reintento de una tarea"""
        task_id = task_item.task_data['id']
        
        # Actualizar número de intentos
        task_item.task_data['attempts'] = attempts
        
        # Actualizar en BD
        self.db_manager.update_task_status(task_id, 'PENDING', error_msg)
        
        # Calcular delay para reintento (backoff exponencial)
        delay = self.retry_delay * (2 ** (attempts - 1))
        retry_time = datetime.now() + timedelta(seconds=delay)
        
        logging.warning(f"🔄 Tarea {task_id} reintentará en {delay}s (intento {attempts}/{self.max_retries})")
        
        # Programar reintento
        def delayed_retry():
            time.sleep(delay)
            if self.is_running:
                with self.queue_lock:
                    self.priority_