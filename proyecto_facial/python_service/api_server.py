#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Server REST para Facial Sync Service
Maneja endpoints para sincronización facial con dispositivos Hikvision
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging
import threading
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional

class APIServer:
    """Servidor API REST usando Flask"""
    
    def __init__(self, db_manager, device_manager, task_queue, config):
        self.db_manager = db_manager
        self.device_manager = device_manager
        self.task_queue = task_queue
        self.config = config
        
        # Configuración Flask
        self.app = Flask(__name__)
        CORS(self.app)  # Permitir CORS para requests desde VB6/otros clientes
        
        # Configurar logging de Flask
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)  # Reducir logs de Flask
        
        # Estado del servidor
        self.is_running = False
        self.server_thread = None
        
        # Configurar rutas
        self.setup_routes()
    
    def setup_routes(self):
        """Configura todas las rutas de la API"""
        
        # ====================================
        # ENDPOINTS DE SALUD Y ESTADO
        # ====================================
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Verificación de salud del servicio"""
            try:
                db_status = self.db_manager.test_connection() if self.db_manager else False
                
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'database': 'connected' if db_status else 'disconnected',
                    'version': '1.0.0'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Estado general del servicio"""
            try:
                devices = self.db_manager.get_device_status() if self.db_manager else []
                
                return jsonify({
                    'service_status': 'running',
                    'total_devices': len(devices),
                    'online_devices': len([d for d in devices if d.get('is_online')]),
                    'pending_tasks': self.task_queue.get_pending_count() if self.task_queue else 0,
                    'last_updated': datetime.now().isoformat()
                })
            except Exception as e:
                logging.error(f"Error obteniendo estado: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINTS DE SINCRONIZACIÓN FACIAL
        # ====================================
        
        @self.app.route('/api/face/create', methods=['POST'])
        def create_face():
            """Crea un nuevo rostro facial y lo sincroniza con dispositivos"""
            try:
                data = request.get_json()
                
                # Validar datos requeridos
                required_fields = ['facial_id', 'persona_id']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'Campo requerido: {field}'}), 400
                
                facial_id = data['facial_id']
                persona_id = data['persona_id']
                priority = data.get('priority', 1)
                
                logging.info(f"📸 API: Crear rostro - FacialID: {facial_id}, PersonaID: {persona_id}")
                
                # Verificar que el rostro existe en BD
                facial_data = self.db_manager.get_facial_data(facial_id)
                if not facial_data:
                    return jsonify({'error': f'Rostro facial {facial_id} no encontrado'}), 404
                
                # Encolar tarea de sincronización
                task_data = {
                    'facial_id': facial_id,
                    'persona_id': persona_id,
                    'action': 'create',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'api'
                }
                
                task_id = self.db_manager.enqueue_sync_task(
                    task_type='CREATE',
                    facial_id=facial_id,
                    persona_id=persona_id,
                    task_data=task_data,
                    priority=priority
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Rostro encolado para sincronización',
                    'task_id': task_id,
                    'facial_id': facial_id,
                    'estimated_devices': len(self.db_manager.get_active_devices())
                })
                
            except Exception as e:
                logging.error(f"Error creando rostro via API: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/face/update', methods=['PUT'])
        def update_face():
            """Actualiza un rostro facial existente"""
            try:
                data = request.get_json()
                
                if 'facial_id' not in data:
                    return jsonify({'error': 'facial_id requerido'}), 400
                
                facial_id = data['facial_id']
                
                logging.info(f"✏️ API: Actualizar rostro - FacialID: {facial_id}")
                
                # Verificar que el rostro existe
                facial_data = self.db_manager.get_facial_data(facial_id)
                if not facial_data:
                    return jsonify({'error': f'Rostro facial {facial_id} no encontrado'}), 404
                
                # Encolar tarea de actualización
                task_data = {
                    'facial_id': facial_id,
                    'persona_id': facial_data.get('persona_id'),
                    'action': 'update',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'api'
                }
                
                task_id = self.db_manager.enqueue_sync_task(
                    task_type='UPDATE',
                    facial_id=facial_id,
                    persona_id=facial_data.get('persona_id'),
                    task_data=task_data,
                    priority=data.get('priority', 1)
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Rostro encolado para actualización',
                    'task_id': task_id,
                    'facial_id': facial_id
                })
                
            except Exception as e:
                logging.error(f"Error actualizando rostro via API: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/face/delete', methods=['DELETE'])
        def delete_face():
            """Elimina un rostro facial de todos los dispositivos"""
            try:
                data = request.get_json()
                
                if 'facial_id' not in data:
                    return jsonify({'error': 'facial_id requerido'}), 400
                
                facial_id = data['facial_id']
                
                logging.info(f"🗑️ API: Eliminar rostro - FacialID: {facial_id}")
                
                # Obtener datos del rostro antes de eliminar
                facial_data = self.db_manager.get_facial_data(facial_id)
                
                # Encolar tarea de eliminación (incluso si no existe en BD)
                task_data = {
                    'facial_id': facial_id,
                    'persona_id': facial_data.get('persona_id') if facial_data else None,
                    'action': 'delete',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'api'
                }
                
                task_id = self.db_manager.enqueue_sync_task(
                    task_type='DELETE',
                    facial_id=facial_id,
                    persona_id=facial_data.get('persona_id') if facial_data else None,
                    task_data=task_data,
                    priority=data.get('priority', 1)
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Rostro encolado para eliminación',
                    'task_id': task_id,
                    'facial_id': facial_id
                })
                
            except Exception as e:
                logging.error(f"Error eliminando rostro via API: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINTS DE DISPOSITIVOS
        # ====================================
        
        @self.app.route('/api/devices', methods=['GET'])
        def get_devices():
            """Lista todos los dispositivos configurados"""
            try:
                devices = self.db_manager.get_active_devices()
                
                # Agregar información de estado
                for device in devices:
                    status_info = self.db_manager.get_device_status(device['dispositivo_id'])
                    if status_info:
                        device.update(status_info[0])
                
                return jsonify({
                    'devices': devices,
                    'total': len(devices)
                })
                
            except Exception as e:
                logging.error(f"Error obteniendo dispositivos: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/devices/<device_id>/status', methods=['GET'])
        def get_device_status(device_id):
            """Obtiene estado específico de un dispositivo"""
            try:
                status = self.db_manager.get_device_status(device_id)
                
                if not status:
                    return jsonify({'error': 'Dispositivo no encontrado'}), 404
                
                return jsonify(status[0])
                
            except Exception as e:
                logging.error(f"Error obteniendo estado de dispositivo {device_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/devices/<device_id>/test', methods=['POST'])
        def test_device_connection(device_id):
            """Prueba la conexión a un dispositivo específico"""
            try:
                if not self.device_manager:
                    return jsonify({'error': 'Device manager no disponible'}), 503
                
                # Obtener configuración del dispositivo
                devices = self.db_manager.get_active_devices()
                device = next((d for d in devices if d['dispositivo_id'] == device_id), None)
                
                if not device:
                    return jsonify({'error': 'Dispositivo no encontrado'}), 404
                
                # Probar conexión
                success, message = self.device_manager.test_device_connection(device)
                
                return jsonify({
                    'device_id': device_id,
                    'success': success,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logging.error(f"Error probando dispositivo {device_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINTS DE TAREAS
        # ====================================
        
        @self.app.route('/api/tasks', methods=['GET'])
        def get_tasks():
            """Lista tareas de sincronización recientes"""
            try:
                # Parámetros de consulta
                status_filter = request.args.get('status', None)
                limit = int(request.args.get('limit', 50))
                
                # Query base
                query = "SELECT TOP {} ID, TaskType, Status, Priority, Attempts, CreatedAt, ProcessedAt, LastError FROM sync_queue".format(limit)
                
                if status_filter:
                    query += f" WHERE Status = '{status_filter}'"
                
                query += " ORDER BY CreatedAt DESC"
                
                results = self.db_manager.execute_query(query)
                
                tasks = []
                for row in results:
                    task = {
                        'id': row[0],
                        'task_type': row[1],
                        'status': row[2],
                        'priority': row[3],
                        'attempts': row[4],
                        'created_at': row[5].isoformat() if row[5] else None,
                        'processed_at': row[6].isoformat() if row[6] else None,
                        'last_error': row[7]
                    }
                    tasks.append(task)
                
                return jsonify({
                    'tasks': tasks,
                    'total': len(tasks),
                    'filter': status_filter
                })
                
            except Exception as e:
                logging.error(f"Error obteniendo tareas: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/stats', methods=['GET'])
        def get_task_stats():
            """Estadísticas de tareas"""
            try:
                stats = self.db_manager.get_task_statistics()
                return jsonify(stats)
                
            except Exception as e:
                logging.error(f"Error obteniendo estadísticas: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINTS DE EVENTOS
        # ====================================
        
        @self.app.route('/api/events', methods=['GET'])
        def get_events():
            """Lista eventos de acceso recientes"""
            try:
                limit = int(request.args.get('limit', 100))
                device_ip = request.args.get('device_ip', None)
                
                query = f"SELECT TOP {limit} DeviceIP, EventType, PersonName, AccessResult, EventTime FROM access_events"
                params = []
                
                if device_ip:
                    query += " WHERE DeviceIP = ?"
                    params.append(device_ip)
                
                query += " ORDER BY EventTime DESC"
                
                results = self.db_manager.execute_query(query, params)
                
                events = []
                for row in results:
                    event = {
                        'device_ip': row[0],
                        'event_type': row[1],
                        'person_name': row[2],
                        'access_result': row[3],
                        'event_time': row[4].isoformat() if row[4] else None
                    }
                    events.append(event)
                
                return jsonify({
                    'events': events,
                    'total': len(events)
                })
                
            except Exception as e:
                logging.error(f"Error obteniendo eventos: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINT PARA VB6
        # ====================================
        
        @self.app.route('/api/vb6/sync', methods=['POST'])
        def vb6_sync():
            """Endpoint específico para sincronización desde VB6"""
            try:
                data = request.get_json()
                
                # Validar datos
                if not data or 'action' not in data:
                    return jsonify({'error': 'Acción requerida'}), 400
                
                action = data['action'].upper()
                facial_id = data.get('facial_id')
                persona_id = data.get('persona_id')
                
                logging.info(f"🔗 VB6 Sync: {action} - FacialID: {facial_id}, PersonaID: {persona_id}")
                
                if action in ['CREATE', 'UPDATE', 'DELETE']:
                    # Encolar tarea
                    task_data = {
                        'facial_id': facial_id,
                        'persona_id': persona_id,
                        'action': action.lower(),
                        'timestamp': datetime.now().isoformat(),
                        'source': 'vb6'
                    }
                    
                    task_id = self.db_manager.enqueue_sync_task(
                        task_type=action,
                        facial_id=facial_id,
                        persona_id=persona_id,
                        task_data=task_data,
                        priority=1  # Alta prioridad para VB6
                    )
                    
                    return jsonify({
                        'success': True,
                        'task_id': task_id,
                        'message': f'Tarea {action} encolada correctamente'
                    })
                else:
                    return jsonify({'error': f'Acción inválida: {action}'}), 400
                
            except Exception as e:
                logging.error(f"Error en VB6 sync: {e}")
                return jsonify({'error': str(e)}), 500
        
        # ====================================
        # ENDPOINT DE INFORMACIÓN
        # ====================================
        
        @self.app.route('/api/info', methods=['GET'])
        def get_info():
            """Información general del servicio"""
            return jsonify({
                'service': 'Facial Sync Service',
                'version': '1.0.0',
                'description': 'Servicio de sincronización facial con dispositivos Hikvision',
                'endpoints': {
                    'health': '/api/health',
                    'status': '/api/status',
                    'devices': '/api/devices',
                    'tasks': '/api/tasks',
                    'events': '/api/events',
                    'vb6_sync': '/api/vb6/sync'
                },
                'timestamp': datetime.now().isoformat()
            })
    
    def start(self):
        """Inicia el servidor API"""
        if self.is_running:
            logging.warning("API Server ya está ejecutándose")
            return
        
        try:
            host = self.config.get('API_HOST', '0.0.0.0')
            port = self.config.get('API_PORT', 5000)
            debug = self.config.get('API_DEBUG', False)
            
            self.is_running = True
            
            logging.info(f"🚀 Iniciando API Server en {host}:{port}")
            
            # Ejecutar Flask en thread separado
            def run_flask():
                self.app.run(
                    host=host,
                    port=port,
                    debug=debug,
                    use_reloader=False,
                    threaded=True
                )
            
            self.server_thread = threading.Thread(target=run_flask, daemon=True)
            self.server_thread.start()
            
            # Verificar que el servidor esté respondiendo
            time.sleep(1)
            logging.info(f"✅ API Server activo en http://{host}:{port}")
            
        except Exception as e:
            self.is_running = False
            logging.error(f"❌ Error iniciando API Server: {e}")
            raise
    
    def stop(self):
        """Detiene el servidor API"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            logging.info("🛑 Deteniendo API Server...")
            
            # Flask no tiene método directo para parar, pero el thread es daemon
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logging.info("✅ API Server detenido")
            
        except Exception as e:
            logging.error(f"❌ Error deteniendo API Server: {e}")

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
    
    # Database manager mock
    db_manager = DatabaseManager(config.get('DB_UDL_PATH'))
    
    # Crear y ejecutar servidor
    api_server = APIServer(db_manager, None, None, config)
    
    try:
        api_server.start()
        print("API Server ejecutándose... Presiona Ctrl+C para parar")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo API Server...")
        api_server.stop()

if __name__ == "__main__":
    main()