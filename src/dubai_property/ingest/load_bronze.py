"""Load raw CSV files into ``bronze.*`` tables with PostgreSQL ``COPY`` (docs/04 §1).

Bronze is an exact, untransformed copy of each source file plus metadata, so any later
cleaning bug can be traced back to the source row. For each CSV in
``<root>/<dataset.subdir>/`` this module:

1. **Hashes** the file (SHA-256) and skips it if that exact content is already in the
   target table. The check reads ``bronze._load_manifest``, which is written *in the same
   transaction* as the COPY, so a crash mid-file can never leave a half-loaded file marked
   as done. ``<root>/manifest.json`` is exported from that table for humans and git diffs.
2. **Inspects** the file in Python: strips a UTF-8 BOM, falls back to Windows-1256
   (Arabic) if the bytes aren't valid UTF-8, reads the header, and counts CSV *records*
   with the ``csv`` module. Counting lines (``wc -l``) would over-count, because quoted
   fields can contain line breaks.
3. **Streams the raw bytes** into ``COPY … FROM STDIN (FORMAT csv, HEADER true)``.
   Postgres's own parser splits the records, and the Python count from step 2 is a
   second, independent parser. The load only commits if the two agree.
4. Adds metadata columns ``_source_file``, ``_source``, ``_snapshot_date``,
   ``_ingested_at`` and ``_row_hash``; runs ``ANALYZE``; appends to
   ``reports/ingest_log.csv``.

Every source column is ``text``. Note that DLD quotes every field, so an empty field
arrives as ``''`` (an empty string) rather than ``NULL``. Bronze keeps that as-is;
``nullif(col, '')`` belongs in dbt staging.

Usage::

    uv run python -m dubai_property.ingest.load_bronze                  # all datasets
    uv run python -m dubai_property.ingest.load_bronze --dataset rents  # one dataset
    uv run python -m dubai_property.ingest.load_bronze --root data/sample --reset
"""

from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from dubai_property import config, db
from dubai_property.config import Dataset

log = logging.getLogger(__name__)

SCHEMA = config.SCHEMA_BRONZE
MANIFEST_TABLE = "_load_manifest"
CHUNK_BYTES = 8 * 1024 * 1024
UTF8_BOM = codecs.BOM_UTF8

# Python codec -> PostgreSQL COPY ENCODING name. UTF-8 is expected; Windows-1256 is the
# usual encoding of Arabic CSVs saved from Excel. Postgres converts WIN1256 to the UTF-8
# database encoding during COPY, so no Python transcoding pass is needed.
ENCODINGS = {"utf-8": "UTF8", "cp1256": "WIN1256"}

METADATA_COLUMNS = ("_source_file", "_source", "_snapshot_date", "_ingested_at", "_row_hash")

LOG_FIELDS = (
    "logged_at",
    "dataset",
    "table",
    "file",
    "status",
    "encoding",
    "had_bom",
    "size_mb",
    "rows_in_file",
    "rows_loaded",
    "rows_match",
    "inspect_seconds",
    "copy_seconds",
    "rows_per_second",
    "note",
)

csv.field_size_limit(sys.maxsize)


class IngestError(RuntimeError):
    """A file can't be loaded safely (schema drift, count mismatch, bad header)."""


# --- Pure helpers (unit-tested without a database) ------------------------------------


def snake_case(name: str) -> str:
    """Turn a CSV header into a Postgres column name.

    ``"TRANS_VALUE"`` -> ``trans_value``; ``"Area (sq m)"`` -> ``area_sq_m``. Leading digits
    get a ``c_`` prefix so the result is a valid unquoted identifier. Leading underscores
    are stripped, so a source column can never collide with a ``_``-prefixed metadata column.
    """
    name = name.strip().lstrip("\ufeff")
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)  # camelCase -> camel_Case
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    if not name:
        name = "col"
    if name[0].isdigit():
        name = f"c_{name}"
    return name


def normalise_header(header: Sequence[str]) -> list[str]:
    """Snake-case a header row and de-duplicate names (``a``, ``a`` -> ``a``, ``a_2``)."""
    out: list[str] = []
    seen: dict[str, int] = {}
    for raw in header:
        col = snake_case(raw)
        seen[col] = seen.get(col, 0) + 1
        out.append(col if seen[col] == 1 else f"{col}_{seen[col]}")
    return out


def snapshot_date_for(path: Path) -> date:
    """Snapshot date of a file: the first ``YYYY-MM-DD`` in its name, else its mtime.

    DLD bulk exports are named like ``transactions_2026-09-29_06-34-19_0001.csv``; the
    date is the day DLD produced the extract, which is what silver de-duplication needs.
    """
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.name)
    if match:
        try:
            return date(*map(int, match.groups()))
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).date()


def file_sha256(path: Path) -> str:
    """SHA-256 of a file's bytes, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class FileInfo:
    """What the Python pre-pass learned about a CSV file."""

    path: Path
    sha256: str
    size_bytes: int
    encoding: str  # Python codec name, a key of ENCODINGS
    had_bom: bool
    header: list[str]  # raw header as in the file
    columns: list[str]  # snake-cased header
    records: int  # data records (header excluded), counted by a CSV parser
    physical_lines: int  # newline count, reported to show why wc -l is not a record count

    @property
    def pg_encoding(self) -> str:
        """Encoding name for ``COPY … (ENCODING …)``."""
        return ENCODINGS[self.encoding]


class _HashingReader(io.RawIOBase):
    """Binary stream wrapper that hashes and counts newlines as bytes are read."""

    def __init__(self, raw: io.BufferedReader) -> None:
        self._raw = raw
        self.sha = hashlib.sha256()
        self.newlines = 0
        self.size = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: memoryview) -> int:  # type: ignore[override]
        n = self._raw.readinto(buffer)
        if n:
            chunk = bytes(buffer[:n])
            self.sha.update(chunk)
            self.newlines += chunk.count(b"\n")
            self.size += n
        return n or 0


def _parse(path: Path, encoding: str) -> FileInfo:
    with path.open("rb") as fh:
        had_bom = fh.read(len(UTF8_BOM)) == UTF8_BOM
        fh.seek(0)
        reader = _HashingReader(fh)
        buffered = io.BufferedReader(reader, buffer_size=CHUNK_BYTES)
        # utf-8-sig drops a leading BOM and is otherwise identical to strict utf-8.
        codec = "utf-8-sig" if encoding == "utf-8" else encoding
        text = io.TextIOWrapper(buffered, encoding=codec, errors="strict", newline="")
        rows = csv.reader(text)
        header = next(rows, None)
        if not header:
            raise IngestError(f"{path.name}: empty file or missing header row")
        records = sum(1 for row in rows if row)  # a blank line is not a record
        # Drain anything the csv reader didn't need, so hash/size cover the whole file.
        while buffered.read(CHUNK_BYTES):
            pass
    return FileInfo(
        path=path,
        sha256=reader.sha.hexdigest(),
        size_bytes=reader.size,
        encoding=encoding,
        had_bom=had_bom,
        header=header,
        columns=normalise_header(header),
        records=records,
        physical_lines=reader.newlines,
    )


def inspect_file(path: Path) -> FileInfo:
    """Hash, detect encoding and count CSV records in one streaming pass per encoding.

    Tries strict UTF-8 first. If a byte sequence is invalid, the whole file is re-read
    as Windows-1256 and a warning is logged, since that choice is a guess about the source.
    """
    try:
        return _parse(path, "utf-8")
    except UnicodeDecodeError as exc:
        log.warning("%s is not valid UTF-8 (%s); reading as Windows-1256", path.name, exc)
        return _parse(path, "cp1256")


def discover_files(folder: Path) -> list[Path]:
    """CSV files in a dataset folder, sorted by name. Other files are ignored."""
    if not folder.is_dir():
        return []
    others = [
        p.name
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() != ".csv" and p.name not in {"README.txt", ".DS_Store"}
    ]
    if others:
        log.warning("%s: ignoring non-CSV files %s (convert them to CSV to load)", folder, others)
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".csv")


# --- Database side ------------------------------------------------------------------


def _ident(*parts: str) -> sql.Identifier:
    return sql.Identifier(*parts)


def ensure_manifest_table(conn: psycopg.Connection) -> None:
    """Create ``bronze._load_manifest``: one row per file loaded into a bronze table."""
    conn.execute(
        sql.SQL(
            """
            create table if not exists {t} (
                table_name     text        not null,
                dataset        text        not null,
                source_file    text        not null,
                sha256         text        not null,
                size_bytes     bigint      not null,
                snapshot_date  date        not null,
                encoding       text        not null,
                had_bom        boolean     not null,
                rows_in_file   bigint      not null,
                rows_loaded    bigint      not null,
                copy_seconds   numeric(10, 1),
                loaded_at      timestamptz not null default now(),
                primary key (table_name, sha256)
            )
            """
        ).format(t=_ident(SCHEMA, MANIFEST_TABLE))
    )


def table_columns(conn: psycopg.Connection, table: str) -> list[str] | None:
    """Source (non-metadata) columns of a bronze table in order, or None if it's missing."""
    rows = conn.execute(
        """
        select column_name from information_schema.columns
        where table_schema = %s and table_name = %s
        order by ordinal_position
        """,
        [SCHEMA, table],
    ).fetchall()
    if not rows:
        return None
    return [r[0] for r in rows if r[0] not in METADATA_COLUMNS]


def _row_hash_expr(columns: Sequence[str]) -> sql.Composable:
    # md5 over every source value joined with the ASCII unit separator (0x1f), with NULL
    # spelled \N so NULL and '' hash differently. It is a STORED generated column, so
    # Postgres computes it during COPY (no second pass over the table). Silver uses it to
    # de-duplicate identical rows that appear in more than one snapshot (rule C1).
    parts = [sql.SQL("coalesce({}, E'\\\\N')").format(_ident(c)) for c in columns]
    return sql.SQL("md5({})").format(sql.SQL(" || E'\\x1f' || ").join(parts))


def ensure_table(conn: psycopg.Connection, table: str, columns: Sequence[str]) -> None:
    """Create the bronze table from a header, or check an existing one still matches.

    Raises:
        IngestError: If the table exists with a different set of source columns. The
            loader never alters a bronze table silently; a new DLD column is a decision.
    """
    existing = table_columns(conn, table)
    if existing is not None:
        if set(existing) != set(columns):
            added = sorted(set(columns) - set(existing))
            missing = sorted(set(existing) - set(columns))
            raise IngestError(
                f"schema drift in {SCHEMA}.{table}: new columns {added}, missing {missing}"
            )
        return
    col_defs = [sql.SQL("{} text").format(_ident(c)) for c in columns]
    meta_defs = [
        sql.SQL("_source_file text not null"),
        sql.SQL("_source text not null"),
        sql.SQL("_snapshot_date date not null"),
        sql.SQL("_ingested_at timestamptz not null default now()"),
        sql.SQL("_row_hash text generated always as ({}) stored").format(_row_hash_expr(columns)),
    ]
    conn.execute(
        sql.SQL("create table {t} ({cols})").format(
            t=_ident(SCHEMA, table), cols=sql.SQL(", ").join(col_defs + meta_defs)
        )
    )
    log.info("created %s.%s (%d source columns, all text)", SCHEMA, table, len(columns))


def is_loaded(conn: psycopg.Connection, table: str, sha256: str) -> tuple[int, int] | None:
    """(rows_in_file, rows_loaded) if this exact file content is already in the table."""
    row = conn.execute(
        sql.SQL(
            "select rows_in_file, rows_loaded from {} where table_name = %s and sha256 = %s"
        ).format(_ident(SCHEMA, MANIFEST_TABLE)),
        [table, sha256],
    ).fetchone()
    return (row[0], row[1]) if row else None


def copy_file(
    conn: psycopg.Connection,
    table: str,
    info: FileInfo,
    *,
    source: str,
    source_file: str,
    snapshot: date,
) -> int:
    """Stream one file into its bronze table with COPY. Returns the rows COPY reported.

    Runs inside the caller's transaction. COPY can only fill columns from the file, so the
    per-file metadata values are set as column DEFAULTs for the duration of this
    transaction and dropped again before commit. This keeps the load a single COPY pass
    (no temp table, no UPDATE rewriting millions of rows).
    """
    t = _ident(SCHEMA, table)
    conn.execute(
        sql.SQL(
            "alter table {t} alter column _source_file set default {f},"
            " alter column _source set default {s},"
            " alter column _snapshot_date set default {d}"
        ).format(
            t=t,
            f=sql.Literal(source_file),
            s=sql.Literal(source),
            d=sql.Literal(snapshot),
        )
    )
    copy_sql = sql.SQL(
        "copy {t} ({cols}) from stdin (format csv, header true, encoding {enc})"
    ).format(
        t=t,
        cols=sql.SQL(", ").join(_ident(c) for c in info.columns),
        enc=sql.Literal(info.pg_encoding),
    )
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy, info.path.open("rb") as fh:
            if info.had_bom:
                fh.seek(len(UTF8_BOM))  # Postgres would read the BOM as part of column 1
            while chunk := fh.read(CHUNK_BYTES):
                copy.write(chunk)
        rows = cur.rowcount
    conn.execute(
        sql.SQL(
            "alter table {t} alter column _source_file drop default,"
            " alter column _source drop default, alter column _snapshot_date drop default"
        ).format(t=t)
    )
    return rows


def record_manifest(
    conn: psycopg.Connection,
    dataset: Dataset,
    info: FileInfo,
    *,
    source_file: str,
    snapshot: date,
    rows_loaded: int,
    copy_seconds: float,
) -> None:
    """Insert the manifest row (same transaction as the COPY)."""
    conn.execute(
        sql.SQL(
            """
            insert into {} (table_name, dataset, source_file, sha256, size_bytes, snapshot_date,
                            encoding, had_bom, rows_in_file, rows_loaded, copy_seconds)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(_ident(SCHEMA, MANIFEST_TABLE)),
        [
            dataset.table,
            dataset.name,
            source_file,
            info.sha256,
            info.size_bytes,
            snapshot,
            info.pg_encoding,
            info.had_bom,
            info.records,
            rows_loaded,
            round(copy_seconds, 1),
        ],
    )


def export_manifest_json(conn: psycopg.Connection, root: Path) -> Path:
    """Write ``<root>/manifest.json`` from ``bronze._load_manifest`` (files under root)."""
    prefix = _source_prefix(root)
    rows = conn.execute(
        sql.SQL(
            """
            select source_file, table_name, dataset, sha256, size_bytes, snapshot_date::text,
                   encoding, had_bom, rows_in_file, rows_loaded, copy_seconds::float8,
                   to_char(loaded_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            from {} where source_file like %s order by source_file, loaded_at
            """
        ).format(_ident(SCHEMA, MANIFEST_TABLE)),
        [prefix + "%"],
    ).fetchall()
    keys = (
        "table",
        "dataset",
        "sha256",
        "size_bytes",
        "snapshot_date",
        "encoding",
        "had_bom",
        "rows_in_file",
        "rows_loaded",
        "copy_seconds",
        "loaded_at",
    )
    files = {r[0]: dict(zip(keys, r[1:], strict=True)) for r in rows}
    path = root / config.MANIFEST_NAME
    path.write_text(json.dumps({"files": files}, indent=2, ensure_ascii=False) + "\n")
    return path


def _source_prefix(root: Path) -> str:
    """How files under ``root`` are named in ``_source_file``: relative to data/, if possible.

    ``raw/dld/rents/x.csv`` vs ``sample/dld/rents/x.csv`` keeps a sample load and a full
    load distinguishable in bronze. Roots elsewhere in the repo (the committed CI fixtures)
    are named relative to the project root, e.g. ``tests/fixtures/dld/rents/x.csv``.
    """
    root = root.resolve()
    for base in (config.DATA_DIR, config.PROJECT_ROOT):
        try:
            return root.relative_to(base.resolve()).as_posix() + "/"
        except ValueError:
            continue
    return root.as_posix() + "/"


def append_ingest_log(rows: Iterable[dict[str, object]], path: Path | None = None) -> None:
    """Append rows to ``reports/ingest_log.csv``, writing the header on first use."""
    # Off the main database the log goes to the scratch reports folder (db.reports_dir).
    # On the main database config.INGEST_LOG is used as is, so tests can redirect it.
    if path is None:
        path = config.INGEST_LOG if db.is_main_db() else db.reports_dir() / config.INGEST_LOG.name
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerows(rows)


def _log_row(dataset: Dataset, file: str, status: str, **values: object) -> dict[str, object]:
    row: dict[str, object] = dict.fromkeys(LOG_FIELDS, "")
    row.update(
        logged_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        dataset=dataset.name,
        table=f"{SCHEMA}.{dataset.table}",
        file=file,
        status=status,
    )
    row.update(values)
    return row


def load_dataset(conn: psycopg.Connection, dataset: Dataset, root: Path) -> list[dict[str, object]]:
    """Load every new CSV of one dataset. Returns ingest-log rows (one per file).

    Each file is its own transaction: COPY, count check and manifest row commit together
    or not at all.
    """
    folder = root / dataset.subdir
    files = discover_files(folder)
    prefix = _source_prefix(root)
    results: list[dict[str, object]] = []
    if not dataset.enabled:
        for path in files:
            results.append(
                _log_row(
                    dataset,
                    prefix + path.relative_to(root).as_posix(),
                    "disabled",
                    note=dataset.note,
                )
            )
        if files:
            log.info(
                "%s: %d file(s) skipped, dataset disabled: %s",
                dataset.name,
                len(files),
                dataset.note,
            )
        return results
    if not files:
        log.info("%s: no CSV files in %s, nothing to load", dataset.name, folder)
        return results

    loaded_any = False
    for path in files:
        source_file = prefix + path.relative_to(root).as_posix()
        size_mb = round(path.stat().st_size / 1e6, 1)
        sha = file_sha256(path)
        done = is_loaded(conn, dataset.table, sha)
        conn.commit()
        if done:
            log.info("%s: skip %s (already loaded, sha256 %s…)", dataset.name, path.name, sha[:12])
            results.append(
                _log_row(
                    dataset,
                    source_file,
                    "skipped",
                    size_mb=size_mb,
                    rows_in_file=done[0],
                    rows_loaded=done[1],
                    rows_match=done[0] == done[1],
                    note="sha256 already in bronze._load_manifest",
                )
            )
            continue

        t0 = time.perf_counter()
        info = inspect_file(path)
        inspect_s = time.perf_counter() - t0
        snapshot = snapshot_date_for(path)
        log.info(
            "%s: loading %s (%.0f MB, %s%s, %d records, %d lines)",
            dataset.name,
            path.name,
            size_mb,
            info.pg_encoding,
            " +BOM" if info.had_bom else "",
            info.records,
            info.physical_lines,
        )
        t1 = time.perf_counter()
        try:
            ensure_table(conn, dataset.table, info.columns)
            rows = copy_file(
                conn,
                dataset.table,
                info,
                source=dataset.source,
                source_file=source_file,
                snapshot=snapshot,
            )
            copy_s = time.perf_counter() - t1
            if rows != info.records:
                raise IngestError(
                    f"{path.name}: COPY loaded {rows} rows but the CSV parser counted "
                    f"{info.records} records; rolled back"
                )
            record_manifest(
                conn,
                dataset,
                info,
                source_file=source_file,
                snapshot=snapshot,
                rows_loaded=rows,
                copy_seconds=copy_s,
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            results.append(
                _log_row(
                    dataset,
                    source_file,
                    "failed",
                    size_mb=size_mb,
                    encoding=info.pg_encoding,
                    rows_in_file=info.records,
                    inspect_seconds=round(inspect_s, 1),
                    note=str(exc)[:300],
                )
            )
            append_ingest_log(results)
            raise
        loaded_any = True
        log.info(
            "%s: %s -> %s.%s: %d rows in %.1fs (%.0f rows/s)",
            dataset.name,
            path.name,
            SCHEMA,
            dataset.table,
            rows,
            copy_s,
            rows / max(copy_s, 1e-9),
        )
        note = "" if info.had_bom is False else "UTF-8 BOM stripped"
        if info.encoding != "utf-8":
            note = f"{note}; transcoded from {info.pg_encoding}".strip("; ")
        results.append(
            _log_row(
                dataset,
                source_file,
                "loaded",
                encoding=info.pg_encoding,
                had_bom=info.had_bom,
                size_mb=size_mb,
                rows_in_file=info.records,
                rows_loaded=rows,
                rows_match=rows == info.records,
                inspect_seconds=round(inspect_s, 1),
                copy_seconds=round(copy_s, 1),
                rows_per_second=round(rows / max(copy_s, 1e-9)),
                note=note,
            )
        )

    if loaded_any:
        t0 = time.perf_counter()
        conn.execute(sql.SQL("analyze {}").format(_ident(SCHEMA, dataset.table)))
        conn.commit()
        log.info(
            "%s: analyze %s.%s in %.1fs",
            dataset.name,
            SCHEMA,
            dataset.table,
            time.perf_counter() - t0,
        )
    return results


def reset_dataset(conn: psycopg.Connection, dataset: Dataset) -> None:
    """Drop a bronze table and forget its manifest rows (for a clean reload).

    CASCADE also drops the silver staging views built on the table; `make dbt` recreates
    them. Without it a reset fails as soon as dbt has run once.
    """
    conn.execute(sql.SQL("drop table if exists {} cascade").format(_ident(SCHEMA, dataset.table)))
    conn.execute(
        sql.SQL("delete from {} where table_name = %s").format(_ident(SCHEMA, MANIFEST_TABLE)),
        [dataset.table],
    )
    conn.commit()
    log.info("reset %s.%s (and dependent silver views)", SCHEMA, dataset.table)


# --- Main-database guard -----------------------------------------------------------------
# On 2026-10-01 a fixture run meant for a scratch database reset the main database's bronze
# (``PG_DB=x make ...`` doesn't override the PG_DB the Makefile reads from .env; it has to
# be a make argument). Rebuilding bronze from data/raw takes most of an hour, so the main
# database now refuses both mistakes outright (decision, docs/05 §8).
ALLOW_MAIN_RESET_ENV = "ALLOW_MAIN_RESET"


def check_target(dbname: str, root: Path, reset: bool, env: dict[str, str] | None = None) -> None:
    """Refuse a bronze load that could overwrite the main database by mistake.

    On the main database (``config.MAIN_DB``):

    * only ``data/raw`` may be loaded, except in CI (``CI=true``, set by GitHub Actions),
      whose throwaway database has the same name and loads the committed fixtures;
    * ``--reset`` needs ``ALLOW_MAIN_RESET=1`` in the environment, set explicitly for an
      approved full reload.

    Raises:
        IngestError: If the load is refused.
    """
    env = os.environ if env is None else env
    if dbname != config.MAIN_DB:
        return
    is_ci = env.get("CI", "").lower() == "true"
    if root.resolve() != config.DATA_RAW.resolve() and not is_ci:
        raise IngestError(
            f"refusing to load {root} into the main database {dbname}: only {config.DATA_RAW}"
            " may be loaded there. For a scratch database pass PG_DB as a make argument"
            " (make bronze ... PG_DB=<scratch>), not as an environment prefix."
        )
    if reset and env.get(ALLOW_MAIN_RESET_ENV) != "1":
        raise IngestError(
            f"refusing --reset on the main database {dbname}: a full reload takes most of an"
            f" hour. Set {ALLOW_MAIN_RESET_ENV}=1 for an approved reload."
        )


def run(root: Path, datasets: Sequence[Dataset], *, reset: bool = False) -> list[dict[str, object]]:
    """Load the given datasets from ``root`` and write the manifest and ingest log."""
    dbname = db.current_dbname()
    log.info("target database %s, bronze root %s, reset %s", dbname, root, reset)
    check_target(dbname, root, reset)
    all_rows: list[dict[str, object]] = []
    with db.connect() as conn:
        # Bigger sort memory speeds up ANALYZE; this session only.
        conn.execute("set maintenance_work_mem = '1GB'")
        ensure_manifest_table(conn)
        conn.commit()
        for dataset in datasets:
            if reset:
                reset_dataset(conn, dataset)
            rows = load_dataset(conn, dataset, root)
            append_ingest_log(rows)
            all_rows.extend(rows)
        manifest = export_manifest_json(conn, root)
        log.info("manifest written to %s", manifest)
    return all_rows


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=config.DATA_RAW,
        help="data root holding dld/, fred/, cbuae/ (default: data/raw)",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(config.DATASETS_BY_NAME),
        help="load only this dataset (repeatable); default: all",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop the selected bronze tables first and reload from scratch",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    names = args.dataset or [d.name for d in config.DATASETS]
    datasets = [config.DATASETS_BY_NAME[n] for n in names]
    rows = run(args.root, datasets, reset=args.reset)
    loaded = [r for r in rows if r["status"] == "loaded"]
    log.info(
        "done: %d file(s) loaded, %d skipped, %d rows",
        len(loaded),
        sum(r["status"] == "skipped" for r in rows),
        sum(int(r["rows_loaded"]) for r in loaded),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
