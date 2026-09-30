"""Project-wide constants: paths, schema names, split dates and business thresholds.

Everything a model or loader needs to agree on lives here so that no module hard-codes
a date or threshold. Each value cites the doc that defines it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

# --- Paths --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"  # immutable source CSVs (docs/03 §3)
DATA_RAW_DLD = DATA_RAW / "dld"
DATA_RAW_CBUAE = DATA_RAW / "cbuae"
DATA_RAW_FRED = DATA_RAW / "fred"
DATA_SAMPLE = DATA_DIR / "sample"  # 2% stratified sample for CI/dev
MANIFEST_NAME = "manifest.json"  # one per data root (raw/ or sample/)
MANIFEST_PATH = DATA_RAW / MANIFEST_NAME  # SHA-256 per loaded file
REPORTS = PROJECT_ROOT / "reports"
FIGURES = REPORTS / "figures"
INGEST_LOG = REPORTS / "ingest_log.csv"  # one row per file per load attempt (docs/04 §1)
DBT_DIR = PROJECT_ROOT / "dbt"
SQL_DIR = PROJECT_ROOT / "sql"
# Trained model binaries: gitignored, rebuilt by `make train`. Kept outside src/ so no
# ignore pattern can ever touch the dubai_property.models package.
ARTIFACTS_MODELS = PROJECT_ROOT / "artifacts" / "models"

# --- Database schemas (medallion layers, docs/03 §3) ---------------------------------
SCHEMA_BRONZE = "bronze"
SCHEMA_SILVER = "silver"
SCHEMA_GOLD = "gold"
SCHEMA_ML = "ml"
SCHEMA_RPT = "rpt"  # the only schema Power BI reads
SCHEMAS = (SCHEMA_BRONZE, SCHEMA_SILVER, SCHEMA_GOLD, SCHEMA_ML, SCHEMA_RPT)


# --- Bronze datasets (docs/04 §1) ------------------------------------------------------
@dataclass(frozen=True)
class Dataset:
    """One source folder that loads into one bronze table.

    Attributes:
        name: Short name used on the command line (``--dataset``).
        subdir: Folder relative to the data root (``data/raw`` or ``data/sample``).
        table: Target table in the ``bronze`` schema.
        source: Value written to the ``_source`` metadata column.
        enabled: Disabled datasets are listed but never loaded (reason in ``note``).
        sample_key: Column that groups the lines of one deal/contract. ``make sample``
            keeps or drops whole groups so multi-line structures survive sampling.
        sample_date: Date column whose year forms the sampling stratum (with ``area_id``).
        note: Why the dataset is configured this way.
    """

    name: str
    subdir: str
    table: str
    source: str
    enabled: bool = True
    sample_key: str | None = None
    sample_date: str | None = None
    note: str = ""


DATASETS: tuple[Dataset, ...] = (
    Dataset(
        "transactions",
        "dld/transactions",
        "dld_transactions",
        "bulk",
        sample_key="transaction_id",
        sample_date="instance_date",
        note="Dubai Pulse bulk export, 47 columns",
    ),
    Dataset(
        "rents",
        "dld/rents",
        "dld_rent_contracts",
        "bulk",
        sample_key="contract_id",
        sample_date="contract_start_date",
        note="Ejari bulk export, 41 columns, the large table",
    ),
    Dataset(
        "transactions_increment",
        "dld/transactions_increment",
        "dld_transactions_increment",
        "increment",
        enabled=False,
        note=(
            "DLD portal export (22-column schema, IDs don't match the bulk file). Fully "
            "overlapped by the bulk snapshot, so skipped for v1 (docs/04 Decisions)"
        ),
    ),
    Dataset("projects", "dld/projects", "dld_projects", "bulk", note="optional for v1"),
    Dataset("buildings", "dld/buildings", "dld_buildings", "bulk", note="optional for v1"),
    Dataset("units", "dld/units", "dld_units", "bulk", note="optional for v1"),
    Dataset("fedfunds", "fred/fedfunds", "rates_fedfunds", "fred", note="FRED FEDFUNDS"),
    Dataset("brent", "fred/dcoilbrenteu", "rates_brent", "fred", note="FRED DCOILBRENTEU"),
    Dataset("eibor", "cbuae", "rates_eibor", "cbuae", note="CBUAE EIBOR, manual download"),
)
DATASETS_BY_NAME = {d.name: d for d in DATASETS}

# FRED series id -> dataset name. Downloaded via the public CSV endpoint (no API key).
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_SERIES = {"FEDFUNDS": "fedfunds", "DCOILBRENTEU": "brent"}

# `make sample` (CLAUDE.md): share of deals/contracts kept per year x area stratum.
SAMPLE_FRACTION = 0.02

# --- Out-of-time split (docs/05 §1). Never random: time order is the whole point. -----
# Pre-2010 is excluded from training (too sparse, crisis-distorted); tested as ablation.
TRAIN_START = date(2010, 1, 1)
TRAIN_END = date(2023, 12, 31)
VALID_START = date(2024, 1, 1)
VALID_END = date(2024, 12, 31)
TEST_START = date(2025, 1, 1)  # test runs to the latest available transaction

# --- Business rules ------------------------------------------------------------------
# Min-n rule (CLAUDE.md, docs/05 §3): no median/yield/index point below 20 observations;
# roll up to zone level instead.
MIN_N = 20
# Units (CLAUDE.md): areas are stored in sq m; convert explicitly when showing sq ft.
SQM_TO_SQFT = 10.7639
# Hedonic price index base (docs/01 §4): Jan 2019 = 100.
INDEX_BASE_MONTH = date(2019, 1, 1)
INDEX_BASE_VALUE = 100.0

# --- AVM leakage alarms (CLAUDE.md) ---------------------------------------------------
# Real-world AVMs rarely beat ~5-8% MdAPE. Results better than this mean: investigate.
LEAKAGE_MDAPE_FLOOR = 0.03
LEAKAGE_HIT10_CEILING = 0.90
