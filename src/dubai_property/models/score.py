"""``make score``: finish the ml.* tables and build the rpt views over them.

1. Runs the collateral stress test (``models.stress_test``). It fits nothing: it marks the
   recent book to market against the published index and writes ``ml.stress_grid`` and
   ``ml.stress_replay``. The fitted models (index, yields, AVM, forecast) write their
   tables in ``make train``.
2. Checks that every ml.* table the rpt views read exists for its current model version,
   and logs its row count, so a missing ``make train`` step fails here with a clear message
   instead of as a dbt compilation error.
3. Runs ``dbt build --select tag:post_ml`` (the rpt views and their tests).

Usage::

    uv run python -m dubai_property.models.score      # make score
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from psycopg import sql

from dubai_property import config, db
from dubai_property.models import stress_test

log = logging.getLogger(__name__)

# ml table -> the model version rpt shows (the dbt vars match these; tests/test_config.py).
ML_TABLES = {
    "fct_price_index": config.HEDONIC_MODEL_VERSION,
    "agg_yield_quarter": config.YIELD_MODEL_VERSION,
    "avm_score": config.AVM_MODEL_VERSION,
    "avm_performance": config.AVM_MODEL_VERSION,
    "feature_importance": config.AVM_MODEL_VERSION,
    "stress_grid": config.STRESS_MODEL_VERSION,
    "stress_replay": config.STRESS_MODEL_VERSION,
    "forecast": config.FORECAST_MODEL_VERSION,
    "forecast_backtest": config.FORECAST_MODEL_VERSION,
}


def table_counts() -> dict[str, int | None]:
    """Rows of the current model version per ml table (None if the table is missing)."""
    out: dict[str, int | None] = {}
    with db.connect() as conn:
        for table, version in ML_TABLES.items():
            (reg,) = conn.execute(
                "select to_regclass(%s)", [f"{config.SCHEMA_ML}.{table}"]
            ).fetchone()
            if reg is None:
                out[table] = None
                continue
            stmt = sql.SQL("select count(*) from {}.{} where model_version = %s").format(
                sql.Identifier(config.SCHEMA_ML), sql.Identifier(table)
            )
            (out[table],) = conn.execute(stmt, [version]).fetchone()
    return out


def dbt_executable() -> str:
    """The dbt installed next to this interpreter (the uv environment)."""
    path = Path(sys.executable).parent / "dbt"
    return str(path) if path.exists() else "dbt"


def run_dbt() -> int:
    """``dbt build --select tag:post_ml``; returns dbt's exit code."""
    cmd = [dbt_executable(), "build", "--select", "tag:post_ml", "--profiles-dir", "."]
    log.info("running %s", " ".join(cmd))
    return subprocess.run(cmd, cwd=config.DBT_DIR, check=False).returncode


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make score``)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-stress", action="store_true", help="don't re-run the stress test")
    parser.add_argument("--skip-dbt", action="store_true", help="don't build the rpt views")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not args.skip_stress:
        stress_test.run()
    counts = table_counts()
    for table, n in counts.items():
        log.info("%s.%s: %s rows", config.SCHEMA_ML, table, "MISSING" if n is None else f"{n:,}")
    missing = [t for t, n in counts.items() if n is None]
    if missing:
        log.error("missing ml tables %s: run make train first", ", ".join(missing))
        return 1
    return 0 if args.skip_dbt else run_dbt()


if __name__ == "__main__":
    sys.exit(main())
