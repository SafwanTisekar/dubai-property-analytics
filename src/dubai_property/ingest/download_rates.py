"""Download rate and macro series into ``data/raw`` (docs/02 §5, docs/04 §1).

* **FRED** ``FEDFUNDS`` (monthly) and ``DCOILBRENTEU`` (daily Brent) via the public CSV
  endpoint, no API key needed. Each download is saved as a dated snapshot,
  ``data/raw/fred/<series>/<SERIES>_<YYYY-MM-DD>.csv``, so bronze stays append-only and
  silver picks the latest snapshot (same rule C1 as DLD data). A snapshot that already
  exists for today is not downloaded again.
* **EIBOR** has no stable machine-readable endpoint at CBUAE, so it is a manual download:
  CSV files placed in ``data/raw/cbuae/`` are loaded; if none are there, EIBOR is skipped
  with a log message and the pipeline carries on (Fed Funds is the fallback rate driver,
  as the AED is pegged to the USD).

Loading into bronze uses the same loader as DLD files (``load_bronze``), so rates get the
same manifest, metadata columns and row-count reconciliation. ``make download`` only
downloads; ``make bronze`` loads; ``--load`` does both for the rate datasets.

Usage::

    uv run python -m dubai_property.ingest.download_rates [--load]
"""

from __future__ import annotations

import argparse
import logging
import urllib.request
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from dubai_property import config
from dubai_property.ingest import load_bronze

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60
USER_AGENT = "dubai-property-analytics/0.1 (portfolio project)"


def fetch(url: str) -> bytes:
    """GET a URL and return the body (raises on HTTP errors)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def check_fred_csv(series: str, body: bytes) -> int:
    """Validate a FRED CSV body and return its number of observations.

    Raises:
        ValueError: If the body isn't the expected two-column CSV for ``series`` (FRED
            returns an HTML error page for unknown series).
    """
    lines = body.decode("utf-8").strip().splitlines()
    header = [h.strip().upper() for h in lines[0].split(",")] if lines else []
    if len(header) != 2 or header[1] != series.upper():
        raise ValueError(f"unexpected FRED response for {series}: {lines[:1]}")
    return len(lines) - 1


def download_fred(
    series: str,
    *,
    root: Path = config.DATA_RAW,
    today: date | None = None,
    fetcher=fetch,
) -> Path:
    """Download one FRED series as a dated CSV snapshot. Returns the file path."""
    today = today or date.today()
    dataset = config.DATASETS_BY_NAME[config.FRED_SERIES[series]]
    folder = root / dataset.subdir
    path = folder / f"{series}_{today.isoformat()}.csv"
    if path.exists():
        log.info("%s: snapshot %s already downloaded", series, path.name)
        return path
    body = fetcher(config.FRED_CSV_URL.format(series=series))
    n = check_fred_csv(series, body)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(body)
    tmp.replace(path)  # atomic: a half-written file is never picked up by the loader
    log.info("%s: %d observations -> %s", series, n, path.relative_to(root.parent))
    return path


def eibor_files(root: Path = config.DATA_RAW) -> list[Path]:
    """CBUAE EIBOR CSVs placed manually in ``data/raw/cbuae/`` (may be empty)."""
    files = load_bronze.discover_files(root / config.DATASETS_BY_NAME["eibor"].subdir)
    if files:
        log.info("EIBOR: %d file(s) found in data/raw/cbuae", len(files))
    else:
        log.info(
            "EIBOR: no CSV in data/raw/cbuae, skipping. Download EIBOR history from "
            "centralbank.ae (open data) and save it there as CSV to include it."
        )
    return files


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--load", action="store_true", help="also load the rates into bronze")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    for series in config.FRED_SERIES:
        download_fred(series)
    eibor_files()
    if args.load:
        rate_datasets = [config.DATASETS_BY_NAME[n] for n in ("fedfunds", "brent", "eibor")]
        load_bronze.run(config.DATA_RAW, rate_datasets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
