"""Reconcile source files to bronze row counts (docs/04 §4 "Reconciliation").

Three numbers must agree for every loaded file:

* ``rows_in_file``: CSV records counted by Python's ``csv`` parser before the load,
* ``rows_loaded``: rows Postgres ``COPY`` reported (both from ``bronze._load_manifest``),
* ``rows_in_bronze``: ``count(*)`` per ``_source_file`` in the bronze table *now*.

The third check catches anything that happened after the load (a manual delete, a
second load of the same file under another name). Bronze rows whose ``_source_file`` has
no manifest entry are reported as orphans. Silver/gold checks are added in Phase 2.

Writes ``reports/bronze_reconciliation.md``; exits 1 if anything is off.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from dubai_property import db
from dubai_property.ingest.load_bronze import MANIFEST_TABLE, SCHEMA

log = logging.getLogger(__name__)

REPORT_NAME = "bronze_reconciliation.md"


def report_path() -> Path:
    """``reports/bronze_reconciliation.md``; a scratch folder when PG_DB isn't the main DB."""
    return db.reports_dir() / REPORT_NAME


@dataclass(frozen=True)
class FileCheck:
    """Reconciliation result for one source file."""

    table: str
    source_file: str
    rows_in_file: int | None
    rows_loaded: int | None
    rows_in_bronze: int

    @property
    def ok(self) -> bool:
        """True when parser count, COPY count and current bronze count all match."""
        return self.rows_in_file == self.rows_loaded == self.rows_in_bronze


def check(conn: psycopg.Connection) -> list[FileCheck]:
    """Compare manifest counts with live bronze counts for every table in the manifest."""
    manifest = conn.execute(
        sql.SQL(
            "select table_name, source_file, rows_in_file, rows_loaded from {} order by 1, 2"
        ).format(sql.Identifier(SCHEMA, MANIFEST_TABLE))
    ).fetchall()
    expected = {(t, f): (n_file, n_loaded) for t, f, n_file, n_loaded in manifest}
    results: list[FileCheck] = []
    for table in sorted({t for t, _ in expected}):
        live = dict(
            conn.execute(
                sql.SQL("select _source_file, count(*) from {} group by 1").format(
                    sql.Identifier(SCHEMA, table)
                )
            ).fetchall()
        )
        files = sorted({f for t, f in expected if t == table} | set(live))
        for f in files:
            n_file, n_loaded = expected.get((table, f), (None, None))
            results.append(FileCheck(table, f, n_file, n_loaded, live.get(f, 0)))
    return results


def write_report(results: list[FileCheck], path: Path | None = None) -> Path:
    """Write the reconciliation table as markdown."""
    path = path or report_path()
    ok = all(r.ok for r in results)
    lines = [
        "# Bronze reconciliation: files vs bronze row counts",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/reconcile.py`. "
        f"Status: **{'PASS' if ok else 'FAIL'}**.",
        "",
        "`rows_in_file` = CSV records counted with Python's `csv` parser (not `wc -l`: quoted "
        "fields can contain line breaks); `rows_loaded` = rows reported by Postgres `COPY`; "
        "`rows_in_bronze` = live `count(*)` per `_source_file`.",
        "",
        "| Table | File | rows_in_file | rows_loaded | rows_in_bronze | OK |",
        "|---|---|---:|---:|---:|:-:|",
    ]
    totals: dict[str, list[int]] = {}
    for r in results:
        name = Path(r.source_file).name
        lines.append(
            f"| {r.table} | {name} | {_fmt(r.rows_in_file)} | {_fmt(r.rows_loaded)} "
            f"| {r.rows_in_bronze:,} | {'✓' if r.ok else '✗'} |"
        )
        t = totals.setdefault(r.table, [0, 0, 0])
        t[0] += r.rows_in_file or 0
        t[1] += r.rows_loaded or 0
        t[2] += r.rows_in_bronze
    lines += [
        "",
        "**Totals per table**",
        "",
        "| Table | Files | rows_in_file | rows_loaded | rows_in_bronze |",
        "|---|---:|---:|---:|---:|",
    ]
    for table, (a, b, c) in totals.items():
        n = sum(r.table == table for r in results)
        lines.append(f"| {table} | {n} | {a:,} | {b:,} | {c:,} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def _fmt(n: int | None) -> str:
    return "orphan" if n is None else f"{n:,}"


def main() -> int:
    """CLI entry point: reconcile, write the report, exit 1 on any mismatch."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with db.connect() as conn:
        results = check(conn)
    path = write_report(results)
    bad = [r for r in results if not r.ok]
    for r in bad:
        log.error("mismatch: %s", r)
    log.info("%d file(s) reconciled, %d mismatch(es); report: %s", len(results), len(bad), path)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
