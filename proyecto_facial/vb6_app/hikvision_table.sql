USE [videoman];
GO

-- Tabla principal de datos faciales
CREATE TABLE [dbo].[face] (
    [FacialID] INT NOT NULL PRIMARY KEY, -- Identificador único del dato facial
    [TemplateData] VARBINARY(MAX) NULL,  -- Datos biométricos faciales
    [Activo] TINYINT NOT NULL DEFAULT 1  -- Estado de activación (1 = activo, 0 = inactivo)
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY];
GO

-- Tabla de categorías asociadas al dato facial
CREATE TABLE [dbo].[facecatval] (
    [FacialID] INT NOT NULL,             -- FK a face
    [CategoriaID] INT NOT NULL,          -- ID de la categoría
    [ValorID] INT NOT NULL,              -- ID del valor asociado
    PRIMARY KEY ([FacialID], [CategoriaID], [ValorID]),
    FOREIGN KEY ([FacialID]) REFERENCES [dbo].[face]([FacialID])
) ON [PRIMARY];
GO

-- Tabla de relación entre personas y datos faciales
CREATE TABLE [dbo].[perface] (
    [PersonaID] INT NOT NULL,            -- ID de la persona
    [FacialID] INT NOT NULL,             -- FK a face
    PRIMARY KEY ([PersonaID], [FacialID]),
    FOREIGN KEY ([FacialID]) REFERENCES [dbo].[face]([FacialID])
) ON [PRIMARY];
GO

IF EXISTS (
    SELECT 1 FROM [videoman].[dbo].[catval]
    WHERE CategoriaID = 3 AND ValorID = 7
)
BEGIN
    -- Actualizar el registro existente
    UPDATE [videoman].[dbo].[catval]
    SET Nombre = 'Facial',
        SystemParameter = 2
    WHERE CategoriaID = 3 AND ValorID = 7
END
ELSE
BEGIN
    -- Insertar nuevo registro
    INSERT INTO [videoman].[dbo].[catval] (CategoriaID, ValorID, Nombre, SystemParameter)
    VALUES (3, 7, 'Facial', 2)
END


-- ============================================
-- TABLA HIKVISION PARA GESTION DE DISPOSITIVOS
-- Version Simplificada - Solo Campos Esenciales
-- ============================================

CREATE TABLE hikvision (
    -- IDENTIFICACION
    ID              INT IDENTITY(1,1) PRIMARY KEY,
    DispositivoID   VARCHAR(50) NOT NULL UNIQUE,
    Nombre          VARCHAR(100) NOT NULL,
    
    -- CONEXION
    IP              VARCHAR(45) NOT NULL,
    Usuario         VARCHAR(32) NOT NULL DEFAULT 'admin',
    Password        VARCHAR(255) NOT NULL,
    
    -- PUERTOS
    PuertoHTTP      INT NOT NULL DEFAULT 80,
    PuertoHTTPS     INT DEFAULT 443,
    PuertoRTSP      INT DEFAULT 554,
    PuertoSVR       INT DEFAULT 8000,
    
    -- CONFIGURACION
    Tipo            VARCHAR(50) NOT NULL,  -- 'Camera', 'AccessControl', 'NVR', 'DVR'
    Modelo          VARCHAR(100),
    
    -- ESTADO
    Activo          BIT DEFAULT 1,
    
    -- METADATOS
    FechaCreacion   DATETIME DEFAULT GETDATE(),
    Descripcion     TEXT
);

-- INDICES
CREATE INDEX IX_Hikvision_IP ON hikvision(IP);
CREATE INDEX IX_Hikvision_Tipo ON hikvision(Tipo);

-- DATOS DE EJEMPLO
-- Verificar e insertar CAM001
IF NOT EXISTS (
    SELECT 1 FROM hikvision WHERE DispositivoID = 'CAM001'
)
BEGIN
    INSERT INTO hikvision (DispositivoID, Nombre, IP, Usuario, Password, Tipo, Modelo, Descripcion)
    VALUES ('CAM001', 'Camara Entrada', '192.168.1.24', 'admin', 'Oem2017*', 'Camera', 'DS-2CD1023G0E-I', 'Camara entrada principal');
END

-- Verificar e insertar ACC001
IF NOT EXISTS (
    SELECT 1 FROM hikvision WHERE DispositivoID = 'ACC001'
)
BEGIN
    INSERT INTO hikvision (DispositivoID, Nombre, IP, Usuario, Password, Tipo, Modelo, Descripcion)
    VALUES ('ACC001', 'Control Facial', '192.168.1.26', 'admin', 'Oem2017*', 'AccessControl', 'DS-K1T344MBFWX-E1', 'Terminal reconocimiento facial');
END
