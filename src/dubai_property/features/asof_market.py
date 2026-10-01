"""As-of market features: what was known about the market before a sale's month.

**The as-of rule (docs/05 §1, CLAUDE.md "no look-ahead").** Every feature of a sale dated
in month M is computed from sales dated in months **before M**: M-1, M-2, ... Sales earlier
in the same month are left out too, which is stricter than "dated before the sale" and
removes any question about same-day ordering or registration order within a month.

Months are handled as integers (``mi`` = year x 12 + month - 1) so a trailing window is
plain arithmetic. A k-month trailing statistic is built by copying each sale forward to
the k months that may use it (target = mi + 1 .. mi + k) and aggregating per target month,
so a sale can only ever feed months after its own. ``tests/test_avm_features.py`` proves it
by perturbing every sale dated M or later and checking that month M's features don't move.

Everything here is pure Polars on the population frame (no database), so the test runs in
CI without data.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from dubai_property.features.asof_index import PricingFit
from dubai_property.models import hedonic_index as h


def month_index(col: str = "month") -> pl.Expr:
    """``year x 12 + month - 1``: consecutive integers for consecutive months."""
    return (pl.col(col).dt.year().cast(pl.Int32) * 12 + pl.col(col).dt.month() - 1).alias("mi")


def trailing_stats(
    sales: pl.DataFrame,
    keys: Sequence[str],
    windows: Sequence[int],
    prefix: str,
    value: str = "ln_ppsqm",
) -> pl.DataFrame:
    """Median of ``value`` and count per key over the previous k months, for each k.

    Args:
        sales: Rows with ``mi``, the keys and ``value``. Rows with a null key are ignored.
        keys: Grouping columns (e.g. area x type x bedrooms x off-plan).
        windows: Trailing window lengths in months, e.g. (3, 6, 12).
        prefix: Output column prefix: ``<prefix>_med_<k>m`` and ``<prefix>_n_<k>m``.
        value: Column to take the median of.

    Returns:
        One row per (keys, mi) that has at least one sale in its longest window; join on
        ``[*keys, "mi"]``. Months with no earlier sale simply have no row.
    """
    k = max(windows)
    lagged = (
        sales.select([*keys, "mi", value])
        .drop_nulls(list(keys))
        .with_columns(lag=pl.int_ranges(1, k + 1, dtype=pl.Int32))
        .explode("lag", empty_as_null=True)
        .with_columns(target=pl.col("mi") + pl.col("lag"))
    )
    aggs = []
    for w in windows:
        within = pl.col("lag") <= w
        aggs += [
            pl.col(value).filter(within).median().alias(f"{prefix}_med_{w}m"),
            within.sum().cast(pl.Int32).alias(f"{prefix}_n_{w}m"),
        ]
    return (
        lagged.group_by([*keys, "target"])
        .agg(aggs)
        .rename({"target": "mi"})
        .with_columns(pl.col("mi").cast(pl.Int32))
    )


def anchor_index(vintages: pl.DataFrame) -> pl.DataFrame:
    """Per (segment, vintage): the latest chained period and the index changes to it.

    Columns: segment_id, vmi (vintage month index), anchor_mi, anchor_log, chg_3m,
    chg_12m (log changes over 3 and 12 months to the anchor; null if a point is missing).
    """
    v = vintages.with_columns(
        month_index("vintage").alias("vmi"), month_index("period").alias("pmi")
    )
    anchor = v.group_by("segment_id", "vmi").agg(
        pl.col("pmi").max().alias("anchor_mi"),
        pl.col("log_index").sort_by("pmi").last().alias("anchor_log"),
    )
    out = anchor
    for lag in (3, 12):
        back = v.select(
            "segment_id",
            "vmi",
            (pl.col("pmi") + lag).alias("anchor_mi"),
            pl.col("log_index").alias(f"log_{lag}"),
        )
        out = out.join(back, on=["segment_id", "vmi", "anchor_mi"], how="left").with_columns(
            (pl.col("anchor_log") - pl.col(f"log_{lag}")).alias(f"chg_{lag}m")
        )
    return out.drop("log_3", "log_12")


def index_features(sales: pl.DataFrame, vintages: pl.DataFrame) -> pl.DataFrame:
    """Index change to the sale's month, from the vintage of that month.

    The zone x type series is used where its vintage has a 12-month change, else the type
    series. Returns ``transaction_id``, ``idx_chg_3m``, ``idx_chg_12m``, ``idx_source``.
    """
    a = anchor_index(vintages).select("segment_id", "vmi", "chg_3m", "chg_12m")
    out = sales.select("transaction_id", "mi", "seg_zone", "seg_type")
    for level in ("zone", "type"):
        out = out.join(
            a.rename({"segment_id": f"seg_{level}", "vmi": "mi"}).rename(
                {"chg_3m": f"{level}_chg_3m", "chg_12m": f"{level}_chg_12m"}
            ),
            on=[f"seg_{level}", "mi"],
            how="left",
        )
    use_zone = pl.col("zone_chg_12m").is_not_null()
    use_type = pl.col("type_chg_12m").is_not_null()
    return out.select(
        "transaction_id",
        pl.when(use_zone)
        .then(pl.col("zone_chg_3m"))
        .when(use_type)
        .then(pl.col("type_chg_3m"))
        .alias("idx_chg_3m"),
        pl.when(use_zone)
        .then(pl.col("zone_chg_12m"))
        .otherwise(pl.col("type_chg_12m"))
        .alias("idx_chg_12m"),
        pl.when(use_zone)
        .then(pl.lit("zone"))
        .when(use_type)
        .then(pl.lit("type"))
        .otherwise(pl.lit("none"))
        .alias("idx_source"),
    )


def indexed_comps(
    sales: pl.DataFrame,
    vintages: pl.DataFrame,
    cell: Sequence[str],
    months: int,
) -> pl.DataFrame:
    """Index-adjusted comparables (baseline b): each comp's price moved to the valuation date.

    For a target month V, every sale of the same cell in the previous ``months`` months
    is adjusted by the index change from its own month to the anchor of vintage V:
    ``ln_ppsqm_j + L_V(anchor) - L_V(month_j)``, with the zone x type vintage where it has
    both points, else the type vintage. Result per (cell, mi): ``comps_idx_med`` (median of
    the adjusted log prices) and ``comps_idx_n`` (comps that could be adjusted).
    """
    v = vintages.select(
        "segment_id",
        month_index("vintage").alias("target"),
        month_index("period").alias("comp_mi"),
        "log_index",
    )
    anchors = anchor_index(vintages).select(
        "segment_id", pl.col("vmi").alias("target"), "anchor_log"
    )
    lagged = (
        sales.select([*cell, "mi", "ln_ppsqm", "seg_zone", "seg_type"])
        .drop_nulls(list(cell))
        .with_columns(lag=pl.int_ranges(1, months + 1, dtype=pl.Int32))
        .explode("lag", empty_as_null=True)
        .with_columns(target=pl.col("mi") + pl.col("lag"), comp_mi=pl.col("mi"))
    )
    for level in ("zone", "type"):
        seg = f"seg_{level}"
        lagged = lagged.join(
            v.rename({"segment_id": seg, "log_index": f"comp_log_{level}"}),
            on=[seg, "target", "comp_mi"],
            how="left",
        ).join(
            anchors.rename({"segment_id": seg, "anchor_log": f"anchor_{level}"}),
            on=[seg, "target"],
            how="left",
        )
    adj = [pl.col(f"anchor_{lv}") - pl.col(f"comp_log_{lv}") for lv in ("zone", "type")]
    lagged = lagged.with_columns((pl.col("ln_ppsqm") + pl.coalesce(adj)).alias("adj_ln"))
    return (
        lagged.group_by([*cell, "target"])
        .agg(
            pl.col("adj_ln").median().alias("comps_idx_med"),
            pl.col("adj_ln").is_not_null().sum().cast(pl.Int32).alias("comps_idx_n"),
        )
        .rename({"target": "mi"})
        .with_columns(pl.col("mi").cast(pl.Int32))
    )


def rolling_ols_prices(sales: pl.DataFrame, pricing: dict[int, dict]) -> pl.DataFrame:
    """Model (c): each sale priced by its type's vintage fit (window ``[V-36, V-1]``).

    Returns ``transaction_id`` and ``ols_ln_ppsqm`` (null where the fit can't price the
    sale: no vintage yet, or an area / bedroom level the window never saw).
    """
    parts = []
    for (type_key, vm), group in sales.group_by("property_type_key", "month"):
        fits = pricing.get(type_key, {})
        pf: PricingFit | None = fits.get(vm)
        if pf is None:
            pred = np.full(group.height, np.nan)
        else:
            pred = h.predict_log(pf.fit, group, pf.period, pf.categoricals, pf.numerics)
        parts.append(
            pl.DataFrame({"transaction_id": group["transaction_id"], "ols_ln_ppsqm": pred})
        )
    if not parts:
        return pl.DataFrame(schema={"transaction_id": pl.Utf8, "ols_ln_ppsqm": pl.Float64})
    return pl.concat(parts).with_columns(pl.col("ols_ln_ppsqm").fill_nan(None))
