from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import pyodbc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_ROOT / "config.ini"
DATA_DIR = PROJECT_ROOT / "data"


def load_config() -> ConfigParser:
    config = ConfigParser()
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No existe el archivo de configuración: {CONFIG_FILE}")
    config.read(CONFIG_FILE, encoding="utf-8")
    return config


def resolve_driver(configured_driver: str) -> str:
    installed = list(pyodbc.drivers())

    if configured_driver in installed:
        return configured_driver

    preferred = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server",
    ]
    for driver in preferred:
        if driver in installed:
            print(
                f"[AVISO] El driver configurado '{configured_driver}' no está instalado. "
                f"Se usará '{driver}'."
            )
            return driver

    raise RuntimeError(
        "No se encontró un driver ODBC para SQL Server.\n"
        f"Drivers detectados: {installed}\n"
        "Instala Microsoft ODBC Driver for SQL Server y vuelve a ejecutar."
    )


def connection_settings(database: str | None = None) -> dict:
    cfg = load_config()
    sql = cfg["sqlserver"]

    driver = resolve_driver(sql.get("driver", "ODBC Driver 18 for SQL Server"))
    server = sql.get("server", r"localhost\SQLEXPRESS")
    db = database or sql.get("database", "PragmaDataChallenge")
    trusted = sql.getboolean("trusted_connection", fallback=True)
    trust_cert = sql.getboolean("trust_server_certificate", fallback=True)

    return {
        "driver": driver,
        "server": server,
        "database": db,
        "trusted": trusted,
        "username": sql.get("username", ""),
        "password": sql.get("password", ""),
        "trust_cert": trust_cert,
    }


def build_connection_string(database: str | None = None) -> str:
    settings = connection_settings(database)

    parts = [
        f"DRIVER={{{settings['driver']}}}",
        f"SERVER={settings['server']}",
        f"DATABASE={settings['database']}",
        f"TrustServerCertificate={'yes' if settings['trust_cert'] else 'no'}",
    ]

    if settings["trusted"]:
        parts.append("Trusted_Connection=yes")
    else:
        parts.extend(
            [
                f"UID={settings['username']}",
                f"PWD={settings['password']}",
            ]
        )

    return ";".join(parts) + ";"


def get_database_name() -> str:
    return load_config()["sqlserver"].get("database", "PragmaDataChallenge")


def get_chunk_size() -> int:
    value = load_config()["pipeline"].getint("chunk_size", fallback=10)
    if value <= 0:
        raise ValueError("chunk_size debe ser mayor que cero.")
    return value
