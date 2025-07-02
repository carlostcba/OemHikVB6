-- ============================================
-- TABLAS ADICIONALES PARA FACIAL SYNC SERVICE
-- Proyecto: Sistema de Sincronización Facial
-- ============================================

-- TABLA DE COLA DE SINCRONIZACIÓN
CREATE TABLE sync_queue (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    TaskType        VARCHAR(50) NOT NULL,           -- 'CREATE', 'UPDATE', 'DELETE'
    FacialID        BIGINT,                         -- Referencia a tabla face
    PersonaID       BIGINT,                         -- Referencia a tabla per
    TaskData        TEXT,                           -- JSON con datos de la tarea
    Status          VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    Priority        INT DEFAULT 1,                 -- Prioridad (1=Alta, 5=Baja)
    Attempts        INT DEFAULT 0,                 -- Intentos de procesamiento
    LastError       TEXT,                          -- Último error ocurrido
    CreatedAt       DATETIME DEFAULT GETDATE(),    -- Fecha de creación
    ProcessedAt     DATETIME,                      -- Fecha de procesamiento
    CompletedAt     DATETIME                       -- Fecha de finalización
);

-- TABLA DE LOG DE EVENTOS DE ACCESO
CREATE TABLE access_events (
    ID              BIGINT IDENTITY(1,1) PRIMARY KEY,
    DeviceIP        VARCHAR(45) NOT NULL,          -- IP del dispositivo
    EventType       VARCHAR(50) NOT NULL,          -- Tipo de evento
    EventCode       VARCHAR(20),                   -- Código del evento (ej: 5-75)
    PersonaID       BIGINT,                        -- ID de persona (si aplica)
    EmployeeNo      VARCHAR(50),                   -- Número de empleado
    PersonName      VARCHAR(200),                  -- Nombre de la persona
    VerifyMode      VARCHAR(50),                   -- Modo de verificación
    AccessResult    VARCHAR(20),                   -- 'SUCCESS', 'FAILED', 'DENIED'
    EventTime       DATETIME NOT NULL,             -- Tiempo del evento
    ReceivedAt      DATETIME DEFAULT GETDATE(),    -- Cuándo se recibió
    RawData         TEXT,                          -- Datos completos del evento en JSON
    ProcessedBy     VARCHAR(100)                   -- Servicio que procesó el evento
);

-- TABLA DE ESTADO DE DISPOSITIVOS
CREATE TABLE device_status (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    DispositivoID   VARCHAR(50) NOT NULL,          -- Referencia a hikvision.DispositivoID
    LastPing        DATETIME,                      -- Última verificación
    IsOnline        BIT DEFAULT 0,                 -- Estado de conectividad
    LastError       TEXT,                          -- Último error de conexión
    ErrorCount      INT DEFAULT 0,                 -- Contador de errores consecutivos
    LastSync        DATETIME,                      -- Última sincronización exitosa
    FaceCount       INT DEFAULT 0,                 -- Cantidad de rostros en dispositivo
    Version         VARCHAR(50),                   -- Versión de firmware
    Capabilities    TEXT,                          -- Capacidades en JSON
    UpdatedAt       DATETIME DEFAULT GETDATE(),    -- Última actualización
    
    FOREIGN KEY (DispositivoID) REFERENCES hikvision(DispositivoID)
);

-- TABLA DE CONFIGURACIÓN DEL SERVICIO
CREATE TABLE service_config (
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    ConfigKey       VARCHAR(100) NOT NULL UNIQUE,  -- Clave de configuración
    ConfigValue     TEXT NOT NULL,                 -- Valor (puede ser JSON)
    Category        VARCHAR(50) DEFAULT 'GENERAL', -- Categoría
    Description     VARCHAR(500),                  -- Descripción
    IsActive        BIT DEFAULT 1,                 -- Configuración activa
    CreatedAt       DATETIME DEFAULT GETDATE(),    -- Fecha de creación
    UpdatedAt       DATETIME DEFAULT GETDATE()     -- Fecha de actualización
);

-- ============================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================

-- Índices para sync_queue
CREATE INDEX IX_SyncQueue_Status ON sync_queue(Status, Priority);
CREATE INDEX IX_SyncQueue_TaskType ON sync_queue(TaskType);
CREATE INDEX IX_SyncQueue_PersonaID ON sync_queue(PersonaID);

-- Índices para access_events
CREATE INDEX IX_AccessEvents_DeviceIP ON access_events(DeviceIP);
CREATE INDEX IX_AccessEvents_EventTime ON access_events(EventTime);
CREATE INDEX IX_AccessEvents_PersonaID ON access_events(PersonaID);
CREATE INDEX IX_AccessEvents_EmployeeNo ON access_events(EmployeeNo);

-- Índices para device_status
CREATE INDEX IX_DeviceStatus_DispositivoID ON device_status(DispositivoID);
CREATE INDEX IX_DeviceStatus_IsOnline ON device_status(IsOnline);

-- Índices para service_config
CREATE INDEX IX_ServiceConfig_Category ON service_config(Category);

-- ============================================
-- CONFIGURACIÓN INICIAL DEL SERVICIO
-- ============================================

INSERT INTO service_config (ConfigKey, ConfigValue, Category, Description) VALUES
('API_HOST', '0.0.0.0', 'API', 'Host del servidor API'),
('API_PORT', '5000', 'API', 'Puerto del servidor API'),
('WEBSOCKET_HOST', '0.0.0.0', 'WEBSOCKET', 'Host del servidor WebSocket'),
('WEBSOCKET_PORT', '8765', 'WEBSOCKET', 'Puerto del servidor WebSocket'),
('SYNC_INTERVAL', '30', 'SYNC', 'Intervalo de sincronización en segundos'),
('MAX_RETRY_ATTEMPTS', '3', 'SYNC', 'Máximo número de reintentos'),
('DEVICE_PING_INTERVAL', '60', 'MONITOR', 'Intervalo de verificación de dispositivos'),
('LOG_LEVEL', 'INFO', 'LOGGING', 'Nivel de logging (DEBUG, INFO, WARNING, ERROR)'),
('LOG_RETENTION_DAYS', '30', 'LOGGING', 'Días de retención de logs'),
('ENABLE_WEBSOCKET_EVENTS', 'true', 'EVENTS', 'Habilitar eventos por WebSocket'),
('EVENT_BUFFER_SIZE', '1000', 'EVENTS', 'Tamaño del buffer de eventos'),
('FACE_SYNC_ENABLED', 'true', 'FACIAL', 'Habilitar sincronización facial'),
('AUTO_RETRY_FAILED_TASKS', 'true', 'SYNC', 'Reintentar tareas fallidas automáticamente');

-- ============================================
-- PROCEDIMIENTOS ALMACENADOS
-- ============================================

-- Procedimiento para encolar tarea de sincronización
CREATE PROCEDURE SP_EnqueueSyncTask
    @TaskType VARCHAR(50),
    @FacialID BIGINT = NULL,
    @PersonaID BIGINT = NULL,
    @TaskData TEXT = NULL,
    @Priority INT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO sync_queue (TaskType, FacialID, PersonaID, TaskData, Priority)
    VALUES (@TaskType, @FacialID, @PersonaID, @TaskData, @Priority);
    
    SELECT SCOPE_IDENTITY() AS TaskID;
END;

-- Procedimiento para obtener siguiente tarea pendiente
CREATE PROCEDURE SP_GetNextPendingTask
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Obtener la tarea con mayor prioridad (menor número)
    SELECT TOP 1 
        ID, TaskType, FacialID, PersonaID, TaskData, Priority, Attempts
    FROM sync_queue 
    WHERE Status = 'PENDING' 
        AND Attempts < 3
    ORDER BY Priority ASC, CreatedAt ASC;
END;

-- Procedimiento para actualizar estado de tarea
CREATE PROCEDURE SP_UpdateTaskStatus
    @TaskID INT,
    @Status VARCHAR(20),
    @Error TEXT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE sync_queue 
    SET Status = @Status,
        LastError = @Error,
        Attempts = Attempts + 1,
        ProcessedAt = CASE WHEN @Status = 'PROCESSING' THEN GETDATE() ELSE ProcessedAt END,
        CompletedAt = CASE WHEN @Status IN ('COMPLETED', 'FAILED') THEN GETDATE() ELSE CompletedAt END
    WHERE ID = @TaskID;
END;

-- Procedimiento para limpiar tareas completadas antiguas
CREATE PROCEDURE SP_CleanupCompletedTasks
    @DaysOld INT = 7
AS
BEGIN
    SET NOCOUNT ON;
    
    DELETE FROM sync_queue 
    WHERE Status IN ('COMPLETED', 'FAILED') 
        AND CompletedAt < DATEADD(DAY, -@DaysOld, GETDATE());
    
    SELECT @@ROWCOUNT AS DeletedTasks;
END;

-- Procedimiento para registrar evento de acceso
CREATE PROCEDURE SP_LogAccessEvent
    @DeviceIP VARCHAR(45),
    @EventType VARCHAR(50),
    @EventCode VARCHAR(20) = NULL,
    @PersonaID BIGINT = NULL,
    @EmployeeNo VARCHAR(50) = NULL,
    @PersonName VARCHAR(200) = NULL,
    @VerifyMode VARCHAR(50) = NULL,
    @AccessResult VARCHAR(20) = NULL,
    @EventTime DATETIME,
    @RawData TEXT = NULL,
    @ProcessedBy VARCHAR(100) = 'FacialSyncService'
AS
BEGIN
    SET NOCOUNT ON;
    
    INSERT INTO access_events (
        DeviceIP, EventType, EventCode, PersonaID, EmployeeNo, 
        PersonName, VerifyMode, AccessResult, EventTime, RawData, ProcessedBy
    ) VALUES (
        @DeviceIP, @EventType, @EventCode, @PersonaID, @EmployeeNo,
        @PersonName, @VerifyMode, @AccessResult, @EventTime, @RawData, @ProcessedBy
    );
    
    SELECT SCOPE_IDENTITY() AS EventID;
END;

-- ============================================
-- VISTA PARA MONITOREO DE TAREAS
-- ============================================

CREATE VIEW VW_TaskMonitor AS
SELECT 
    sq.ID,
    sq.TaskType,
    sq.Status,
    sq.Priority,
    sq.Attempts,
    sq.CreatedAt,
    sq.ProcessedAt,
    sq.CompletedAt,
    CASE 
        WHEN sq.Status = 'PENDING' THEN 
            DATEDIFF(MINUTE, sq.CreatedAt, GETDATE())
        ELSE 0 
    END AS PendingMinutes,
    CASE 
        WHEN sq.ProcessedAt IS NOT NULL AND sq.CompletedAt IS NOT NULL THEN
            DATEDIFF(SECOND, sq.ProcessedAt, sq.CompletedAt)
        ELSE NULL
    END AS ProcessingSeconds,
    per.Nombre + ' ' + per.Apellido AS PersonName,
    sq.LastError
FROM sync_queue sq
LEFT JOIN per ON sq.PersonaID = per.PersonaID;

-- ============================================
-- VISTA PARA ESTADÍSTICAS DE EVENTOS
-- ============================================

CREATE VIEW VW_EventStats AS
SELECT 
    ae.DeviceIP,
    h.Nombre AS DeviceName,
    COUNT(*) AS TotalEvents,
    SUM(CASE WHEN ae.AccessResult = 'SUCCESS' THEN 1 ELSE 0 END) AS SuccessEvents,
    SUM(CASE WHEN ae.AccessResult = 'FAILED' THEN 1 ELSE 0 END) AS FailedEvents,
    SUM(CASE WHEN ae.AccessResult = 'DENIED' THEN 1 ELSE 0 END) AS DeniedEvents,
    MAX(ae.EventTime) AS LastEventTime,
    COUNT(DISTINCT ae.EmployeeNo) AS UniqueUsers
FROM access_events ae
LEFT JOIN hikvision h ON ae.DeviceIP = h.IP
WHERE ae.EventTime >= DATEADD(DAY, -1, GETDATE())
GROUP BY ae.DeviceIP, h.Nombre;

-- ============================================
-- TRIGGER PARA AUDITORÍA DE CONFIGURACIÓN
-- ============================================

CREATE TRIGGER TR_ServiceConfig_UpdateTimestamp 
ON service_config
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE service_config 
    SET UpdatedAt = GETDATE()
    FROM service_config sc
    INNER JOIN inserted i ON sc.ID = i.ID;
END;