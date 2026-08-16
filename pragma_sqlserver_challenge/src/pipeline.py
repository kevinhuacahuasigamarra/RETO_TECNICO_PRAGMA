from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyodbc

from .config import build_connection_string, get_chunk_size
from .database import (
    get_incremental_stats,
    is_file_processed,
    update_incremental_stats,
)
from .statistics import batch_statistics


REQUIRED_COLUMNS = ["timestamp", "price", "user_id"]


def validate_columns(df: pd.DataFrame, file_name: str) -> None:
    actual = list(df.columns)
    if actual != REQUIRED_COLUMNS:
        raise ValueError(
            f"{file_name}: columnas inválidas. "
            f"Esperadas={REQUIRED_COLUMNS}; recibidas={actual}"
        )


def prepare_chunk(df: pd.DataFrame, file_name: str) -> pd.DataFrame:
    validate_columns(df, file_name)

    clean = df.copy()

    # Los archivos están en formato mes/día/año: 2/29/2012 confirma esa interpretación.
    clean["timestamp"] = pd.to_datetime(
        clean["timestamp"],
        format="%m/%d/%Y",
        errors="raise",
    )

    clean["price"] = pd.to_numeric(clean["price"], errors="coerce")
    clean["user_id"] = pd.to_numeric(clean["user_id"], errors="raise")

    if clean["timestamp"].isna().any():
        raise ValueError(f"{file_name}: existen timestamp nulos.")

    if clean["user_id"].isna().any():
        raise ValueError(f"{file_name}: existen user_id nulos.")

    if (clean["user_id"] <= 0).any():
        raise ValueError(f"{file_name}: user_id debe ser mayor que cero.")

    return clean



def insert_chunk(cursor, df: pd.DataFrame, source_file: str) -> None:
    rows = []
    for row in df.itertuples(index=False):
        price_value = None if pd.isna(row.price) else Decimal(str(row.price))
        rows.append(
            (
                row.timestamp.to_pydatetime(),
                price_value,
                int(row.user_id),
                source_file,
            )
        )

    cursor.fast_executemany = True
    cursor.executemany(
        """
        INSERT INTO dbo.transactions
        (
            event_timestamp,
            price,
            user_id,
            source_file
        )
        VALUES (?, ?, ?, ?);
        """,
        rows,
    )


def format_number(value, decimals: int = 4) -> str:
    if value is None or pd.isna(value):
        return "NULL"
    return f"{Decimal(str(value)):.{decimals}f}"


def print_stats(title: str, stats: dict) -> None:
    """Imprime las estadísticas solicitadas explícitamente por el reto."""
    print("\n" + "=" * 72)
    print(title)
    print("-" * 72)
    print(f"COUNT                  : {stats['total_rows']}")
    print(f"AVG(price)             : {format_number(stats['avg_price'])}")
    print(f"MIN(price)             : {format_number(stats['min_price'])}")
    print(f"MAX(price)             : {format_number(stats['max_price'])}")
    print(f"Prices no nulos        : {stats['valid_price_count']}")
    print("=" * 72)


def process_file(file_path: Path) -> dict:
    file_name = file_path.name
    chunk_size = get_chunk_size()

    conn = pyodbc.connect(build_connection_string(), autocommit=False)

    try:
        cursor = conn.cursor()

        if is_file_processed(cursor, file_name):
            print(f"\n[SKIP] {file_name} ya fue procesado anteriormente.")
            stats = get_incremental_stats(cursor)
            conn.rollback()
            return stats

        print(f"\n[ARCHIVO] Procesando {file_name}")
        print(f"[MICRO-BATCH] chunk_size = {chunk_size}")

        total_file_rows = 0
        total_file_valid_prices = 0

        # CLAVE DEL RETO:
        # read_csv(chunksize=...) evita tener todo el conjunto de archivos en memoria.
        for chunk_number, raw_chunk in enumerate(
            pd.read_csv(file_path, chunksize=chunk_size),
            start=1,
        ):
            chunk = prepare_chunk(raw_chunk, file_name)
            bstats = batch_statistics(chunk)

            insert_chunk(cursor, chunk, file_name)

            current = update_incremental_stats(
                cursor=cursor,
                source_file=file_name,
                chunk_number=chunk_number,
                rows_in_chunk=bstats["rows"],
                valid_price_count=bstats["valid_price_count"],
                price_sum=bstats["price_sum"],
                min_price=bstats["min_price"],
                max_price=bstats["max_price"],
            )

            total_file_rows += bstats["rows"]
            total_file_valid_prices += bstats["valid_price_count"]

            # Con chunk_size = 1, mostramos la fila recién insertada y las
            # cuatro estadísticas acumuladas requeridas por el reto.
            if len(chunk) == 1:
                current_price = chunk.iloc[0]["price"]
                print(
                    f"Fila {current['total_rows']:>3} | "
                    f"price={format_number(current_price):>8} | "
                    f"COUNT={current['total_rows']:>3} | "
                    f"AVG={format_number(current['avg_price']):>8} | "
                    f"MIN={format_number(current['min_price']):>8} | "
                    f"MAX={format_number(current['max_price']):>8}"
                )
            else:
                # Se mantiene compatibilidad si en un escenario real se aumenta
                # chunk_size a más de una fila.
                print(
                    f"Micro-batch {chunk_number:>3} | "
                    f"filas={bstats['rows']:>4} | "
                    f"COUNT={current['total_rows']:>6} | "
                    f"AVG={format_number(current['avg_price']):>10} | "
                    f"MIN={format_number(current['min_price']):>10} | "
                    f"MAX={format_number(current['max_price']):>10}"
                )

        cursor.execute(
            """
            INSERT INTO dbo.processed_files
            (
                file_name,
                rows_loaded,
                valid_price_count
            )
            VALUES (?, ?, ?);
            """,
            file_name,
            total_file_rows,
            total_file_valid_prices,
        )

        # Un archivo se confirma de forma atómica.
        # Si falla a mitad, rollback evita una carga parcial duplicable.
        conn.commit()

        final_stats = get_incremental_stats(cursor)
        print_stats(f"ESTADÍSTICAS DESPUÉS DE {file_name}", final_stats)
        return final_stats

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
