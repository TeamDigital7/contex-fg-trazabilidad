/* =============================================================================
   Contex FYG · Paso 1: conocer las tablas del ERP (HDSOFT, SQL Server)
   -----------------------------------------------------------------------------
   SOLO LECTURA: no crea, no modifica y no borra nada. Solo consulta el catálogo
   del sistema (INFORMATION_SCHEMA / sys). Ejecutar en SQL Server Management
   Studio sobre la base del ERP y exportar los 3 resultados a Excel.
   Con eso se escriben las vistas que lee la app (paso 2).
   ============================================================================= */

-- 1) Tablas y vistas con su cantidad de filas (para saber cuáles se usan de verdad)
SELECT  s.name                       AS esquema,
        t.name                       AS tabla,
        SUM(p.rows)                  AS filas
FROM    sys.tables t
JOIN    sys.schemas s     ON s.schema_id = t.schema_id
JOIN    sys.partitions p  ON p.object_id = t.object_id AND p.index_id IN (0, 1)
GROUP BY s.name, t.name
ORDER BY filas DESC;

-- 2) Las tablas que probablemente son del flujo de producción y costos
--    (cotización, OT, orden de proceso, liquidación, kardex, almacén, guías)
SELECT  c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION, c.COLUMN_NAME, c.DATA_TYPE,
        c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE
FROM    INFORMATION_SCHEMA.COLUMNS c
WHERE   c.TABLE_NAME LIKE '%COTIZ%'  OR c.TABLE_NAME LIKE '%ORDEN%'   OR c.TABLE_NAME LIKE '%OT%'
     OR c.TABLE_NAME LIKE '%PROCES%' OR c.TABLE_NAME LIKE '%LIQUID%'  OR c.TABLE_NAME LIKE '%KARDEX%'
     OR c.TABLE_NAME LIKE '%ALMAC%'  OR c.TABLE_NAME LIKE '%PARTE%'   OR c.TABLE_NAME LIKE '%GUIA%'
     OR c.TABLE_NAME LIKE '%PRODUC%' OR c.TABLE_NAME LIKE '%FICHA%'   OR c.TABLE_NAME LIKE '%CLIENT%'
     OR c.TABLE_NAME LIKE '%PROVEED%' OR c.TABLE_NAME LIKE '%PERSONAL%' OR c.TABLE_NAME LIKE '%SERVIC%'
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;

-- 3) Relaciones entre tablas (claves foráneas), si el ERP las declara
SELECT  fk.name                            AS relacion,
        OBJECT_NAME(fk.parent_object_id)   AS tabla,
        COL_NAME(fc.parent_object_id, fc.parent_column_id)       AS columna,
        OBJECT_NAME(fk.referenced_object_id)                     AS tabla_referida,
        COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS columna_referida
FROM    sys.foreign_keys fk
JOIN    sys.foreign_key_columns fc ON fc.constraint_object_id = fk.object_id
ORDER BY tabla;
