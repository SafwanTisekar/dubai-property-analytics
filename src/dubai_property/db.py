"""Database connection helpers built from `.env`.

Three access paths, each used for what it does best (docs/03 §4):

* ``connect()``: psycopg 3 connection, used for ``COPY`` bulk loads and writes.
* ``get_engine()``: SQLAlchemy engine, for pandas/Polars ``read_sql`` and ad-hoc SQL.
* ``connectorx_uri()``: URI for connectorx, the fastest way to pull a model-sized
  result set into Polars/pandas.
* ``copy_frame()``: write a model result back with ``COPY`` (never row-by-row inserts).
* ``reports_dir()`` / ``figures_dir()`` / ``artifacts_dir()``: where outputs go, which
  depends on the database in use (scratch databases never write the committed reports).

Credentials come only from environment variables (loaded from `.env`), never code.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import polars as pl
import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import make_conninfo
from sqlalchemy import Engine, create_engine

from dubai_property import config
from dubai_property.config import PROJECT_ROOT

_REQUIRED = ("PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD")


@dataclass(frozen=True)
class PgSettings:
    """Connection settings for the pipeline owner role (``dpa_owner``)."""

    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> PgSettings:
        """Load settings from the environment, reading `.env` first if present.

        Existing environment variables win over `.env`, so CI can inject its own.

        Raises:
            RuntimeError: If any required ``PG_*`` variable is missing or empty.
        """
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        missing = [name for name in _REQUIRED if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                f"Missing database settings: {', '.join(missing)}. "
                "Copy .env.example to .env and fill them in."
            )
        return cls(
            host=os.environ["PG_HOST"],
            port=int(os.environ["PG_PORT"]),
            dbname=os.environ["PG_DB"],
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
        )

    def conninfo(self) -> str:
        """Return a libpq conninfo string (values are quoted/escaped by psycopg)."""
        return make_conninfo(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )

    def _url(self, scheme: str) -> str:
        # URL-encode user and password so characters like @ : / # don't break the URI.
        return (
            f"{scheme}://{quote(self.user, safe='')}:{quote(self.password, safe='')}"
            f"@{self.host}:{self.port}/{quote(self.dbname, safe='')}"
        )

    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy URL that uses the psycopg 3 driver."""
        return self._url("postgresql+psycopg")

    def connectorx_uri(self) -> str:
        """Return a plain ``postgresql://`` URI as expected by connectorx."""
        return self._url("postgresql")


def connect(settings: PgSettings | None = None, **kwargs: object) -> psycopg.Connection:
    """Open a psycopg 3 connection (use as a context manager).

    Args:
        settings: Connection settings; defaults to ``PgSettings.from_env()``.
        **kwargs: Passed through to ``psycopg.connect`` (e.g. ``autocommit=True``).
    """
    settings = settings or PgSettings.from_env()
    return psycopg.connect(settings.conninfo(), **kwargs)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine for the ``dubai_property`` database."""
    return create_engine(PgSettings.from_env().sqlalchemy_url(), pool_pre_ping=True)


def connectorx_uri() -> str:
    """Return the connectorx URI for the configured database."""
    return PgSettings.from_env().connectorx_uri()


# --- Where outputs go: the main database writes the committed reports, others don't ---
# Reports, figures and model artifacts describe the database they were computed from. A
# run against a scratch or fixture database (e.g. the CI sequence reproduced locally with
# PG_DB=dpa_scratch) must never overwrite the committed reports/*.md, which describe the
# full register: in Phase 4a one such run replaced reports/kpi_reconciliation.md with
# fixture numbers. So every DB-derived writer resolves its directory here, at run time.
def current_dbname() -> str:
    """The database this process talks to (``PG_DB``, `.env` read first)."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return os.environ.get("PG_DB") or config.MAIN_DB


def is_main_db() -> bool:
    """True when ``PG_DB`` is the project database whose results are committed."""
    return current_dbname() == config.MAIN_DB


def _scratch_name() -> str:
    # Database names may hold characters a folder name shouldn't.
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", current_dbname())


def reports_dir() -> Path:
    """``reports/`` for the main database, else ``reports/scratch/<db>/`` (gitignored)."""
    if is_main_db():
        return config.REPORTS
    path = config.REPORTS / config.SCRATCH_DIRNAME / _scratch_name()
    path.mkdir(parents=True, exist_ok=True)
    return path


def figures_dir() -> Path:
    """``figures/`` under :func:`reports_dir` (``reports/figures`` for the main DB)."""
    return reports_dir() / config.FIGURES.name


def artifacts_dir() -> Path:
    """``artifacts/`` for the main database, else ``artifacts/scratch/<db>/``."""
    if is_main_db():
        return config.ARTIFACTS
    return config.ARTIFACTS / config.SCRATCH_DIRNAME / _scratch_name()


def copy_frame(conn: psycopg.Connection, df: pl.DataFrame, schema: str, table: str) -> int:
    """Append a Polars frame to an existing table with ``COPY ... FROM STDIN`` (CSV).

    Columns are matched by name, so the frame may list them in any order and the table may
    have extra columns with defaults. Nulls are written as unquoted empty fields, which
    COPY reads as NULL. The caller owns the transaction (commit or roll back).

    Args:
        conn: Open psycopg connection.
        df: Rows to write; column names must exist in the table.
        schema: Target schema (e.g. ``ml``).
        table: Target table.

    Returns:
        The number of rows COPY reported, which the caller should log.
    """
    if df.is_empty():
        return 0
    buffer = io.BytesIO()
    df.write_csv(buffer, include_header=False, null_value="", date_format="%Y-%m-%d")
    stmt = sql.SQL("copy {}.{} ({}) from stdin (format csv)").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in df.columns),
    )
    with conn.cursor() as cur:
        with cur.copy(stmt) as copy:
            copy.write(buffer.getvalue())
        return cur.rowcount
