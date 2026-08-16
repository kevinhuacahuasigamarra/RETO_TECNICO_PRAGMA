from __future__ import annotations

from decimal import Decimal
import pyodbc

from .config import build_connection_string, get_database_name


SCHEMA_SQL = r"""
IF OBJECT_ID(N'dbo.transactions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.transactions
    (
        transaction_id BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_transactions PRIMARY KEY,
        event_timestamp DATETIME2(0) NOT NULL,
        price DECIMAL(18,4) NULL,
        user_id BIGINT NOT NULL,
        source_file VARCHAR(100) NOT NULL,
        ingested_at DATETIME2(0) NOT NULL
            CONSTRAINT DF_transactions_ingested_at DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_transactions_source_file
        ON dbo.transactions(source_file);

    CREATE INDEX IX_transactions_event_timestamp
        ON dbo.transactions(event_timestamp);
END;

IF OBJECT_ID(N'dbo.processed_files', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.processed_files
    (
        file_name VARCHAR(100) NOT NULL
            CONSTRAINT PK_processed_files PRIMARY KEY,
        rows_loaded BIGINT NOT NULL,
        valid_price_count BIGINT NOT NULL,
        processed_at DATETIME2(0) NOT NULL
            CONSTRAINT DF_processed_files_processed_at DEFAULT SYSUTCDATETIME()
    );
END;

IF OBJECT_ID(N'dbo.pipeline_statistics', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.pipeline_statistics
    (
        statistics_id TINYINT NOT NULL
            CONSTRAINT PK_pipeline_statistics PRIMARY KEY,
        total_rows BIGINT NOT NULL,
        valid_price_count BIGINT NOT NULL,
        price_sum DECIMAL(38,4) NOT NULL,
        avg_price DECIMAL(38,10) NULL,
        min_price DECIMAL(18,4) NULL,
        max_price DECIMAL(18,4) NULL,
        updated_at DATETIME2(0) NOT NULL,
        CONSTRAINT CK_pipeline_statistics_single_row CHECK (statistics_id = 1)
    );

    INSERT INTO dbo.pipeline_statistics
    (
        statistics_id, total_rows, valid_price_count, price_sum,
        avg_price, min_price, max_price, updated_at
    )
    VALUES (1, 0, 0, 0, NULL, NULL, NULL, SYSUTCDATETIME());
END;

IF OBJECT_ID(N'dbo.statistics_history', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.statistics_history
    (
        history_id BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_statistics_history PRIMARY KEY,
        source_file VARCHAR(100) NOT NULL,
        chunk_number INT NOT NULL,
        rows_in_chunk INT NOT NULL,
        total_rows BIGINT NOT NULL,
        valid_price_count BIGINT NOT NULL,
        price_sum DECIMAL(38,4) NOT NULL,
        avg_price DECIMAL(38,10) NULL,
        min_price DECIMAL(18,4) NULL,
        max_price DECIMAL(18,4) NULL,
        recorded_at DATETIME2(0) NOT NULL
            CONSTRAINT DF_statistics_history_recorded_at DEFAULT SYSUTCDATETIME()
    );
END;
"""


def create_database_if_needed() -> None:
    db_name = get_database_name().replace("]", "]]")
    conn = pyodbc.connect(build_connection_string("master"), autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"IF DB_ID(N'{db_name.replace(chr(39), chr(39)*2)}') IS NULL "
            f"CREATE DATABASE [{db_name}]"
        )
    finally:
        conn.close()


def ensure_schema() -> None:
    conn = pyodbc.connect(build_connection_string(), autocommit=False)
    try:
        cursor = conn.cursor()
        cursor.execute(SCHEMA_SQL)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_pipeline() -> None:
    conn = pyodbc.connect(build_connection_string(), autocommit=False)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dbo.statistics_history;")
        cursor.execute("DELETE FROM dbo.processed_files;")
        cursor.execute("DELETE FROM dbo.transactions;")

        # Para una ejecución de demostración realmente limpia, reiniciamos
        # los IDENTITY después de borrar los datos.
        cursor.execute("DBCC CHECKIDENT ('dbo.statistics_history', RESEED, 0);")
        cursor.execute("DBCC CHECKIDENT ('dbo.transactions', RESEED, 0);")
        cursor.execute(
            """
            UPDATE dbo.pipeline_statistics
            SET total_rows = 0,
                valid_price_count = 0,
                price_sum = 0,
                avg_price = NULL,
                min_price = NULL,
                max_price = NULL,
                updated_at = SYSUTCDATETIME()
            WHERE statistics_id = 1;
            """
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_file_processed(cursor, file_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM dbo.processed_files WHERE file_name = ?;",
        file_name,
    )
    return cursor.fetchone() is not None


def get_incremental_stats(cursor) -> dict:
    cursor.execute(
        """
        SELECT
            total_rows,
            valid_price_count,
            price_sum,
            avg_price,
            min_price,
            max_price
        FROM dbo.pipeline_statistics
        WHERE statistics_id = 1;
        """
    )
    row = cursor.fetchone()
    return {
        "total_rows": int(row.total_rows),
        "valid_price_count": int(row.valid_price_count),
        "price_sum": row.price_sum,
        "avg_price": row.avg_price,
        "min_price": row.min_price,
        "max_price": row.max_price,
    }


def update_incremental_stats(
    cursor,
    source_file: str,
    chunk_number: int,
    rows_in_chunk: int,
    valid_price_count: int,
    price_sum: Decimal,
    min_price: Decimal | None,
    max_price: Decimal | None,
) -> dict:
    current = get_incremental_stats(cursor)

    new_total_rows = current["total_rows"] + rows_in_chunk
    new_valid_count = current["valid_price_count"] + valid_price_count
    new_sum = Decimal(str(current["price_sum"])) + price_sum

    current_min = (
        Decimal(str(current["min_price"])) if current["min_price"] is not None else None
    )
    current_max = (
        Decimal(str(current["max_price"])) if current["max_price"] is not None else None
    )

    if min_price is None:
        new_min = current_min
    elif current_min is None:
        new_min = min_price
    else:
        new_min = min(current_min, min_price)

    if max_price is None:
        new_max = current_max
    elif current_max is None:
        new_max = max_price
    else:
        new_max = max(current_max, max_price)

    new_avg = (
        (new_sum / Decimal(new_valid_count))
        if new_valid_count > 0
        else None
    )

    cursor.execute(
        """
        UPDATE dbo.pipeline_statistics
        SET
            total_rows = ?,
            valid_price_count = ?,
            price_sum = ?,
            avg_price = ?,
            min_price = ?,
            max_price = ?,
            updated_at = SYSUTCDATETIME()
        WHERE statistics_id = 1;
        """,
        new_total_rows,
        new_valid_count,
        new_sum,
        new_avg,
        new_min,
        new_max,
    )

    cursor.execute(
        """
        INSERT INTO dbo.statistics_history
        (
            source_file, chunk_number, rows_in_chunk,
            total_rows, valid_price_count, price_sum,
            avg_price, min_price, max_price
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        source_file,
        chunk_number,
        rows_in_chunk,
        new_total_rows,
        new_valid_count,
        new_sum,
        new_avg,
        new_min,
        new_max,
    )

    return {
        "total_rows": new_total_rows,
        "valid_price_count": new_valid_count,
        "price_sum": new_sum,
        "avg_price": new_avg,
        "min_price": new_min,
        "max_price": new_max,
    }


def query_database_stats() -> dict:
    conn = pyodbc.connect(build_connection_string())
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_rows,
                COUNT(price) AS valid_price_count,
                COALESCE(SUM(price), 0) AS price_sum,
                AVG(price) AS avg_price,
                MIN(price) AS min_price,
                MAX(price) AS max_price
            FROM dbo.transactions;
            """
        )
        row = cursor.fetchone()
        return {
            "total_rows": int(row.total_rows),
            "valid_price_count": int(row.valid_price_count),
            "price_sum": row.price_sum,
            "avg_price": row.avg_price,
            "min_price": row.min_price,
            "max_price": row.max_price,
        }
    finally:
        conn.close()
