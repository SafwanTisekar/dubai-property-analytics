"""Build stratified CSV samples in ``data/sample/`` for dev and CI (``make sample``).

For each DLD dataset with a ``sample_key`` (docs/04, ``config.DATASETS``):

* **Strata** are year (of ``sample_date``) × ``area_id``. Within each stratum, keep the
  first ``ceil(n × fraction)`` keys ordered by ``md5(key)``: deterministic (same sample on
  every run), and every year × area combination keeps at least one deal, so rare
  areas and early years are still present for tests. This slightly over-samples tiny
  strata, which is intended.
* **Whole groups** are sampled: all lines of a chosen ``transaction_id`` /
  ``contract_id`` are kept, so multi-unit rent contracts (rule C11) and portfolio deals
  keep their structure.

The sample is written with ``COPY … TO STDOUT (FORMAT csv, HEADER, FORCE_QUOTE *)``,
the same shape as the DLD files (every field quoted), so ``load_bronze --root
data/sample`` loads it exactly like the real data. Rate files are tiny and are copied
whole. Only rows loaded from ``data/raw`` are sampled.

``data/`` is gitignored (docs/01 §7), so the sample is a local artefact; CI builds its
own fixtures (see docs/04 Decisions).

Usage::

    uv run python -m dubai_property.ingest.sample [--fraction 0.02]
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import psycopg
from psycopg import sql

from dubai_property import config, db
from dubai_property.config import Dataset
from dubai_property.ingest.load_bronze import METADATA_COLUMNS, SCHEMA, table_columns

log = logging.getLogger(__name__)

RAW_PREFIX = "raw/"  # _source_file prefix of rows loaded from data/raw


def sample_query(dataset: Dataset, columns: Sequence[str], fraction: float) -> sql.Composed:
    """SQL that selects every line of the sampled keys, source columns only."""
    assert dataset.sample_key and dataset.sample_date
    return sql.SQL(
        """
        with k as (
            select {key} as key, min(left({date}, 4)) as yr, min(area_id) as area_id
            from {t} where _source_file like {raw} group by 1
        ), ranked as (
            select key, row_number() over (partition by yr, area_id order by md5(key)) as rn,
                   count(*) over (partition by yr, area_id) as n
            from k
        )
        select {cols} from {t}
        where _source_file like {raw}
          and {key} in (select key from ranked where rn <= ceil(n * {frac}::numeric))
        order by {date}, {key}
        """
    ).format(
        key=sql.Identifier(dataset.sample_key),
        date=sql.Identifier(dataset.sample_date),
        t=sql.Identifier(SCHEMA, dataset.table),
        raw=sql.Literal(RAW_PREFIX + "%"),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        frac=sql.Literal(fraction),
    )


def write_sample(
    conn: psycopg.Connection, dataset: Dataset, fraction: float, out_root: Path
) -> Path | None:
    """Write one dataset's sample CSV. Returns its path, or None if bronze is empty."""
    columns = table_columns(conn, dataset.table)
    if not columns:
        log.info("%s: bronze.%s not loaded, no sample", dataset.name, dataset.table)
        return None
    columns = [c for c in columns if c not in METADATA_COLUMNS]
    (snapshot,) = conn.execute(
        sql.SQL("select max(_snapshot_date) from {} where _source_file like %s").format(
            sql.Identifier(SCHEMA, dataset.table)
        ),
        [RAW_PREFIX + "%"],
    ).fetchone()
    folder = out_root / dataset.subdir
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.csv"):
        old.unlink()  # one sample file per dataset; a re-run replaces it
    path = folder / f"{dataset.name}_sample_{snapshot}.csv"
    query = sample_query(dataset, columns, fraction)
    copy_sql = sql.SQL("copy ({}) to stdout (format csv, header true, force_quote *)").format(query)
    t0 = time.perf_counter()
    with conn.cursor() as cur, cur.copy(copy_sql) as copy, path.open("wb") as fh:
        for chunk in copy:
            fh.write(chunk)
    conn.commit()
    log.info(
        "%s: %s (%.1f MB) in %.0fs",
        dataset.name,
        path.relative_to(out_root.parent),
        path.stat().st_size / 1e6,
        time.perf_counter() - t0,
    )
    return path


def copy_rate_files(raw_root: Path, out_root: Path) -> list[Path]:
    """Copy the (small) rate files whole into the sample tree."""
    copied = []
    for name in ("fedfunds", "brent", "eibor"):
        d = config.DATASETS_BY_NAME[name]
        src_dir = raw_root / d.subdir
        for src in sorted(src_dir.glob("*.csv")) if src_dir.is_dir() else []:
            dst = out_root / d.subdir / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fraction", type=float, default=config.SAMPLE_FRACTION)
    parser.add_argument("--out", type=Path, default=config.DATA_SAMPLE)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not 0 < args.fraction <= 1:
        parser.error("--fraction must be in (0, 1]")

    with db.connect() as conn:
        conn.execute("set work_mem = '512MB'")
        for dataset in config.DATASETS:
            if dataset.enabled and dataset.sample_key:
                write_sample(conn, dataset, args.fraction, args.out)
    copied = copy_rate_files(config.DATA_RAW, args.out)
    log.info("rates: %d file(s) copied", len(copied))
    return 0


if __name__ == "__main__":
    sys.exit(main())
