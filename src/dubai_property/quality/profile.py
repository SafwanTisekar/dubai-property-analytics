"""Profile every column of every bronze table into ``reports/profile_<table>.md``.

All the work happens in SQL, so the 10M-row rent table is never pulled into Python. Each
column costs one ``GROUP BY`` (value -> count); every statistic is then computed from those
groups:

* **blank %**: ``NULL`` *or* ``''``. DLD quotes every field, so missing values arrive
  as empty strings in bronze, not NULLs (see ``load_bronze``).
* **distinct**: distinct non-blank values.
* **min / max**: numeric min/max when at least 95% of non-blank values parse as numbers,
  otherwise text (lexical) min/max, which works for ISO dates.
* **numeric %**: share of non-blank values that parse as numbers, a hint for staging casts.
* **top values**: the 5 most frequent values with counts.

Usage::

    uv run python -m dubai_property.quality.profile [--table dld_transactions]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from dubai_property import db
from dubai_property.ingest.load_bronze import MANIFEST_TABLE, SCHEMA

log = logging.getLogger(__name__)

NUMERIC_RE = r"^\s*-?[0-9]+(\.[0-9]+)?\s*$"
NUMERIC_SHARE_FOR_NUMERIC_MINMAX = 0.95
TOP_N = 5
MAX_CELL = 40


@dataclass(frozen=True)
class ColumnProfile:
    """Profile statistics for one column."""

    column: str
    rows: int
    blank: int
    distinct: int
    text_min: str | None
    text_max: str | None
    numeric_rows: int
    num_min: float | None
    num_max: float | None
    top: list[tuple[str | None, int]]

    @property
    def blank_pct(self) -> float:
        """Share of rows that are NULL or empty, in percent."""
        return 100.0 * self.blank / self.rows if self.rows else 0.0

    @property
    def numeric_pct(self) -> float:
        """Share of non-blank rows that parse as a number, in percent."""
        filled = self.rows - self.blank
        return 100.0 * self.numeric_rows / filled if filled else 0.0


def _column_query(table: str, column: str) -> sql.Composed:
    return sql.SQL(
        """
        with g as materialized (
            select {c}::text as v, count(*)::bigint as n from {t} group by 1
        ),
        top as (
            select v, n from g order by n desc, v nulls first limit {top_n}
        )
        select
            coalesce(sum(n), 0)::bigint,
            coalesce(sum(n) filter (where v is null or v = ''), 0)::bigint,
            count(*) filter (where v <> ''),
            min(v) filter (where v <> ''),
            max(v) filter (where v <> ''),
            coalesce(sum(n) filter (where v ~ {re}), 0)::bigint,
            min(v::numeric) filter (where v ~ {re})::float8,
            max(v::numeric) filter (where v ~ {re})::float8,
            (select json_agg(json_build_array(v, n) order by n desc, v nulls first) from top)
        from g
        """
    ).format(
        c=sql.Identifier(column),
        t=sql.Identifier(SCHEMA, table),
        re=sql.Literal(NUMERIC_RE),
        top_n=sql.Literal(TOP_N),
    )


def profile_column(conn: psycopg.Connection, table: str, column: str) -> ColumnProfile:
    """Run the one-scan profile query for a column."""
    row = conn.execute(_column_query(table, column)).fetchone()
    assert row is not None
    rows, blank, distinct, tmin, tmax, num_rows, nmin, nmax, top = row
    return ColumnProfile(
        column=column,
        rows=rows,
        blank=blank,
        distinct=distinct,
        text_min=tmin,
        text_max=tmax,
        numeric_rows=num_rows,
        num_min=nmin,
        num_max=nmax,
        top=[(v, int(n)) for v, n in (top or [])],
    )


def bronze_tables(conn: psycopg.Connection) -> list[str]:
    """All bronze tables except the load manifest."""
    rows = conn.execute(
        "select table_name from information_schema.tables where table_schema = %s"
        " and table_type = 'BASE TABLE' and table_name <> %s order by 1",
        [SCHEMA, MANIFEST_TABLE],
    ).fetchall()
    return [r[0] for r in rows]


def table_columns(conn: psycopg.Connection, table: str) -> list[str]:
    """Columns of a bronze table in order (metadata columns included)."""
    rows = conn.execute(
        "select column_name from information_schema.columns where table_schema = %s"
        " and table_name = %s order by ordinal_position",
        [SCHEMA, table],
    ).fetchall()
    return [r[0] for r in rows]


def _cell(value: object) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if text == "":
        return "''"
    text = text.replace("\r", " ").replace("\n", "⏎").replace("|", "\\|")
    return text if len(text) <= MAX_CELL else text[: MAX_CELL - 1] + "…"


def _num(x: float | None) -> str:
    if x is None:
        return ""
    return f"{x:,.0f}" if float(x).is_integer() or abs(x) >= 1000 else f"{x:,.4g}"


def render(table: str, profiles: Sequence[ColumnProfile], meta: dict[str, str]) -> str:
    """Render a table's profile as markdown."""
    rows = profiles[0].rows if profiles else 0
    lines = [
        f"# Profile: `{SCHEMA}.{table}`",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/profile.py` (SQL-based, "
        "exact counts over the full table).",
        "",
        f"- Rows: **{rows:,}**",
        f"- Columns: {len(profiles)} ({sum(not p.column.startswith('_') for p in profiles)} "
        "source + metadata)",
    ]
    lines += [f"- {k}: {v}" for k, v in meta.items()]
    lines += [
        "",
        "Blank = `NULL` or `''` (DLD quotes every field, so missing values are empty strings "
        "in bronze). Min/max are numeric when ≥95% of non-blank values are numeric, otherwise "
        "text order. Values are truncated to 40 characters; ⏎ marks a line break.",
        "",
        "| Column | Blank % | Distinct | Min | Max | Numeric % | Top values (count) |",
        "|---|---:|---:|---|---|---:|---|",
    ]
    for p in profiles:
        numeric = p.numeric_pct >= 100 * NUMERIC_SHARE_FOR_NUMERIC_MINMAX
        lo = _num(p.num_min) if numeric else _cell(p.text_min) if p.text_min else ""
        hi = _num(p.num_max) if numeric else _cell(p.text_max) if p.text_max else ""
        top = "<br>".join(f"{_cell(v)} ({n:,})" for v, n in p.top)
        lines.append(
            f"| `{p.column}` | {p.blank_pct:.1f} | {p.distinct:,} | {lo} | {hi} "
            f"| {p.numeric_pct:.1f} | {top} |"
        )
    return "\n".join(lines) + "\n"


def profile_table(conn: psycopg.Connection, table: str, out_dir: Path | None = None) -> Path:
    """Profile all columns of one bronze table and write its markdown report.

    ``out_dir`` defaults to ``db.reports_dir()`` (``reports/``, or a scratch folder when
    ``PG_DB`` isn't the main database).
    """
    out_dir = out_dir or db.reports_dir()
    t0 = time.perf_counter()
    profiles = []
    for column in table_columns(conn, table):
        profiles.append(profile_column(conn, table, column))
        conn.rollback()  # read-only; keep no transaction open between columns
    (size,) = conn.execute(
        "select pg_size_pretty(pg_total_relation_size(%s::regclass))", [f"{SCHEMA}.{table}"]
    ).fetchone()
    elapsed = time.perf_counter() - t0
    meta = {"Table size on disk": size, "Profiling time": f"{elapsed:.0f} s"}
    path = out_dir / f"profile_{table}.md"
    path.write_text(render(table, profiles, meta))
    log.info("%s: %d columns profiled in %.0fs -> %s", table, len(profiles), elapsed, path.name)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--table", action="append", help="bronze table(s); default: all")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with db.connect() as conn:
        conn.execute("set work_mem = '256MB'")  # this session only: fewer hash-agg spills
        conn.commit()
        for table in args.table or bronze_tables(conn):
            profile_table(conn, table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
