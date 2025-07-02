#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facial Sync Service - Punto de Entrada Principal
Orquestador del servicio de sincronización facial Hikvision
"""

import sys
import os
import logging
import threading
import time
import signal
import tkinter as tk
from pathlib import Path

# Agregar directorio actual al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports del servicio
from config import get_config
from database_manager import DatabaseManager
from tray_service import TrayService
from api_server import APIServer
from websocket_server import WebSocketServer
from device_manager import DeviceManager
from task_queue import TaskQueue
from workers.sync_worker import SyncWorker
from workers.health_worker import HealthWorker
from event_processor import EventProcessor

class FacialSyncService:
    """Servicio principal de sincronización facial"""
    
    def __init__(self):
        self.config = get_config()
        self.is_running = False
        self.is_stopping = False
        
        # Componentes del servicio
        self.db_manager = None
        self.api_server = None
        self.websocket_server = None
        self.device_manager = None
        self.task_queue = None
        self.sync_worker = None
        self.health_worker = None
        self.event_processor = None
        self.tray_service = None
        
        # Threads
        self.threads = []
        
        # Configurar señales para cierre limpio
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configura manejadores de señales para cierre limpio"""
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            if hasattr(signal, 'SIGBREAK'):  # Windows
                signal.signal(signal.SIGBREAK, self.signal_handler)
        except Exception as e:
            logging.warning(f"Error configurando señales: {e}")
    
    def signal_handler(self, signum, frame):
        """Maneja señales de cierre del sistema"""
        logging.info(f"Señal recibida: {signum}. Iniciando cierre limpio...")
        self.stop()
    
    def initialize(self):
        """Inicializa todos los componentes del servicio"""
        try:
            logging.info("=== Iniciando Facial Sync Service ===")
            
            # Validar configuración
            is_valid, errors = self.config.validate_config()
            if not is_valid:
                for error in errors:
                    logging.error(f"Error de configuración: {error}")
                raise Exception("Configuración inválida")
            
            # Inicializar base de datos
            self.init_database()
            
            # Inicializar configuración con BD
            self.config.initialize(self.db_manager)
            
            # Inicializar componentes core
            self.init_components()
            
            logging.info("Todos los componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logging.error(f"Error inicializando servicio: {e}")
            return False
    
    def init_database(self):
        """Inicializa el gestor de base de datos"""
        try:
            udl_path = self.config.get('DB_UDL_PATH')
            logging.info(f"Inicializando base de datos: {udl_path}")
            
            self.db_manager = DatabaseManager(udl_path)
            
            # Probar conexión
            if not self.db_manager.test_connection():
                raise Exception("No se pudo conectar a la base de datos")
            
            logging.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            logging.error(f"Error inicializando base de datos: {e}")
            raise
    
    def init_components(self):
        """Inicializa todos los componentes del servicio"""
        try:
            # Task Queue (debe ser primero)
            self.task_queue = TaskQueue(self.db_manager, self.config)
            logging.info("TaskQueue inicializado")
            
            # Device Manager
            self.device_manager = DeviceManager(self.db_manager, self.config)
            logging.info("DeviceManager inicializado")
            
            # Event Processor
            self.event_processor = EventProcessor(self.db_manager, self.config)
            logging.info("EventProcessor inicializado")
            
            # API Server
            self.api_server = APIServer(
                self.db_manager, 
                self.device_manager, 
                self.task_queue, 
                self.config
            )
            logging.info("APIServer inicializado")
            
            # WebSocket Server
            if self.config.get('WEBSOCKET_ENABLED'):
                self.websocket_server = WebSocketServer(
                    self.event_processor, 
                    self.config
                )
                logging.info("WebSocketServer inicializado")
            
            # Workers
            self.sync_worker = SyncWorker(
                self.db_manager,
                self.device_manager,
                self.task_queue,
                self.config
            )
            logging.info("SyncWorker inicializado")
            
            self.health_worker = HealthWorker(
                self.db_manager,
                self.device_manager,
                self.config
            )
            logging.info("HealthWorker inicializado")
            
            # Tray Service
            self.tray_service = TrayService(self)
            logging.info("TrayService inicializado")
            
        except Exception as e:
            logging.error(f"Error inicializando componentes: {e}")
            raise
    
    def start(self):
        """Inicia todos los servicios"""
        if self.is_running:
            logging.warning("El servicio ya está ejecutándose")
            return
        
        try:
            logging.info("🚀 Iniciando Facial Sync Service...")
            
            # Marcar como iniciando
            self.is_running = True
            self.is_stopping = False
            
            # Inicializar componentes si no se ha hecho
            if not self.db_manager:
                if not self.initialize():
                    raise Exception("Fallo en inicialización")
            
            # Iniciar API Server
            if self.api_server:
                api_thread = threading.Thread(target=self.api_server.start, daemon=True)
                api_thread.start()
                self.threads.append(api_thread)
                logging.info("✅ API Server iniciado")
            
            # Iniciar WebSocket Server
            if self.websocket_server and self.config.get('WEBSOCKET_ENABLED'):
                ws_thread = threading.Thread(target=self.websocket_server.start, daemon=True)
                ws_thread.start()
                self.threads.append(ws_thread)
                logging.info("✅ WebSocket Server iniciado")
            
            # Iniciar Workers
            if self.sync_worker:
                sync_thread = threading.Thread(target=self.sync_worker.start, daemon=True)
                sync_thread.start()
                self.threads.append(sync_thread)
                logging.info("✅ Sync Worker iniciado")
            
            if self.health_worker:
                health_thread = threading.Thread(target=self.health_worker.start, daemon=True)
                health_thread.start()
                self.threads.append(health_thread)
                logging.info("✅ Health Worker iniciado")
            
            # Iniciar Event Processor
            if self.event_processor:
                event_thread = threading.Thread(target=self.event_processor.start, daemon=True)
                event_thread.start()
                self.threads.append(event_thread)
                logging.info("✅ Event Processor iniciado")
            
            logging.info("🎯 Todos los servicios iniciados correctamente")
            logging.info(f"📡 API disponible en: http://localhost:{self.config.get('API_PORT')}")
            if self.config.get('WEBSOCKET_ENABLED'):
                logging.info(f"🔌 WebSocket disponible en: ws://localhost:{self.config.get('WEBSOCKET_PORT')}")
            
        except Exception as e:
            logging.error(f"❌ Error iniciando servicio: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Detiene todos los servicios"""
        if not self.is_running or self.is_stopping:
            return
        
        try:
            logging.info("🛑 Deteniendo Facial Sync Service...")
            self.is_stopping = True
            
            # Detener componentes
            if self.sync_worker:
                self.sync_worker.stop()
                logging.info("🔄 Sync Worker detenido")
            
            if self.health_worker:
                self.health_worker.stop()
                logging.info("💓 Health Worker detenido")
            
            if self.event_processor:
                self.event_processor.stop()
                logging.info("📨 Event Processor detenido")
            
            if self.websocket_server:
                self.websocket_server.stop()
                logging.info("🔌 WebSocket Server detenido")
            
            if self.api_server:
                self.api_server.stop()
                logging.info("📡 API Server detenido")
            
            # Cerrar conexiones de BD
            if self.db_manager:
                self.db_manager.close_all_connections()
                logging.info("🗄️ Conexiones BD cerradas")
            
            # Esperar threads
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            
            self.is_running = False
            self.is_stopping = False
            
            logging.info("✅ Facial Sync Service detenido correctamente")
            
        except Exception as e:
            logging.error(f"❌ Error deteniendo servicio: {e}")
    
    def restart(self):
        """Reinicia el servicio"""
        logging.info("🔄 Reiniciando Facial Sync Service...")
        self.stop()
        time.sleep(2)  # Pausa breve
        self.start()
    
    def get_status(self):
        """Obtiene el estado actual del servicio"""
        status = {
            'running': self.is_running,
            'stopping': self.is_stopping,
            'components': {}
        }
        
        if self.is_running:
            status['components'] = {
                'database': self.db_manager is not None,
                'api_server': self.api_server is not None,
                'websocket_server': self.websocket_server is not None and self.config.get('WEBSOCKET_ENABLED'),
                'device_manager': self.device_manager is not None,
                'sync_worker': self.sync_worker is not None,
                'health_worker': self.health_worker is not None,
                'event_processor': self.event_processor is not None
            }
        
        return status
    
    def run_console_mode(self):
        """Ejecuta el servicio en modo consola (para desarrollo)"""
        try:
            if not self.initialize():
                raise Exception("Error en inicialización")
            
            self.start()
            
            print("\n=== FACIAL SYNC SERVICE ===")
            print("Presione Ctrl+C para detener el servicio")
            print("Comandos disponibles:")
            print("  status  - Mostrar estado")
            print("  stop    - Detener servicio")
            print("  restart - Reiniciar servicio")
            print("  exit    - Salir")
            print("===============================\n")
            
            # Loop principal para comandos
            while self.is_running:
                try:
                    command = input("facial-sync> ").strip().lower()
                    
                    if command == "status":
                        status = self.get_status()
                        print(f"Estado: {'🟢 Activo' if status['running'] else '🔴 Detenido'}")
                        if status['running']:
                            for comp, active in status['components'].items():
                                print(f"  {comp}: {'✅' if active else '❌'}")
                    
                    elif command == "stop":
                        self.stop()
                        break
                    
                    elif command == "restart":
                        self.restart()
                    
                    elif command in ["exit", "quit"]:
                        break
                    
                    elif command == "help":
                        print("Comandos: status, stop, restart, exit")
                    
                    elif command:
                        print(f"Comando desconocido: {command}")
                    
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")
            
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error(f"Error en modo consola: {e}")
        finally:
            self.stop()
    
    def run_tray_mode(self):
        """Ejecuta el servicio con icono en bandeja del sistema"""
        try:
            if not self.initialize():
                raise Exception("Error en inicialización")
            
            # Iniciar servicios
            self.start()
            
            # Ejecutar tray service (bloquea hasta que se cierre)
            self.tray_service.start()
            
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error(f"Error en modo tray: {e}")
        finally:
            self.stop()

def main():
    """Función principal"""
    # Verificar argumentos de línea de comandos
    import argparse
    
    parser = argparse.ArgumentParser(description='Facial Sync Service')
    parser.add_argument('--mode', choices=['console', 'tray', 'service'], 
                       default='tray', help='Modo de ejecución')
    parser.add_argument('--config', help='Archivo de configuración personalizado')
    parser.add_argument('--debug', action='store_true', help='Modo debug')
    
    args = parser.parse_args()
    
    # Configurar modo debug
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Crear instancia del servicio
    service = FacialSyncService()
    
    try:
        if args.mode == 'console':
            print("🖥️  Iniciando en modo CONSOLA")
            service.run_console_mode()
            
        elif args.mode == 'tray':
            print("🖼️  Iniciando en modo BANDEJA")
            service.run_tray_mode()
            
        elif args.mode == 'service':
            print("⚙️  Iniciando como SERVICIO")
            # Para implementar más tarde como servicio Windows
            service.run_console_mode()
            
    except Exception as e:
        logging.error(f"💥 Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()