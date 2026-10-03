"""AVM accuracy (docs/05 §1): MdAPE, hit rates, MAPE, R², coverage, by segment and month.

All metrics are on the **sale price in AED** (AED per sq m x area), the number a lender
compares with a valuation:

* **APE** = |predicted - actual| / actual. **MdAPE** (median APE) is the headline: an AVM
  is judged on its typical error, and a few wild sales (unobserved views, distressed
  sellers) shouldn't dominate it. **MAPE** (mean) is shown too, for the tail.
* **Hit rate ±10% / ±20%**: share of sales valued within 10% / 20%, the industry measure.
* **R² on ln(price)**: variance explained on the log scale.
* **Coverage**: scored sales / all sales in the segment. A model that only values easy
  cases looks better than it is, so every comparison also runs on the **common subset**
  that every model can value.

**Price bands are by predicted value** (decision, 2026-10-01). Banding by the actual price
builds in regression to the mean: a sale that closed unusually low lands in a low band
*because* it was low, so cheap bands look over-valued and dear ones under-valued even for
a perfect model. Predicted value is known before the sale, so its bands are fair. The
actual-price banding is published alongside (``price_band_actual``), labelled.

Segments with fewer than ``MIN_N`` scored sales get no row (min-n rule).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from dubai_property import config

BREAKDOWNS = (
    "overall",
    "reg_type",
    "property_type",
    "price_band",
    "price_band_actual",
    "area",
    "month",
)
# Also run on the subset every model scores (head to head).
COMMON_BREAKDOWNS = ("overall", "reg_type", "property_type")

PERF_SCHEMA = {
    "model": pl.Utf8,
    "split": pl.Utf8,
    "breakdown": pl.Utf8,
    "segment": pl.Utf8,
    "n_total": pl.Int64,
    "n_scored": pl.Int64,
    "coverage": pl.Float64,
    "mdape": pl.Float64,
    "hit10": pl.Float64,
    "hit20": pl.Float64,
    "mape": pl.Float64,
    "r2_log_price": pl.Float64,
}


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """MdAPE, ±10% / ±20% hit rates, MAPE and R² on ln(price) for scored sales."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    ape = np.abs(predicted - actual) / actual
    la, lp = np.log(actual), np.log(predicted)
    ss_tot = float(((la - la.mean()) ** 2).sum())
    return {
        "mdape": float(np.median(ape)),
        "hit10": float((ape <= 0.10).mean()),
        "hit20": float((ape <= 0.20).mean()),
        "mape": float(ape.mean()),
        "r2_log_price": 1 - float(((la - lp) ** 2).sum()) / ss_tot if ss_tot > 0 else None,
    }


def band_expr(col: str, bands: Sequence[float] = config.AVM_PRICE_BANDS) -> pl.Expr:
    """AED price band label, e.g. ``AED 1M-2M`` (``< AED 1M``, ``>= AED 5M`` at the ends)."""

    def m(x: float) -> str:
        return f"{x / 1e6:g}M"

    expr = (
        pl.when(pl.col(col).is_null())
        .then(pl.lit(None, dtype=pl.Utf8))
        .when(pl.col(col) < bands[0])
        .then(pl.lit(f"< AED {m(bands[0])}"))
    )
    for lo, hi in zip(bands, bands[1:], strict=False):
        expr = expr.when(pl.col(col) < hi).then(pl.lit(f"AED {m(lo)}-{m(hi)}"))
    return expr.otherwise(pl.lit(f">= AED {m(bands[-1])}"))


def _segment_col(breakdown: str, pred: str, top_areas: Sequence[int]) -> pl.Expr:
    if breakdown == "overall":
        return pl.lit("all")
    if breakdown == "reg_type":
        return pl.when(pl.col("is_offplan")).then(pl.lit("off-plan")).otherwise(pl.lit("ready"))
    if breakdown == "property_type":
        return (
            pl.when(pl.col("property_type_key") == config.RESIDENTIAL_APARTMENT_KEY)
            .then(pl.lit("apartment"))
            .otherwise(pl.lit("villa"))
        )
    if breakdown == "price_band":
        return band_expr(pred)
    if breakdown == "price_band_actual":
        return band_expr("price_aed")
    if breakdown == "area":
        return pl.when(pl.col("area_key").is_in(list(top_areas))).then(pl.col("area_name"))
    if breakdown == "month":
        return pl.col("month").dt.strftime("%Y-%m")
    raise ValueError(f"unknown breakdown {breakdown}")


def top_areas(scored: pl.DataFrame, n: int = config.AVM_TOP_AREAS) -> list[int]:
    """The ``n`` areas with the most test sales."""
    test = scored.filter(pl.col("split") == "test")
    return (
        test.group_by("area_key").len().sort("len", descending=True).head(n)["area_key"].to_list()
    )


def evaluate(
    scored: pl.DataFrame,
    models: Sequence[str],
    splits: Sequence[str] = ("validation", "test"),
    min_n: int = config.MIN_N,
) -> pl.DataFrame:
    """Metrics per model x split x breakdown x segment (``PERF_SCHEMA``).

    Args:
        scored: One row per sale with ``split``, ``price_aed``, ``month``, ``is_offplan``,
            ``property_type_key``, ``area_key``, ``area_name`` and a ``pred_<model>``
            column (predicted AED, null where the model can't value the sale).
        models: Model keys.
        splits: Splits to evaluate.
        min_n: Segments with fewer scored sales are left out.
    """
    areas = top_areas(scored)
    common = pl.all_horizontal([pl.col(f"pred_{m}").is_not_null() for m in models])
    rows = []
    for split in splits:
        part = scored.filter(pl.col("split") == split)
        if part.is_empty():
            continue
        for model in models:
            pred = f"pred_{model}"
            runs = [(b, b, part) for b in BREAKDOWNS]
            runs += [(f"{b}_common", b, part.filter(common)) for b in COMMON_BREAKDOWNS]
            for label, breakdown, frame in runs:
                seg = _segment_col(breakdown, pred, areas)
                # Null segment: not in this breakdown (an area outside the top 20, or a
                # predicted-value band of a sale the model can't value).
                frame = frame.with_columns(seg.alias("segment")).filter(
                    pl.col("segment").is_not_null()
                )
                totals = frame.group_by("segment").len()
                total = dict(zip(totals["segment"], totals["len"], strict=True))
                ok = frame.filter(pl.col(pred).is_not_null())
                for (segment,), g in ok.group_by("segment"):
                    if g.height < min_n:
                        continue
                    # Predicted-value bands have no "unscored" members: coverage is n/a.
                    n_total = None if breakdown == "price_band" else total.get(segment)
                    rows.append(
                        {
                            "model": model,
                            "split": split,
                            "breakdown": label,
                            "segment": segment,
                            "n_total": n_total,
                            "n_scored": g.height,
                            "coverage": g.height / n_total if n_total else None,
                            **metrics(g["price_aed"].to_numpy(), g[pred].to_numpy()),
                        }
                    )
    out = pl.DataFrame(rows, schema=PERF_SCHEMA)
    return out.sort("model", "split", "breakdown", "segment")


def leakage_alarm(
    perf: pl.DataFrame,
    mdape_floor: float = config.LEAKAGE_MDAPE_FLOOR,
    hit10_ceiling: float = config.LEAKAGE_HIT10_CEILING,
    min_scored: int = config.LEAKAGE_MIN_SCORED,
) -> list[str]:
    """Reasons to stop (docs/01 §7): any model too good on the test set to be believable.

    Real AVMs rarely beat ~5-8% MdAPE; below ~3%, or more than ~90% within ±10%, the
    usual cause is a feature that saw the answer. Only applies with ``min_scored`` scored
    test sales (the CI fixtures have a handful).
    """
    overall = perf.filter(
        (pl.col("split") == "test")
        & (pl.col("breakdown") == "overall")
        & (pl.col("n_scored") >= min_scored)
    )
    reasons = []
    for r in overall.iter_rows(named=True):
        if r["mdape"] < mdape_floor:
            reasons.append(f"{r['model']}: test MdAPE {r['mdape']:.2%} < {mdape_floor:.0%}")
        if r["hit10"] > hit10_ceiling:
            reasons.append(
                f"{r['model']}: test ±10% hit rate {r['hit10']:.1%} > {hit10_ceiling:.0%}"
            )
    return reasons
