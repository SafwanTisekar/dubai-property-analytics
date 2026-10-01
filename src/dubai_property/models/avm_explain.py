"""AVM explainability (docs/05 §1): SHAP importance, dependence data, worked examples.

**SHAP values** come from LightGBM's own TreeSHAP (``predict(..., pred_contrib=True)``):
the same exact algorithm as ``shap.TreeExplainer``, computed inside LightGBM, so native
categorical splits are handled without conversion. For each sale the contributions plus
the expected value add up to the model's output, the log ratio of the AVM's AED per sq m
to the as-of reference price (``features.build``). The reference itself is the starting
point of every worked example.

**Worked examples are chosen by a rule, not by hand** (owner, 2026-10-01), and the rule is
published with them (``SELECTION_RULE``):

* three accurate valuations (APE < 10%), one per profile below, each the test sale whose
  predicted value is closest to the median predicted value of the qualifying sales, so a
  *typical* unit of that profile, not a flattering one;
* one **large miss** (APE > 25%): of the test sales in the top-20 areas that the AVM
  missed by more than 25%, the one with the median APE (sorted by APE, then id), shown
  with the reasons the data gives for the miss. Showing only accurate cases would read as
  cherry-picking.
"""

from __future__ import annotations

from collections.abc import Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd
import polars as pl

from dubai_property import config

DUBAI_MARINA, JVC = 330, 441  # DLD areas "Marsa Dubai", "Al Barsha South Fourth"

PROFILES = [
    {
        "key": "marina_2bed_ready",
        "title": "2-bed ready apartment, Dubai Marina",
        "filter": (pl.col("area_key") == DUBAI_MARINA)
        & (pl.col("property_type_key") == config.RESIDENTIAL_APARTMENT_KEY)
        & (pl.col("bedrooms") == 2)
        & ~pl.col("is_offplan"),
    },
    {
        "key": "jvc_offplan_small",
        "title": "Off-plan studio or 1-bed, JVC",
        "filter": (pl.col("area_key") == JVC)
        & (pl.col("property_type_key") == config.RESIDENTIAL_APARTMENT_KEY)
        & pl.col("bedrooms").is_in([0, 1])
        & pl.col("is_offplan"),
    },
    {
        "key": "dubailand_villa",
        "title": "Villa in Dubailand's busiest villa area",
        "filter": None,  # resolved in pick_examples: the Dubailand area with most villa sales
    },
]

SELECTION_RULE = (
    "Test-period sales (2025 onwards) only. Accurate examples: among sales of the profile "
    "valued within 10% (APE < 10%), the sale whose AVM value is closest to the median AVM "
    "value of those sales (ties: lowest transaction id), so a typical unit of the profile. "
    "Profiles: a 2-bed ready apartment in Dubai Marina (DLD area Marsa Dubai); an off-plan "
    "studio or 1-bed in JVC (DLD area Al Barsha South Fourth); a villa in the Dubailand "
    "area with the most test-period villa sales. Large miss: among test sales in the 20 "
    "areas with most test sales that the AVM missed by more than 25%, the one with the "
    "median APE (ties: lowest transaction id)."
)


def shap_values(booster: lgb.Booster, X: pd.DataFrame) -> tuple[np.ndarray, float]:
    """TreeSHAP contributions per row and feature, and the expected value (bias)."""
    contrib = booster.predict(X, pred_contrib=True)
    return contrib[:, :-1], float(contrib[0, -1])


def importance(booster: lgb.Booster, shap: np.ndarray, features: Sequence[str]) -> pl.DataFrame:
    """Mean |SHAP| (log points) and split gain per feature, ranked by mean |SHAP|."""
    gain = dict(zip(booster.feature_name(), booster.feature_importance("gain"), strict=True))
    df = pl.DataFrame(
        {
            "feature": list(features),
            "mean_abs_shap": np.abs(shap).mean(axis=0),
            "gain": [float(gain[f]) for f in features],
        }
    ).sort("mean_abs_shap", descending=True)
    return df.with_columns(pl.int_range(1, df.height + 1).alias("rank"))


def _typical(candidates: pl.DataFrame) -> pl.DataFrame:
    """The sale with predicted value closest to the candidates' median (ties: lowest id)."""
    med = candidates["pred_value"].median()
    return (
        candidates.with_columns((pl.col("pred_value") - med).abs().alias("_dist"))
        .sort("_dist", "transaction_id")
        .head(1)
        .drop("_dist")
    )


def pick_examples(test: pl.DataFrame, top_areas: Sequence[int]) -> list[dict]:
    """Apply ``SELECTION_RULE`` to the scored test sales.

    Args:
        test: Test sales with ``pred_value`` (AVM AED) and ``ape``.
        top_areas: The 20 areas with most test sales.

    Returns:
        One dict per example: key, title, kind (``accurate`` / ``miss``) and the row.
    """
    out = []
    accurate = test.filter(pl.col("ape") < 0.10)
    villas = test.filter(
        (pl.col("property_type_key") != config.RESIDENTIAL_APARTMENT_KEY)
        & (pl.col("zone") == "Dubailand")
    )
    villa_area = (
        villas.group_by("area_key").len().sort(["len", "area_key"], descending=[True, False])
    )
    for profile in PROFILES:
        flt = profile["filter"]
        if flt is None:
            if villa_area.is_empty():
                continue
            flt = (pl.col("area_key") == villa_area["area_key"][0]) & (
                pl.col("property_type_key") != config.RESIDENTIAL_APARTMENT_KEY
            )
        candidates = accurate.filter(flt)
        if candidates.is_empty():
            continue
        row = _typical(candidates).row(0, named=True)
        out.append(
            {"key": profile["key"], "title": profile["title"], "kind": "accurate", "row": row}
        )
    misses = test.filter((pl.col("ape") > 0.25) & pl.col("area_key").is_in(list(top_areas)))
    if not misses.is_empty():
        ordered = misses.sort("ape", "transaction_id")
        row = ordered.row(ordered.height // 2, named=True)
        out.append(
            {
                "key": "large_miss",
                "title": f"Large miss: {row['area_name']}",
                "kind": "miss",
                "row": row,
            }
        )
    return out


def contributions(
    booster: lgb.Booster, X_row: pd.DataFrame, features: Sequence[str], top: int = 8
) -> dict:
    """One sale's SHAP breakdown: bias, the ``top`` largest contributions, the rest."""
    shap, bias = shap_values(booster, X_row)
    vals = shap[0]
    order = np.argsort(-np.abs(vals))
    items = [
        {"feature": features[i], "value": _plain(X_row.iloc[0, i]), "shap": float(vals[i])}
        for i in order[:top]
    ]
    return {"bias": bias, "top": items, "other": float(vals[order[top:]].sum())}


def _plain(v: object) -> object:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, np.generic):
        return v.item()
    return v if isinstance(v, int | float | bool) else str(v)


def miss_reasons(row: dict, contrib: dict) -> list[str]:
    """Plain-language reasons the data gives for a large miss (no speculation beyond it)."""
    reasons = []
    gap = row["gap_pct"]
    side = "above" if gap > 0 else "below"
    reasons.append(
        f"The sale closed {abs(gap):.0%} {side} the AVM value: the AVM read this unit as "
        f"a typical {row['bedrooms']}-bed in {row['area_name']}."
    )
    if row.get("cell_n_6m", 0) < config.AVM_COMPS_MIN_N:
        reasons.append(
            f"Thin comparables: {row.get('cell_n_6m', 0)} sales of the same type, bedrooms "
            "and off-plan status in this area in the previous 6 months."
        )
    if row.get("bldg_n_24m"):
        reasons.append(
            f"Its building had {row['bldg_n_24m']} sales in the previous 24 months; this "
            "price is far from that building's trailing median, so the difference is "
            "specific to the unit, not the building."
        )
    reasons.append(
        "What the register doesn't record: floor, view, layout, condition, furnishing, or "
        "the circumstances of the sale (a distressed or related-party sale, a bundled "
        "payment plan). Any of these can move one unit's price by 25% or more."
    )
    biggest = contrib["top"][0]
    reasons.append(
        f"Largest single model input: {biggest['feature']} = {biggest['value']} "
        f"({biggest['shap']:+.3f} log points)."
    )
    return reasons
