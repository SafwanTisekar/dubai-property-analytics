"""Project-wide constants: paths, schema names, split dates and business thresholds.

Everything a model or loader needs to agree on lives here so that no module hard-codes
a date or threshold. Each value cites the doc that defines it.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

# --- Paths --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"  # immutable source CSVs (docs/03 §3)
DATA_RAW_DLD = DATA_RAW / "dld"
DATA_RAW_CBUAE = DATA_RAW / "cbuae"
DATA_SAMPLE = DATA_DIR / "sample"  # 2% stratified sample for CI/dev
MANIFEST_PATH = DATA_RAW / "manifest.json"  # SHA-256 per loaded file
REPORTS = PROJECT_ROOT / "reports"
FIGURES = REPORTS / "figures"
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
