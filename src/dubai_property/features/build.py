"""AVM feature table: static characteristics + as-of market state + the baselines' inputs.

One row per clean residential market sale (docs/05 §1). Every market column obeys the
as-of rule in ``asof_market`` (only months before the sale's month); static columns are
the sale's own characteristics, known at the transaction.

**Relative target.** LightGBM predicts the log ratio of the sale's AED per sq m to an
as-of *reference* price (the best comparable median available before the sale), not the
level itself. Trees can't extrapolate: a model trained on 2011-2023 prices maps any 2025
input to a leaf seen in training, so levels above the training range get capped, and 2025
prices sit well above 2023's. As a ratio to the as-of market, the target and the market
features stay on the same scale in every year. Reference, in order of preference (each
needing ``AVM_COMPS_MIN_N`` sales):

1. index-adjusted comparables of the cell (area x type x bedrooms x off-plan), 12 months;
2. the cell's median, 12 months;
3. area x type median, 12 months;
4. zone x type median, 12 months;
5. property type median, 3 months (any count).

No static target encoding is used: projects and buildings enter as trailing medians,
which are leak-free by construction and also work for projects launched after 2023.
There is no time trend feature either (a tree can't extrapolate it).
"""

from __future__ import annotations

from datetime import date

import polars as pl

from dubai_property import config
from dubai_property.features import asof_index, asof_market
from dubai_property.features.asof_market import month_index
from dubai_property.models import hedonic_index as h

CELL = ["area_key", "property_type_key", "bedrooms", "is_offplan"]

# (keys, windows, prefix) of every trailing median / count.
TRAILING = [
    (CELL, (3, 6, 12), "cell"),
    (["area_key", "property_type_key"], (3, 12), "at"),
    (["zone", "property_type_key"], (12,), "zt"),
    (["project_key", "property_type_key"], (12,), "proj"),
    (["building_name"], (24,), "bldg"),
    (["property_type_key"], (3,), "tt"),
]

CATEGORICALS = [
    "area_key",
    "zone",
    "property_type_key",
    "property_sub_type",
    "is_offplan",
    "has_parking",
    "is_penthouse",
    "nearest_metro",
    "master_project",
    "idx_source",
    "ref_source",
]
NUMERICS = [
    "ln_area",
    "bedrooms",
    "month_of_year",
    "cell_rel_3m",
    "cell_n_3m",
    "cell_rel_6m",
    "cell_n_6m",
    "cell_rel_12m",
    "cell_n_12m",
    "at_rel_3m",
    "at_n_3m",
    "at_rel_12m",
    "at_n_12m",
    "zt_rel_12m",
    "zt_n_12m",
    "proj_rel_12m",
    "proj_n_12m",
    "bldg_rel_24m",
    "bldg_n_24m",
    "comps_idx_rel",
    "comps_idx_n",
    "idx_chg_3m",
    "idx_chg_12m",
    "fed_funds_prev",
]
FEATURES = CATEGORICALS + NUMERICS

# Output columns that are not model inputs: the baselines and the reference.
BASELINES = {
    "comps": "base_comps_ln",
    "comps_indexed": "base_comps_idx_ln",
    "hedonic_ols": "base_ols_ln",
}


def prepare(population: pl.DataFrame) -> pl.DataFrame:
    """Add the month index and the index segment ids (zone x type, type) to each sale."""
    type_name = pl.col("property_type_key").replace_strict(h.TYPE_NAMES, default=None)
    zone_ok = pl.col("zone").is_not_null() & (pl.col("zone") != "Unknown")
    return population.with_columns(
        month_index(),
        type_name.alias("seg_type"),
        pl.when(zone_ok)
        .then(
            pl.concat_str(
                [type_name, pl.col("zone").map_elements(h.slug, return_dtype=pl.Utf8)],
                separator="-",
            )
        )
        .alias("seg_zone"),
    )


def compute_vintages(population: pl.DataFrame, end: date) -> tuple[pl.DataFrame, dict[int, dict]]:
    """Index vintages from the month after ``HEDONIC_START`` to ``end`` (a first-of-month)."""
    vintages = asof_index.vintage_months(config.HEDONIC_START, end)
    return asof_index.build_vintages(population, vintages)


def _reference() -> tuple[pl.Expr, pl.Expr]:
    """The as-of reference log price and which source it came from (module docstring)."""
    k = config.AVM_COMPS_MIN_N
    options = [
        ("comps_indexed", pl.col("comps_idx_n") >= k, pl.col("comps_idx_med")),
        ("cell_12m", pl.col("cell_n_12m") >= k, pl.col("cell_med_12m")),
        ("area_12m", pl.col("at_n_12m") >= k, pl.col("at_med_12m")),
        ("zone_12m", pl.col("zt_n_12m") >= k, pl.col("zt_med_12m")),
        ("type_3m", pl.col("tt_n_3m") >= 1, pl.col("tt_med_3m")),
    ]
    ref, src = pl.lit(None, dtype=pl.Float64), pl.lit("none")
    for name, ok, value in reversed(options):
        ref = pl.when(ok.fill_null(False)).then(value).otherwise(ref)
        src = pl.when(ok.fill_null(False)).then(pl.lit(name)).otherwise(src)
    return ref.alias("ref_ln"), src.alias("ref_source")


def build_features(
    population: pl.DataFrame,
    rates: pl.DataFrame,
    vintages: pl.DataFrame,
    pricing: dict[int, dict],
) -> pl.DataFrame:
    """The AVM table: population + features + baseline log prices + reference.

    Args:
        population: Sales (``avm.POPULATION_SQL`` columns), any date range.
        rates: ``month``, ``fed_funds_rate`` (monthly).
        vintages: ``asof_index.build_vintages`` output for these sales.
        pricing: Type-level vintage fits (model c).

    Returns:
        One row per sale, with ``FEATURES``, the ``BASELINES`` columns (log AED per sq m,
        null where the baseline can't value the sale), ``ref_ln`` / ``ref_source`` and
        ``target_rel`` (= ln_ppsqm - ref_ln, the LightGBM target).
    """
    sales = prepare(population)
    out = sales
    for keys, windows, prefix in TRAILING:
        valid = sales
        if "project_key" in keys:
            valid = sales.filter(pl.col("project_key") >= 0)  # -1 = no project (C9)
        stats = asof_market.trailing_stats(valid, keys, windows, prefix)
        out = out.join(stats, on=[*keys, "mi"], how="left", nulls_equal=False)
    counts = [c for c in out.columns if "_n_" in c and c.endswith("m")]
    out = out.with_columns(pl.col(counts).fill_null(0))

    comps = asof_market.indexed_comps(sales, vintages, CELL, config.AVM_COMPS_INDEXED_MONTHS)
    out = out.join(comps, on=[*CELL, "mi"], how="left").with_columns(
        pl.col("comps_idx_n").fill_null(0)
    )
    out = out.join(asof_market.index_features(sales, vintages), on="transaction_id", how="left")
    out = out.join(asof_market.rolling_ols_prices(sales, pricing), on="transaction_id", how="left")

    prev_rate = rates.select(
        (month_index() + 1).alias("mi"), pl.col("fed_funds_rate").alias("fed_funds_prev")
    )
    out = out.join(prev_rate, on="mi", how="left")

    ref, ref_source = _reference()
    out = out.with_columns(ref, ref_source)
    rel = {
        f"{p}_rel_{w}m": pl.col(f"{p}_med_{w}m") - pl.col("ref_ln")
        for keys, windows, p in TRAILING
        for w in windows
    }
    k = config.AVM_COMPS_MIN_N
    return out.with_columns(
        **rel,
        comps_idx_rel=pl.col("comps_idx_med") - pl.col("ref_ln"),
        month_of_year=pl.col("month").dt.month().cast(pl.Int32),
        base_comps_ln=pl.when(pl.col(f"cell_n_{config.AVM_COMPS_MONTHS}m") >= k).then(
            pl.col(f"cell_med_{config.AVM_COMPS_MONTHS}m")
        ),
        base_comps_idx_ln=pl.when(pl.col("comps_idx_n") >= k).then(pl.col("comps_idx_med")),
        base_ols_ln=pl.col("ols_ln_ppsqm"),
        target_rel=pl.col("ln_ppsqm") - pl.col("ref_ln"),
    )


def compute_all(population: pl.DataFrame, rates: pl.DataFrame, end: date) -> pl.DataFrame:
    """Vintages + features in one call (the pipeline and the no-look-ahead test)."""
    vintages, pricing = compute_vintages(population, end)
    return build_features(population, rates, vintages, pricing)
