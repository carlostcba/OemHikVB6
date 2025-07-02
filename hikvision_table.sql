-- ============================================
-- TABLA HIKVISION PARA GESTIÓN DE DISPOSITIVOS
-- Versión Simplificada - Solo Campos Esenciales
-- ============================================

CREATE TABLE hikvision (
    -- IDENTIFICACIÓN
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    DispositivoID   VARCHAR(50) NOT NULL UNIQUE,
    Nombre          VARCHAR(100) NOT NULL,
    
    -- CONEXIÓN
    IP              VARCHAR(45) NOT NULL,
    Usuario         VARCHAR(32) NOT NULL DEFAULT 'admin',
    Password        VARCHAR(255) NOT NULL,
    
    -- PUERTOS
    PuertoHTTP      INT NOT NULL DEFAULT 80,
    PuertoHTTPS     INT DEFAULT 443,
    PuertoRTSP      INT DEFAULT 554,
    PuertoSVR       INT DEFAULT 8000,
    
    -- CONFIGURACIÓN
    Tipo            VARCHAR(50) NOT NULL,  -- 'Camera', 'AccessControl', 'NVR', 'DVR'
    Modelo          VARCHAR(100),
    
    -- ESTADO
    Activo          BIT DEFAULT 1,
    
    -- METADATOS
    FechaCreacion   DATETIME DEFAULT GETDATE(),
    Descripcion     TEXT
);

-- ÍNDICES
CREATE INDEX IX_Hikvision_IP ON hikvision(IP);
CREATE INDEX IX_Hikvision_Tipo ON hikvision(Tipo);

-- DATOS DE EJEMPLO
INSERT INTO hikvision (DispositivoID, Nombre, IP, Usuario, Password, Tipo, Modelo, Descripcion) 
VALUES 
('CAM001', 'Camara Entrada', '192.168.1.24', 'admin', 'Oem2017*', 'Camera', 'DS-2CD1023G0E-I', 'Cámara entrada principal'),
('ACC001', 'Control Facial', '192.168.1.26', 'admin', 'Oem2017*', 'AccessControl', 'DS-K1T344MBFWX-E1', 'Terminal reconocimiento facial');