"""Collateral stress test (docs/05 §4): negative equity of recent buyers under price shocks.

**Illustrative, not a regulatory stress test.** The question (docs/01 Q7): if prices fall
X%, what share of recent buyers would owe more than their home is worth, at typical
loan-to-value (LTV) ratios, and where?

Steps:

1. **Population.** Clean residential market sales (apartments, villas / townhouses) of the
   last 36 complete months before the data snapshot (the partial snapshot month is left
   out), with the purchase mortgage matched to the sale where Phase 3 found one.
2. **Mark-to-market.** current value = price × (index now / index at purchase), using the
   published hedonic index (``ml.fct_price_index``) of the sale's zone × type where that
   series is published and has a point for the purchase period, else its type series.
   "Now" is the series' latest *complete* period (Aug 2026 monthly, Q2 2026 quarterly).
3. **Loans.** Three bases, each a separate view:

   * ``grid``: an assumed loan = price × LTV for LTV 50 / 60 / 70 / 80 / 85% (85 = the UAE
     national first-home cap, the worst case);
   * ``cbuae_cap``: the reference scenario, the CBUAE cap in force on the sale date for an
     expatriate's first home (``seed_ltv_rules``: 80% up to AED 5M / 70% above since
     2020-04-08, 75% / 65% before; off-plan 50%);
   * ``actual_loan``: the registered loan of a matched purchase mortgage (ready sales only;
     the match is a lower bound, ~37% of ready purchases).

   The loan is held at its origination amount (no amortisation). Real balances are lower,
   so negative equity is overstated: conservative, and stated in the report.
4. **Shocks.** shocked value = current value × (1 + shock) for shocks 0 to −50% in 5-point
   steps, plus a historical replay: each series' 2014 → 2020 drawdown (Dubai −24%,
   apartments −25%, villas −30%; zone series where they cover the 2014 peak).
5. **Negative equity**: loan > shocked value. Count, share and AED (Σ loan − value) per
   segment (Dubai / type / zone × type / area × type, each split ready vs off-plan).
   Min-n: segments with fewer than 20 purchases keep their count but no share or AED.

**Off-plan is never pooled with ready.** Banks cap off-plan lending at 50% and most
off-plan buyers pay the developer in instalments, so an assumed LTV on the full price
overstates what a bank has at risk; off-plan rows are a separate segment and the report
says so. The off-plan premium is held fixed by the index (it carries an off-plan control),
so marking an off-plan purchase to market with it is like for like.

The sales (~0.5M rows, 10 columns) are model-sized; everything after the load is Polars,
and the grid is aggregated per cell before it is rolled up (all measures are additive).

Usage::

    uv run python -m dubai_property.models.stress_test      # part of make score
"""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

import connectorx as cx
import polars as pl

from dubai_property import config, db
from dubai_property.models.hedonic_index import add_months

log = logging.getLogger(__name__)

GRID_TABLE = "stress_grid"
REPLAY_TABLE = "stress_replay"
ARTIFACTS_NAME = "stress_test"
APARTMENT, VILLA = config.RESIDENTIAL_APARTMENT_KEY, 102

# Finest cell: every published level is a roll-up of these (counts and AED are additive).
CELL = ["area_key", "zone", "property_type_key", "is_offplan"]
LEVELS: dict[str, list[str]] = {
    "dubai": [],
    "type": ["property_type_key"],
    "zone": ["zone", "property_type_key"],
    "area": ["area_key", "zone", "property_type_key"],
}
SCENARIO_KEYS = ["scenario", "shock_pct", "ltv_basis", "ltv_pct"]
SUMS = [
    "purchases",
    "loan_aed",
    "current_value_aed",
    "negative_equity_count",
    "negative_equity_aed",
    "shock_sum",
    "zone_basis_count",
]


def diagnostics_path() -> Path:
    """``artifacts/stress_test/diagnostics.json`` (scratch DBs: under artifacts/scratch/)."""
    return db.artifacts_dir() / ARTIFACTS_NAME / "diagnostics.json"


POPULATION_SQL = """
select t.transaction_id,
       t.txn_date,
       date_trunc('month', t.txn_date)::date as month,
       t.area_key,
       coalesce(a.zone, 'Unknown') as zone,
       t.property_type_key,
       t.is_offplan,
       t.actual_worth_aed::float8 as price_aed,
       pm.loan_aed::float8 as loan_aed
from gold.fct_transaction as t
join gold.dim_area as a on a.area_key = t.area_key
left join silver.int_purchase_mortgage_pairs as pm on pm.sale_transaction_id = t.transaction_id
where t.is_clean_market_sale
  and t.is_in_report_scope
  and t.property_type_key in ({apt}, {villa})
  and t.txn_date >= date '{start}'
  and t.txn_date < date '{end}'
  and t.actual_worth_aed > 0
"""

INDEX_SQL = """
select segment_id, segment_level, property_type_key, zone, frequency, period_start,
       index_value::float8 as index_value, is_partial_period
from {ml}.fct_price_index
where model_version = '{version}'
"""

RULES_SQL = """
select rule_id, borrower, property_status, home_number, value_band, max_ltv::float8 as max_ltv,
       effective_from, effective_to, source_citation
from silver.seed_ltv_rules
"""

GRID_DDL = f"""
create table if not exists {config.SCHEMA_ML}.{GRID_TABLE} (
    model_version          text           not null,
    fitted_at              timestamptz    not null,
    snapshot_date          date           not null,
    window_start           date           not null,
    window_end             date           not null,
    segment_level          text           not null,
    property_type_key      integer,
    zone                   text,
    area_key               integer,
    is_offplan             boolean        not null,
    scenario               text           not null,
    shock_pct              integer,
    applied_shock          numeric(8, 6),
    ltv_basis              text           not null,
    ltv_pct                integer,
    purchases              integer        not null,
    loan_aed               numeric(18, 2),
    current_value_aed      numeric(18, 2),
    negative_equity_count  integer,
    negative_equity_share  numeric(8, 6),
    negative_equity_aed    numeric(18, 2),
    index_zone_share       numeric(8, 6),
    is_published           boolean        not null
)
"""

GRID_COLUMNS = [
    "model_version", "fitted_at", "snapshot_date", "window_start", "window_end",
    "segment_level", "property_type_key", "zone", "area_key", "is_offplan", "scenario",
    "shock_pct", "applied_shock", "ltv_basis", "ltv_pct", "purchases", "loan_aed",
    "current_value_aed", "negative_equity_count", "negative_equity_share",
    "negative_equity_aed", "index_zone_share", "is_published",
]  # fmt: skip

REPLAY_DDL = f"""
create table if not exists {config.SCHEMA_ML}.{REPLAY_TABLE} (
    model_version     text          not null,
    fitted_at         timestamptz   not null,
    segment_id        text          not null,
    segment_level     text          not null,
    property_type_key integer,
    zone              text,
    frequency         text          not null,
    first_period      date          not null,
    peak_period       date,
    peak_index        numeric(10, 4),
    trough_period     date,
    trough_index      numeric(10, 4),
    drawdown          numeric(8, 6),
    is_used           boolean       not null,
    note              text,
    primary key (model_version, segment_id)
)
"""

REPLAY_COLUMNS = [
    "model_version", "fitted_at", "segment_id", "segment_level", "property_type_key", "zone",
    "frequency", "first_period", "peak_period", "peak_index", "trough_period", "trough_index",
    "drawdown", "is_used", "note",
]  # fmt: skip


# --- Window ---------------------------------------------------------------------------
def last_complete_month(snapshot: date) -> date:
    """The snapshot's month if the snapshot is its last day, else the month before."""
    month = date(snapshot.year, snapshot.month, 1)
    month_end = date.fromordinal(add_months(month, 1).toordinal() - 1)
    return month if snapshot == month_end else add_months(month, -1)


def window(snapshot: date, months: int = config.STRESS_WINDOW_MONTHS) -> tuple[date, date]:
    """First and last month of the population: ``months`` complete months to the snapshot."""
    last = last_complete_month(snapshot)
    return add_months(last, -(months - 1)), last


# --- CBUAE cap (reference scenario) -------------------------------------------------------
def value_band(price: pl.Expr, threshold: int = config.STRESS_CAP_VALUE_BAND_AED) -> pl.Expr:
    """The seed's value band label for a price ("up to AED 5M" / "above AED 5M")."""
    m = f"{threshold / 1e6:g}M"
    return (
        pl.when(price <= threshold)
        .then(pl.lit(f"up to AED {m}"))
        .otherwise(pl.lit(f"above AED {m}"))
    )


def cap_ltv(
    sales: pl.DataFrame,
    rules: pl.DataFrame,
    borrower: str = config.STRESS_CAP_BORROWER,
    home: str = config.STRESS_CAP_HOME,
) -> pl.DataFrame:
    """Add ``cap_ltv`` and ``cap_rule_id``: the cap in force on each sale's date.

    The rule must match the property status (off-plan / ready), the borrower (or "Any"),
    the home number (or "any"), the price's value band (or "any") and the sale date
    (``effective_from`` ≤ date ≤ ``effective_to``, an open end if NULL). A sale with no
    matching rule gets NULL; two matches raise (the seed's no-overlap test should prevent it).
    """
    r = rules.filter(
        pl.col("borrower").is_in([borrower, "Any"]) & pl.col("home_number").is_in([home, "any"])
    ).select("rule_id", "property_status", "value_band", "max_ltv", "effective_from",
             "effective_to")  # fmt: skip
    keyed = sales.with_row_index("_row").with_columns(
        _status=pl.when(pl.col("is_offplan")).then(pl.lit("off-plan")).otherwise(pl.lit("ready")),
        _band=value_band(pl.col("price_aed")),
    )
    matches = (
        keyed.select("_row", "_status", "_band", "txn_date")
        .join(r, left_on="_status", right_on="property_status", how="inner")
        .filter(
            ((pl.col("value_band") == "any") | (pl.col("value_band") == pl.col("_band")))
            & (pl.col("effective_from") <= pl.col("txn_date"))
            & (pl.col("effective_to").is_null() | (pl.col("txn_date") <= pl.col("effective_to")))
        )
    )
    dupes = matches.group_by("_row").len().filter(pl.col("len") > 1)
    if dupes.height:
        raise ValueError(f"{dupes.height} sales match more than one LTV rule: check the seed")
    out = keyed.join(
        matches.select("_row", cap_ltv=pl.col("max_ltv"), cap_rule_id=pl.col("rule_id")),
        on="_row",
        how="left",
    )
    return out.drop("_row", "_status", "_band")


# --- Mark-to-market ---------------------------------------------------------------------
def _period(month: pl.Expr, frequency: pl.Expr) -> pl.Expr:
    return pl.when(frequency == "quarter").then(month.dt.truncate("1q")).otherwise(month)


def _attach_series(sales: pl.DataFrame, index: pl.DataFrame, level: str) -> pl.DataFrame:
    """Per sale (``_row``): this level's series, its value at purchase and now.

    ``<level>_ok`` says whether the series can mark the sale: it has a point for the
    purchase period, and that period is no later than "now".
    """
    seg = index.filter(pl.col("segment_level") == level)
    keys = ["property_type_key"] + (["zone"] if level == "zone" else [])
    now = (
        seg.filter(~pl.col("is_partial_period"))
        .sort("period_start")
        .group_by("segment_id")
        .agg(now_period=pl.col("period_start").last(), idx_now=pl.col("index_value").last())
    )
    meta = seg.select("segment_id", *keys, "frequency").unique().join(now, on="segment_id")
    points = seg.select("segment_id", period=pl.col("period_start"), idx_buy=pl.col("index_value"))
    out = (
        sales.select("_row", "month", *keys)
        .join(meta, on=keys, how="left")
        .with_columns(period=_period(pl.col("month"), pl.col("frequency")))
        .join(points, on=["segment_id", "period"], how="left")
        .with_columns(
            ok=pl.col("idx_buy").is_not_null()
            & pl.col("idx_now").is_not_null()
            & (pl.col("period") <= pl.col("now_period"))
        )
    )
    return out.select(
        "_row",
        pl.col("segment_id").alias(f"{level}_segment"),
        pl.col("idx_buy").alias(f"{level}_idx_buy"),
        pl.col("idx_now").alias(f"{level}_idx_now"),
        pl.col("ok").fill_null(False).alias(f"{level}_ok"),
    )


def mark_to_market(sales: pl.DataFrame, index: pl.DataFrame) -> pl.DataFrame:
    """Add ``index_segment``, ``index_basis``, ``mtm_ratio`` and ``current_value_aed``.

    ``index_basis`` is zone, type or None: sales no published series can mark get NULLs (the
    caller logs and drops them).
    """
    s = sales.with_row_index("_row")
    zone = _attach_series(s, index, "zone")
    typ = _attach_series(s, index, "type")
    out = s.join(zone, on="_row", how="left").join(typ, on="_row", how="left")
    use_zone, use_type = pl.col("zone_ok"), ~pl.col("zone_ok") & pl.col("type_ok")
    out = out.with_columns(
        index_basis=pl.when(use_zone)
        .then(pl.lit("zone"))
        .when(use_type)
        .then(pl.lit("type"))
        .otherwise(pl.lit(None, dtype=pl.Utf8)),
        index_segment=pl.when(use_zone)
        .then(pl.col("zone_segment"))
        .when(use_type)
        .then(pl.col("type_segment")),
        mtm_ratio=pl.when(use_zone)
        .then(pl.col("zone_idx_now") / pl.col("zone_idx_buy"))
        .when(use_type)
        .then(pl.col("type_idx_now") / pl.col("type_idx_buy")),
    ).with_columns(current_value_aed=pl.col("price_aed") * pl.col("mtm_ratio"))
    drop = [c for c in out.columns if c.startswith(("zone_", "type_"))] + ["_row"]
    return out.drop(drop)


# --- Historical replay ------------------------------------------------------------------
def replay_drawdowns(
    index: pl.DataFrame,
    start: date = config.STRESS_REPLAY_START,
    end: date = config.STRESS_REPLAY_END,
    peak_by: date = config.STRESS_REPLAY_PEAK_BY,
) -> pl.DataFrame:
    """Each series' deepest fall from its running peak inside [start, end].

    A zone series is used only if it is published from ``peak_by`` or earlier, so it saw
    the 2014 peak (a series starting in 2016 would measure a smaller, later fall). Type
    and Dubai series start in 2011 and are always used.
    """
    rows = []
    for (sid,), g in index.sort("period_start").group_by(["segment_id"], maintain_order=True):
        first = g["period_start"].min()
        meta = g.row(0, named=True)
        row = {
            "segment_id": sid,
            "segment_level": meta["segment_level"],
            "property_type_key": meta["property_type_key"],
            "zone": meta["zone"],
            "frequency": meta["frequency"],
            "first_period": first,
            "peak_period": None,
            "peak_index": None,
            "trough_period": None,
            "trough_index": None,
            "drawdown": None,
            "is_used": False,
            "note": None,
        }
        w = g.filter(pl.col("period_start").is_between(start, end))
        if first > peak_by:
            row["note"] = f"published from {first:%b %Y}, after the {peak_by:%b %Y} peak: type used"
        elif w.height < 2:
            row["note"] = "too few points in the replay window"
        else:
            periods, values = w["period_start"].to_list(), w["index_value"].to_list()
            peak_i, worst, trough_i, best_peak_i = 0, 0.0, None, 0
            for i, v in enumerate(values):
                if v > values[peak_i]:
                    peak_i = i
                dd = v / values[peak_i] - 1
                if dd < worst:
                    worst, trough_i, best_peak_i = dd, i, peak_i
            if trough_i is None:
                row["note"] = "no fall in the replay window"
                row.update(drawdown=0.0, is_used=True)
            else:
                row.update(
                    peak_period=periods[best_peak_i],
                    peak_index=values[best_peak_i],
                    trough_period=periods[trough_i],
                    trough_index=values[trough_i],
                    drawdown=worst,
                    is_used=True,
                )
        rows.append(row)
    schema = {
        "segment_id": pl.Utf8,
        "segment_level": pl.Utf8,
        "property_type_key": pl.Int32,
        "zone": pl.Utf8,
        "frequency": pl.Utf8,
        "first_period": pl.Date,
        "peak_period": pl.Date,
        "peak_index": pl.Float64,
        "trough_period": pl.Date,
        "trough_index": pl.Float64,
        "drawdown": pl.Float64,
        "is_used": pl.Boolean,
        "note": pl.Utf8,
    }
    return pl.DataFrame(rows, schema=schema)


def attach_replay(sales: pl.DataFrame, replay: pl.DataFrame) -> pl.DataFrame:
    """Add ``replay_shock`` and ``replay_basis`` to each sale.

    The shock is the zone × type series' drawdown where the replay uses it, else the type's.
    """
    used = replay.filter(pl.col("is_used"))
    zone = used.filter(pl.col("segment_level") == "zone").select(
        "property_type_key", "zone", zone_dd=pl.col("drawdown")
    )
    typ = used.filter(pl.col("segment_level") == "type").select(
        "property_type_key", type_dd=pl.col("drawdown")
    )
    out = sales.join(zone, on=["property_type_key", "zone"], how="left").join(
        typ, on="property_type_key", how="left"
    )
    return out.with_columns(
        replay_shock=pl.coalesce("zone_dd", "type_dd"),
        replay_basis=pl.when(pl.col("zone_dd").is_not_null())
        .then(pl.lit("zone"))
        .when(pl.col("type_dd").is_not_null())
        .then(pl.lit("type")),
    ).drop("zone_dd", "type_dd")


# --- Loans and negative equity ------------------------------------------------------------
def loan_book(
    sales: pl.DataFrame, ltv_grid: Sequence[int] = config.STRESS_LTV_GRID
) -> pl.DataFrame:
    """One row per sale × loan basis, each loan held at origination.

    Bases: the assumed grid loans, the CBUAE cap loan and (matched purchases only) the
    registered loan.
    """
    base = sales.select(
        *CELL,
        "current_value_aed",
        "replay_shock",
        zone_basis=(pl.col("index_basis") == "zone").cast(pl.Int64),
        price=pl.col("price_aed"),
        actual=pl.col("loan_aed"),
        cap=pl.col("cap_ltv"),
    )
    parts = [
        base.with_columns(
            ltv_basis=pl.lit("grid"),
            ltv_pct=pl.lit(ltv, dtype=pl.Int32),
            loan=pl.col("price") * ltv / 100,
        )
        for ltv in ltv_grid
    ]
    parts.append(
        base.filter(pl.col("cap").is_not_null()).with_columns(
            ltv_basis=pl.lit("cbuae_cap"),
            ltv_pct=pl.lit(None, dtype=pl.Int32),
            loan=pl.col("price") * pl.col("cap"),
        )
    )
    parts.append(
        base.filter(pl.col("actual").is_not_null()).with_columns(
            ltv_basis=pl.lit("actual_loan"),
            ltv_pct=pl.lit(None, dtype=pl.Int32),
            loan=pl.col("actual"),
        )
    )
    return pl.concat(parts).drop("price", "actual", "cap")


def stress_cells(
    book: pl.DataFrame,
    shocks: Sequence[int] = config.STRESS_SHOCKS,
    replay_name: str = config.STRESS_REPLAY_NAME,
) -> pl.DataFrame:
    """Negative equity per finest cell × loan basis × scenario (additive measures only)."""
    scenarios: list[tuple[str, int | None, pl.Expr]] = [
        ("grid", s, pl.lit(s / 100)) for s in shocks
    ]
    scenarios.append((replay_name, None, pl.col("replay_shock")))
    frames = []
    for name, shock_pct, shock in scenarios:
        b = book if name == "grid" else book.filter(pl.col("replay_shock").is_not_null())
        shocked = pl.col("current_value_aed") * (1 + shock)
        ne = pl.col("loan") > shocked
        frames.append(
            b.group_by(*CELL, "ltv_basis", "ltv_pct")
            .agg(
                purchases=pl.len(),
                loan_aed=pl.col("loan").sum(),
                current_value_aed=pl.col("current_value_aed").sum(),
                negative_equity_count=ne.sum(),
                negative_equity_aed=pl.when(ne).then(pl.col("loan") - shocked).otherwise(0).sum(),
                shock_sum=shock.sum() if name != "grid" else pl.len() * (shock_pct / 100),
                zone_basis_count=pl.col("zone_basis").sum(),
            )
            .with_columns(scenario=pl.lit(name), shock_pct=pl.lit(shock_pct, dtype=pl.Int32))
        )
    out = pl.concat(frames)
    return out.with_columns(pl.col(SUMS).cast(pl.Float64))


def roll_up(cells: pl.DataFrame, min_n: int = config.MIN_N) -> pl.DataFrame:
    """Sum the cells to every level (each split ready / off-plan) and apply min-n.

    Under min-n a row keeps its purchase count but no share, AED or applied shock.
    """
    frames = []
    for level, keys in LEVELS.items():
        g = (
            cells.group_by(*keys, "is_offplan", *SCENARIO_KEYS)
            .agg(pl.col(SUMS).sum())
            .with_columns(segment_level=pl.lit(level))
        )
        frames.append(g)
    out = pl.concat(frames, how="diagonal_relaxed")
    published = pl.col("purchases") >= min_n
    return out.with_columns(
        is_published=published,
        negative_equity_share=pl.when(published).then(
            pl.col("negative_equity_count") / pl.col("purchases")
        ),
        negative_equity_aed=pl.when(published).then(pl.col("negative_equity_aed")),
        negative_equity_count=pl.when(published).then(pl.col("negative_equity_count")),
        applied_shock=pl.col("shock_sum") / pl.col("purchases"),
        index_zone_share=pl.col("zone_basis_count") / pl.col("purchases"),
    ).drop("shock_sum", "zone_basis_count")


# --- Database I/O -------------------------------------------------------------------
def load_sales(start: date, end_month: date) -> pl.DataFrame:
    """Clean residential sales of the window (via connectorx)."""
    sql = POPULATION_SQL.format(
        apt=APARTMENT, villa=VILLA, start=start.isoformat(), end=add_months(end_month, 1)
    )
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    return df.with_columns(
        pl.col("txn_date").cast(pl.Date),
        pl.col("month").cast(pl.Date),
        pl.col("area_key").cast(pl.Int32),
        pl.col("property_type_key").cast(pl.Int32),
    )


def load_index() -> pl.DataFrame:
    """The published hedonic index (current model version)."""
    sql = INDEX_SQL.format(ml=config.SCHEMA_ML, version=config.HEDONIC_MODEL_VERSION)
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    return df.with_columns(
        pl.col("period_start").cast(pl.Date), pl.col("property_type_key").cast(pl.Int32)
    )


def load_rules() -> pl.DataFrame:
    """The dated CBUAE LTV caps (``seed_ltv_rules``)."""
    df = cx.read_sql(db.connectorx_uri(), RULES_SQL, return_type="polars")
    return df.with_columns(
        pl.col("effective_from").cast(pl.Date), pl.col("effective_to").cast(pl.Date)
    )


def write_table(conn, ddl: str, table: str, version: str, frame: pl.DataFrame) -> int:
    """Replace this model version's rows in ``ml.<table>`` (caller commits)."""
    conn.execute(ddl)
    conn.execute(f"delete from {config.SCHEMA_ML}.{table} where model_version = %s", [version])
    n = db.copy_frame(conn, frame, config.SCHEMA_ML, table)
    conn.execute(f"analyze {config.SCHEMA_ML}.{table}")
    return n


# --- Orchestration ------------------------------------------------------------------
def summarise_loans(sales: pl.DataFrame) -> dict:
    """Match rate and LTV distribution of the matched purchase mortgages (report inputs)."""
    ready = sales.filter(~pl.col("is_offplan"))
    m = ready.filter(pl.col("loan_aed").is_not_null()).with_columns(
        purchase_ltv=pl.col("loan_aed") / pl.col("price_aed"),
        current_ltv=pl.col("loan_aed") / pl.col("current_value_aed"),
    )
    out: dict = {
        "ready_purchases": ready.height,
        "matched_loans": m.height,
        "match_rate": m.height / ready.height if ready.height else None,
    }
    if m.height:
        out.update(
            purchase_ltv_median=m["purchase_ltv"].median(),
            current_ltv_median=m["current_ltv"].median(),
            current_ltv_p90=m["current_ltv"].quantile(0.9),
            current_ltv_over_80=(m["current_ltv"] > 0.8).mean(),
            current_ltv_over_100=(m["current_ltv"] > 1.0).mean(),
            purchase_ltv_over_cap=(m["purchase_ltv"] > m["cap_ltv"] + 1e-6).mean(),
        )
    return out


def run() -> dict:
    """Score the recent book, write ``ml.stress_grid`` / ``ml.stress_replay`` and diagnostics."""
    t0 = time.perf_counter()
    with db.connect() as conn:
        (snapshot,) = conn.execute(
            "select data_snapshot_date from silver.int_data_snapshot"
        ).fetchone()
    start, end = window(snapshot)
    fitted_at = datetime.now().astimezone()
    sales = load_sales(start, end)
    index = load_index()
    rules = load_rules()
    log.info("population: %d clean residential sales %s to %s", sales.height, start, end)

    sales = cap_ltv(sales, rules)
    no_cap = sales.filter(pl.col("cap_ltv").is_null()).height
    if no_cap:
        log.warning("%d sales match no CBUAE cap rule (reference scenario skips them)", no_cap)
    sales = mark_to_market(sales, index)
    no_index = sales.filter(pl.col("mtm_ratio").is_null())
    log.info(
        "mark-to-market: %d by zone x type, %d by type, %d dropped (no published series can"
        " mark them)",
        sales.filter(pl.col("index_basis") == "zone").height,
        sales.filter(pl.col("index_basis") == "type").height,
        no_index.height,
    )
    sales = sales.filter(pl.col("mtm_ratio").is_not_null())
    replay = replay_drawdowns(index)
    sales = attach_replay(sales, replay)
    loans = summarise_loans(sales)
    log.info(
        "actual loans: %d of %d ready purchases matched (%.1f%%)",
        loans["matched_loans"],
        loans["ready_purchases"],
        100 * (loans["match_rate"] or 0),
    )

    if sales.is_empty():
        grid = pl.DataFrame(schema=dict.fromkeys(GRID_COLUMNS, pl.Utf8))
    else:
        cells = stress_cells(loan_book(sales))
        grid = (
            roll_up(cells)
            .with_columns(
                model_version=pl.lit(config.STRESS_MODEL_VERSION),
                fitted_at=pl.lit(fitted_at.isoformat()),
                snapshot_date=pl.lit(snapshot),
                window_start=pl.lit(start),
                window_end=pl.lit(end),
                purchases=pl.col("purchases").cast(pl.Int64),
                negative_equity_count=pl.col("negative_equity_count").cast(pl.Int64),
                loan_aed=pl.col("loan_aed").round(2),
                current_value_aed=pl.col("current_value_aed").round(2),
                negative_equity_aed=pl.col("negative_equity_aed").round(2),
                negative_equity_share=pl.col("negative_equity_share").round(6),
                applied_shock=pl.col("applied_shock").round(6),
                index_zone_share=pl.col("index_zone_share").round(6),
            )
            .select(GRID_COLUMNS)
        )
    replay_out = replay.with_columns(
        model_version=pl.lit(config.STRESS_MODEL_VERSION), fitted_at=pl.lit(fitted_at.isoformat())
    ).select(REPLAY_COLUMNS)
    with db.connect() as conn:
        n_grid = write_table(conn, GRID_DDL, GRID_TABLE, config.STRESS_MODEL_VERSION, grid)
        n_replay = write_table(
            conn, REPLAY_DDL, REPLAY_TABLE, config.STRESS_MODEL_VERSION, replay_out
        )
        conn.commit()
    log.info(
        "%s.%s: %d rows, %s.%s: %d rows, in %.0fs",
        config.SCHEMA_ML,
        GRID_TABLE,
        n_grid,
        config.SCHEMA_ML,
        REPLAY_TABLE,
        n_replay,
        time.perf_counter() - t0,
    )
    as_of = index.filter((pl.col("segment_level") == "type") & ~pl.col("is_partial_period"))
    diagnostics = {
        "model_version": config.STRESS_MODEL_VERSION,
        "fitted_at": fitted_at,
        "snapshot": snapshot,
        "window": [start, end],
        "index_as_of": as_of["period_start"].max() if as_of.height else None,
        "population_rows": sales.height + no_index.height,
        "dropped_no_index": no_index.height,
        "no_cap_rule": no_cap,
        "scored_rows": sales.height,
        "by_basis": sales.group_by("index_basis").len().to_dicts(),
        "by_type_offplan": sales.group_by("property_type_key", "is_offplan").len().to_dicts(),
        "cap_mix": sales.group_by("is_offplan", "cap_ltv")
        .len()
        .sort("is_offplan", "cap_ltv")
        .to_dicts(),
        "mtm_ratio": {
            "median": sales["mtm_ratio"].median(),
            "p10": sales["mtm_ratio"].quantile(0.1),
            "below_1": (sales["mtm_ratio"] < 1).mean() if sales.height else None,
        },
        "loans": loans,
        "rows_written": {"grid": n_grid, "replay": n_replay},
        "seconds": time.perf_counter() - t0,
    }
    path = diagnostics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagnostics, default=str, indent=1))
    return diagnostics


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make score`` runs it through ``models.score``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
