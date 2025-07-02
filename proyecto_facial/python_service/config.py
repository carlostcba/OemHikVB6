#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada para Facial Sync Service
Maneja configuración desde base de datos y archivos
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class Config:
    """Gestión centralizada de configuración"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # proyecto_facial/
        self.config_file = self.base_dir / "config.json"
        self.udl_file = self.base_dir / "videoman.udl"
        
        # Configuración por defecto
        self.defaults = {
            # API Configuration
            "API_HOST": "0.0.0.0",
            "API_PORT": 5000,
            "API_DEBUG": False,
            
            # WebSocket Configuration
            "WEBSOCKET_HOST": "0.0.0.0", 
            "WEBSOCKET_PORT": 8765,
            "WEBSOCKET_ENABLED": True,
            
            # Database Configuration
            "DB_UDL_PATH": str(self.udl_file),
            "DB_CONNECTION_TIMEOUT": 30,
            "DB_RETRY_ATTEMPTS": 3,
            
            # Synchronization Configuration
            "SYNC_INTERVAL": 30,
            "SYNC_ENABLED": True,
            "MAX_RETRY_ATTEMPTS": 3,
            "BATCH_SIZE": 10,
            "SYNC_TIMEOUT": 60,
            
            # Device Monitoring
            "DEVICE_PING_INTERVAL": 60,
            "DEVICE_TIMEOUT": 10,
            "DEVICE_RETRY_COUNT": 2,
            "HEALTH_CHECK_INTERVAL": 300,
            
            # Facial Recognition
            "FACE_SYNC_ENABLED": True,
            "FACE_QUALITY_THRESHOLD": 80,
            "FACE_LIBRARY_ID": "1",
            "MAX_FACE_SIZE_KB": 200,
            
            # Event Processing
            "EVENT_BUFFER_SIZE": 1000,
            "EVENT_BATCH_SIZE": 50,
            "EVENT_RETENTION_DAYS": 30,
            "ENABLE_WEBSOCKET_EVENTS": True,
            
            # Logging Configuration
            "LOG_LEVEL": "INFO",
            "LOG_DIR": "logs",
            "LOG_FILE": "service.log",
            "LOG_MAX_SIZE_MB": 10,
            "LOG_BACKUP_COUNT": 5,
            "LOG_RETENTION_DAYS": 30,
            
            # Service Configuration
            "SERVICE_NAME": "FacialSyncService",
            "SERVICE_DESCRIPTION": "Servicio de Sincronización Facial Hikvision",
            "TRAY_ICON": "assets/icon.ico",
            "AUTO_START": True,
            
            # Security
            "API_TOKEN_REQUIRED": False,
            "API_TOKEN": "",
            "ENCRYPT_PASSWORDS": True,
            
            # Performance
            "WORKER_THREADS": 4,
            "MAX_CONCURRENT_DEVICES": 10,
            "REQUEST_TIMEOUT": 30,
            "CONNECTION_POOL_SIZE": 20,
            
            # Hikvision Specific
            "HIK_DEFAULT_USERNAME": "admin",
            "HIK_DEFAULT_HTTP_PORT": 80,
            "HIK_DEFAULT_SVR_PORT": 8000,
            "HIK_DEFAULT_HTTPS_PORT": 443,
            "HIK_DEFAULT_RTSP_PORT": 554,
            "HIK_AUTH_TIMEOUT": 15,
            "HIK_FACE_LIB_TYPE": "blackFD",
            
            # Error Handling
            "AUTO_RETRY_FAILED_TASKS": True,
            "RETRY_DELAY_SECONDS": 60,
            "MAX_ERROR_COUNT": 5,
            "CIRCUIT_BREAKER_ENABLED": True,
            
            # Notifications
            "ENABLE_NOTIFICATIONS": True,
            "NOTIFICATION_LEVEL": "ERROR",
            "EMAIL_NOTIFICATIONS": False,
            
            # Development
            "DEBUG_MODE": False,
            "VERBOSE_LOGGING": False,
            "ENABLE_PROFILING": False
        }
        
        self._config = self.defaults.copy()
        self._db_manager = None
        
    def initialize(self, db_manager=None):
        """Inicializa la configuración cargando desde archivos y BD"""
        self._db_manager = db_manager
        
        # Cargar desde archivo si existe
        self.load_from_file()
        
        # Cargar desde base de datos si está disponible
        if self._db_manager:
            self.load_from_database()
        
        # Configurar logging
        self.setup_logging()
        
        logging.info("Configuración inicializada correctamente")
    
    def load_from_file(self):
        """Carga configuración desde archivo JSON"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                    logging.info(f"Configuración cargada desde {self.config_file}")
            except Exception as e:
                logging.warning(f"Error cargando configuración desde archivo: {e}")
    
    def save_to_file(self):
        """Guarda configuración actual al archivo JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
                logging.info(f"Configuración guardada en {self.config_file}")
        except Exception as e:
            logging.error(f"Error guardando configuración: {e}")
    
    def load_from_database(self):
        """Carga configuración desde base de datos"""
        if not self._db_manager:
            return
            
        try:
            query = "SELECT ConfigKey, ConfigValue FROM service_config WHERE IsActive = 1"
            results = self._db_manager.execute_query(query)
            
            if results:
                for row in results:
                    key = row[0]
                    value = row[1]
                    
                    # Convertir valor según tipo
                    if key in self._config:
                        original_type = type(self._config[key])
                        if original_type == bool:
                            self._config[key] = value.lower() in ['true', '1', 'yes', 'on']
                        elif original_type == int:
                            self._config[key] = int(value)
                        elif original_type == float:
                            self._config[key] = float(value)
                        else:
                            self._config[key] = value
                
                logging.info("Configuración cargada desde base de datos")
                
        except Exception as e:
            logging.warning(f"Error cargando configuración desde BD: {e}")
    
    def save_to_database(self, key: str, value: Any):
        """Guarda un valor específico en la base de datos"""
        if not self._db_manager:
            return False
            
        try:
            # Convertir valor a string
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
            
            query = """
            IF EXISTS (SELECT 1 FROM service_config WHERE ConfigKey = ?)
                UPDATE service_config SET ConfigValue = ?, UpdatedAt = GETDATE() WHERE ConfigKey = ?
            ELSE
                INSERT INTO service_config (ConfigKey, ConfigValue, Category) VALUES (?, ?, 'RUNTIME')
            """
            
            self._db_manager.execute_non_query(query, [key, str_value, key, key, str_value])
            self._config[key] = value
            
            logging.info(f"Configuración guardada en BD: {key} = {value}")
            return True
            
        except Exception as e:
            logging.error(f"Error guardando configuración en BD: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene valor de configuración"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any, save_to_db: bool = True):
        """Establece valor de configuración"""
        self._config[key] = value
        
        if save_to_db and self._db_manager:
            self.save_to_database(key, value)
    
    def get_api_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de API"""
        return {
            'host': self.get('API_HOST'),
            'port': self.get('API_PORT'),
            'debug': self.get('API_DEBUG'),
            'token_required': self.get('API_TOKEN_REQUIRED'),
            'token': self.get('API_TOKEN')
        }
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de WebSocket"""
        return {
            'host': self.get('WEBSOCKET_HOST'),
            'port': self.get('WEBSOCKET_PORT'),
            'enabled': self.get('WEBSOCKET_ENABLED')
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de base de datos"""
        return {
            'udl_path': self.get('DB_UDL_PATH'),
            'timeout': self.get('DB_CONNECTION_TIMEOUT'),
            'retry_attempts': self.get('DB_RETRY_ATTEMPTS')
        }
    
    def get_sync_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de sincronización"""
        return {
            'enabled': self.get('SYNC_ENABLED'),
            'interval': self.get('SYNC_INTERVAL'),
            'max_retries': self.get('MAX_RETRY_ATTEMPTS'),
            'batch_size': self.get('BATCH_SIZE'),
            'timeout': self.get('SYNC_TIMEOUT')
        }
    
    def get_device_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de dispositivos"""
        return {
            'ping_interval': self.get('DEVICE_PING_INTERVAL'),
            'timeout': self.get('DEVICE_TIMEOUT'),
            'retry_count': self.get('DEVICE_RETRY_COUNT'),
            'max_concurrent': self.get('MAX_CONCURRENT_DEVICES')
        }
    
    def get_hikvision_config(self) -> Dict[str, Any]:
        """Obtiene configuración específica de Hikvision"""
        return {
            'default_username': self.get('HIK_DEFAULT_USERNAME'),
            'http_port': self.get('HIK_DEFAULT_HTTP_PORT'),
            'svr_port': self.get('HIK_DEFAULT_SVR_PORT'),
            'https_port': self.get('HIK_DEFAULT_HTTPS_PORT'),
            'rtsp_port': self.get('HIK_DEFAULT_RTSP_PORT'),
            'auth_timeout': self.get('HIK_AUTH_TIMEOUT'),
            'face_lib_type': self.get('HIK_FACE_LIB_TYPE')
        }
    
    def setup_logging(self):
        """Configura el sistema de logging"""
        log_dir = Path(self.get('LOG_DIR'))
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / self.get('LOG_FILE')
        log_level = getattr(logging, self.get('LOG_LEVEL').upper())
        
        # Configuración de logging con rotación
        from logging.handlers import RotatingFileHandler
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler con rotación
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.get('LOG_MAX_SIZE_MB') * 1024 * 1024,
            backupCount=self.get('LOG_BACKUP_COUNT'),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        
        if self.get('DEBUG_MODE'):
            root_logger.addHandler(console_handler)
    
    def validate_config(self) -> tuple[bool, list]:
        """Valida la configuración actual"""
        errors = []
        
        # Validar archivo UDL
        udl_path = Path(self.get('DB_UDL_PATH'))
        if not udl_path.exists():
            errors.append(f"Archivo UDL no encontrado: {udl_path}")
        
        # Validar puertos
        api_port = self.get('API_PORT')
        ws_port = self.get('WEBSOCKET_PORT')
        
        if not (1024 <= api_port <= 65535):
            errors.append(f"Puerto API inválido: {api_port}")
        
        if not (1024 <= ws_port <= 65535):
            errors.append(f"Puerto WebSocket inválido: {ws_port}")
        
        if api_port == ws_port:
            errors.append("Puerto API y WebSocket no pueden ser iguales")
        
        # Validar directorios
        log_dir = Path(self.get('LOG_DIR'))
        try:
            log_dir.mkdir(exist_ok=True)
        except Exception as e:
            errors.append(f"No se puede crear directorio de logs: {e}")
        
        # Validar valores numéricos
        numeric_configs = [
            'SYNC_INTERVAL', 'MAX_RETRY_ATTEMPTS', 'DEVICE_PING_INTERVAL',
            'WORKER_THREADS', 'REQUEST_TIMEOUT', 'CONNECTION_POOL_SIZE'
        ]
        
        for config_key in numeric_configs:
            value = self.get(config_key)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"Valor inválido para {config_key}: {value}")
        
        return len(errors) == 0, errors
    
    def reset_to_defaults(self):
        """Restaura configuración a valores por defecto"""
        self._config = self.defaults.copy()
        self.save_to_file()
        logging.info("Configuración restaurada a valores por defecto")
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obtiene toda la configuración actual"""
        return self._config.copy()
    
    def __getitem__(self, key):
        """Permite acceso como diccionario"""
        return self.get(key)
    
    def __setitem__(self, key, value):
        """Permite asignación como diccionario"""
        self.set(key, value)
    
    def __contains__(self, key):
        """Permite usar 'in' operator"""
        return key in self._config

# Instancia global de configuración
config = Config()

def get_config() -> Config:
    """Obtiene la instancia global de configuración"""
    return config