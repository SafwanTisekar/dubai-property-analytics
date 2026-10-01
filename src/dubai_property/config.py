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
ARTIFACTS = PROJECT_ROOT / "artifacts"
ARTIFACTS_MODELS = ARTIFACTS / "models"
# The database whose results are committed (reports/*.md, figures). Any other PG_DB (a
# scratch or fixture database) writes to reports/scratch/<db>/ and artifacts/scratch/<db>/
# instead (db.reports_dir), so a test run can't overwrite the full-data reports.
MAIN_DB = "dubai_property"
SCRATCH_DIRNAME = "scratch"

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
    Dataset(
        "price_index",
        "dld/price_index",
        "dld_price_index",
        "bulk",
        note=(
            "DLD Residential Sale Index (data.dubai): wide, one row per month, all / flat / "
            "villa. Used only to validate the hedonic index (docs/05 §2)"
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
# Reporting scope (docs/04 §3): from dim_date_start (dbt var; tests/test_config.py checks
# they agree) to the data snapshot date, which is data (silver.int_data_snapshot, the latest
# transaction date), not config.
REPORT_SCOPE_START = date(2004, 1, 1)
# Largest plausible unit area (sq m) per conformed property class id (seed_property_class);
# other classes use AREA_CAP_OTHER_SQM. Mirrors the dbt vars area_cap_* (checked by a test).
AREA_CAP_SQM = {1: 1000, 2: 3000, 4: 5000, 5: 5000}
AREA_CAP_OTHER_SQM = 10000
# Headline area-weighted AED per sq m (owner, 2026-09-30): residential apartments and
# villas / townhouses only, i.e. property_type_key 101 and 102 (usage group 1 x class 1, 2).
RESIDENTIAL_HOMES_KEYS = (101, 102)
RESIDENTIAL_APARTMENT_KEY = 101
# Hedonic price index base (docs/01 §4): Jan 2019 = 100.
INDEX_BASE_MONTH = date(2019, 1, 1)
INDEX_BASE_VALUE = 100.0

# --- Hedonic price index (docs/05 §2, decisions in §8) --------------------------------
# Every index starts in Jan 2011 (owner, 2026-10-01). In 2009-10, 30-50% of clean sales were
# registered after their application year (the Law 13/2008 backlog), so their prices date
# from the earlier boom and the index showed a rise through the 2009 crash. DLD's own index
# starts in 2011-03.
HEDONIC_START = date(2011, 1, 1)
# A segment is published monthly if this share of its months pass min-n, else quarterly if
# this share of its quarters pass, else not at all.
PERIOD_COVERAGE_MIN = 0.90
# Noise gate: a segment whose period-on-period log changes have a standard deviation above
# this is dominated by sampling noise (its base period, and so every level, is unreliable)
# and isn't published. Set on 2026-10-01 after the first full run: every segment was <= 0.09
# except JVC villas (quarterly, 0.16, one 69% quarter-on-quarter jump).
NOISE_MAX_SD = 0.10
# Peak-to-trough episodes: a fall of at least 10% from the running peak. Smaller dips are
# within the noise of a monthly hedonic index.
EPISODE_MIN_DRAWDOWN = 0.10
# Published method (owner, 2026-10-01): rolling-window time dummy (RTD), 36-month windows
# stepped 12 months, chained on the overlapping periods. One pooled fit over the whole span
# is kept as the robustness comparison; a gap above these limits is called "material".
RTD_WINDOW_MONTHS = 36
RTD_STEP_MONTHS = 12
RTD_MATERIAL_LEVEL_GAP = 0.05
RTD_MATERIAL_YOY_GAP = 0.03
# DLD's monthly index behaves like a trailing 12-month average (ours leads it by ~6
# months), so validation also compares our index averaged over the same 12 months.
DLD_ALIGN_MONTHS = 12
# DLD's official index (validation only): monthly ratio, Jan 2012 = 1.000.
DLD_INDEX_BASE_MONTH = date(2012, 1, 1)
HEDONIC_MODEL_VERSION = "hedonic-rtd-v1"

# --- Rental yields (docs/05 §3) --------------------------------------------------------
# docs/04 §4 "yield sanity": a gross yield outside 2-15% for a segment with n >= 20 is a
# warning sign (a bedroom label or a price that doesn't match the rent's unit).
YIELD_SANITY = (0.02, 0.15)
YIELD_START = date(2010, 1, 1)
YIELD_MODEL_VERSION = "yield-gross-v1"

# --- AVM (docs/05 §1, decisions in §8) ------------------------------------------------
# Fitting starts in 2011, like the index (owner, 2026-10-01): 2009-10 registrations carry
# backlog prices agreed in the 2006-08 boom. 2010 sales are loaded only as history for the
# trailing features of early-2011 sales. TRAIN_START (2010) is kept for the ablation.
AVM_TRAIN_START = date(2011, 1, 1)
AVM_HISTORY_START = date(2010, 1, 1)
# Comparable-sales baselines: a cell is area x property type x bedrooms x off-plan flag.
# A valuation needs at least this many comparables (a valuer's comp set; the min-n rule
# is for *published* medians and doesn't apply to one sale's estimate).
AVM_COMPS_MIN_N = 5
AVM_COMPS_MONTHS = 6  # baseline (a): median over the previous 6 months (docs/05 §1)
AVM_COMPS_INDEXED_MONTHS = 12  # baseline (b): comps of the last 12 months, index-adjusted
# |gap| above this flags a sale for collateral review: a statistical anomaly, not an
# accusation (docs/05 §1). Set only on out-of-sample rows (owner, 2026-10-01).
AVM_REVIEW_GAP = 0.25
AVM_OPTUNA_TRIALS = 20  # docs/05 §1 allows 50; 20 on full data (docs/05 §8)
AVM_SEED = 42
# Breakdowns: price bands (AED) by *predicted* value (owner, 2026-10-01: banding by the
# actual price builds in regression to the mean); the top areas by test volume.
AVM_PRICE_BANDS = (1_000_000, 2_000_000, 5_000_000)
AVM_TOP_AREAS = 20
AVM_SHAP_SAMPLE = 20_000
AVM_MODEL_VERSION = "avm-lgbm-v1"

# --- AVM leakage alarms (CLAUDE.md) ---------------------------------------------------
# Real-world AVMs rarely beat ~5-8% MdAPE. Results better than this mean: investigate.
LEAKAGE_MDAPE_FLOOR = 0.03
LEAKAGE_HIT10_CEILING = 0.90
# The alarm needs this many scored test sales: on the ~2k-line CI fixtures a handful of
# test sales can land anywhere, so their metrics mean nothing.
LEAKAGE_MIN_SCORED = 1_000

# --- Collateral stress test (docs/05 §4, Phase 4c) -------------------------------------
# Illustrative, not a regulatory stress test. Population: clean residential market sales of
# the last 36 complete months before the snapshot (the recent-vintage buyers).
STRESS_WINDOW_MONTHS = 36
# Assumed-LTV grid (integer %, the Power BI what-if keys; docs/06). 85 is the CBUAE cap for a
# UAE national's first home up to AED 5M: the most permissive cap, so the worst case (owner,
# 2026-10-01).
STRESS_LTV_GRID = (50, 60, 70, 80, 85)
STRESS_LTV_LABELS = {85: "UAE national first home cap (worst case)"}
# Price shocks on top of the mark-to-market value: 0 to -50% in 5-point steps (integers).
STRESS_SHOCKS = tuple(range(0, -55, -5))
# Reference scenario: the CBUAE cap in force on the sale date for this borrower (seed
# seed_ltv_rules). Nationality and first/second home aren't in the register; an expatriate
# first home matches the observed median loan/price of 0.80 since 2020 (findings F2.4).
STRESS_CAP_BORROWER = "Expatriate"
STRESS_CAP_HOME = "first"
STRESS_CAP_VALUE_BAND_AED = 5_000_000  # "up to AED 5M" / "above AED 5M" in the seed
# Historical replay (owner, 2026-10-01): the 2014 -> 2020 episode, peak to trough, measured
# per series inside this window. A zone series is used only if it is published from the
# peak month on (so it saw the 2014 peak); otherwise its type series.
STRESS_REPLAY_START = date(2014, 1, 1)
STRESS_REPLAY_END = date(2021, 12, 1)
STRESS_REPLAY_PEAK_BY = date(2014, 6, 1)
STRESS_REPLAY_NAME = "replay_2014_2020"
# The same episode at the Dubai-wide depth (the Dubai series' drawdown, -24%, for every
# buyer), shown beside the zone-level replay (owner, 2026-10-01): zone max-drawdowns come
# from noisier series and overstate the depth, so the zone replay is an upper range.
STRESS_REPLAY_DUBAI_NAME = "replay_2014_2020_dubai"
STRESS_MODEL_VERSION = "stress-mtm-v1"

# --- Market forecast (docs/05 §5, Phase 4c) ---------------------------------------------
# Rolling-origin backtest: forecasts made at the start of each of the last 24 complete
# months, scored at these horizons (months ahead).
FORECAST_ORIGINS = 24
FORECAST_HORIZONS = (1, 3, 6, 12)
FORECAST_STEPS = 12
# Fed Funds (the EIBOR proxy while EIBOR isn't loaded, docs/01: the AED is pegged to the USD)
# enters lagged by this many months, so a rate change reaches prices after the lag.
FORECAST_RATE_LAG = 6
# Rate scenarios: a step change from the first forecast month, in basis points.
FORECAST_RATE_SCENARIOS = {"rates_flat": 0, "rates_up_100bp": 100, "rates_down_100bp": -100}
FORECAST_INTERVALS = (0.80, 0.95)
# Series need this many months before the first backtest origin to fit SARIMAX at all.
FORECAST_MIN_MONTHS = 48
FORECAST_MODEL_VERSION = "forecast-sarimax-v1"
