#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Base de Datos para Facial Sync Service
Maneja conexiones MSSQL usando videoman.udl
"""

import pyodbc
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import threading
import time
from contextlib import contextmanager

class DatabaseManager:
    """Gestor de conexiones y operaciones de base de datos"""
    
    def __init__(self, udl_path: str):
        self.udl_path = Path(udl_path)
        self.connection_string = None
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.max_pool_size = 10
        self.current_pool_size = 0
        
        self._parse_udl_file()
    
    def _parse_udl_file(self):
        """Parsea el archivo UDL para obtener la cadena de conexión"""
        if not self.udl_path.exists():
            raise FileNotFoundError(f"Archivo UDL no encontrado: {self.udl_path}")
        
        try:
            with open(self.udl_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar la línea de conexión en el archivo UDL
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('[') and '=' in line:
                    # Esta es la línea de conexión
                    self.connection_string = line
                    break
            
            if not self.connection_string:
                raise ValueError("No se encontró cadena de conexión en archivo UDL")
            
            logging.info(f"Cadena de conexión cargada desde {self.udl_path}")
            
        except Exception as e:
            logging.error(f"Error parseando archivo UDL: {e}")
            raise
    
    def get_connection(self) -> pyodbc.Connection:
        """Obtiene una conexión de la base de datos"""
        with self.pool_lock:
            # Intentar reutilizar conexión del pool
            if self.connection_pool:
                conn = self.connection_pool.pop()
                try:
                    # Verificar si la conexión sigue activa
                    conn.execute("SELECT 1")
                    return conn
                except:
                    # Conexión inválida, crear nueva
                    pass
            
            # Crear nueva conexión
            try:
                conn = pyodbc.connect(self.connection_string, timeout=30)
                conn.autocommit = True
                self.current_pool_size += 1
                logging.debug("Nueva conexión creada")
                return conn
            except Exception as e:
                logging.error(f"Error creando conexión: {e}")
                raise
    
    def return_connection(self, conn: pyodbc.Connection):
        """Devuelve una conexión al pool"""
        if not conn:
            return
            
        with self.pool_lock:
            if len(self.connection_pool) < self.max_pool_size:
                try:
                    # Verificar que la conexión siga válida
                    conn.execute("SELECT 1")
                    self.connection_pool.append(conn)
                except:
                    # Conexión inválida, cerrarla
                    try:
                        conn.close()
                    except:
                        pass
                    self.current_pool_size -= 1
            else:
                # Pool lleno, cerrar conexión
                try:
                    conn.close()
                except:
                    pass
                self.current_pool_size -= 1
    
    @contextmanager
    def get_connection_context(self):
        """Context manager para manejo automático de conexiones"""
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute_query(self, query: str, params: List = None) -> List[Tuple]:
        """Ejecuta una consulta SELECT y retorna resultados"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                logging.debug(f"Query ejecutado: {len(results)} filas")
                return results
            except Exception as e:
                logging.error(f"Error ejecutando query: {e}")
                logging.error(f"Query: {query}")
                logging.error(f"Params: {params}")
                raise
            finally:
                cursor.close()
    
    def execute_non_query(self, query: str, params: List = None) -> int:
        """Ejecuta INSERT, UPDATE o DELETE y retorna filas afectadas"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                affected_rows = cursor.rowcount
                conn.commit()
                logging.debug(f"Non-query ejecutado: {affected_rows} filas afectadas")
                return affected_rows
            except Exception as e:
                conn.rollback()
                logging.error(f"Error ejecutando non-query: {e}")
                logging.error(f"Query: {query}")
                logging.error(f"Params: {params}")
                raise
            finally:
                cursor.close()
    
    def execute_scalar(self, query: str, params: List = None) -> Any:
        """Ejecuta consulta y retorna un solo valor"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                logging.error(f"Error ejecutando scalar: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_procedure(self, proc_name: str, params: List = None) -> List[Tuple]:
        """Ejecuta un procedimiento almacenado"""
        with self.get_connection_context() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(f"EXEC {proc_name} {','.join(['?' for _ in params])}", params)
                else:
                    cursor.execute(f"EXEC {proc_name}")
                
                results = cursor.fetchall()
                conn.commit()
                return results
            except Exception as e:
                conn.rollback()
                logging.error(f"Error ejecutando procedimiento {proc_name}: {e}")
                raise
            finally:
                cursor.close()
    
    def test_connection(self) -> bool:
        """Prueba la conexión a la base de datos"""
        try:
            with self.get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT GETDATE()")
                result = cursor.fetchone()
                cursor.close()
                logging.info("Conexión a base de datos exitosa")
                return True
        except Exception as e:
            logging.error(f"Error probando conexión: {e}")
            return False
    
    # ========================================
    # MÉTODOS ESPECÍFICOS PARA SYNC SERVICE
    # ========================================
    
    def get_active_devices(self) -> List[Dict[str, Any]]:
        """Obtiene lista de dispositivos activos"""
        query = """
        SELECT DispositivoID, Nombre, IP, Usuario, Password, 
               PuertoHTTP, PuertoSVR, PuertoHTTPS, PuertoRTSP, 
               Tipo, Modelo, Activo
        FROM hikvision 
        WHERE Activo = 1
        ORDER BY DispositivoID
        """
        
        results = self.execute_query(query)
        devices = []
        
        for row in results:
            device = {
                'dispositivo_id': row[0],
                'nombre': row[1],
                'ip': row[2],
                'usuario': row[3],
                'password': row[4],
                'puerto_http': row[5],
                'puerto_svr': row[6],
                'puerto_https': row[7],
                'puerto_rtsp': row[8],
                'tipo': row[9],
                'modelo': row[10],
                'activo': row[11]
            }
            devices.append(device)
        
        return devices
    
    def enqueue_sync_task(self, task_type: str, facial_id: int = None, 
                         persona_id: int = None, task_data: Dict = None, 
                         priority: int = 1) -> int:
        """Encola una tarea de sincronización"""
        task_data_json = json.dumps(task_data) if task_data else None
        
        results = self.execute_procedure('SP_EnqueueSyncTask', [
            task_type, facial_id, persona_id, task_data_json, priority
        ])
        
        return results[0][0] if results else None
    
    def get_next_pending_task(self) -> Optional[Dict[str, Any]]:
        """Obtiene la siguiente tarea pendiente"""
        results = self.execute_procedure('SP_GetNextPendingTask')
        
        if results:
            row = results[0]
            task_data = json.loads(row[4]) if row[4] else {}
            
            return {
                'id': row[0],
                'task_type': row[1],
                'facial_id': row[2],
                'persona_id': row[3],
                'task_data': task_data,
                'priority': row[5],
                'attempts': row[6]
            }
        
        return None
    
    def update_task_status(self, task_id: int, status: str, error: str = None):
        """Actualiza el estado de una tarea"""
        self.execute_procedure('SP_UpdateTaskStatus', [task_id, status, error])
    
    def log_access_event(self, device_ip: str, event_type: str, event_code: str = None,
                        persona_id: int = None, employee_no: str = None, 
                        person_name: str = None, verify_mode: str = None,
                        access_result: str = None, event_time: str = None,
                        raw_data: str = None) -> int:
        """Registra un evento de acceso"""
        results = self.execute_procedure('SP_LogAccessEvent', [
            device_ip, event_type, event_code, persona_id, employee_no,
            person_name, verify_mode, access_result, event_time, raw_data
        ])
        
        return results[0][0] if results else None
    
    def get_facial_data(self, facial_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene datos faciales por ID"""
        query = """
        SELECT f.FacialID, f.TemplateData, f.Activo,
               p.PersonaID, p.Nombre, p.Apellido,
               pf.PersonaID as LinkedPersonaID
        FROM face f
        LEFT JOIN perface pf ON f.FacialID = pf.FacialID
        LEFT JOIN per p ON pf.PersonaID = p.PersonaID
        WHERE f.FacialID = ?
        """
        
        results = self.execute_query(query, [facial_id])
        
        if results:
            row = results[0]
            return {
                'facial_id': row[0],
                'template_data': row[1],
                'activo': row[2],
                'persona_id': row[3],
                'nombre': row[4],
                'apellido': row[5],
                'linked_persona_id': row[6]
            }
        
        return None
    
    def get_persona_facial_data(self, persona_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene datos faciales de una persona"""
        query = """
        SELECT TOP 1 f.FacialID, f.TemplateData, f.Activo,
               p.PersonaID, p.Nombre, p.Apellido
        FROM per p
        LEFT JOIN perface pf ON p.PersonaID = pf.PersonaID
        LEFT JOIN face f ON pf.FacialID = f.FacialID
        WHERE p.PersonaID = ?
        ORDER BY f.FacialID DESC
        """
        
        results = self.execute_query(query, [persona_id])
        
        if results:
            row = results[0]
            return {
                'facial_id': row[0],
                'template_data': row[1],
                'activo': row[2],
                'persona_id': row[3],
                'nombre': row[4],
                'apellido': row[5]
            }
        
        return None
    
    def update_device_status(self, dispositivo_id: str, is_online: bool, 
                           last_error: str = None, face_count: int = None):
        """Actualiza el estado de un dispositivo"""
        query = """
        IF EXISTS (SELECT 1 FROM device_status WHERE DispositivoID = ?)
            UPDATE device_status 
            SET LastPing = GETDATE(), IsOnline = ?, LastError = ?, 
                FaceCount = COALESCE(?, FaceCount),
                ErrorCount = CASE WHEN ? = 1 THEN 0 ELSE ErrorCount + 1 END,
                UpdatedAt = GETDATE()
            WHERE DispositivoID = ?
        ELSE
            INSERT INTO device_status (DispositivoID, LastPing, IsOnline, LastError, FaceCount)
            VALUES (?, GETDATE(), ?, ?, ?)
        """
        
        self.execute_non_query(query, [
            dispositivo_id, is_online, last_error, face_count, is_online, dispositivo_id,
            dispositivo_id, is_online, last_error, face_count
        ])
    
    def get_device_status(self, dispositivo_id: str = None) -> List[Dict[str, Any]]:
        """Obtiene estado de dispositivos"""
        if dispositivo_id:
            query = """
            SELECT h.DispositivoID, h.Nombre, h.IP, h.Tipo,
                   ds.LastPing, ds.IsOnline, ds.LastError, ds.ErrorCount,
                   ds.LastSync, ds.FaceCount, ds.Version
            FROM hikvision h
            LEFT JOIN device_status ds ON h.DispositivoID = ds.DispositivoID
            WHERE h.DispositivoID = ? AND h.Activo = 1
            """
            results = self.execute_query(query, [dispositivo_id])
        else:
            query = """
            SELECT h.DispositivoID, h.Nombre, h.IP, h.Tipo,
                   ds.LastPing, ds.IsOnline, ds.LastError, ds.ErrorCount,
                   ds.LastSync, ds.FaceCount, ds.Version
            FROM hikvision h
            LEFT JOIN device_status ds ON h.DispositivoID = ds.DispositivoID
            WHERE h.Activo = 1
            ORDER BY h.DispositivoID
            """
            results = self.execute_query(query)
        
        devices = []
        for row in results:
            device = {
                'dispositivo_id': row[0],
                'nombre': row[1],
                'ip': row[2],
                'tipo': row[3],
                'last_ping': row[4],
                'is_online': row[5],
                'last_error': row[6],
                'error_count': row[7],
                'last_sync': row[8],
                'face_count': row[9],
                'version': row[10]
            }
            devices.append(device)
        
        return devices
    
    def cleanup_old_data(self, days_old: int = 30):
        """Limpia datos antiguos de logs y eventos"""
        try:
            # Limpiar tareas completadas
            self.execute_procedure('SP_CleanupCompletedTasks', [days_old])
            
            # Limpiar eventos antiguos
            query = "DELETE FROM access_events WHERE ReceivedAt < DATEADD(DAY, -?, GETDATE())"
            self.execute_non_query(query, [days_old])
            
            logging.info(f"Limpieza de datos antiguos completada ({days_old} días)")
            
        except Exception as e:
            logging.error(f"Error en limpieza de datos: {e}")
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de tareas"""
        query = """
        SELECT 
            Status,
            COUNT(*) as Count,
            AVG(CASE WHEN ProcessedAt IS NOT NULL AND CompletedAt IS NOT NULL 
                THEN DATEDIFF(SECOND, ProcessedAt, CompletedAt) ELSE NULL END) as AvgProcessingTime
        FROM sync_queue 
        WHERE CreatedAt >= DATEADD(DAY, -1, GETDATE())
        GROUP BY Status
        """
        
        results = self.execute_query(query)
        stats = {}
        
        for row in results:
            stats[row[0]] = {
                'count': row[1],
                'avg_processing_time': row[2]
            }
        
        return stats
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de eventos"""
        query = """
        SELECT 
            DeviceIP,
            AccessResult,
            COUNT(*) as Count
        FROM access_events 
        WHERE EventTime >= DATEADD(HOUR, -24, GETDATE())
        GROUP BY DeviceIP, AccessResult
        ORDER BY DeviceIP, AccessResult
        """
        
        results = self.execute_query(query)
        stats = {}
        
        for row in results:
            device_ip = row[0]
            result = row[1]
            count = row[2]
            
            if device_ip not in stats:
                stats[device_ip] = {}
            
            stats[device_ip][result] = count
        
        return stats
    
    def close_all_connections(self):
        """Cierra todas las conexiones del pool"""
        with self.pool_lock:
            for conn in self.connection_pool:
                try:
                    conn.close()
                except:
                    pass
            
            self.connection_pool.clear()
            self.current_pool_size = 0
            
        logging.info("Todas las conexiones cerradas")
    
    def __del__(self):
        """Destructor - cierra conexiones"""
        try:
            self.close_all_connections()
        except:
            pass