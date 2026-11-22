/* =============================================================================
   Contex FYG · Usuario de SOLO LECTURA para la app
   Lo ejecuta el administrador de la base. La app nunca escribe en el ERP.
   Cambiar la contraseña y el nombre de la base antes de ejecutar.
   ============================================================================= */
CREATE LOGIN app_trazabilidad WITH PASSWORD = 'CambiarEstaClave#2026', CHECK_POLICY = ON;
GO
USE [NOMBRE_BASE_ERP];
GO
CREATE USER app_trazabilidad FOR LOGIN app_trazabilidad;
GO
CREATE SCHEMA app AUTHORIZATION dbo;   -- aquí viven las vistas que lee la app
GO
GRANT SELECT ON SCHEMA::app TO app_trazabilidad;   -- solo puede leer las vistas del esquema app
GO
