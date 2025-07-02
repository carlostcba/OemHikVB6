#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Processor para Facial Sync Service
Procesa eventos de acceso de dispositivos Hikvision y los distribuye
"""

import threading
import time
import logging
import json
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

class EventHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para recibir eventos de dispositivos Hikvision"""
    
    def __init__(self, event_processor, *args, **kwargs):
        self.event_processor = event_processor
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """Maneja eventos POST enviados por dispositivos Hikvision"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', '')
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                
                # Obtener IP del dispositivo
                device_ip = self.client_address[0]
                
                # Procesar según tipo de contenido
                if 'multipart' in content_type.lower():
                    self.event_processor.process_multipart_event(post_data, content_type, device_ip)
                else:
                    # Intentar procesar como JSON
                    try:
                        event_data = json.loads(post_data.decode('utf-8'))
                        self.event_processor.process_json_event(event_data, device_ip)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Procesar como datos binarios
                        self.event_processor.process_binary_event(post_data, device_ip)
            
            # Responder OK al dispositivo
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "OK"}')
            
        except Exception as e:
            self.log_error(f"Error procesando evento de control de acceso: {e}")
    
    def _process_generic_event(self, event_data: Dict[str, Any]):
        """Procesa evento genérico"""
        try:
            device_ip = event_data.get('_device_ip')
            event_type = event_data.get('eventType', 'UNKNOWN')
            
            processed_event = {
                'device_ip': device_ip,
                'event_type': event_type,
                'event_code': '',
                'person_id': '',
                'employee_no': '',
                'person_name': '',
                'verify_mode': '',
                'access_result': 'UNKNOWN',
                'event_time': event_data.get('dateTime', datetime.now().isoformat()),
                'raw_data': json.dumps(event_data)
            }
            
            # Guardar eventos genéricos también
            self._save_event_to_database(processed_event)
            
            logging.debug(f"📨 Evento genérico - {self._get_device_name(device_ip)} ({device_ip}) - Tipo: {event_type}")
            
        except Exception as e:
            self.log_error(f"Error procesando evento genérico: {e}")
    
    def _save_event_to_database(self, event_data: Dict[str, Any]):
        """Guarda evento en la base de datos"""
        try:
            self.db_manager.log_access_event(
                device_ip=event_data['device_ip'],
                event_type=event_data['event_type'],
                event_code=event_data.get('event_code'),
                persona_id=None,  # Se podría mapear usando employee_no
                employee_no=event_data.get('employee_no'),
                person_name=event_data.get('person_name'),
                verify_mode=event_data.get('verify_mode'),
                access_result=event_data.get('access_result'),
                event_time=event_data['event_time'],
                raw_data=event_data.get('raw_data')
            )
            
        except Exception as e:
            self.log_error(f"Error guardando evento en BD: {e}")
    
    def _distribute_event(self, event_data: Dict[str, Any]):
        """Distribuye evento a todos los callbacks registrados"""
        for callback in self.event_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                self.log_error(f"Error en callback de evento: {e}")
    
    def _get_device_name(self, device_ip: str) -> str:
        """Obtiene nombre del dispositivo por IP"""
        device_info = self.known_devices.get(device_ip)
        if device_info:
            return device_info['nombre']
        return f"Device_{device_ip}"
    
    def register_event_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Registra callback para recibir eventos procesados"""
        self.event_callbacks.append(callback)
        logging.info(f"📡 Callback de eventos registrado ({len(self.event_callbacks)} total)")
    
    def unregister_event_callback(self, callback: Callable):
        """Desregistra callback de eventos"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            logging.info(f"📡 Callback de eventos desregistrado ({len(self.event_callbacks)} total)")
    
    def simulate_event(self, device_ip: str = "192.168.1.100", event_type: str = "SUCCESS"):
        """Simula un evento para testing"""
        try:
            if event_type == "SUCCESS":
                event_data = {
                    "AccessControllerEvent": {
                        "majorEventType": 5,
                        "subEventType": 75,
                        "employeeNoString": "EMP001",
                        "name": "Usuario Prueba",
                        "currentVerifyMode": "Face"
                    },
                    "dateTime": datetime.now().isoformat(),
                    "_device_ip": device_ip,
                    "_received_at": datetime.now().isoformat(),
                    "_format": "simulated"
                }
            else:
                event_data = {
                    "AccessControllerEvent": {
                        "majorEventType": 5,
                        "subEventType": 76,
                        "employeeNoString": "",
                        "name": "",
                        "currentVerifyMode": "Face"
                    },
                    "dateTime": datetime.now().isoformat(),
                    "_device_ip": device_ip,
                    "_received_at": datetime.now().isoformat(),
                    "_format": "simulated"
                }
            
            self._enqueue_event(event_data)
            logging.info(f"🎭 Evento simulado: {event_type} desde {device_ip}")
            
        except Exception as e:
            self.log_error(f"Error simulando evento: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del procesador"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'listen_port': self.listen_port,
            'queue_size': self.event_queue.qsize(),
            'known_devices': len(self.known_devices),
            'registered_callbacks': len(self.event_callbacks),
            'stats': self.stats.copy(),
            'uptime_seconds': uptime
        }
    
    def get_recent_events(self, limit: int = 50, device_ip: str = None) -> List[Dict[str, Any]]:
        """Obtiene eventos recientes de la base de datos"""
        try:
            query = f"SELECT TOP {limit} DeviceIP, EventType, EventCode, PersonName, AccessResult, EventTime, RawData FROM access_events"
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
                    'event_code': row[2],
                    'person_name': row[3],
                    'access_result': row[4],
                    'event_time': row[5].isoformat() if row[5] else None,
                    'raw_data': row[6]
                }
                events.append(event)
            
            return events
            
        except Exception as e:
            self.log_error(f"Error obteniendo eventos recientes: {e}")
            return []
    
    def clear_old_events(self, days_old: int = 30) -> int:
        """Limpia eventos antiguos de la base de datos"""
        try:
            query = "DELETE FROM access_events WHERE ReceivedAt < DATEADD(DAY, -?, GETDATE())"
            deleted_count = self.db_manager.execute_non_query(query, [days_old])
            
            logging.info(f"🧹 {deleted_count} eventos antiguos eliminados")
            return deleted_count
            
        except Exception as e:
            self.log_error(f"Error limpiando eventos antiguos: {e}")
            return 0
    
    def get_event_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Obtiene resumen de eventos de las últimas horas"""
        try:
            query = """
            SELECT 
                DeviceIP,
                AccessResult,
                COUNT(*) as EventCount
            FROM access_events 
            WHERE EventTime >= DATEADD(HOUR, -?, GETDATE())
            GROUP BY DeviceIP, AccessResult
            ORDER BY DeviceIP, AccessResult
            """
            
            results = self.db_manager.execute_query(query, [hours])
            
            summary = {
                'period_hours': hours,
                'total_events': 0,
                'by_device': {},
                'by_result': {'SUCCESS': 0, 'FAILED': 0, 'UNKNOWN': 0}
            }
            
            for row in results:
                device_ip = row[0]
                result = row[1] or 'UNKNOWN'
                count = row[2]
                
                summary['total_events'] += count
                summary['by_result'][result] = summary['by_result'].get(result, 0) + count
                
                if device_ip not in summary['by_device']:
                    summary['by_device'][device_ip] = {
                        'device_name': self._get_device_name(device_ip),
                        'total': 0,
                        'SUCCESS': 0,
                        'FAILED': 0,
                        'UNKNOWN': 0
                    }
                
                summary['by_device'][device_ip]['total'] += count
                summary['by_device'][device_ip][result] = count
            
            return summary
            
        except Exception as e:
            self.log_error(f"Error obteniendo resumen de eventos: {e}")
            return {'error': str(e)}
    
    def refresh_known_devices(self):
        """Recarga dispositivos conocidos desde la base de datos"""
        self._load_known_devices()
        logging.info("🔄 Dispositivos conocidos actualizados")
    
    def log_error(self, message: str):
        """Log de errores con conteo"""
        logging.error(message)
        self.stats['events_errors'] += 1
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Obtiene estado de la cola de eventos"""
        return {
            'queue_size': self.event_queue.qsize(),
            'queue_max_size': self.buffer_size,
            'queue_full': self.event_queue.full(),
            'batch_size': self.batch_size,
            'events_in_queue_percent': (self.event_queue.qsize() / self.buffer_size) * 100
        }

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
    
    # Crear event processor
    event_processor = EventProcessor(db_manager, config)
    
    # Callback de ejemplo
    def example_callback(event_data):
        print(f"📨 Evento recibido: {event_data.get('event_type')} desde {event_data.get('_device_ip')}")
    
    event_processor.register_event_callback(example_callback)
    
    print(f"Event Processor iniciado en puerto {event_processor.listen_port}")
    print("Comandos disponibles:")
    print("  start - Iniciar procesador")
    print("  stop - Detener procesador")
    print("  stats - Ver estadísticas")
    print("  simulate <type> - Simular evento (SUCCESS/FAILED)")
    print("  recent - Ver eventos recientes")
    print("  summary - Resumen de eventos (24h)")
    print("  queue - Estado de la cola")
    print("  quit - Salir")
    
    try:
        while True:
            try:
                command = input("\nevent> ").strip().split()
                
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == "start":
                    event_processor.start()
                    print("Event Processor iniciado")
                
                elif cmd == "stop":
                    event_processor.stop()
                    print("Event Processor detenido")
                
                elif cmd == "stats":
                    stats = event_processor.get_statistics()
                    print("Estadísticas:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                
                elif cmd == "simulate":
                    event_type = command[1] if len(command) > 1 else "SUCCESS"
                    event_processor.simulate_event(event_type=event_type)
                    print(f"Evento {event_type} simulado")
                
                elif cmd == "recent":
                    events = event_processor.get_recent_events(10)
                    print(f"Últimos {len(events)} eventos:")
                    for event in events:
                        result_emoji = "✅" if event['access_result'] == 'SUCCESS' else "❌" if event['access_result'] == 'FAILED' else "❓"
                        print(f"  {result_emoji} {event['device_ip']} - {event['person_name']} - {event['event_time']}")
                
                elif cmd == "summary":
                    summary = event_processor.get_event_summary(24)
                    print("Resumen (24h):")
                    print(f"  Total eventos: {summary['total_events']}")
                    print(f"  Exitosos: {summary['by_result']['SUCCESS']}")
                    print(f"  Fallidos: {summary['by_result']['FAILED']}")
                    print(f"  Dispositivos activos: {len(summary['by_device'])}")
                
                elif cmd == "queue":
                    queue_status = event_processor.get_queue_status()
                    print("Estado de la cola:")
                    for key, value in queue_status.items():
                        print(f"  {key}: {value}")
                
                elif cmd in ["quit", "exit"]:
                    break
                
                elif cmd == "help":
                    print("Comandos: start, stop, stats, simulate <type>, recent, summary, queue, quit")
                
                else:
                    print(f"Comando desconocido: {cmd}")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except IndexError:
                print("Parámetros insuficientes")
    
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando Event Processor...")
        event_processor.stop()

if __name__ == "__main__":
    main()event_processor.log_error(f"Error en EventHandler: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suprimir logs HTTP automáticos"""
        pass

class EventProcessor:
    """Procesador de eventos de acceso facial"""
    
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config
        
        # Configuración
        self.listen_port = config.get('EVENT_LISTEN_PORT', 8080)
        self.buffer_size = config.get('EVENT_BUFFER_SIZE', 1000)
        self.batch_size = config.get('EVENT_BATCH_SIZE', 50)
        
        # Estado del procesador
        self.is_running = False
        self.http_server = None
        self.server_thread = None
        
        # Cola de eventos
        self.event_queue = queue.Queue(maxsize=self.buffer_size)
        self.processor_thread = None
        
        # Callbacks para distribución
        self.event_callbacks: List[Callable] = []
        
        # Estadísticas
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_dropped': 0,
            'events_errors': 0,
            'start_time': None
        }
        
        # Cache de dispositivos conocidos
        self.known_devices = {}
        self._load_known_devices()
        
        logging.info("EventProcessor inicializado")
    
    def start(self):
        """Inicia el procesador de eventos"""
        if self.is_running:
            logging.warning("EventProcessor ya está ejecutándose")
            return
        
        try:
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            # Iniciar servidor HTTP para recibir eventos
            self._start_http_server()
            
            # Iniciar procesador de cola
            self.processor_thread = threading.Thread(target=self._process_events_loop, daemon=True)
            self.processor_thread.start()
            
            logging.info(f"✅ EventProcessor iniciado en puerto {self.listen_port}")
            
        except Exception as e:
            self.is_running = False
            logging.error(f"❌ Error iniciando EventProcessor: {e}")
            raise
    
    def stop(self):
        """Detiene el procesador de eventos"""
        if not self.is_running:
            return
        
        try:
            logging.info("🛑 Deteniendo EventProcessor...")
            self.is_running = False
            
            # Detener servidor HTTP
            if self.http_server:
                self.http_server.shutdown()
                self.http_server = None
            
            # Esperar threads
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            if self.processor_thread and self.processor_thread.is_alive():
                self.processor_thread.join(timeout=5)
            
            logging.info("✅ EventProcessor detenido")
            
        except Exception as e:
            logging.error(f"❌ Error deteniendo EventProcessor: {e}")
    
    def _start_http_server(self):
        """Inicia el servidor HTTP para recibir eventos"""
        try:
            # Crear handler con referencia a este procesador
            def handler(*args, **kwargs):
                EventHandler(self, *args, **kwargs)
            
            self.http_server = HTTPServer(('', self.listen_port), handler)
            
            def run_server():
                logging.info(f"🌐 Servidor de eventos escuchando en puerto {self.listen_port}")
                self.http_server.serve_forever()
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
        except Exception as e:
            logging.error(f"Error iniciando servidor HTTP: {e}")
            raise
    
    def _load_known_devices(self):
        """Carga dispositivos conocidos desde la base de datos"""
        try:
            devices = self.db_manager.get_active_devices()
            for device in devices:
                self.known_devices[device['ip']] = {
                    'dispositivo_id': device['dispositivo_id'],
                    'nombre': device['nombre'],
                    'tipo': device['tipo'],
                    'modelo': device.get('modelo', 'Unknown')
                }
            
            logging.info(f"📱 {len(self.known_devices)} dispositivos cargados")
            
        except Exception as e:
            logging.error(f"Error cargando dispositivos: {e}")
    
    def process_json_event(self, event_data: Dict[str, Any], device_ip: str):
        """Procesa evento en formato JSON"""
        try:
            # Agregar metadata
            event_data['_device_ip'] = device_ip
            event_data['_received_at'] = datetime.now().isoformat()
            event_data['_format'] = 'json'
            
            # Encolar para procesamiento
            self._enqueue_event(event_data)
            
        except Exception as e:
            self.log_error(f"Error procesando evento JSON: {e}")
    
    def process_multipart_event(self, data: bytes, content_type: str, device_ip: str):
        """Procesa evento en formato multipart (con imagen)"""
        try:
            # Extraer JSON del multipart
            json_data = self._extract_json_from_multipart(data, content_type)
            
            if json_data:
                json_data['_device_ip'] = device_ip
                json_data['_received_at'] = datetime.now().isoformat()
                json_data['_format'] = 'multipart'
                json_data['_has_image'] = True
                
                self._enqueue_event(json_data)
            else:
                self.log_error("No se pudo extraer JSON de evento multipart")
                
        except Exception as e:
            self.log_error(f"Error procesando evento multipart: {e}")
    
    def process_binary_event(self, data: bytes, device_ip: str):
        """Procesa evento en formato binario"""
        try:
            # Intentar extraer JSON de datos binarios
            json_data = self._extract_json_from_binary(data)
            
            if json_data:
                json_data['_device_ip'] = device_ip
                json_data['_received_at'] = datetime.now().isoformat()
                json_data['_format'] = 'binary'
                
                self._enqueue_event(json_data)
            else:
                # Log evento no procesable
                self.log_error(f"Evento binario no procesable de {device_ip}")
                
        except Exception as e:
            self.log_error(f"Error procesando evento binario: {e}")
    
    def _extract_json_from_multipart(self, data: bytes, content_type: str) -> Optional[Dict[str, Any]]:
        """Extrae JSON de datos multipart"""
        try:
            # Buscar boundary
            boundary = None
            if 'boundary=' in content_type:
                boundary = content_type.split('boundary=')[1].split(';')[0]
            
            if not boundary:
                # Buscar boundary en los datos
                data_start = data[:500]
                for line in data_start.split(b'\r\n'):
                    if line.startswith(b'--') and len(line) > 10:
                        boundary = line[2:].decode('ascii', errors='ignore')
                        break
            
            if boundary:
                # Dividir por boundary y buscar JSON
                parts = data.split(f'--{boundary}'.encode())
                
                for part in parts:
                    if b'application/json' in part:
                        # Extraer JSON de esta parte
                        if b'\r\n\r\n' in part:
                            headers, content = part.split(b'\r\n\r\n', 1)
                            content_str = content.decode('utf-8', errors='ignore')
                            
                            json_start = content_str.find('{')
                            json_end = content_str.rfind('}') + 1
                            
                            if json_start != -1 and json_end > json_start:
                                json_str = content_str[json_start:json_end]
                                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            self.log_error(f"Error extrayendo JSON de multipart: {e}")
            return None
    
    def _extract_json_from_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Extrae JSON de datos binarios"""
        try:
            # Buscar patrones de inicio de JSON
            json_patterns = [b'{"', b'{\r\n', b'{\n', b'{ "']
            
            start_pos = -1
            for pattern in json_patterns:
                pos = data.find(pattern)
                if pos != -1:
                    start_pos = pos
                    break
            
            if start_pos == -1:
                return None
            
            # Extraer JSON balanceando llaves
            json_data = data[start_pos:]
            brace_count = 0
            end_pos = -1
            in_string = False
            escape_next = False
            
            for i, byte in enumerate(json_data):
                if byte > 127:  # Skip non-ASCII
                    continue
                    
                char = chr(byte)
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"':
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
            
            if end_pos > 0:
                json_bytes = json_data[:end_pos]
                json_str = json_bytes.decode('utf-8', errors='replace')
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            self.log_error(f"Error extrayendo JSON de binario: {e}")
            return None
    
    def _enqueue_event(self, event_data: Dict[str, Any]):
        """Encola evento para procesamiento"""
        try:
            self.event_queue.put_nowait(event_data)
            self.stats['events_received'] += 1
            
        except queue.Full:
            self.stats['events_dropped'] += 1
            self.log_error("Cola de eventos llena, descartando evento")
    
    def _process_events_loop(self):
        """Loop principal de procesamiento de eventos"""
        logging.info("🔄 Procesador de eventos iniciado")
        
        while self.is_running:
            try:
                # Procesar eventos en lotes
                events_batch = []
                
                # Recoger lote de eventos
                for _ in range(self.batch_size):
                    try:
                        event = self.event_queue.get(timeout=1.0)
                        events_batch.append(event)
                    except queue.Empty:
                        break
                
                # Procesar lote si hay eventos
                if events_batch:
                    self._process_events_batch(events_batch)
                
            except Exception as e:
                self.log_error(f"Error en loop de procesamiento: {e}")
                time.sleep(1)
        
        logging.info("🔄 Procesador de eventos finalizado")
    
    def _process_events_batch(self, events: List[Dict[str, Any]]):
        """Procesa un lote de eventos"""
        for event in events:
            try:
                self._process_single_event(event)
                self.stats['events_processed'] += 1
                
            except Exception as e:
                self.stats['events_errors'] += 1
                self.log_error(f"Error procesando evento: {e}")
    
    def _process_single_event(self, event_data: Dict[str, Any]):
        """Procesa un evento individual"""
        try:
            device_ip = event_data.get('_device_ip')
            
            # Identificar tipo de evento
            if 'AccessControllerEvent' in event_data:
                self._process_access_control_event(event_data)
            elif 'eventType' in event_data:
                self._process_generic_event(event_data)
            else:
                logging.debug(f"Evento no reconocido de {device_ip}")
            
            # Distribuir a callbacks registrados
            self._distribute_event(event_data)
            
        except Exception as e:
            self.log_error(f"Error procesando evento individual: {e}")
    
    def _process_access_control_event(self, event_data: Dict[str, Any]):
        """Procesa evento específico de control de acceso"""
        try:
            acc_event = event_data['AccessControllerEvent']
            device_ip = event_data.get('_device_ip')
            
            # Extraer información del evento
            major_type = acc_event.get('majorEventType', 0)
            minor_type = acc_event.get('subEventType', 0)
            
            # Solo procesar eventos de reconocimiento facial (5-75, 5-76)
            if major_type == 5 and minor_type in [75, 76]:
                
                processed_event = {
                    'device_ip': device_ip,
                    'event_type': 'ACCESS_CONTROL',
                    'event_code': f"{major_type}-{minor_type}",
                    'person_id': acc_event.get('employeeNoString', ''),
                    'employee_no': acc_event.get('employeeNoString', ''),
                    'person_name': acc_event.get('name', ''),
                    'verify_mode': acc_event.get('currentVerifyMode', ''),
                    'access_result': 'SUCCESS' if minor_type == 75 else 'FAILED',
                    'event_time': event_data.get('dateTime', datetime.now().isoformat()),
                    'raw_data': json.dumps(event_data)
                }
                
                # Guardar en base de datos
                self._save_event_to_database(processed_event)
                
                # Log del evento
                device_name = self._get_device_name(device_ip)
                status_emoji = "✅" if minor_type == 75 else "❌"
                
                logging.info(f"{status_emoji} Evento facial - {device_name} ({device_ip}) - "
                           f"Usuario: {processed_event['person_name']} ({processed_event['employee_no']}) - "
                           f"Resultado: {processed_event['access_result']}")
            
        except Exception as e:
            self.