/*
PRAGMA - Prueba de Ingeniería de Datos
SQL Server schema

Este script es opcional porque main.py también puede crear la base y las tablas.
Puedes ejecutarlo manualmente desde SSMS para demostrar el diseño.
*/

USE master;
GO

IF DB_ID(N'PragmaDataChallenge') IS NULL
BEGIN
    CREATE DATABASE PragmaDataChallenge;
END;
GO

USE PragmaDataChallenge;
GO

IF OBJECT_ID(N'dbo.transactions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.transactions
    (
        transaction_id      BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_transactions PRIMARY KEY,
        event_timestamp     DATETIME2(0) NOT NULL,
        price               DECIMAL(18,4) NULL,
        user_id              BIGINT NOT NULL,
        source_file          VARCHAR(100) NOT NULL,
        ingested_at          DATETIME2(0) NOT NULL
            CONSTRAINT DF_transactions_ingested_at DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_transactions_source_file
        ON dbo.transactions(source_file);

    CREATE INDEX IX_transactions_event_timestamp
        ON dbo.transactions(event_timestamp);
END;
GO

IF OBJECT_ID(N'dbo.processed_files', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.processed_files
    (
        file_name            VARCHAR(100) NOT NULL
            CONSTRAINT PK_processed_files PRIMARY KEY,
        rows_loaded          BIGINT NOT NULL,
        valid_price_count    BIGINT NOT NULL,
        processed_at         DATETIME2(0) NOT NULL
            CONSTRAINT DF_processed_files_processed_at DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.pipeline_statistics', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.pipeline_statistics
    (
        statistics_id        TINYINT NOT NULL
            CONSTRAINT PK_pipeline_statistics PRIMARY KEY,
        total_rows           BIGINT NOT NULL,
        valid_price_count    BIGINT NOT NULL,
        price_sum            DECIMAL(38,4) NOT NULL,
        avg_price            DECIMAL(38,10) NULL,
        min_price            DECIMAL(18,4) NULL,
        max_price            DECIMAL(18,4) NULL,
        updated_at           DATETIME2(0) NOT NULL,
        CONSTRAINT CK_pipeline_statistics_single_row
            CHECK (statistics_id = 1)
    );

    INSERT INTO dbo.pipeline_statistics
    (
        statistics_id, total_rows, valid_price_count,
        price_sum, avg_price, min_price, max_price, updated_at
    )
    VALUES
    (
        1, 0, 0, 0, NULL, NULL, NULL, SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.statistics_history', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.statistics_history
    (
        history_id           BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_statistics_history PRIMARY KEY,
        source_file          VARCHAR(100) NOT NULL,
        chunk_number         INT NOT NULL,
        rows_in_chunk        INT NOT NULL,
        total_rows           BIGINT NOT NULL,
        valid_price_count    BIGINT NOT NULL,
        price_sum            DECIMAL(38,4) NOT NULL,
        avg_price            DECIMAL(38,10) NULL,
        min_price            DECIMAL(18,4) NULL,
        max_price            DECIMAL(18,4) NULL,
        recorded_at          DATETIME2(0) NOT NULL
            CONSTRAINT DF_statistics_history_recorded_at DEFAULT SYSUTCDATETIME()
    );
END;
GO
