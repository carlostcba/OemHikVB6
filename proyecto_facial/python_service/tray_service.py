#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio System Tray para Facial Sync Service
Maneja icono en bandeja del sistema y control del servicio
"""

import pystray
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
import webbrowser
from PIL import Image, ImageDraw
import sys
import os
from pathlib import Path
import json
import time

class TrayService:
    """Servicio de icono en bandeja del sistema"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.config = service_manager.config
        self.icon = None
        self.is_running = False
        self.status_window = None
        
        # Crear icono por defecto si no existe
        self.icon_path = self.get_icon_path()
        
    def get_icon_path(self) -> str:
        """Obtiene la ruta del icono"""
        icon_path = self.config.get('TRAY_ICON', 'assets/icon.ico')
        
        # Si es ruta relativa, hacerla absoluta
        if not os.path.isabs(icon_path):
            base_dir = Path(__file__).parent.parent
            icon_path = base_dir / icon_path
        
        # Si no existe, crear icono por defecto
        if not Path(icon_path).exists():
            return self.create_default_icon()
        
        return str(icon_path)
    
    def create_default_icon(self) -> str:
        """Crea un icono por defecto"""
        try:
            # Crear directorio assets si no existe
            assets_dir = Path(__file__).parent / "assets"
            assets_dir.mkdir(exist_ok=True)
            
            icon_path = assets_dir / "icon.ico"
            
            # Crear imagen simple
            image = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(image)
            
            # Dibujar un círculo simple
            draw.ellipse([10, 10, 54, 54], fill='white', outline='blue')
            draw.text((25, 25), "FS", fill='blue')
            
            # Guardar como ICO
            image.save(icon_path, format='ICO')
            logging.info(f"Icono por defecto creado: {icon_path}")
            
            return str(icon_path)
            
        except Exception as e:
            logging.warning(f"Error creando icono por defecto: {e}")
            # Crear imagen en memoria
            return self.create_memory_icon()
    
    def create_memory_icon(self):
        """Crea un icono en memoria"""
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.ellipse([10, 10, 54, 54], fill='white', outline='blue')
        draw.text((25, 25), "FS", fill='blue')
        return image
    
    def create_menu(self):
        """Crea el menú contextual"""
        return pystray.Menu(
            pystray.MenuItem("Facial Sync Service", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Estado del Servicio",
                self.toggle_service,
                checked=lambda item: self.service_manager.is_running
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Mostrar Estado", self.show_status_window),
            pystray.MenuItem("Configuración", self.show_config_window),
            pystray.MenuItem("Ver Logs", self.show_logs_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("API Web", self.open_api_web),
            pystray.MenuItem("Monitor Eventos", self.open_event_monitor),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self.quit_application)
        )
    
    def start(self):
        """Inicia el servicio de bandeja"""
        try:
            # Cargar icono
            if isinstance(self.icon_path, str) and os.path.exists(self.icon_path):
                icon_image = Image.open(self.icon_path)
            else:
                icon_image = self.icon_path  # Ya es una imagen PIL
            
            # Crear icono de bandeja
            self.icon = pystray.Icon(
                name="FacialSyncService",
                icon=icon_image,
                title="Facial Sync Service",
                menu=self.create_menu()
            )
            
            # Mostrar notificación inicial
            self.show_notification("Facial Sync Service", "Servicio iniciado correctamente")
            
            # Ejecutar en thread principal de pystray
            self.icon.run()
            
        except Exception as e:
            logging.error(f"Error iniciando servicio de bandeja: {e}")
    
    def stop(self):
        """Detiene el servicio de bandeja"""
        if self.icon:
            self.icon.stop()
    
    def update_icon_status(self, is_running: bool):
        """Actualiza el estado visual del icono"""
        if not self.icon:
            return
            
        try:
            # Cambiar título según estado
            if is_running:
                self.icon.title = "Facial Sync Service - Activo"
            else:
                self.icon.title = "Facial Sync Service - Detenido"
            
            # Actualizar menú
            self.icon.menu = self.create_menu()
            
        except Exception as e:
            logging.error(f"Error actualizando icono: {e}")
    
    def show_notification(self, title: str, message: str):
        """Muestra notificación del sistema"""
        if self.icon:
            self.icon.notify(message, title)
    
    def toggle_service(self, icon, item):
        """Alterna el estado del servicio"""
        try:
            if self.service_manager.is_running:
                self.service_manager.stop()
                self.show_notification("Servicio", "Facial Sync Service detenido")
            else:
                self.service_manager.start()
                self.show_notification("Servicio", "Facial Sync Service iniciado")
            
            self.update_icon_status(self.service_manager.is_running)
            
        except Exception as e:
            logging.error(f"Error alternando servicio: {e}")
            messagebox.showerror("Error", f"Error al cambiar estado del servicio: {e}")
    
    def show_status_window(self, icon, item):
        """Muestra ventana de estado del servicio"""
        def create_status_window():
            if self.status_window and self.status_window.winfo_exists():
                self.status_window.lift()
                return
            
            # Crear ventana
            self.status_window = tk.Toplevel()
            self.status_window.title("Estado del Servicio - Facial Sync")
            self.status_window.geometry("800x600")
            self.status_window.resizable(True, True)
            
            # Crear notebook para pestañas
            notebook = ttk.Notebook(self.status_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Pestaña de estado general
            status_frame = ttk.Frame(notebook)
            notebook.add(status_frame, text="Estado General")
            
            # Información del servicio
            info_frame = ttk.LabelFrame(status_frame, text="Información del Servicio", padding="10")
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            status_text = "🟢 ACTIVO" if self.service_manager.is_running else "🔴 DETENIDO"
            ttk.Label(info_frame, text=f"Estado: {status_text}", font=("Arial", 12, "bold")).pack(anchor=tk.W)
            
            # Información de configuración
            config_info = [
                f"Puerto API: {self.config.get('API_PORT')}",
                f"Puerto WebSocket: {self.config.get('WEBSOCKET_PORT')}",
                f"Intervalo Sync: {self.config.get('SYNC_INTERVAL')}s",
                f"Workers: {self.config.get('WORKER_THREADS')}",
                f"Log Level: {self.config.get('LOG_LEVEL')}"
            ]
            
            for info in config_info:
                ttk.Label(info_frame, text=info).pack(anchor=tk.W)
            
            # Estadísticas
            stats_frame = ttk.LabelFrame(status_frame, text="Estadísticas", padding="10")
            stats_frame.pack(fill=tk.BOTH, expand=True)
            
            # Tabla de estadísticas
            stats_tree = ttk.Treeview(stats_frame, columns=("Valor",), show="tree headings", height=10)
            stats_tree.heading("#0", text="Métrica")
            stats_tree.heading("Valor", text="Valor")
            stats_tree.pack(fill=tk.BOTH, expand=True)
            
            # Pestaña de dispositivos
            devices_frame = ttk.Frame(notebook)
            notebook.add(devices_frame, text="Dispositivos")
            
            # Tabla de dispositivos
            devices_tree = ttk.Treeview(devices_frame, 
                columns=("IP", "Tipo", "Estado", "Última Conexión"), 
                show="tree headings", height=15)
            
            devices_tree.heading("#0", text="Dispositivo")
            devices_tree.heading("IP", text="IP")
            devices_tree.heading("Tipo", text="Tipo")
            devices_tree.heading("Estado", text="Estado")
            devices_tree.heading("Última Conexión", text="Última Conexión")
            
            devices_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Pestaña de tareas
            tasks_frame = ttk.Frame(notebook)
            notebook.add(tasks_frame, text="Tareas de Sync")
            
            tasks_tree = ttk.Treeview(tasks_frame,
                columns=("Tipo", "Estado", "Intentos", "Creado", "Error"),
                show="tree headings", height=15)
            
            tasks_tree.heading("#0", text="ID")
            tasks_tree.heading("Tipo", text="Tipo")
            tasks_tree.heading("Estado", text="Estado")
            tasks_tree.heading("Intentos", text="Intentos")
            tasks_tree.heading("Creado", text="Creado")
            tasks_tree.heading("Error", text="Error")
            
            tasks_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Botones de control
            button_frame = ttk.Frame(self.status_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            ttk.Button(button_frame, text="Actualizar", 
                      command=lambda: self.refresh_status_data(stats_tree, devices_tree, tasks_tree)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="Cerrar", 
                      command=self.status_window.destroy).pack(side=tk.RIGHT)
            
            # Cargar datos iniciales
            self.refresh_status_data(stats_tree, devices_tree, tasks_tree)
            
            # Auto-actualizar cada 30 segundos
            self.schedule_status_refresh(stats_tree, devices_tree, tasks_tree)
        
        # Ejecutar en thread principal
        threading.Thread(target=create_status_window, daemon=True).start()
    
    def refresh_status_data(self, stats_tree, devices_tree, tasks_tree):
        """Actualiza los datos de la ventana de estado"""
        try:
            # Limpiar árboles
            for item in stats_tree.get_children():
                stats_tree.delete(item)
            for item in devices_tree.get_children():
                devices_tree.delete(item)
            for item in tasks_tree.get_children():
                tasks_tree.delete(item)
            
            # Obtener estadísticas del servicio
            if hasattr(self.service_manager, 'db_manager') and self.service_manager.db_manager:
                try:
                    # Estadísticas generales
                    device_count = len(self.service_manager.db_manager.get_active_devices())
                    stats_tree.insert("", "end", text="Dispositivos Activos", values=(device_count,))
                    
                    # Estadísticas de tareas
                    task_stats = self.service_manager.db_manager.get_task_statistics()
                    for status, data in task_stats.items():
                        stats_tree.insert("", "end", text=f"Tareas {status}", values=(data['count'],))
                    
                    # Estadísticas de eventos
                    event_stats = self.service_manager.db_manager.get_event_statistics()
                    total_events = sum(sum(device_events.values()) for device_events in event_stats.values())
                    stats_tree.insert("", "end", text="Eventos (24h)", values=(total_events,))
                    
                    # Información de dispositivos
                    devices = self.service_manager.db_manager.get_device_status()
                    for device in devices:
                        status_text = "🟢 Online" if device.get('is_online') else "🔴 Offline"
                        last_ping = device.get('last_ping', 'Nunca')
                        if last_ping and last_ping != 'Nunca':
                            last_ping = last_ping.strftime('%Y-%m-%d %H:%M:%S')
                        
                        devices_tree.insert("", "end", 
                            text=device.get('nombre', 'Sin nombre'),
                            values=(
                                device.get('ip', ''),
                                device.get('tipo', ''),
                                status_text,
                                last_ping
                            ))
                    
                    # Información de tareas recientes
                    recent_tasks_query = """
                    SELECT TOP 20 ID, TaskType, Status, Attempts, CreatedAt, LastError
                    FROM sync_queue 
                    ORDER BY CreatedAt DESC
                    """
                    recent_tasks = self.service_manager.db_manager.execute_query(recent_tasks_query)
                    
                    for task in recent_tasks:
                        created_time = task[4].strftime('%H:%M:%S') if task[4] else ''
                        error_text = task[5][:50] + "..." if task[5] and len(task[5]) > 50 else task[5] or ""
                        
                        tasks_tree.insert("", "end",
                            text=str(task[0]),
                            values=(
                                task[1],  # TaskType
                                task[2],  # Status
                                task[3],  # Attempts
                                created_time,
                                error_text
                            ))
                
                except Exception as e:
                    logging.error(f"Error obteniendo estadísticas: {e}")
                    stats_tree.insert("", "end", text="Error", values=(f"Error: {e}",))
            
            else:
                stats_tree.insert("", "end", text="Base de Datos", values=("No conectada",))
        
        except Exception as e:
            logging.error(f"Error actualizando datos de estado: {e}")
    
    def schedule_status_refresh(self, stats_tree, devices_tree, tasks_tree):
        """Programa actualización automática de datos"""
        def auto_refresh():
            try:
                if self.status_window and self.status_window.winfo_exists():
                    self.refresh_status_data(stats_tree, devices_tree, tasks_tree)
                    # Programar siguiente actualización
                    self.status_window.after(30000, auto_refresh)  # 30 segundos
            except:
                pass  # Ventana cerrada
        
        if self.status_window:
            self.status_window.after(30000, auto_refresh)
    
    def show_config_window(self, icon, item):
        """Muestra ventana de configuración"""
        def create_config_window():
            config_window = tk.Toplevel()
            config_window.title("Configuración - Facial Sync Service")
            config_window.geometry("600x500")
            config_window.resizable(True, True)
            
            # Crear notebook para categorías
            notebook = ttk.Notebook(config_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Variables para configuración
            config_vars = {}
            
            # Pestaña API
            api_frame = ttk.Frame(notebook)
            notebook.add(api_frame, text="API")
            
            # Configuración API
            ttk.Label(api_frame, text="Puerto API:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['API_PORT'] = tk.StringVar(value=str(self.config.get('API_PORT')))
            ttk.Entry(api_frame, textvariable=config_vars['API_PORT'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(api_frame, text="Host API:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['API_HOST'] = tk.StringVar(value=self.config.get('API_HOST'))
            ttk.Entry(api_frame, textvariable=config_vars['API_HOST'], width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Pestaña WebSocket
            ws_frame = ttk.Frame(notebook)
            notebook.add(ws_frame, text="WebSocket")
            
            ttk.Label(ws_frame, text="Puerto WebSocket:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['WEBSOCKET_PORT'] = tk.StringVar(value=str(self.config.get('WEBSOCKET_PORT')))
            ttk.Entry(ws_frame, textvariable=config_vars['WEBSOCKET_PORT'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            config_vars['WEBSOCKET_ENABLED'] = tk.BooleanVar(value=self.config.get('WEBSOCKET_ENABLED'))
            ttk.Checkbutton(ws_frame, text="WebSocket Habilitado", 
                           variable=config_vars['WEBSOCKET_ENABLED']).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Pestaña Sincronización
            sync_frame = ttk.Frame(notebook)
            notebook.add(sync_frame, text="Sincronización")
            
            ttk.Label(sync_frame, text="Intervalo Sync (seg):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['SYNC_INTERVAL'] = tk.StringVar(value=str(self.config.get('SYNC_INTERVAL')))
            ttk.Entry(sync_frame, textvariable=config_vars['SYNC_INTERVAL'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(sync_frame, text="Máx. Reintentos:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['MAX_RETRY_ATTEMPTS'] = tk.StringVar(value=str(self.config.get('MAX_RETRY_ATTEMPTS')))
            ttk.Entry(sync_frame, textvariable=config_vars['MAX_RETRY_ATTEMPTS'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            config_vars['SYNC_ENABLED'] = tk.BooleanVar(value=self.config.get('SYNC_ENABLED'))
            ttk.Checkbutton(sync_frame, text="Sincronización Habilitada", 
                           variable=config_vars['SYNC_ENABLED']).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Pestaña Logging
            log_frame = ttk.Frame(notebook)
            notebook.add(log_frame, text="Logging")
            
            ttk.Label(log_frame, text="Nivel de Log:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['LOG_LEVEL'] = tk.StringVar(value=self.config.get('LOG_LEVEL'))
            log_combo = ttk.Combobox(log_frame, textvariable=config_vars['LOG_LEVEL'], 
                                   values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], width=15)
            log_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            ttk.Label(log_frame, text="Retención (días):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
            config_vars['LOG_RETENTION_DAYS'] = tk.StringVar(value=str(self.config.get('LOG_RETENTION_DAYS')))
            ttk.Entry(log_frame, textvariable=config_vars['LOG_RETENTION_DAYS'], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Botones
            button_frame = ttk.Frame(config_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            def save_config():
                try:
                    # Guardar configuración
                    for key, var in config_vars.items():
                        if isinstance(var, tk.BooleanVar):
                            self.config.set(key, var.get())
                        else:
                            value = var.get()
                            # Convertir a tipo apropiado
                            if key.endswith('_PORT') or key.endswith('_INTERVAL') or key.endswith('_ATTEMPTS') or key.endswith('_DAYS'):
                                value = int(value)
                            self.config.set(key, value)
                    
                    # Guardar en archivo
                    self.config.save_to_file()
                    
                    messagebox.showinfo("Éxito", "Configuración guardada correctamente.\nReinicie el servicio para aplicar cambios.")
                    config_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error guardando configuración: {e}")
            
            def reset_config():
                if messagebox.askyesno("Confirmar", "¿Restaurar configuración por defecto?"):
                    self.config.reset_to_defaults()
                    messagebox.showinfo("Éxito", "Configuración restaurada. Reinicie la aplicación.")
                    config_window.destroy()
            
            ttk.Button(button_frame, text="Guardar", command=save_config).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="Restaurar Defecto", command=reset_config).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="Cancelar", command=config_window.destroy).pack(side=tk.RIGHT)
        
        threading.Thread(target=create_config_window, daemon=True).start()
    
    def show_logs_window(self, icon, item):
        """Muestra ventana de logs"""
        def create_logs_window():
            logs_window = tk.Toplevel()
            logs_window.title("Logs - Facial Sync Service")
            logs_window.geometry("800x600")
            logs_window.resizable(True, True)
            
            # Frame para controles
            control_frame = ttk.Frame(logs_window)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Selector de archivo de log
            ttk.Label(control_frame, text="Archivo de Log:").pack(side=tk.LEFT)
            
            log_var = tk.StringVar()
            log_files = self.get_log_files()
            log_combo = ttk.Combobox(control_frame, textvariable=log_var, values=log_files, width=30)
            log_combo.pack(side=tk.LEFT, padx=(5, 10))
            if log_files:
                log_combo.set(log_files[0])
            
            # Filtro de nivel
            ttk.Label(control_frame, text="Nivel:").pack(side=tk.LEFT)
            level_var = tk.StringVar(value="ALL")
            level_combo = ttk.Combobox(control_frame, textvariable=level_var, 
                                     values=['ALL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], width=10)
            level_combo.pack(side=tk.LEFT, padx=(5, 10))
            
            # Botones
            ttk.Button(control_frame, text="Actualizar", 
                      command=lambda: self.load_log_content(log_var.get(), level_var.get(), log_text)).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Limpiar", 
                      command=lambda: log_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
            
            # Área de texto para logs
            log_text = scrolledtext.ScrolledText(logs_window, wrap=tk.WORD, font=("Consolas", 9))
            log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Cargar log inicial
            if log_files:
                self.load_log_content(log_files[0], "ALL", log_text)
        
        threading.Thread(target=create_logs_window, daemon=True).start()
    
    def get_log_files(self) -> list:
        """Obtiene lista de archivos de log disponibles"""
        log_dir = Path(self.config.get('LOG_DIR', 'logs'))
        if not log_dir.exists():
            return []
        
        log_files = []
        for file_path in log_dir.glob("*.log"):
            log_files.append(str(file_path))
        
        return sorted(log_files, reverse=True)  # Más recientes primero
    
    def load_log_content(self, log_file: str, level_filter: str, text_widget):
        """Carga contenido de archivo de log"""
        if not log_file or not os.path.exists(log_file):
            text_widget.insert(tk.END, "Archivo de log no encontrado\n")
            return
        
        try:
            text_widget.delete(1.0, tk.END)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filtrar por nivel si es necesario
            filtered_lines = []
            for line in lines:
                if level_filter == "ALL" or level_filter in line:
                    filtered_lines.append(line)
            
            # Mostrar últimas 1000 líneas para performance
            if len(filtered_lines) > 1000:
                text_widget.insert(tk.END, f"... mostrando últimas 1000 de {len(filtered_lines)} líneas ...\n\n")
                filtered_lines = filtered_lines[-1000:]
            
            for line in filtered_lines:
                text_widget.insert(tk.END, line)
            
            # Ir al final
            text_widget.see(tk.END)
            
        except Exception as e:
            text_widget.insert(tk.END, f"Error leyendo archivo de log: {e}\n")
    
    def open_api_web(self, icon, item):
        """Abre la interfaz web de la API"""
        try:
            api_port = self.config.get('API_PORT')
            url = f"http://localhost:{api_port}"
            webbrowser.open(url)
            self.show_notification("API Web", f"Abriendo {url}")
        except Exception as e:
            logging.error(f"Error abriendo API web: {e}")
    
    def open_event_monitor(self, icon, item):
        """Abre monitor de eventos en tiempo real"""
        def create_event_monitor():
            monitor_window = tk.Toplevel()
            monitor_window.title("Monitor de Eventos - Tiempo Real")
            monitor_window.geometry("900x600")
            monitor_window.resizable(True, True)
            
            # Frame de control
            control_frame = ttk.Frame(monitor_window)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Estado de conexión
            status_label = ttk.Label(control_frame, text="🔴 Desconectado", font=("Arial", 10, "bold"))
            status_label.pack(side=tk.LEFT)
            
            # Filtros
            ttk.Label(control_frame, text="Filtro:").pack(side=tk.LEFT, padx=(20, 5))
            filter_var = tk.StringVar()
            filter_entry = ttk.Entry(control_frame, textvariable=filter_var, width=20)
            filter_entry.pack(side=tk.LEFT, padx=(0, 10))
            
            # Botones
            ttk.Button(control_frame, text="Limpiar", 
                      command=lambda: event_text.delete(1.0, tk.END)).pack(side=tk.RIGHT, padx=5)
            
            # Área de eventos
            event_text = scrolledtext.ScrolledText(monitor_window, wrap=tk.WORD, font=("Consolas", 9))
            event_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Simular eventos (en una implementación real, esto vendría del WebSocket)
            def simulate_events():
                import random
                devices = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
                events = ["FACE_SUCCESS", "FACE_FAILED", "CARD_SUCCESS", "DOOR_OPEN"]
                
                while monitor_window.winfo_exists():
                    try:
                        time.sleep(random.randint(2, 8))
                        if random.random() < 0.3:  # 30% probabilidad de evento
                            device = random.choice(devices)
                            event = random.choice(events)
                            timestamp = time.strftime("%H:%M:%S")
                            
                            filter_text = filter_var.get().lower()
                            event_line = f"[{timestamp}] {device} - {event}\n"
                            
                            if not filter_text or filter_text in event_line.lower():
                                event_text.insert(tk.END, event_line)
                                event_text.see(tk.END)
                                
                                # Limitar líneas para performance
                                lines = event_text.get(1.0, tk.END).split('\n')
                                if len(lines) > 500:
                                    event_text.delete(1.0, "50.0")
                    except:
                        break
            
            # Iniciar simulación de eventos
            threading.Thread(target=simulate_events, daemon=True).start()
            status_label.config(text="🟢 Conectado (Simulación)")
        
        threading.Thread(target=create_event_monitor, daemon=True).start()
    
    def quit_application(self, icon, item):
        """Cierra la aplicación completamente"""
        try:
            # Confirmar salida
            if messagebox.askyesno("Confirmar", "¿Desea cerrar Facial Sync Service?"):
                # Detener servicio
                if self.service_manager.is_running:
                    self.service_manager.stop()
                
                # Cerrar ventanas
                if self.status_window and self.status_window.winfo_exists():
                    self.status_window.destroy()
                
                # Detener icono de bandeja
                self.stop()
                
                # Salir completamente
                sys.exit(0)
        except Exception as e:
            logging.error(f"Error cerrando aplicación: {e}")
            sys.exit(1)

def main():
    """Función principal para pruebas"""
    # Crear servicio mock para pruebas
    class MockServiceManager:
        def __init__(self):
            self.is_running = False
            from config import get_config
            self.config = get_config()
        
        def start(self):
            self.is_running = True
            print("Servicio iniciado")
        
        def stop(self):
            self.is_running = False
            print("Servicio detenido")
    
    # Inicializar configuración
    from config import get_config
    config = get_config()
    config.initialize()
    
    # Crear y ejecutar servicio de bandeja
    mock_service = MockServiceManager()
    tray_service = TrayService(mock_service)
    
    try:
        tray_service.start()
    except KeyboardInterrupt:
        print("Servicio interrumpido por usuario")
    except Exception as e:
        print(f"Error en servicio de bandeja: {e}")

if __name__ == "__main__":
    main()