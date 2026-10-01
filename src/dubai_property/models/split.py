"""Out-of-time split for the AVM (docs/05 §1): never random, time order is the point.

| Set | Months | Use |
|---|---|---|
| history | 2010 | trailing features of early-2011 sales only (never fitted or scored) |
| train | 2011-01 to 2023-12 | fit |
| validation | 2024-01 to 2024-12 | early stopping, Optuna tuning, champion choice |
| test | 2025-01 to the data snapshot | the reported numbers |

A random split would put 2025 sales in training next to their own neighbours and month,
which is leakage by another name. The test period includes the 2026 slowdown (Jan-Aug
2026 sales -19% on 2025, findings F1), so accuracy is also reported by month.
"""

from __future__ import annotations

import polars as pl

from dubai_property import config

SPLITS = ("history", "train", "validation", "test")


def split_expr(col: str = "month", train_start=config.AVM_TRAIN_START) -> pl.Expr:
    """``history`` / ``train`` / ``validation`` / ``test`` from the sale's date."""
    d = pl.col(col)
    return (
        pl.when(d < train_start)
        .then(pl.lit("history"))
        .when(d <= config.TRAIN_END)
        .then(pl.lit("train"))
        .when(d <= config.VALID_END)
        .then(pl.lit("validation"))
        .otherwise(pl.lit("test"))
        .alias("split")
    )


def assign_split(df: pl.DataFrame, col: str = "month", train_start=config.AVM_TRAIN_START):
    """``df`` with a ``split`` column (see the module table)."""
    return df.with_columns(split_expr(col, train_start))
