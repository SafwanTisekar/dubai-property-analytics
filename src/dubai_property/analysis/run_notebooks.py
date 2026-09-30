"""Execute the Phase 3 notebooks in place (``make eda``) and check their size.

Each notebook runs top to bottom with nbclient, from the ``notebooks/`` folder, and is
saved with its outputs so GitHub renders the charts. A pre-commit hook blocks files over
1 MB, so the run fails if an executed notebook is larger than ``MAX_BYTES`` (inline charts
are 72 dpi for that reason; the full-resolution PNGs are in reports/figures/).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from dubai_property import config

log = logging.getLogger(__name__)

NOTEBOOK_DIR = config.PROJECT_ROOT / "notebooks"
NOTEBOOKS = ("01_market_cycles", "02_financing_mix", "03_prices_and_rents")
MAX_BYTES = 1_000_000
CELL_TIMEOUT_S = 600


def execute(path: Path) -> int:
    """Run one notebook in place and return its size in bytes."""
    nb = nbformat.read(path, as_version=4)
    NotebookClient(
        nb,
        timeout=CELL_TIMEOUT_S,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    ).execute()
    # Execution timestamps change on every run and add nothing to a reader: drop them.
    for cell in nb.cells:
        cell.metadata.pop("execution", None)
    nbformat.write(nb, path)
    return path.stat().st_size


def main(argv: list[str] | None = None) -> int:
    """Execute the notebooks named on the command line (default: all three)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", default=list(NOTEBOOKS))
    args = parser.parse_args(argv)
    too_big = []
    for name in args.names:
        path = NOTEBOOK_DIR / f"{name.removesuffix('.ipynb')}.ipynb"
        t0 = time.time()
        size = execute(path)
        log.info("%s: executed in %.0f s, %s KB", path.name, time.time() - t0, f"{size / 1e3:,.0f}")
        if size > MAX_BYTES:
            too_big.append(path.name)
    if too_big:
        log.error("Over %s bytes: %s", f"{MAX_BYTES:,}", ", ".join(too_big))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
