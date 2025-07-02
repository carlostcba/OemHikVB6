#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Manager para Facial Sync Service
Maneja comunicación con dispositivos Hikvision para sincronización facial
"""

import requests
import logging
import time
import json
import base64
from typing import Dict, List, Tuple, Any, Optional
from requests.auth import HTTPDigestAuth
import urllib3
from datetime import datetime
import threading
import os

# Deshabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DeviceManager:
    """Gestor de dispositivos Hikvision"""
    
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config
        
        # Configuración de timeouts
        self.timeout = config.get('DEVICE_TIMEOUT', 10)
        self.retry_count = config.get('DEVICE_RETRY_COUNT', 2)
        
        # Cache de sesiones por dispositivo
        self.device_sessions = {}
        self.session_lock = threading.Lock()
        
        # Configuración Hikvision
        self.hik_config = config.get_hikvision_config()
        
        logging.info("DeviceManager inicializado")
    
    def get_device_session(self, device: Dict[str, Any]) -> requests.Session:
        """Obtiene o crea sesión HTTP para un dispositivo"""
        device_id = device['dispositivo_id']
        
        with self.session_lock:
            if device_id not in self.device_sessions:
                session = requests.Session()
                session.auth = HTTPDigestAuth(
                    device['usuario'], 
                    device['password']
                )
                session.headers.update({
                    'User-Agent': 'FacialSyncService/1.0',
                    'Accept': 'application/json, application/xml',
                    'Connection': 'keep-alive'
                })
                session.verify = False
                
                self.device_sessions[device_id] = session
                logging.debug(f"Nueva sesión creada para dispositivo {device_id}")
            
            return self.device_sessions[device_id]
    
    def test_device_connection(self, device: Dict[str, Any]) -> Tuple[bool, str]:
        """Prueba conexión a un dispositivo Hikvision"""
        try:
            session = self.get_device_session(device)
            
            # Probar con puerto SVR primero, luego HTTP
            ports_to_try = [
                device.get('puerto_svr', 8000),
                device.get('puerto_http', 80)
            ]
            
            for port in ports_to_try:
                url = f"http://{device['ip']}:{port}/ISAPI/System/deviceInfo"
                
                try:
                    response = session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        # Actualizar estado en BD
                        self.db_manager.update_device_status(
                            device['dispositivo_id'], 
                            True, 
                            None
                        )
                        return True, f"Conexión exitosa en puerto {port}"
                        
                except requests.exceptions.RequestException as e:
                    logging.debug(f"Error en puerto {port}: {e}")
                    continue
            
            # Si llegamos aquí, todos los puertos fallaron
            error_msg = f"No se pudo conectar en puertos {ports_to_try}"
            self.db_manager.update_device_status(
                device['dispositivo_id'], 
                False, 
                error_msg
            )
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Error de conexión: {str(e)}"
            logging.error(f"Error probando dispositivo {device['dispositivo_id']}: {e}")
            
            self.db_manager.update_device_status(
                device['dispositivo_id'], 
                False, 
                error_msg
            )
            return False, error_msg
    
    def ensure_face_library_exists(self, device: Dict[str, Any]) -> Tuple[bool, str, str]:
        """Verifica y crea biblioteca facial por defecto si no existe"""
        try:
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            # Verificar bibliotecas existentes
            url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib?format=json"
            response = session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                libraries = data.get('FPLibListInfo', {}).get('FPLib', [])
                
                # Buscar biblioteca blackFD
                for lib in libraries:
                    if lib.get('faceLibType') == 'blackFD':
                        fdid = lib.get('FDID', '1')
                        logging.debug(f"Biblioteca facial encontrada: {fdid}")
                        return True, fdid, "Biblioteca existente encontrada"
            
            # Si no existe, crear biblioteca por defecto
            logging.info(f"Creando biblioteca facial en dispositivo {device['dispositivo_id']}")
            
            create_data = {
                "FPLibInfo": {
                    "faceLibType": "blackFD",
                    "name": "FacialSyncService Library",
                    "customInfo": "Biblioteca creada por FacialSyncService",
                    "libArmingType": "armingLib"
                }
            }
            
            response = session.post(url, json=create_data, timeout=self.timeout)
            if response.status_code in [200, 201]:
                result = response.json()
                fdid = result.get('FPLibInfo', {}).get('FDID', '1')
                logging.info(f"Biblioteca facial creada: {fdid}")
                return True, fdid, "Biblioteca creada correctamente"
            else:
                # Usar ID por defecto si falla
                logging.warning(f"Error creando biblioteca, usando ID por defecto")
                return True, '1', "Usando biblioteca por defecto"
                
        except Exception as e:
            logging.error(f"Error verificando biblioteca facial: {e}")
            return True, '1', f"Error: {e} - Usando biblioteca por defecto"
    
    def upload_face_to_device(self, device: Dict[str, Any], facial_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Sube imagen facial a un dispositivo Hikvision"""
        try:
            # Verificar biblioteca facial
            lib_success, fdid, lib_msg = self.ensure_face_library_exists(device)
            if not lib_success:
                return False, f"Error en biblioteca facial: {lib_msg}"
            
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
            
            # Preparar metadata
            face_data = {
                "faceLibType": "blackFD",
                "FDID": fdid,
                "FPID": str(facial_data['facial_id']),
                "name": f"{facial_data.get('nombre', '')} {facial_data.get('apellido', '')}".strip() or f"User_{facial_data['facial_id']}"
            }
            
            # Obtener imagen binaria
            image_data = facial_data.get('template_data')
            if not image_data:
                return False, "No hay datos de imagen"
            
            # Crear multipart manualmente
            boundary = '---------------------------FacialSyncService'
            
            body = f'--{boundary}\r\n'
            body += 'Content-Disposition: form-data; name="FaceDataRecord"\r\n'
            body += 'Content-Type: application/json\r\n'
            body += f'Content-Length: {len(json.dumps(face_data))}\r\n'
            body += '\r\n'
            body += json.dumps(face_data)
            body += f'\r\n--{boundary}\r\n'
            body += 'Content-Disposition: form-data; name="FaceImage"\r\n'
            body += 'Content-Type: image/jpeg\r\n'
            body += f'Content-Length: {len(image_data)}\r\n'
            body += '\r\n'
            
            # Convertir a bytes y agregar imagen
            body_bytes = body.encode('utf-8') + image_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
            
            headers = {
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body_bytes))
            }
            
            # Enviar request
            response = session.post(url, data=body_bytes, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                logging.info(f"✅ Rostro {facial_data['facial_id']} subido a {device['dispositivo_id']}")
                return True, "Imagen facial subida correctamente"
            else:
                error_msg = f"Error HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if 'statusString' in error_data:
                        error_msg += f": {error_data['statusString']}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                logging.error(f"❌ Error subiendo rostro a {device['dispositivo_id']}: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Excepción subiendo rostro: {str(e)}"
            logging.error(f"❌ {error_msg}")
            return False, error_msg
    
    def update_face_on_device(self, device: Dict[str, Any], facial_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Actualiza imagen facial en un dispositivo"""
        # Para Hikvision, actualizar es igual que crear (sobrescribe)
        return self.upload_face_to_device(device, facial_data)
    
    def delete_face_from_device(self, device: Dict[str, Any], facial_id: int) -> Tuple[bool, str]:
        """Elimina imagen facial de un dispositivo"""
        try:
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            # Primero obtener FDID de la biblioteca
            _, fdid, _ = self.ensure_face_library_exists(device)
            
            # URL para eliminar cara específica
            url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib/FaceDataRecord/Delete?format=json&FDID={fdid}&FPID={facial_id}"
            
            response = session.put(url, timeout=self.timeout)
            
            if response.status_code in [200, 201]:
                logging.info(f"✅ Rostro {facial_id} eliminado de {device['dispositivo_id']}")
                return True, "Rostro eliminado correctamente"
            else:
                error_msg = f"Error HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if 'statusString' in error_data:
                        error_msg += f": {error_data['statusString']}"
                except:
                    pass
                
                logging.warning(f"⚠️ Error eliminando rostro de {device['dispositivo_id']}: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Excepción eliminando rostro: {str(e)}"
            logging.error(f"❌ {error_msg}")
            return False, error_msg
    
    def sync_face_to_all_devices(self, facial_data: Dict[str, Any], action: str = 'create') -> Dict[str, Any]:
        """Sincroniza rostro facial con todos los dispositivos activos"""
        results = {
            'total_devices': 0,
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        try:
            # Obtener dispositivos activos
            devices = self.db_manager.get_active_devices()
            results['total_devices'] = len(devices)
            
            if not devices:
                logging.warning("No hay dispositivos activos para sincronizar")
                return results
            
            logging.info(f"🔄 Sincronizando rostro {facial_data['facial_id']} - Acción: {action} - Dispositivos: {len(devices)}")
            
            for device in devices:
                device_result = {
                    'device_id': device['dispositivo_id'],
                    'device_name': device['nombre'],
                    'device_ip': device['ip'],
                    'success': False,
                    'message': '',
                    'timestamp': datetime.now().isoformat()
                }
                
                try:
                    # Ejecutar acción según tipo
                    if action.lower() == 'create':
                        success, message = self.upload_face_to_device(device, facial_data)
                    elif action.lower() == 'update':
                        success, message = self.update_face_on_device(device, facial_data)
                    elif action.lower() == 'delete':
                        success, message = self.delete_face_from_device(device, facial_data['facial_id'])
                    else:
                        success, message = False, f"Acción desconocida: {action}"
                    
                    device_result['success'] = success
                    device_result['message'] = message
                    
                    if success:
                        results['successful'] += 1
                        # Actualizar estado del dispositivo como online
                        self.db_manager.update_device_status(device['dispositivo_id'], True, None)
                    else:
                        results['failed'] += 1
                        # Actualizar estado del dispositivo con error
                        self.db_manager.update_device_status(device['dispositivo_id'], False, message)
                    
                except Exception as e:
                    device_result['success'] = False
                    device_result['message'] = f"Excepción: {str(e)}"
                    results['failed'] += 1
                    
                    logging.error(f"Error sincronizando con {device['dispositivo_id']}: {e}")
                    self.db_manager.update_device_status(device['dispositivo_id'], False, str(e))
                
                results['details'].append(device_result)
                
                # Pausa breve entre dispositivos para no saturar
                time.sleep(0.5)
            
            # Log resumen
            success_rate = (results['successful'] / results['total_devices']) * 100 if results['total_devices'] > 0 else 0
            logging.info(f"📊 Sincronización completada - Éxito: {results['successful']}/{results['total_devices']} ({success_rate:.1f}%)")
            
        except Exception as e:
            logging.error(f"Error en sincronización masiva: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_device_face_count(self, device: Dict[str, Any]) -> Tuple[bool, int, str]:
        """Obtiene el número de rostros almacenados en un dispositivo"""
        try:
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            # Obtener información de la biblioteca facial
            url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib?format=json"
            response = session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                libraries = data.get('FPLibListInfo', {}).get('FPLib', [])
                
                total_faces = 0
                for lib in libraries:
                    if lib.get('faceLibType') == 'blackFD':
                        # Obtener número de rostros en esta biblioteca
                        fdid = lib.get('FDID', '1')
                        count_url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib/FaceDataRecord/Count?format=json&FDID={fdid}"
                        
                        count_response = session.get(count_url, timeout=self.timeout)
                        if count_response.status_code == 200:
                            count_data = count_response.json()
                            face_count = count_data.get('numOfMatches', 0)
                            total_faces += face_count
                
                return True, total_faces, "Conteo exitoso"
            else:
                return False, 0, f"Error HTTP {response.status_code}"
                
        except Exception as e:
            logging.error(f"Error obteniendo conteo de rostros de {device['dispositivo_id']}: {e}")
            return False, 0, str(e)
    
    def ping_all_devices(self) -> Dict[str, Any]:
        """Verifica conectividad de todos los dispositivos"""
        results = {
            'total_devices': 0,
            'online': 0,
            'offline': 0,
            'devices': []
        }
        
        try:
            devices = self.db_manager.get_active_devices()
            results['total_devices'] = len(devices)
            
            logging.info(f"🏓 Verificando conectividad de {len(devices)} dispositivos...")
            
            for device in devices:
                device_status = {
                    'device_id': device['dispositivo_id'],
                    'device_name': device['nombre'],
                    'device_ip': device['ip'],
                    'online': False,
                    'response_time': None,
                    'message': '',
                    'face_count': 0
                }
                
                start_time = time.time()
                success, message = self.test_device_connection(device)
                response_time = (time.time() - start_time) * 1000  # en ms
                
                device_status['online'] = success
                device_status['response_time'] = round(response_time, 2)
                device_status['message'] = message
                
                if success:
                    results['online'] += 1
                    # Obtener conteo de rostros si está online
                    face_success, face_count, face_msg = self.get_device_face_count(device)
                    if face_success:
                        device_status['face_count'] = face_count
                        # Actualizar conteo en BD
                        self.db_manager.update_device_status(
                            device['dispositivo_id'], 
                            True, 
                            None, 
                            face_count
                        )
                else:
                    results['offline'] += 1
                
                results['devices'].append(device_status)
            
            # Log resumen
            online_percentage = (results['online'] / results['total_devices']) * 100 if results['total_devices'] > 0 else 0
            logging.info(f"📡 Ping completado - Online: {results['online']}/{results['total_devices']} ({online_percentage:.1f}%)")
            
        except Exception as e:
            logging.error(f"Error en ping masivo: {e}")
            results['error'] = str(e)
        
        return results
    
    def configure_event_notification(self, device: Dict[str, Any], callback_url: str) -> Tuple[bool, str]:
        """Configura notificación de eventos en un dispositivo"""
        try:
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            # Configurar notificación HTTP
            url = f"http://{device['ip']}:{port}/ISAPI/Event/notification/httpHosts"
            
            config_data = {
                "HttpHostNotificationList": {
                    "HttpHostNotification": [{
                        "id": "1",
                        "url": callback_url,
                        "protocolType": "HTTP",
                        "parameterFormatType": "JSON",
                        "addressingFormatType": "ipaddress",
                        "httpAuthenticationMethod": "none"
                    }]
                }
            }
            
            response = session.put(url, json=config_data, timeout=self.timeout)
            
            if response.status_code in [200, 201]:
                # Activar eventos de control de acceso
                event_url = f"http://{device['ip']}:{port}/ISAPI/Event/triggers/AccessControllerEvent"
                
                event_config = {
                    "AccessControllerEventTrigger": {
                        "enabled": True,
                        "eventType": "AccessControllerEvent"
                    }
                }
                
                event_response = session.put(event_url, json=event_config, timeout=self.timeout)
                
                if event_response.status_code in [200, 201]:
                    return True, "Eventos configurados correctamente"
                else:
                    return False, f"Error configurando eventos: {event_response.status_code}"
            else:
                return False, f"Error configurando notificación: {response.status_code}"
                
        except Exception as e:
            return False, f"Error configurando eventos: {str(e)}"
    
    def get_device_info(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene información detallada de un dispositivo"""
        try:
            session = self.get_device_session(device)
            port = device.get('puerto_svr', 8000)
            
            # Información básica del dispositivo
            info_url = f"http://{device['ip']}:{port}/ISAPI/System/deviceInfo"
            response = session.get(info_url, timeout=self.timeout)
            
            device_info = {
                'device_id': device['dispositivo_id'],
                'name': device['nombre'],
                'ip': device['ip'],
                'model': device.get('modelo', 'Unknown'),
                'type': device.get('tipo', 'Unknown'),
                'online': False,
                'device_info': {},
                'capabilities': {},
                'face_libraries': []
            }
            
            if response.status_code == 200:
                device_info['online'] = True
                try:
                    device_info['device_info'] = response.json()
                except:
                    pass
                
                # Obtener capacidades
                try:
                    cap_url = f"http://{device['ip']}:{port}/ISAPI/System/capabilities"
                    cap_response = session.get(cap_url, timeout=self.timeout)
                    if cap_response.status_code == 200:
                        device_info['capabilities'] = cap_response.json()
                except:
                    pass
                
                # Obtener bibliotecas faciales
                try:
                    lib_url = f"http://{device['ip']}:{port}/ISAPI/Intelligent/FDLib?format=json"
                    lib_response = session.get(lib_url, timeout=self.timeout)
                    if lib_response.status_code == 200:
                        lib_data = lib_response.json()
                        device_info['face_libraries'] = lib_data.get('FPLibListInfo', {}).get('FPLib', [])
                except:
                    pass
            
            return device_info
            
        except Exception as e:
            logging.error(f"Error obteniendo info de dispositivo {device['dispositivo_id']}: {e}")
            return {
                'device_id': device['dispositivo_id'],
                'error': str(e),
                'online': False
            }
    
    def cleanup_sessions(self):
        """Limpia sesiones HTTP no utilizadas"""
        with self.session_lock:
            for device_id, session in list(self.device_sessions.items()):
                try:
                    session.close()
                except:
                    pass
                del self.device_sessions[device_id]
            
            logging.info("Sesiones HTTP limpiadas")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del gestor de dispositivos"""
        try:
            devices = self.db_manager.get_active_devices()
            device_status = self.db_manager.get_device_status()
            
            stats = {
                'total_devices': len(devices),
                'active_sessions': len(self.device_sessions),
                'online_devices': len([d for d in device_status if d.get('is_online')]),
                'offline_devices': len([d for d in device_status if not d.get('is_online')]),
                'total_faces': sum([d.get('face_count', 0) for d in device_status]),
                'device_types': {}
            }
            
            # Contar por tipos
            for device in devices:
                device_type = device.get('tipo', 'Unknown')
                stats['device_types'][device_type] = stats['device_types'].get(device_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logging.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

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
    
    # Crear device manager
    device_manager = DeviceManager(db_manager, config)
    
    print("Device Manager iniciado")
    print("Comandos disponibles:")
    print("  ping - Verificar conectividad de dispositivos")
    print("  stats - Mostrar estadísticas")
    print("  devices - Listar dispositivos")
    print("  test <device_id> - Probar dispositivo específico")
    print("  quit - Salir")
    
    try:
        while True:
            try:
                command = input("\ndevice> ").strip().split()
                
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == "ping":
                    print("Verificando conectividad...")
                    results = device_manager.ping_all_devices()
                    print(f"Dispositivos: {results['online']}/{results['total_devices']} online")
                    for device in results['devices']:
                        status = "🟢" if device['online'] else "🔴"
                        print(f"  {status} {device['device_name']} ({device['device_ip']}) - {device['response_time']}ms")
                
                elif cmd == "stats":
                    stats = device_manager.get_statistics()
                    print("Estadísticas:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                
                elif cmd == "devices":
                    devices = db_manager.get_active_devices()
                    print(f"Dispositivos activos: {len(devices)}")
                    for device in devices:
                        print(f"  {device['dispositivo_id']}: {device['nombre']} ({device['ip']})")
                
                elif cmd == "test" and len(command) > 1:
                    device_id = command[1]
                    devices = db_manager.get_active_devices()
                    device = next((d for d in devices if d['dispositivo_id'] == device_id), None)
                    
                    if device:
                        print(f"Probando dispositivo {device_id}...")
                        success, message = device_manager.test_device_connection(device)
                        print(f"Resultado: {'✅' if success else '❌'} {message}")
                    else:
                        print(f"Dispositivo {device_id} no encontrado")
                
                elif cmd in ["quit", "exit"]:
                    break
                
                elif cmd == "help":
                    print("Comandos: ping, stats, devices, test <device_id>, quit")
                
                else:
                    print(f"Comando desconocido: {cmd}")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    except KeyboardInterrupt:
        pass
    finally:
        print("\nCerrando Device Manager...")
        device_manager.cleanup_sessions()

if __name__ == "__main__":
    main()