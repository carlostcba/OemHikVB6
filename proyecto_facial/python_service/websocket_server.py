#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Server para Facial Sync Service
Envía eventos de acceso en tiempo real a clientes (como VB6)
"""

import asyncio
import websockets
import json
import logging
import threading
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional
import queue

class WebSocketServer:
    """Servidor WebSocket para eventos en tiempo real"""
    
    def __init__(self, event_processor, config):
        self.event_processor = event_processor
        self.config = config
        
        # Configuración
        self.host = config.get('WEBSOCKET_HOST', '0.0.0.0')
        self.port = config.get('WEBSOCKET_PORT', 8765)
        
        # Estado del servidor
        self.is_running = False
        self.server = None
        self.server_thread = None
        self.loop = None
        
        # Clientes conectados
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_info: Dict[websockets.WebSocketServerProtocol, Dict] = {}
        
        # Cola de eventos para enviar
        self.event_queue = queue.Queue(maxsize=config.get('EVENT_BUFFER_SIZE', 1000))
        
        # Estadísticas
        self.stats = {
            'total_connections': 0,
            'current_connections': 0,
            'events_sent': 0,
            'errors': 0,
            'start_time': None
        }
    
    def start(self):
        """Inicia el servidor WebSocket"""
        if self.is_running:
            logging.warning("WebSocket Server ya está ejecutándose")
            return
        
        try:
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            logging.info(f"🚀 Iniciando WebSocket Server en {self.host}:{self.port}")
            
            # Crear thread para el servidor asyncio
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            # Esperar un momento para que inicie
            time.sleep(1)
            
            logging.info(f"✅ WebSocket Server activo en ws://{self.host}:{self.port}")
            
        except Exception as e:
            self.is_running = False
            logging.error(f"❌ Error iniciando WebSocket Server: {e}")
            raise
    
    def stop(self):
        """Detiene el servidor WebSocket"""
        if not self.is_running:
            return
        
        try:
            logging.info("🛑 Deteniendo WebSocket Server...")
            self.is_running = False
            
            # Cerrar servidor si existe
            if self.loop and self.server:
                asyncio.run_coroutine_threadsafe(self.server.close(), self.loop)
            
            # Esperar thread
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logging.info("✅ WebSocket Server detenido")
            
        except Exception as e:
            logging.error(f"❌ Error deteniendo WebSocket Server: {e}")
    
    def _run_server(self):
        """Ejecuta el servidor asyncio en thread separado"""
        try:
            # Crear nuevo loop para este thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Iniciar servidor
            start_server = websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.server = self.loop.run_until_complete(start_server)
            
            # Ejecutar loop hasta que se detenga
            self.loop.run_forever()
            
        except Exception as e:
            logging.error(f"Error en loop del WebSocket Server: {e}")
        finally:
            if self.loop:
                self.loop.close()
    
    async def _handle_client(self, websocket, path):
        """Maneja conexión de un cliente WebSocket"""
        client_info = {
            'connected_at': datetime.now(),
            'remote_address': websocket.remote_address,
            'path': path,
            'events_sent': 0
        }
        
        self.clients.add(websocket)
        self.client_info[websocket] = client_info
        self.stats['total_connections'] += 1
        self.stats['current_connections'] += 1
        
        logging.info(f"🔌 Cliente WebSocket conectado: {websocket.remote_address}")
        
        try:
            # Enviar mensaje de bienvenida
            welcome_msg = {
                'type': 'welcome',
                'message': 'Conectado a Facial Sync Service',
                'server_time': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Mantener conexión y procesar mensajes
            async for message in websocket:
                await self._process_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"🔌 Cliente WebSocket desconectado: {websocket.remote_address}")
        except Exception as e:
            logging.error(f"Error manejando cliente WebSocket: {e}")
            self.stats['errors'] += 1
        finally:
            # Limpiar cliente
            self.clients.discard(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]
            self.stats['current_connections'] -= 1
    
    async def _process_client_message(self, websocket, message):
        """Procesa mensaje recibido de un cliente"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')
            
            if msg_type == 'ping':
                # Responder pong
                pong_msg = {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }
                await websocket.send(json.dumps(pong_msg))
            
            elif msg_type == 'subscribe':
                # Cliente se suscribe a tipos específicos de eventos
                event_types = data.get('event_types', [])
                self.client_info[websocket]['subscriptions'] = event_types
                
                response = {
                    'type': 'subscription_confirmed',
                    'event_types': event_types
                }
                await websocket.send(json.dumps(response))
            
            elif msg_type == 'get_stats':
                # Enviar estadísticas del servidor
                stats_msg = {
                    'type': 'stats',
                    'data': self.get_stats()
                }
                await websocket.send(json.dumps(stats_msg))
            
            else:
                logging.warning(f"Tipo de mensaje desconocido: {msg_type}")
                
        except json.JSONDecodeError:
            logging.error("Mensaje WebSocket con formato JSON inválido")
        except Exception as e:
            logging.error(f"Error procesando mensaje WebSocket: {e}")
    
    def broadcast_event(self, event_data: Dict[str, Any]):
        """Envía evento a todos los clientes conectados"""
        if not self.is_running or not self.clients:
            return
        
        try:
            # Formatear evento para WebSocket
            ws_event = self._format_event_for_websocket(event_data)
            
            # Enviar a todos los clientes
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_to_all_clients(ws_event),
                    self.loop
                )
                
        except Exception as e:
            logging.error(f"Error broadcasting evento: {e}")
    
    def send_event_to_vb6(self, event_data: Dict[str, Any]):
        """Envía evento en formato texto plano para VB6"""
        if not self.is_running or not self.clients:
            return
        
        try:
            # Formato especial para VB6: "EVENTO|TIMESTAMP|DEVICE_IP|USER_ID|STATUS|NAME"
            vb6_text = self._format_event_for_vb6(event_data)
            
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_text_to_vb6_clients(vb6_text),
                    self.loop
                )
                
        except Exception as e:
            logging.error(f"Error enviando evento a VB6: {e}")
    
    def _format_event_for_websocket(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea evento para envío vía WebSocket JSON"""
        return {
            'type': 'access_event',
            'timestamp': datetime.now().isoformat(),
            'device_ip': event_data.get('device_ip', ''),
            'event_type': event_data.get('event_type', ''),
            'event_code': event_data.get('event_code', ''),
            'person_id': event_data.get('person_id', ''),
            'employee_no': event_data.get('employee_no', ''),
            'person_name': event_data.get('person_name', ''),
            'verify_mode': event_data.get('verify_mode', ''),
            'access_result': event_data.get('access_result', ''),
            'event_time': event_data.get('event_time', ''),
            'source': 'facial_sync_service'
        }
    
    def _format_event_for_vb6(self, event_data: Dict[str, Any]) -> str:
        """Formatea evento como texto plano para VB6"""
        # Formato: "EVENTO|TIMESTAMP|DEVICE_IP|USER_ID|STATUS|NAME"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        device_ip = event_data.get('device_ip', 'UNKNOWN')
        user_id = event_data.get('employee_no', event_data.get('person_id', ''))
        status = event_data.get('access_result', 'UNKNOWN')
        name = event_data.get('person_name', 'UNKNOWN')
        event_type = event_data.get('event_type', 'ACCESS')
        
        return f"{event_type}|{timestamp}|{device_ip}|{user_id}|{status}|{name}"
    
    async def _send_to_all_clients(self, event_data: Dict[str, Any]):
        """Envía evento JSON a todos los clientes conectados"""
        if not self.clients:
            return
        
        message = json.dumps(event_data)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message)
                self.client_info[client]['events_sent'] += 1
                self.stats['events_sent'] += 1
                
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logging.error(f"Error enviando evento a cliente: {e}")
                disconnected_clients.add(client)
        
        # Limpiar clientes desconectados
        for client in disconnected_clients:
            self.clients.discard(client)
            if client in self.client_info:
                del self.client_info[client]
            self.stats['current_connections'] -= 1
    
    async def _send_text_to_vb6_clients(self, text_message: str):
        """Envía mensaje de texto a clientes que pueden ser VB6"""
        if not self.clients:
            return
        
        # Enviar como mensaje de texto simple
        vb6_event = {
            'type': 'vb6_event',
            'text': text_message,
            'timestamp': datetime.now().isoformat()
        }
        
        message = json.dumps(vb6_event)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message)
                self.client_info[client]['events_sent'] += 1
                self.stats['events_sent'] += 1
                
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logging.error(f"Error enviando texto a cliente VB6: {e}")
                disconnected_clients.add(client)
        
        # Limpiar clientes desconectados
        for client in disconnected_clients:
            self.clients.discard(client)
            if client in self.client_info:
                del self.client_info[client]
            self.stats['current_connections'] -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servidor WebSocket"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'current_connections': self.stats['current_connections'],
            'total_connections': self.stats['total_connections'],
            'events_sent': self.stats['events_sent'],
            'errors': self.stats['errors'],
            'uptime_seconds': uptime,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None
        }
    
    def get_client_info(self) -> list:
        """Obtiene información de clientes conectados"""
        clients = []
        
        for client, info in self.client_info.items():
            client_data = {
                'remote_address': str(info['remote_address']),
                'connected_at': info['connected_at'].isoformat(),
                'path': info['path'],
                'events_sent': info['events_sent'],
                'subscriptions': info.get('subscriptions', [])
            }
            clients.append(client_data)
        
        return clients
    
    def simulate_event(self, event_type: str = 'FACE_SUCCESS'):
        """Simula un evento para testing"""
        test_event = {
            'device_ip': '192.168.1.100',
            'event_type': 'ACCESS_CONTROL',
            'event_code': '5-75' if event_type == 'FACE_SUCCESS' else '5-76',
            'person_id': '123',
            'employee_no': 'EMP001',
            'person_name': 'Usuario Prueba',
            'verify_mode': 'Face',
            'access_result': 'SUCCESS' if event_type == 'FACE_SUCCESS' else 'FAILED',
            'event_time': datetime.now().isoformat()
        }
        
        # Enviar por ambos canales
        self.broadcast_event(test_event)
        self.send_event_to_vb6(test_event)
        
        logging.info(f"📡 Evento simulado enviado: {event_type}")

def main():
    """Función principal para testing"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from config import get_config
    
    # Configuración de prueba
    config = get_config()
    config.initialize()
    
    # Crear servidor WebSocket
    ws_server = WebSocketServer(None, config)
    
    try:
        ws_server.start()
        print(f"WebSocket Server ejecutándose en ws://localhost:{config.get('WEBSOCKET_PORT')}")
        print("Comandos disponibles:")
        print("  simulate - Simular evento de acceso")
        print("  stats - Mostrar estadísticas")
        print("  clients - Mostrar clientes conectados")
        print("  quit - Salir")
        
        while True:
            try:
                command = input("\nws> ").strip().lower()
                
                if command == "simulate":
                    ws_server.simulate_event('FACE_SUCCESS')
                    print("Evento simulado enviado")
                
                elif command == "stats":
                    stats = ws_server.get_stats()
                    print("Estadísticas del servidor:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                
                elif command == "clients":
                    clients = ws_server.get_client_info()
                    print(f"Clientes conectados: {len(clients)}")
                    for i, client in enumerate(clients, 1):
                        print(f"  {i}. {client['remote_address']} - {client['events_sent']} eventos")
                
                elif command in ["quit", "exit"]:
                    break
                
                elif command == "help":
                    print("Comandos: simulate, stats, clients, quit")
                
                elif command:
                    print(f"Comando desconocido: {command}")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    except KeyboardInterrupt:
        pass
    finally:
        print("\nDeteniendo WebSocket Server...")
        ws_server.stop()

if __name__ == "__main__":
    main()