-- =====================================
-- SCRIPT PARA CREAR TABLAS SISTEMA HIKVISION
-- Base de datos: RobleJoven
-- =====================================

USE [RobleJoven]
GO

-- 1. Tabla de logs de operaciones Hikvision
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='hiklog' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[hiklog] (
        [ID] INT IDENTITY(1,1) PRIMARY KEY,
        [Timestamp] DATETIME DEFAULT GETDATE(),
        [Nivel] VARCHAR(20) NOT NULL DEFAULT 'INFO',
        [DispositivoID] VARCHAR(50),
        [PersonaID] VARCHAR(50),
        [Accion] VARCHAR(50),
        [Mensaje] NVARCHAR(500),
        [Exito] BIT,
        [DetalleError] NVARCHAR(1000)
    )
    PRINT 'Tabla hiklog creada correctamente'
END
ELSE
    PRINT 'Tabla hiklog ya existe'
GO

-- 2. Tabla de grupos de dispositivos Hikvision
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='gruhik' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[gruhik] (
        [ID] INT IDENTITY(1,1) PRIMARY KEY,
        [Nombre] VARCHAR(100) NOT NULL,
        [Descripcion] NVARCHAR(200),
        [Activo] BIT DEFAULT 1,
        [FechaCreacion] DATETIME DEFAULT GETDATE()
    )
    PRINT 'Tabla gruhik creada correctamente'
END
ELSE
    PRINT 'Tabla gruhik ya existe'
GO

-- 3. Tabla de relación persona-dispositivo Hikvision
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='perhik' AND xtype='U')
BEGIN
    CREATE TABLE [dbo].[perhik] (
        [ID] INT IDENTITY(1,1) PRIMARY KEY,
        [PersonaID] INT NOT NULL,
        [DispositivoID] VARCHAR(50) NOT NULL,
        [GrupoID] INT,
        [Activo] BIT DEFAULT 1,
        [FechaCreacion] DATETIME DEFAULT GETDATE(),
        [FechaUltimaSync] DATETIME
    )
    PRINT 'Tabla perhik creada correctamente'
END
ELSE
    PRINT 'Tabla perhik ya existe'
GO

-- 4. Crear índices para mejorar rendimiento
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_hiklog_timestamp')
BEGIN
    CREATE INDEX IX_hiklog_timestamp ON [dbo].[hiklog] ([Timestamp] DESC)
    PRINT 'Índice IX_hiklog_timestamp creado'
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_hiklog_dispositivo')
BEGIN
    CREATE INDEX IX_hiklog_dispositivo ON [dbo].[hiklog] ([DispositivoID])
    PRINT 'Índice IX_hiklog_dispositivo creado'
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_hiklog_persona')
BEGIN
    CREATE INDEX IX_hiklog_persona ON [dbo].[hiklog] ([PersonaID])
    PRINT 'Índice IX_hiklog_persona creado'
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_perhik_persona')
BEGIN
    CREATE INDEX IX_perhik_persona ON [dbo].[perhik] ([PersonaID])
    PRINT 'Índice IX_perhik_persona creado'
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_perhik_dispositivo')
BEGIN
    CREATE INDEX IX_perhik_dispositivo ON [dbo].[perhik] ([DispositivoID])
    PRINT 'Índice IX_perhik_dispositivo creado'
END
GO

-- 5. Insertar grupos por defecto
IF NOT EXISTS (SELECT * FROM [dbo].[gruhik] WHERE [Nombre] = 'Todos los dispositivos')
BEGIN
    INSERT INTO [dbo].[gruhik] ([Nombre], [Descripcion])
    VALUES ('Todos los dispositivos', 'Grupo por defecto que incluye todos los dispositivos AccessControl activos')
    PRINT 'Grupo por defecto insertado'
END
GO

IF NOT EXISTS (SELECT * FROM [dbo].[gruhik] WHERE [Nombre] = 'Dispositivos principales')
BEGIN
    INSERT INTO [dbo].[gruhik] ([Nombre], [Descripcion])
    VALUES ('Dispositivos principales', 'Dispositivos de control de acceso principales')
    PRINT 'Grupo dispositivos principales insertado'
END
GO

-- 6. Crear vista para consulta rápida de logs
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_hiklog_resumen')
BEGIN
    EXEC('CREATE VIEW [dbo].[vw_hiklog_resumen] AS
    SELECT 
        h.ID,
        h.Timestamp,
        h.Nivel,
        h.DispositivoID,
        hik.Nombre as NombreDispositivo,
        h.PersonaID,
        per.Nombre + '' '' + per.Apellido as NombrePersona,
        h.Accion,
        h.Mensaje,
        h.Exito,
        h.DetalleError
    FROM [dbo].[hiklog] h
    LEFT JOIN [dbo].[hikvision] hik ON h.DispositivoID = hik.DispositivoID
    LEFT JOIN [dbo].[per] per ON CAST(h.PersonaID AS INT) = per.PersonaID')
    PRINT 'Vista vw_hiklog_resumen creada'
END
GO

-- 7. Crear vista para dispositivos activos
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_hikvision_activos')
BEGIN
    EXEC('CREATE VIEW [dbo].[vw_hikvision_activos] AS
    SELECT 
        DispositivoID,
        Nombre,
        IP,
        Usuario,
        PuertoHTTP,
        Modelo,
        Descripcion,
        FechaCreacion
    FROM [dbo].[hikvision]
    WHERE Tipo = ''AccessControl'' AND Activo = 1')
    PRINT 'Vista vw_hikvision_activos creada'
END
GO

-- 8. Crear procedimientos almacenados útiles

-- Procedimiento para obtener logs recientes
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_GetHikLogsRecientes')
    DROP PROCEDURE [dbo].[sp_GetHikLogsRecientes]
GO

CREATE PROCEDURE [dbo].[sp_GetHikLogsRecientes]
    @CantidadRegistros INT = 100,
    @DispositivoID VARCHAR(50) = NULL,
    @PersonaID VARCHAR(50) = NULL,
    @FechaDesde DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT TOP (@CantidadRegistros)
        ID,
        Timestamp,
        Nivel,
        DispositivoID,
        PersonaID,
        Accion,
        Mensaje,
        Exito,
        DetalleError
    FROM [dbo].[hiklog]
    WHERE 
        (@DispositivoID IS NULL OR DispositivoID = @DispositivoID)
        AND (@PersonaID IS NULL OR PersonaID = @PersonaID)
        AND (@FechaDesde IS NULL OR Timestamp >= @FechaDesde)
    ORDER BY Timestamp DESC
END
GO
PRINT 'Procedimiento sp_GetHikLogsRecientes creado'

-- Procedimiento para limpiar logs antiguos
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_LimpiarHikLogsAntiguos')
    DROP PROCEDURE [dbo].[sp_LimpiarHikLogsAntiguos]
GO

CREATE PROCEDURE [dbo].[sp_LimpiarHikLogsAntiguos]
    @DiasAConservar INT = 30
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @FechaLimite DATETIME
    SET @FechaLimite = DATEADD(DAY, -@DiasAConservar, GETDATE())
    
    DELETE FROM [dbo].[hiklog]
    WHERE Timestamp < @FechaLimite
    
    SELECT @@ROWCOUNT as RegistrosEliminados
END
GO
PRINT 'Procedimiento sp_LimpiarHikLogsAntiguos creado'

-- Procedimiento para sincronizar persona con dispositivos
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_SincronizarPersonaHikvision')
    DROP PROCEDURE [dbo].[sp_SincronizarPersonaHikvision]
GO

CREATE PROCEDURE [dbo].[sp_SincronizarPersonaHikvision]
    @PersonaID INT,
    @DispositivosIDs VARCHAR(500) = NULL, -- IDs separados por coma, NULL = todos
    @Accion VARCHAR(20) = 'CREATE' -- CREATE, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validar que la persona existe
    IF NOT EXISTS (SELECT 1 FROM [dbo].[per] WHERE PersonaID = @PersonaID)
    BEGIN
        RAISERROR('La persona con ID %d no existe', 16, 1, @PersonaID)
        RETURN
    END
    
    -- Si no se especifican dispositivos, usar todos los activos
    IF @DispositivosIDs IS NULL
    BEGIN
        SELECT @DispositivosIDs = STUFF((
            SELECT ',' + DispositivoID
            FROM [dbo].[hikvision]
            WHERE Tipo = 'AccessControl' AND Activo = 1
            FOR XML PATH('')
        ), 1, 1, '')
    END
    
    -- Registrar en perhik si es CREATE o UPDATE
    IF @Accion IN ('CREATE', 'UPDATE')
    BEGIN
        -- Crear tabla temporal con dispositivos
        DECLARE @Dispositivos TABLE (DispositivoID VARCHAR(50))
        
        DECLARE @xml XML
        SET @xml = CAST('<root><item>' + REPLACE(@DispositivosIDs, ',', '</item><item>') + '</item></root>' AS XML)
        
        INSERT INTO @Dispositivos
        SELECT LTRIM(RTRIM(item.value('.', 'VARCHAR(50)')))
        FROM @xml.nodes('/root/item') x(item)
        WHERE LTRIM(RTRIM(item.value('.', 'VARCHAR(50)'))) <> ''
        
        -- Insertar/actualizar registros en perhik
        MERGE [dbo].[perhik] AS target
        USING @Dispositivos AS source
        ON target.PersonaID = @PersonaID AND target.DispositivoID = source.DispositivoID
        WHEN MATCHED THEN
            UPDATE SET 
                Activo = 1,
                FechaUltimaSync = GETDATE()
        WHEN NOT MATCHED THEN
            INSERT (PersonaID, DispositivoID, GrupoID, Activo, FechaUltimaSync)
            VALUES (@PersonaID, source.DispositivoID, 1, 1, GETDATE());
    END
    
    -- Si es DELETE, marcar como inactivo
    IF @Accion = 'DELETE'
    BEGIN
        UPDATE [dbo].[perhik]
        SET Activo = 0, FechaUltimaSync = GETDATE()
        WHERE PersonaID = @PersonaID
        AND (@DispositivosIDs IS NULL OR DispositivoID IN (
            SELECT LTRIM(RTRIM(value))
            FROM STRING_SPLIT(@DispositivosIDs, ',')
        ))
    END
    
    -- Retornar información
    SELECT 
        @PersonaID as PersonaID,
        @Accion as Accion,
        @DispositivosIDs as Dispositivos,
        GETDATE() as FechaProceso
END
GO
PRINT 'Procedimiento sp_SincronizarPersonaHikvision creado'

-- 9. Crear función para obtener dispositivos de una persona
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'fn_GetDispositivosPersona')
    DROP FUNCTION [dbo].[fn_GetDispositivosPersona]
GO

CREATE FUNCTION [dbo].[fn_GetDispositivosPersona](@PersonaID INT)
RETURNS VARCHAR(500)
AS
BEGIN
    DECLARE @Dispositivos VARCHAR(500)
    
    SELECT @Dispositivos = STUFF((
        SELECT ',' + ph.DispositivoID
        FROM [dbo].[perhik] ph
        INNER JOIN [dbo].[hikvision] h ON ph.DispositivoID = h.DispositivoID
        WHERE ph.PersonaID = @PersonaID 
        AND ph.Activo = 1
        AND h.Activo = 1
        AND h.Tipo = 'AccessControl'
        FOR XML PATH('')
    ), 1, 1, '')
    
    RETURN ISNULL(@Dispositivos, '')
END
GO
PRINT 'Función fn_GetDispositivosPersona creada'

-- 10. Crear trigger para auditoría en tabla per
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_per_audit_hikvision')
    DROP TRIGGER [dbo].[tr_per_audit_hikvision]
GO

CREATE TRIGGER [dbo].[tr_per_audit_hikvision]
ON [dbo].[per]
FOR INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Para INSERT
    IF EXISTS (SELECT * FROM inserted) AND NOT EXISTS (SELECT * FROM deleted)
    BEGIN
        INSERT INTO [dbo].[hiklog] (Nivel, PersonaID, Accion, Mensaje)
        SELECT 'INFO', CAST(PersonaID AS VARCHAR(50)), 'PERSONA_CREADA', 
               'Persona creada: ' + Nombre + ' ' + Apellido
        FROM inserted
    END
    
    -- Para UPDATE
    IF EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
    BEGIN
        INSERT INTO [dbo].[hiklog] (Nivel, PersonaID, Accion, Mensaje)
        SELECT 'INFO', CAST(i.PersonaID AS VARCHAR(50)), 'PERSONA_MODIFICADA',
               'Persona modificada: ' + i.Nombre + ' ' + i.Apellido
        FROM inserted i
        INNER JOIN deleted d ON i.PersonaID = d.PersonaID
        WHERE i.Nombre <> d.Nombre OR i.Apellido <> d.Apellido
    END
    
    -- Para DELETE
    IF NOT EXISTS (SELECT * FROM inserted) AND EXISTS (SELECT * FROM deleted)
    BEGIN
        INSERT INTO [dbo].[hiklog] (Nivel, PersonaID, Accion, Mensaje)
        SELECT 'INFO', CAST(PersonaID AS VARCHAR(50)), 'PERSONA_ELIMINADA',
               'Persona eliminada: ' + Nombre + ' ' + Apellido
        FROM deleted
        
        -- Desactivar registros en perhik
        UPDATE [dbo].[perhik]
        SET Activo = 0, FechaUltimaSync = GETDATE()
        WHERE PersonaID IN (SELECT PersonaID FROM deleted)
    END
END
GO
PRINT 'Trigger tr_per_audit_hikvision creado'

-- 11. Insertar datos de ejemplo en perhik para dispositivos existentes
IF EXISTS (SELECT * FROM [dbo].[hikvision] WHERE Tipo = 'AccessControl' AND Activo = 1)
AND EXISTS (SELECT * FROM [dbo].[per])
BEGIN
    -- Relacionar algunas personas existentes con dispositivos AccessControl
    INSERT INTO [dbo].[perhik] (PersonaID, DispositivoID, GrupoID, Activo)
    SELECT DISTINCT 
        p.PersonaID,
        h.DispositivoID,
        1, -- Grupo por defecto
        1  -- Activo
    FROM (SELECT TOP 5 PersonaID FROM [dbo].[per] ORDER BY PersonaID) p
    CROSS JOIN [dbo].[hikvision] h
    WHERE h.Tipo = 'AccessControl' AND h.Activo = 1
    AND NOT EXISTS (
        SELECT 1 FROM [dbo].[perhik] ph 
        WHERE ph.PersonaID = p.PersonaID AND ph.DispositivoID = h.DispositivoID
    )
    
    PRINT 'Datos de ejemplo insertados en perhik'
END
GO

-- 12. Mostrar resumen final
SELECT 
    'Tabla' as Tipo,
    name as Nombre,
    'Creada' as Estado
FROM sys.tables 
WHERE name IN ('hiklog', 'gruhik', 'perhik')

UNION ALL

SELECT 
    'Vista' as Tipo,
    name as Nombre,
    'Creada' as Estado
FROM sys.views 
WHERE name IN ('vw_hiklog_resumen', 'vw_hikvision_activos')

UNION ALL

SELECT 
    'Procedimiento' as Tipo,
    name as Nombre,
    'Creado' as Estado
FROM sys.procedures 
WHERE name LIKE 'sp_%Hik%'

UNION ALL

SELECT 
    'Función' as Tipo,
    name as Nombre,
    'Creada' as Estado
FROM sys.objects 
WHERE type = 'FN' AND name LIKE '%Persona%'

UNION ALL

SELECT 
    'Trigger' as Tipo,
    name as Nombre,
    'Creado' as Estado
FROM sys.triggers 
WHERE name LIKE '%hikvision%'

ORDER BY Tipo, Nombre
GO

PRINT '==============================================='
PRINT 'INSTALACIÓN COMPLETADA'
PRINT '==============================================='
PRINT 'Tablas creadas: hiklog, gruhik, perhik'
PRINT 'Vistas creadas: vw_hiklog_resumen, vw_hikvision_activos'
PRINT 'Procedimientos: sp_GetHikLogsRecientes, sp_LimpiarHikLogsAntiguos, sp_SincronizarPersonaHikvision'
PRINT 'Función: fn_GetDispositivosPersona'
PRINT 'Trigger: tr_per_audit_hikvision'
PRINT '==============================================='
