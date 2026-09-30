"""Database connection helpers built from `.env`.

Three access paths, each used for what it does best (docs/03 §4):

* ``connect()``: psycopg 3 connection, used for ``COPY`` bulk loads and writes.
* ``get_engine()``: SQLAlchemy engine, for pandas/Polars ``read_sql`` and ad-hoc SQL.
* ``connectorx_uri()``: URI for connectorx, the fastest way to pull a model-sized
  result set into Polars/pandas.

Credentials come only from environment variables (loaded from `.env`), never code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo
from sqlalchemy import Engine, create_engine

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
