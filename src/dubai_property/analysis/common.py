"""Shared helpers for the analysis modules: SQL runner, snapshot date, min-n, scope."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import Engine, text

from dubai_property import config, db

# Reporting scope ends at the data snapshot date, which is data (rpt.report_info), not config.
SNAPSHOT_SQL = 'select "Data As Of" as snapshot from rpt.report_info'


def query(sql: str, params: Mapping[str, Any] | None = None, engine: Engine | None = None):
    """Run one SQL statement and return the (small) result as a pandas DataFrame.

    Args:
        sql: SQL with ``:name`` bind parameters.
        params: Values for the bind parameters.
        engine: SQLAlchemy engine; defaults to ``db.get_engine()``.
    """
    engine = engine or db.get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=dict(params or {}))


def snapshot_date(engine: Engine | None = None) -> date:
    """The data snapshot date (latest transaction date), "Data As Of" in the report."""
    value = query(SNAPSHOT_SQL, engine=engine)["snapshot"].iloc[0]
    return pd.Timestamp(value).date()


def last_12_months(snapshot: date) -> tuple[date, date]:
    """First and last day of the 12 months ending on the snapshot date (inclusive)."""
    start = (pd.Timestamp(snapshot) - pd.DateOffset(years=1) + pd.Timedelta(days=1)).date()
    return start, snapshot


def is_partial_year(year: int, snapshot: date) -> bool:
    """True when the year is not complete in the data (the snapshot falls before 31 Dec)."""
    return year == snapshot.year and snapshot < date(year, 12, 31)


def apply_min_n(
    df: pd.DataFrame,
    n_col: str | Iterable[str],
    value_cols: Iterable[str],
    min_n: int = config.MIN_N,
) -> pd.DataFrame:
    """Blank (NaN) the values of every row whose n is under the min-n rule (CLAUDE.md).

    Args:
        df: Frame with one row per segment.
        n_col: Column (or columns, all of which must pass) holding the observations.
        value_cols: Columns to blank when n < ``min_n``; n itself is kept, so the reader
            can see why a value is missing.
        min_n: Threshold, ``config.MIN_N`` (20) by default.

    Returns:
        A copy of ``df`` with the thin segments blanked.
    """
    n_cols = [n_col] if isinstance(n_col, str) else list(n_col)
    out = df.copy()
    thin = (out[n_cols].fillna(0) < min_n).any(axis=1)
    for col in value_cols:
        out[col] = out[col].astype("float64").mask(thin)
    return out
