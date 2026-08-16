from __future__ import annotations

from decimal import Decimal
import pandas as pd


def batch_statistics(df: pd.DataFrame) -> dict:
    """
    Calcula SOLO las estadísticas del micro-batch actual.

    Importante:
    - rows cuenta todas las filas.
    - valid_price_count cuenta solo price no nulos.
    - price_sum/min/max ignoran price nulos.
    """
    price = df["price"]
    valid = price.dropna()

    if valid.empty:
        return {
            "rows": len(df),
            "valid_price_count": 0,
            "price_sum": Decimal("0"),
            "min_price": None,
            "max_price": None,
        }

    values = [Decimal(str(v)) for v in valid.tolist()]

    return {
        "rows": len(df),
        "valid_price_count": len(values),
        "price_sum": sum(values, Decimal("0")),
        "min_price": min(values),
        "max_price": max(values),
    }
