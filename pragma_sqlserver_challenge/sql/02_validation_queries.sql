/*
Consultas para demostrar la prueba desde SQL Server Management Studio (SSMS).
Ejecutar después del pipeline.
*/

USE PragmaDataChallenge;
GO

-- 1. Datos cargados
SELECT TOP (100)
    transaction_id,
    event_timestamp,
    price,
    user_id,
    source_file,
    ingested_at
FROM dbo.transactions
ORDER BY transaction_id;
GO

-- 2. Archivos procesados
SELECT
    file_name,
    rows_loaded,
    valid_price_count,
    processed_at
FROM dbo.processed_files
ORDER BY processed_at, file_name;
GO

-- 3. Estadística incremental mantenida por el pipeline
SELECT
    total_rows,
    valid_price_count,
    price_sum,
    avg_price,
    min_price,
    max_price,
    updated_at
FROM dbo.pipeline_statistics
WHERE statistics_id = 1;
GO

-- 4. Comprobación independiente contra los datos persistidos.
-- IMPORTANTE:
-- COUNT(*) cuenta todas las filas.
-- AVG/MIN/MAX(price) ignoran automáticamente los NULL de price.
SELECT
    COUNT(*) AS total_rows,
    COUNT(price) AS valid_price_count,
    SUM(price) AS price_sum,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM dbo.transactions;
GO

-- 5. Historial de cada micro-batch
SELECT
    history_id,
    source_file,
    chunk_number,
    rows_in_chunk,
    total_rows,
    valid_price_count,
    price_sum,
    avg_price,
    min_price,
    max_price,
    recorded_at
FROM dbo.statistics_history
ORDER BY history_id;
GO

-- 6. Conteo por archivo
SELECT
    source_file,
    COUNT(*) AS rows_loaded,
    COUNT(price) AS valid_price_count,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM dbo.transactions
GROUP BY source_file
ORDER BY source_file;
GO
