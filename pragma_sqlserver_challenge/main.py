from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
import sys

from src.config import DATA_DIR
from src.database import (
    create_database_if_needed,
    ensure_schema,
    query_database_stats,
    reset_pipeline,
)
from src.pipeline import process_file, print_stats


MAIN_FILES = [
    "2012-1.csv",
    "2012-2.csv",
    "2012-3.csv",
    "2012-4.csv",
    "2012-5.csv",
]
VALIDATION_FILE = "validation.csv"


def decimal_close(a, b, tolerance=Decimal("0.000001")) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(Decimal(str(a)) - Decimal(str(b))) <= tolerance


def verify(incremental: dict, database: dict) -> None:
    checks = {
        "total_rows": incremental["total_rows"] == database["total_rows"],
        "valid_price_count": (
            incremental["valid_price_count"] == database["valid_price_count"]
        ),
        "price_sum": decimal_close(incremental["price_sum"], database["price_sum"]),
        "avg_price": decimal_close(incremental["avg_price"], database["avg_price"]),
        "min_price": decimal_close(incremental["min_price"], database["min_price"]),
        "max_price": decimal_close(incremental["max_price"], database["max_price"]),
    }

    print("\nCOMPROBACIÓN INCREMENTAL VS CONSULTA DIRECTA A SQL SERVER")
    print("-" * 72)
    for key, ok in checks.items():
        print(f"{key:20} {'OK' if ok else 'ERROR'}")

    if not all(checks.values()):
        raise RuntimeError(
            "Las estadísticas incrementales no coinciden con la consulta de validación."
        )

    print("RESULTADO: todas las estadísticas coinciden.\n")


def ensure_files() -> None:
    expected = MAIN_FILES + [VALIDATION_FILE]
    missing = [name for name in expected if not (DATA_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Faltan archivos en la carpeta data/: " + ", ".join(missing)
        )


def run(reset: bool) -> None:
    print("\nPRAGMA - PRUEBA DE INGENIERÍA DE DATOS")
    print("Pipeline micro-batch con Python + SQL Server")
    print("=" * 72)

    ensure_files()

    print("\n[1/6] Verificando/creando base de datos...")
    create_database_if_needed()

    print("[2/6] Verificando/creando tablas...")
    ensure_schema()

    if reset:
        print("[3/6] Reiniciando datos para una demostración limpia...")
        reset_pipeline()
    else:
        print("[3/6] Conservando datos existentes (modo idempotente).")

    print("\n[4/6] Cargando los cinco archivos principales...")
    last_stats = None
    for file_name in MAIN_FILES:
        last_stats = process_file(DATA_DIR / file_name)

    print("\n[5/6] Comprobación ANTES de validation.csv")
    db_stats_before = query_database_stats()
    print_stats("CONSULTA DIRECTA A SQL SERVER - ANTES DE VALIDATION", db_stats_before)
    verify(last_stats, db_stats_before)

    print("\n[6/6] Ejecutando validation.csv por TODO el mismo pipeline...")
    final_incremental = process_file(DATA_DIR / VALIDATION_FILE)

    db_stats_after = query_database_stats()
    print_stats("CONSULTA DIRECTA A SQL SERVER - DESPUÉS DE VALIDATION", db_stats_after)
    verify(final_incremental, db_stats_after)

    print("=" * 72)
    print("PIPELINE FINALIZADO CORRECTAMENTE")
    print("Abre SSMS y ejecuta: sql/02_validation_queries.sql")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PRAGMA Data Engineer Challenge - SQL Server micro-batch pipeline"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Limpia las tablas antes de ejecutar toda la demostración.",
    )
    args = parser.parse_args()

    try:
        run(reset=args.reset)
        return 0
    except Exception as exc:
        print("\n[ERROR]")
        print(exc)
        print(
            "\nRevisa config.ini, que SQL Server esté iniciado y "
            "que el driver ODBC esté instalado."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
