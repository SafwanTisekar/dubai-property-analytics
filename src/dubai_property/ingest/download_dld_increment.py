"""Monthly DLD Open Data top-ups (docs/04 §1). Deferred: a stub for v1.

Why deferred: the bulk Dubai Pulse snapshot in ``data/raw/dld/transactions/`` already runs
to 2026-09-25, and the DLD portal export (``transactions_increment/``) has a different,
22-column schema whose ``TRANSACTION_NUMBER`` does not match the bulk ``transaction_id``.
Top-ups would need their own staging model and date-window de-duplication, which is not
needed until the first monthly refresh. Until then, refresh by downloading a new bulk
snapshot into ``data/raw/dld/<dataset>/``: the loader appends it, and silver keeps the
latest snapshot per row (rule C1).
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)


def main() -> int:
    """Log that the step is deferred and exit successfully, so `make download` runs."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info(
        "download_dld_increment: deferred for v1 (see module docstring). "
        "Place new bulk snapshots in data/raw/dld/<dataset>/ manually."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
