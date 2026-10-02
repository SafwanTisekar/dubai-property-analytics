"""AVM model card, figures and the website's worked examples (``make model-reports``).

Reads what ``make train`` wrote: ``ml.avm_performance``, ``ml.feature_importance``,
``artifacts/avm/diagnostics.json`` and ``artifacts/avm/shap_sample.parquet``. Writes
``reports/avm_model_card.md``, ``reports/avm_examples.json`` and ``reports/figures/avm_*``
(all under a scratch folder when ``PG_DB`` isn't the main database). Every number in the
card comes from those tables, so re-running after ``make train`` keeps them in sync.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import connectorx as cx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402

from dubai_property import config, db  # noqa: E402
from dubai_property.analysis import plotting as P  # noqa: E402
from dubai_property.models import avm, avm_explain  # noqa: E402
from dubai_property.models.avm_explain import label  # noqa: E402
from dubai_property.models.report_4a import pct, table, to_date  # noqa: E402

log = logging.getLogger(__name__)

CARD = "avm_model_card.md"
EXAMPLES = "avm_examples.json"

NAME = {
    "lightgbm": "LightGBM",
    "comps_indexed": "Index-adjusted comparables",
    "comps": "Comparable sales (6 months)",
    "hedonic_ols": "Hedonic OLS (rolling)",
}
# Colour follows the model, never its rank (one fixed slot each).
COLOR = {
    "lightgbm": P.NAVY,
    "comps_indexed": P.MAGENTA,
    "comps": P.TEAL,
    "hedonic_ols": P.MUTED,
}
ORDER = ["lightgbm", "comps_indexed", "comps", "hedonic_ols"]


# --- Data -----------------------------------------------------------------------------
def load_perf() -> pl.DataFrame:
    """``ml.avm_performance`` for the current model version."""
    sql = (
        f"select * from {config.SCHEMA_ML}.avm_performance where model_version = "
        f"'{config.AVM_MODEL_VERSION}'"
    )
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    num = ["coverage", "mdape", "hit10", "hit20", "mape", "r2_log_price"]
    return df.with_columns(pl.col(num).cast(pl.Float64))


def load_score_summary() -> pl.DataFrame:
    """Review flags and gaps by split (aggregated in SQL)."""
    sql = f"""
        select model_set, count(*) as n,
               count(*) filter (where is_review) as review,
               count(*) filter (where is_review and gap_pct > 0) as review_above,
               percentile_cont(0.5) within group (order by gap_pct) as median_gap
        from {config.SCHEMA_ML}.avm_score where model_version = '{config.AVM_MODEL_VERSION}'
        group by 1"""
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    return df.with_columns(pl.col("median_gap").cast(pl.Float64))


def load_gaps() -> np.ndarray:
    """Test-period gaps, binned in SQL (1% bins from -100% to +100%)."""
    sql = f"""
        select least(greatest(floor(gap_pct * 100), -100), 100)::int as bin, count(*) as n
        from {config.SCHEMA_ML}.avm_score
        where model_version = '{config.AVM_MODEL_VERSION}' and model_set = 'test'
        group by 1 order by 1"""
    return cx.read_sql(db.connectorx_uri(), sql, return_type="polars")


# The committed 4b result before the 2026-10-01 restore re-tuned the model from scratch
# (docs/05 §8). A dated record, not a model output: the card compares today's numbers with it.
REPRODUCIBILITY_PREVIOUS = {"date": "2026-10-01", "mdape": 0.0682, "hit10": 0.652}


def pick(perf: pl.DataFrame, split: str, breakdown: str, model: str, segment: str = "all"):
    """One row of the performance table as a dict (or None)."""
    r = perf.filter(
        (pl.col("split") == split)
        & (pl.col("breakdown") == breakdown)
        & (pl.col("model") == model)
        & (pl.col("segment") == segment)
    )
    return r.row(0, named=True) if r.height else None


# --- Figures --------------------------------------------------------------------------
def fig_by_month(perf: pl.DataFrame, snapshot: date) -> Path:
    """Test MdAPE by month, one line per model."""
    fig, ax = P.figure(size=(10, 5.2))
    m = perf.filter((pl.col("split") == "test") & (pl.col("breakdown") == "month"))
    for model in ORDER:
        d = m.filter(pl.col("model") == model).sort("segment")
        if d.is_empty():
            continue
        x = [date.fromisoformat(s + "-01") for s in d["segment"]]
        ls = "--" if model == "hedonic_ols" else "-"
        ax.plot(x, d["mdape"], color=COLOR[model], ls=ls, label=NAME[model])
        P.direct_label(ax, x[-1], d["mdape"][-1], NAME[model])
    P.pct_axis(ax)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Median absolute % error (MdAPE)")
    ax.grid(False, axis="x")
    fig.subplots_adjust(right=0.80)  # lines are labelled at their ends: no legend
    P.titled(
        fig,
        "AVM error by month, out-of-time test period",
        "Lower is better. Every model values each sale with data from before its month only.",
    )
    P.add_source(fig, snapshot, note=f"{snapshot:%b %Y} is partial.", partial=False)
    return P.save(fig, "avm_accuracy_by_month")


def fig_segments(perf: pl.DataFrame, snapshot: date) -> Path:
    """Test MdAPE by segment, models side by side (horizontal bars, one axis)."""
    rows = [
        ("reg_type", "ready", "Ready"),
        ("reg_type", "off-plan", "Off-plan"),
        ("property_type", "apartment", "Apartments"),
        ("property_type", "villa", "Villas / townhouses"),
    ]
    bands = (
        perf.filter((pl.col("split") == "test") & (pl.col("breakdown") == "price_band"))
        .select("segment")
        .unique()["segment"]
        .to_list()
    )

    def band_key(b: str) -> float:
        digits = "".join(c if c.isdigit() or c == "." else " " for c in b).split()
        return (
            float(digits[0])
            + (0.5 if b.startswith(">=") else 0)
            - (0.5 if b.startswith("<") else 0)
        )

    rows += [("price_band", b, f"Value {b}") for b in sorted(bands, key=band_key)]
    fig, ax = P.figure(size=(10, 6.4))
    h = 0.8 / len(ORDER)
    y = np.arange(len(rows))
    for k, model in enumerate(ORDER):
        vals = []
        for breakdown, seg, _ in rows:
            r = pick(perf, "test", breakdown, model, seg)
            vals.append(r["mdape"] if r else np.nan)
        ax.barh(y + (k - 1.5) * h, vals, height=h * 0.9, color=COLOR[model], label=NAME[model])
    ax.set_yticks(y, [r[2] for r in rows])
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(MultipleLocator(0.02))  # whole-percent ticks
    P.pct_axis(ax, axis="x")
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    ax.set_xlabel("Median absolute % error (MdAPE), test 2025+")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False)
    fig.subplots_adjust(left=0.2, bottom=0.2)
    P.titled(
        fig,
        "AVM error by segment",
        "Each model on the sales it can value. Price bands by predicted value (see the model card).",
    )
    P.add_source(fig, snapshot, partial=False)
    return P.save(fig, "avm_accuracy_by_segment")


def fig_importance(imp: pl.DataFrame, snapshot: date, top: int = 15) -> Path:
    """Mean |SHAP| of the top features (one series, so no legend)."""
    d = imp.sort("rank").head(top)
    fig, ax = P.figure(size=(10, 5.8))
    y = np.arange(d.height)
    ax.barh(y, d["mean_abs_shap"], color=P.NAVY, height=0.7)
    ax.set_yticks(y, [label(f) for f in d["feature"]])
    ax.invert_yaxis()
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    ax.set_xlabel("Mean |SHAP|, log points of the predicted price (0.05 ≈ 5%)")
    for yi, v in zip(y, d["mean_abs_shap"], strict=True):
        ax.annotate(f"{v:.3f}", (v, yi), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=8, color=P.TEXT_2)  # fmt: skip
    P.titled(
        fig,
        "What drives the AVM",
        f"Top {top} features by mean absolute SHAP value, on a sample of test-period sales.",
    )
    fig.subplots_adjust(left=0.3)  # room for the feature names
    P.add_source(fig, snapshot, partial=False)
    return P.save(fig, "avm_shap_importance")


def fig_dependence(sample: pl.DataFrame, snapshot: date) -> Path:
    """SHAP dependence: size, bedrooms, area (top 12) and off-plan, one panel each."""
    fig, axes = P.figure(2, 2, size=(11, 8.2))
    (a1, a2), (a3, a4) = axes
    apt = sample.filter(pl.col("property_type_key") == config.RESIDENTIAL_APARTMENT_KEY)
    vil = sample.filter(pl.col("property_type_key") != config.RESIDENTIAL_APARTMENT_KEY)
    for d, key, name in ((apt, "apartment", "Apartments"), (vil, "villa", "Villas")):
        a1.scatter(d["area_sqm"], d["shap_ln_area"], s=4, alpha=0.25, color=P.SERIES[key],
                   label=name, linewidths=0)  # fmt: skip
    a1.set_xscale("log")
    a1.set_xlabel("Size, sq m (log scale)")
    a1.set_ylabel("SHAP, log points")
    a1.set_title("Size: larger units cost less per sq m")
    a1.legend(loc="upper right", markerscale=4)

    beds = (
        sample.filter(pl.col("bedrooms") >= 0)
        .group_by("property_type_key", "bedrooms")
        .agg(pl.col("shap_bedrooms").mean(), pl.len())
        .filter(pl.col("len") >= config.MIN_N)
        .sort("bedrooms")
    )
    for type_key, key, name in ((101, "apartment", "Apartments"), (102, "villa", "Villas")):
        d = beds.filter(pl.col("property_type_key") == type_key)
        a2.plot(d["bedrooms"], d["shap_bedrooms"], marker="o", color=P.SERIES[key], label=name)
    a2.axhline(0, color=P.GRID, lw=1)
    a2.set_xlabel("Bedrooms (0 = studio)")
    a2.set_title("Bedrooms, on top of size (mean SHAP)")
    a2.legend(loc="upper left")

    areas = (
        sample.group_by("area_name")
        .agg(pl.col("shap_area_key").mean(), pl.len())
        .sort("len", descending=True)
        .head(12)
        .sort("shap_area_key")
    )
    y = np.arange(areas.height)
    a3.barh(y, areas["shap_area_key"], color=P.NAVY, height=0.7)
    a3.set_yticks(y, areas["area_name"].to_list(), fontsize=8)
    a3.axvline(0, color=P.MUTED, lw=1)
    a3.grid(True, axis="x")
    a3.grid(False, axis="y")
    a3.set_xlabel("Mean SHAP of the area feature, log points")
    a3.set_title("Area: 12 busiest areas in the sample")

    off = (
        sample.group_by("property_type_key", "is_offplan")
        .agg(pl.col("shap_is_offplan").mean(), pl.len())
        .sort("property_type_key", "is_offplan")
    )
    labels, vals, cols = [], [], []
    for r in off.iter_rows(named=True):
        t = "Apartment" if r["property_type_key"] == 101 else "Villa"
        labels.append(f"{t}, {'off-plan' if r['is_offplan'] else 'ready'}")
        vals.append(r["shap_is_offplan"])
        cols.append(P.SERIES["offplan" if r["is_offplan"] else "ready"])
    a4.bar(labels, vals, color=cols, width=0.6)
    a4.axhline(0, color=P.MUTED, lw=1)
    a4.set_title("Off-plan vs ready (mean SHAP)")
    a4.tick_params(axis="x", labelsize=8)
    P.titled(
        fig,
        "How the AVM uses size, bedrooms, location and off-plan status",
        "SHAP values: the feature's push on the log price relative to the as-of reference price.",
    )
    fig.subplots_adjust(hspace=0.45, wspace=0.35, bottom=0.1, left=0.14)
    P.add_source(fig, snapshot, partial=False)
    return P.save(fig, "avm_shap_dependence")


def fig_example(ex: dict, snapshot: date) -> Path:
    """Waterfall for one worked example: reference price -> SHAP pushes -> AVM value."""
    shap = ex["shap"]
    ref_value = ex["reference_ppsqm_aed"] * ex["area_sqm"]
    steps = [("Bias (average adjustment)", shap["bias"])]

    def value_text(c: dict) -> str:
        # The DLD area enters as a key; the example carries its name.
        if c["feature"] == "area_key":
            return ex["area"]
        return avm_explain.describe(c["feature"], c["value"])

    steps += [(f"{label(c['feature'])}: {value_text(c)}", c["shap"]) for c in shap["top"]]
    steps += [("Other features", shap["other"]), ("Median calibration", ex["calibration"])]
    fig, ax = P.figure(size=(10, 6.0))
    level = np.log(ref_value)
    y = 0
    ax.barh(y, ref_value, color=P.MUTED, height=0.6)
    names = [f"Reference: {ex['reference_source'].replace('_', ' ')}"]
    for name, delta in steps:
        y += 1
        start, end = np.exp(level), np.exp(level + delta)
        ax.barh(y, end - start, left=start, height=0.6,
                color=P.NAVY if delta >= 0 else P.MAGENTA)  # fmt: skip
        names.append(name)
        level += delta
    y += 1
    ax.barh(y, np.exp(level), color=P.NAVY, height=0.6)
    names.append("AVM value")
    ax.axvline(ex["price_aed"], color=P.TEXT, lw=1.2, ls="--")
    ax.annotate(f"Sale price {P.fmt_aed(ex['price_aed'], decimals=2)}", (ex["price_aed"], y + 0.6),
                fontsize=8.5, color=P.TEXT, ha="center")  # fmt: skip
    ax.set_yticks(range(len(names)), names, fontsize=8.5)
    ax.invert_yaxis()
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    P.aed_axis(ax, axis="x", decimals=2)
    lo = min(ref_value, ex["price_aed"], np.exp(level)) * 0.8
    hi = max(ax.get_xlim()[1], ex["price_aed"]) * 1.06  # room for the sale-price label
    ax.set_xlim(lo, hi)
    ax.set_xlabel("AED (x-axis starts above zero: the bars show the steps)")
    flag = "  Large miss." if ex["kind"] == "miss" else ""
    P.titled(
        fig,
        f"{ex['title']}: valued at {P.fmt_aed(ex['avm_value_aed'], decimals=2)}",
        f"{ex['bedrooms']}-bed, {ex['area_sqm']:.0f} sq m, sold {ex['date']} for "
        f"{P.fmt_aed(ex['price_aed'], decimals=2)} (error {ex['ape']:.1%}).{flag} Orange steps lower the "
        "value, blue raise it.",
    )
    fig.subplots_adjust(left=0.36)
    P.add_source(fig, snapshot, partial=False)
    return P.save(fig, f"avm_example_{ex['key']}")


def fig_gaps(gaps: pl.DataFrame, snapshot: date) -> Path:
    """Distribution of the test-period gap with the ±25% review thresholds."""
    fig, ax = P.figure(size=(10, 4.8))
    review = (gaps["bin"] < -25) | (gaps["bin"] >= 25)
    colors = [P.MAGENTA if r else P.NAVY for r in review]
    ax.bar(gaps["bin"], gaps["n"], width=0.9, color=colors)
    for x in (-25, 25):
        ax.axvline(x, color=P.TEXT, lw=1, ls="--")
    ax.set_xlim(-60, 60)
    ax.set_xlabel("Gap: (price - AVM value) / AVM value, %")
    P.count_axis(ax)
    ax.grid(False, axis="x")
    P.titled(
        fig,
        "How far test-period prices sit from the AVM",
        "Orange: beyond ±25%, flagged for collateral review as a statistical anomaly, "
        "not an accusation.",
    )
    P.add_source(fig, snapshot, partial=False)
    return P.save(fig, "avm_gap_distribution")


# --- Report ---------------------------------------------------------------------------
def rel(path: Path) -> str:
    """Path relative to the reports folder (markdown links)."""
    return path.relative_to(db.reports_dir()).as_posix()


def metric_row(r: dict | None, name: str) -> list[str]:
    """One table row: model, n, coverage, MdAPE, hit rates, MAPE, R²."""
    if r is None:
        return [name, "–", "–", "–", "–", "–", "–", "–"]
    return [
        name,
        f"{r['n_scored']:,}",
        pct(r["coverage"], 1, sign=False) if r["coverage"] is not None else "–",
        f"**{pct(r['mdape'], 1, sign=False)}**",
        pct(r["hit10"], 1, sign=False),
        pct(r["hit20"], 1, sign=False),
        pct(r["mape"], 1, sign=False),
        f"{r['r2_log_price']:.3f}" if r["r2_log_price"] is not None else "–",
    ]


HEADER = ["Model", "Sales valued", "Coverage", "MdAPE", "±10%", "±20%", "MAPE", "R² ln(price)"]
ALIGN = "lrrrrrrr"


def segment_table(perf: pl.DataFrame, breakdown: str, segments: Sequence[str]) -> str:
    """MdAPE and ±10% per segment, the four models side by side (test)."""
    head = ["Segment"] + [f"{NAME[m]} MdAPE / ±10%" for m in ORDER]
    rows = []
    for seg in segments:
        cells = [seg]
        for m in ORDER:
            r = pick(perf, "test", breakdown, m, seg)
            cells.append(
                f"{pct(r['mdape'], 1, sign=False)} / {pct(r['hit10'], 0, sign=False)}" if r else "–"
            )
        rows.append(cells)
    return table(head, rows, "l" + "r" * len(ORDER))


def comps_comparison(base: dict, idx: dict) -> str:
    """Summary point on index-adjusted vs plain comparables (test, each on its own coverage).

    The wording follows the numbers: "did not beat" only when the index-adjusted MdAPE is
    not lower. The reason given is the one the decomposition in docs/05 §8 supports.
    """
    b, i = pct(base["mdape"], 2, sign=False), pct(idx["mdape"], 2, sign=False)
    if idx["mdape"] < base["mdape"]:
        return (
            f"3. **Index-adjusting the comparables helps:** MdAPE {i} against {b} for six "
            "months of raw comparables."
        )
    return (
        f"3. **Index-adjusted comparables did not beat plain comparables** (MdAPE {i} vs {b}). "
        "The adjustment does its job: it removes the lag bias of a 12-month window (raw "
        "12-month comparables under-value by a median ~3%, adjusted ones by ~0.5%). The likely "
        "reason it still loses is that six months of raw comparables carry only ~2% of drift, "
        "small next to the ~10% unit-to-unit spread, while the extra six older months bring in "
        "sales less like today's that no index can align; and at the 2026 turn the zone-level "
        "real-time index misjudged how individual cells moved. It edged ahead in rising 2025 "
        "and fell behind in 2026 (figures from the 2026-10-01 decomposition in docs/05 §8)."
    )


def villa_comparison(perf: pl.DataFrame) -> str | None:
    """Summary point on villas: LightGBM vs comparables on the villas both can value (test)."""
    lg = pick(perf, "test", "property_type_common", "lightgbm", "villa")
    cp = pick(perf, "test", "property_type_common", "comps", "villa")
    own = pick(perf, "test", "property_type", "lightgbm", "villa")
    if not (lg and cp and own):
        return None
    head = (
        f"on the {lg['n_scored']:,} test villas both can value, MdAPE "
        f"{pct(lg['mdape'], 2, sign=False)} LightGBM vs {pct(cp['mdape'], 2, sign=False)} "
        f"comparables; ±20%: {pct(lg['hit20'], 1, sign=False)} vs {pct(cp['hit20'], 1, sign=False)}"
    )
    if lg["mdape"] < 0.97 * cp["mdape"]:
        return f"4. **Villas:** LightGBM also beats comparables {head}."
    # Within 0.05 pp is a tie; otherwise say which side is ahead (owner, 2026-10-01: the
    # re-tuned model's 8.66% vs 8.51% is comparables ahead, not a tie).
    if abs(lg["mdape"] - cp["mdape"]) <= 0.0005:
        verdict = "Villas are a tie on MdAPE"
    elif lg["mdape"] > cp["mdape"]:
        slightly = "slightly " if lg["mdape"] <= 1.03 * cp["mdape"] else ""
        verdict = f"On villas, comparables are {slightly}better than LightGBM on MdAPE"
    else:
        verdict = "On villas, LightGBM is slightly ahead of comparables on MdAPE"
    return (
        f"4. **{verdict}** ({head}). LightGBM's edge is in the tails, and its "
        f"{pct(own['mdape'], 1, sign=False)} on all villas includes "
        f"{own['n_scored'] - lg['n_scored']:,} villas with too few comparables to value. The "
        "likely reason: villa communities repeat a few layouts, so the cell median (area × "
        "bedrooms × off-plan) is already a close match, and villas are about one in eight "
        "training sales, so the shared model's splits are shaped mostly by apartments."
    )


def tuning_summary(trials: Sequence[dict]) -> dict | None:
    """Spread of the Optuna validation MdAPE across trials (None if tuning didn't run)."""
    done = [t for t in trials if t.get("value") is not None]
    if not done:
        return None
    best = min(done, key=lambda t: t["value"])
    return {
        "n": len(done),
        "min": best["value"],
        "max": max(t["value"] for t in done),
        "best_trial": best["number"] + 1,  # 1-based, as train.log counts them
    }


def tuning_sentence(ts: dict | None) -> str:
    """One sentence on how much tuning mattered (empty without a study)."""
    if ts is None:
        return ""
    return (
        f"**Tuning was flat:** across {ts['n']} Optuna trials the validation MdAPE stayed between "
        f"{pct(ts['min'], 1, sign=False)} and {pct(ts['max'], 1, sign=False)} (best: trial "
        f"{ts['best_trial']}). The flat results suggest the remaining error likely comes from what "
        "the register doesn't record (view, floor, finish), rather than from tuning; it is also "
        f"why {ts['n']} trials rather than 50 were enough (docs/05 §8)."
    )


def render(perf, imp, diag, summary, figs, examples, tuning=None) -> str:  # noqa: C901
    """The model card (markdown). ``tuning``: ``tuning_summary`` of the Optuna study."""
    snap = to_date(diag["snapshot"])
    champ = diag["champion"]
    t = {m: pick(perf, "test", "overall", m) for m in ORDER}
    c = {m: pick(perf, "test", "overall_common", m) for m in ORDER}
    v = {m: pick(perf, "validation", "overall_common", m) for m in ORDER}
    lg, base, idx = t["lightgbm"], t["comps"], t["comps_indexed"]
    lgc, basec, idxc = c["lightgbm"], c["comps"], c["comps_indexed"]
    abl = diag.get("ablation_2010", {})
    sm = {r["model_set"]: r for r in summary.to_dicts()}
    tst = sm.get("test", {})
    months = perf.filter(
        (pl.col("split") == "test")
        & (pl.col("breakdown") == "month")
        & (pl.col("model") == "lightgbm")
    ).sort("segment")
    worst = (
        months.sort("mdape", descending=True).head(1).row(0, named=True) if months.height else None
    )
    best = months.sort("mdape").head(1).row(0, named=True) if months.height else None
    sp = diag["split_rows"]
    lines = [
        "# AVM model card",
        "",
        "Phase 4b (docs/05 §1). Automated valuation model for Dubai residential sales: what a "
        "unit was worth on the day it sold, from what was known before that day.",
        "",
        f"- **Data:** clean residential market sales to the snapshot date, **{snap:%-d %b %Y}**. "
        f"Model `{config.AVM_MODEL_VERSION}`, fitted {str(diag['fitted_at'])[:16]}.",
        "- **Tables:** `ml.avm_score`, `ml.avm_performance`, `ml.feature_importance`; Power BI "
        "views `rpt.avm_score`, `rpt.avm_performance`, `rpt.feature_importance`.",
        "- **Regenerate:** `make train score model-reports`. Code: `src/dubai_property/features/`, "
        "`models/avm.py`, `avm_eval.py`, `avm_explain.py`; this card: `models/report_avm.py`.",
        "- **Intended use:** collateral screening for a bank's mortgage book and market "
        "analytics. Not a RICS valuation, not lending advice; the review flag marks statistical "
        "anomalies, not wrongdoing.",
        "",
        "## Summary",
        "",
    ]
    if lg and base and idx and lgc and basec:
        lines += [
            f"1. **LightGBM values {pct(lg['hit10'], 0, sign=False)} of 2025–26 sales within ±10% "
            f"(MdAPE {pct(lg['mdape'], 1, sign=False)})**, against "
            f"{pct(base['hit10'], 0, sign=False)} (MdAPE {pct(base['mdape'], 1, sign=False)}) for "
            f"the comparable-sales baseline and {pct(idx['hit10'], 0, sign=False)} "
            f"({pct(idx['mdape'], 1, sign=False)}) for index-adjusted comparables. Out of time: "
            "trained to 2023, tuned on 2024, never shown 2025+. "
            f"([chart]({rel(figs['segments'])}))",
            f"2. **Head to head** on the {lgc['n_scored']:,} test sales every model can value: "
            f"MdAPE {pct(lgc['mdape'], 1, sign=False)} LightGBM vs {pct(basec['mdape'], 1, sign=False)} "
            f"comparables vs {pct(idxc['mdape'], 1, sign=False)} index-adjusted. Coverage: LightGBM "
            f"{pct(lg['coverage'], 1, sign=False)}, comparables {pct(base['coverage'], 1, sign=False)}.",
            comps_comparison(base, idx),
        ]
    villa = villa_comparison(perf)
    if villa:
        lines.append(villa)
    if worst and best:
        lines.append(
            f"5. **Accuracy by month** ranges from {pct(best['mdape'], 1, sign=False)} "
            f"({best['segment']}) to {pct(worst['mdape'], 1, sign=False)} ({worst['segment']}); "
            "see the table below for the 2026 slowdown months. "
            f"([chart]({rel(figs['month'])}))"
        )
    if imp.height:
        top3 = ", ".join(label(f) for f in imp.sort("rank").head(3)["feature"])
        lines.append(
            f"6. **What drives it:** {top3}. The model mostly asks *where in the market this "
            f"unit's project and building trade* relative to the comparables. ([chart]({rel(figs['importance'])}))"
        )
    if tst:
        lines.append(
            f"7. **Review flags:** {tst['review']:,} of {tst['n']:,} test-period sales "
            f"({tst['review'] / tst['n']:.1%}) sit more than 25% from the AVM "
            f"({tst['review_above']:,} above, {tst['review'] - tst['review_above']:,} below). "
            "Statistical anomalies for a collateral review, not accusations. "
            f"([chart]({rel(figs['gaps'])}))"
        )
    lines += [
        "8. **No sign of leakage:** test MdAPE and hit rates are within the range of "
        "production AVMs, far from the alarm thresholds (MdAPE < "
        f"{config.LEAKAGE_MDAPE_FLOOR:.0%} or ±10% > {config.LEAKAGE_HIT10_CEILING:.0%}), and a "
        "pytest proves no feature of a month-M sale changes when every sale from M on is rewritten.",
        "",
        "## Data and split",
        "",
        "**Population:** `is_clean_market_sale` (arm's-length market sales without a C3–C6 / "
        "C16 / C18 quality flag) apartments and villas / townhouses, within the class area cap; "
        "villas with a known bedroom count only (the index's basis: bedroom-less villa areas are "
        "plots, findings F3.1).",
        "",
    ]
    excl = diag.get("exclusions", [])
    if excl:
        rows = [
            [
                "Apartments" if e["property_type_key"] == 101 else "Villas / townhouses",
                f"{e['clean_sales']:,}",
                f"{e['above_class_cap']:,}",
                f"{e['villa_no_bedrooms']:,}",
            ]
            for e in excl
        ]
        lines += [
            table(
                [
                    "Type",
                    f"Clean sales since {config.AVM_HISTORY_START.year}",
                    "Above class cap (out)",
                    "Villas without bedrooms (out)",
                ],
                rows,
                "lrrr",
            ),  # fmt: skip
            "",
        ]
    lines += [
        table(
            ["Set", "Months", "Sales", "Use"],
            [
                [
                    "history",
                    "2010",
                    f"{sp.get('history', 0):,}",
                    "trailing features of early-2011 sales only",
                ],
                ["train", "2011-01 – 2023-12", f"{sp.get('train', 0):,}", "fit"],
                [
                    "validation",
                    "2024-01 – 2024-12",
                    f"{sp.get('validation', 0):,}",
                    "early stopping, Optuna, champion choice, median calibration",
                ],
                [
                    "test",
                    f"2025-01 – {snap:%Y-%m}",
                    f"{sp.get('test', 0):,}",
                    "every number in this card",
                ],
            ],
            "llrl",
        ),  # fmt: skip
        "",
        f"{diag['no_reference_rows']:,} sales without any earlier sale of their type (the first "
        "month of the history) have no reference price and are not modelled. The split is by "
        "date, never random: a random split would put a 2025 sale's neighbours, month and "
        "building in training. **The test period includes the 2026 slowdown** (Jan–Aug 2026 "
        "sales −19% on 2025, ready −37%; findings F1), which is why accuracy is also shown by "
        "month.",
        "",
        "**Why fitting starts in 2011** (owner, 2026-10-01): 30–50% of 2009–10 sales were "
        "registered after their application year (the Law 13/2008 backlog, findings F1.3), so "
        "their prices date from the 2006–08 boom. The index starts in 2011 for the same reason.",
    ]
    now = pick(perf, "test", "overall", "lightgbm")
    if now:
        prev = REPRODUCIBILITY_PREVIOUS
        lines += [
            "",
            f"**Reproducibility.** On {prev['date']} the model was re-tuned from scratch (a new "
            f"{config.AVM_OPTUNA_TRIALS}-trial Optuna study) when the database was restored "
            "(docs/05 §8): test MdAPE moved "
            f"{pct(prev['mdape'], 2, sign=False)} → {pct(now['mdape'], 2, sign=False)} and the ±10% "
            f"hit rate {pct(prev['hit10'], 1, sign=False)} → {pct(now['hit10'], 1, sign=False)}, so the "
            "result is stable across tuning runs. The tuned parameters are committed "
            "(`artifacts/avm/best_params.json`): a rebuild with the same features reuses them "
            "and reproduces this model, up to small differences from LightGBM's multithreading.",
        ]
    if abl:
        a, b = abl.get("2011_start"), abl.get("2010_start")
        if a and b:
            lines += [
                f" Ablation (train-only models, same parameters): starting in 2011 gives test MdAPE "
                f"{pct(a['mdape'], 2, sign=False)} (±10%: {pct(a['hit10'], 1, sign=False)}); starting in "
                f"2010, {pct(b['mdape'], 2, sign=False)} ({pct(b['hit10'], 1, sign=False)}).",
            ]
    lines += [
        "",
        "## Features and the no-look-ahead rule",
        "",
        "Every market feature of a sale dated in month M uses **only sales dated in months "
        "before M** (sales earlier in the same month are excluded too, which is stricter than "
        '"before the sale"). `tests/test_avm_features.py` proves it on a synthetic market: it '
        "reprices every sale dated M or later (including the ones being valued), drops later "
        "sales, adds new ones, rebuilds everything and requires month M's features and baseline "
        "values to be unchanged; a power check shows they do move when month M−1 changes.",
        "",
        table(
            ["Group", "Features"],
            [
                [
                    "Property",
                    "type, DLD sub-type, bedrooms (6+ pooled), ln(sq m), off-plan, parking, penthouse, month of year",
                ],
                [
                    "Location",
                    "DLD area, zone, nearest metro (or none), master project (native LightGBM categoricals)",
                ],
                [
                    "Comparable sales",
                    "median AED/sq m and count of the cell (area × type × bedrooms × off-plan) over 3 / 6 / 12 months; area × type 3 / 12; zone × type 12; index-adjusted cell comparables 12",
                ],
                [
                    "Project / building",
                    "trailing median AED/sq m and count: project × type 12 months, building 24 months",
                ],
                [
                    "Market state",
                    "real-time index change over 3 and 12 months (zone × type vintage, else type), Fed Funds rate of the previous month (EIBOR proxy)",
                ],
            ],
            "ll",
        ),  # fmt: skip
        "",
        "- **Real-time index, not the published one.** A published index point comes from a "
        "36-month window that also contains later sales (and the sale itself), and the last "
        "window is revised as months arrive. So for each month V the same rolling-window method "
        "is re-chained on the sales before V only (a *vintage*); a sale in month V reads vintage V "
        f"({diag['vintage_rows']:,} vintage points).",
        "- **Relative target.** LightGBM predicts ln(AED/sq m) minus an as-of *reference* price "
        "(index-adjusted cell comparables if ≥ 5, else cell, area, zone or type medians), and the "
        "medians enter relative to it. Trees can't extrapolate: trained on 2011–2023 levels, a "
        "level model would cap 2025 prices at what it had seen.",
        "- **No static target encoding**: projects and buildings enter as trailing medians, "
        "which can't see the future and work for projects launched after 2023. No time-trend "
        "feature (a tree can't extrapolate it). Not available: property age and developer (the "
        "DLD projects file isn't loaded) — limitations below.",
        "",
        "## Models",
        "",
        table(
            ["Model", "How it values a sale in month M"],
            [
                [
                    "Comparable sales (docs/05 §1 baseline)",
                    f"median AED/sq m of the cell over months M−6 … M−1 (≥ {config.AVM_COMPS_MIN_N} sales) × sq m",
                ],
                [
                    "Index-adjusted comparables",
                    "the cell's sales of M−12 … M−1, each × the real-time index change from its month to M−1; median (≥ 5)",
                ],
                [
                    "Hedonic OLS (rolling)",
                    "the index's time-dummy regression (area fixed effects, bedrooms, off-plan, parking, penthouse, ln sq m) re-fitted on M−36 … M−1, priced at the latest month's effect; median-calibrated",
                ],
                [
                    "LightGBM",
                    f"Huber loss, native categoricals, early stopping on 2024, Optuna TPE ({diag.get('n_trials', 0)} trials, validation MdAPE), re-fitted on 2011–2024 with the tuned {diag['best_iteration']} trees; median-calibrated on 2024 ({diag['calibration']:+.4f} log points)",
                ],
            ],
            "ll",
        ),  # fmt: skip
        "",
        *([tuning_sentence(tuning), ""] if tuning else []),
        f"**Champion: {NAME[champ]}**, chosen on the 2024 validation MdAPE (common subset), never on test:",
        "",
        table(HEADER, [metric_row(v[m], NAME[m]) for m in ORDER], ALIGN),
        "",
        "## Results on the test set (2025-01 to the snapshot)",
        "",
        "Each model on every sale it can value:",
        "",
        table(HEADER, [metric_row(t[m], NAME[m]) for m in ORDER], ALIGN),
        "",
        "Head to head, on the sales every model can value:",
        "",
        table(HEADER, [metric_row(c[m], NAME[m]) for m in ORDER], ALIGN),
        "",
        f"![Error by segment]({rel(figs['segments'])})",
        "",
        "### By segment (MdAPE / ±10% hit rate)",
        "",
        segment_table(perf, "reg_type", ["ready", "off-plan"]),
        "",
        segment_table(perf, "property_type", ["apartment", "villa"]),
        "",
    ]
    bands = perf.filter((pl.col("split") == "test") & (pl.col("breakdown") == "price_band"))[
        "segment"
    ].unique()
    order = ["< AED 1M", "AED 1M-2M", "AED 2M-5M", ">= AED 5M"]
    lines += [
        "**Price bands by predicted value** (owner, 2026-10-01). Banding by the sale price builds "
        "in regression to the mean: a sale that closed unusually low lands in a low band *because* "
        "it was low, so low bands look over-valued and high bands under-valued even for a perfect "
        "model. The AVM value is known before the sale, so its bands are fair. The sale-price "
        "version follows, labelled, for comparison only.",
        "",
        segment_table(perf, "price_band", [b for b in order if b in bands.to_list()]),
        "",
        "*By sale price (biased by regression to the mean; for comparison):*",
        "",
        segment_table(perf, "price_band_actual", order),
        "",
        "### Top 20 areas by test-period sales",
        "",
    ]
    areas = (
        perf.filter(
            (pl.col("split") == "test")
            & (pl.col("breakdown") == "area")
            & (pl.col("model") == "lightgbm")
        )
        .sort("n_total", descending=True)["segment"]
        .to_list()
    )
    lines += [segment_table(perf, "area", areas), "", "### By month", ""]
    month_rows = []
    for s in sorted(months["segment"].to_list()):
        cells = [s]
        for m in ORDER:
            r = pick(perf, "test", "month", m, s)
            cells.append(pct(r["mdape"], 1, sign=False) if r else "–")
        r = pick(perf, "test", "month", "lightgbm", s)
        cells.append(pct(r["hit10"], 0, sign=False) if r else "–")
        cells.append(f"{r['n_scored']:,}" if r else "–")
        month_rows.append(cells)
    lines += [
        table(
            ["Month"] + [f"{NAME[m]} MdAPE" for m in ORDER] + ["LightGBM ±10%", "Sales"],
            month_rows,
            "l" + "r" * (len(ORDER) + 2),
        ),  # fmt: skip
        "",
        f"![By month]({rel(figs['month'])})",
        "",
        "## Explainability (SHAP)",
        "",
        f"TreeSHAP from LightGBM (`pred_contrib`, the same algorithm as `shap.TreeExplainer`) on "
        f"{diag['shap_sample_rows']:,} seeded test sales. Values are log points of the predicted "
        "price relative to the reference price (0.05 ≈ +5%).",
        "",
        table(
            ["Rank", "Feature", "Group", "Mean abs. SHAP", "Split gain"],
            [
                [
                    r["rank"],
                    label(r["feature"]),
                    r["feature_group"],
                    f"{r['mean_abs_shap']:.4f}",
                    f"{r['gain']:,.0f}",
                ]
                for r in imp.sort("rank").head(15).iter_rows(named=True)
            ],
            "rllrr",
        ),  # fmt: skip
        "",
        f"![Importance]({rel(figs['importance'])})",
        "",
        f"![Dependence]({rel(figs['dependence'])})",
        "",
        "## Worked examples",
        "",
        f"**Selection rule** (published with the examples in `reports/{EXAMPLES}`): "
        f"{diag['selection_rule']}",
        "",
    ]
    for ex in examples:
        # A miss's title already says "Large miss: <area>" (avm_explain.pick_examples).
        heading = ex["title"] if ex["kind"] == "miss" else f"Example: {ex['title']}"
        lines += [
            f"### {heading}",
            "",
            f"{ex['bedrooms']}-bed {ex['property_type']}, {ex['area_sqm']:.0f} sq m, "
            f"{'off-plan' if ex['is_offplan'] else 'ready'}, {ex['area']} ({ex['zone']}), sold "
            f"{ex['date']} for **AED {ex['price_aed']:,}**. AVM value **AED {ex['avm_value_aed']:,}** "
            f"(error {ex['ape']:.1%}, gap {ex['gap_pct']:+.1%}). Reference: "
            f"{ex['reference_source'].replace('_', ' ')} at AED {ex['reference_ppsqm_aed']:,.0f}/sq m; "
            f"{ex['comps_6m_n']} comparable sales in the previous 6 months.",
            "",
        ]
        if ex.get("reasons"):
            lines += ["Why the model missed:", ""] + [f"- {r}" for r in ex["reasons"]] + [""]
        lines += [f"![{ex['key']}]({rel(figs['examples'][ex['key']])})", ""]
    review_rows = [
        [s, f"{sm[s]['n']:,}", f"{sm[s]['review']:,}" if sm[s]["review"] is not None else "–",
         pct(sm[s]["review"] / sm[s]["n"], 1, sign=False) if s != "train" else "not flagged",
         pct(sm[s]["median_gap"], 1)]
        for s in ("train", "validation", "test") if s in sm
    ]  # fmt: skip
    lines += [
        "## Review flags (|gap| > 25%)",
        "",
        "`gap = (price − AVM value) / AVM value`. A sale more than 25% above or below its AVM "
        "value is flagged **for collateral review as a statistical anomaly, not as an "
        "accusation**: the register doesn't record floor, view, condition, furnishing or the "
        "circumstances of a sale, any of which can explain a gap. **Flags are set only out of "
        "sample** (validation 2024 and test 2025+; owner, 2026-10-01): for 2011–2023 the model "
        "has fitted the sales, so their gaps understate how unusual the price was, and the flag "
        "is left blank.",
        "",
        table(["Set", "Sales valued", "Flagged", "Share", "Median gap"], review_rows, "lrrrr"),
        "",
        f"![Gaps]({rel(figs['gaps'])})",
        "",
        "## Limitations",
        "",
        "- **Unit quality is unobserved:** floor, view, layout, finish, condition and age aren't "
        "in the DLD register. Building and project medians absorb some of it; a penthouse flag is "
        "the only within-building signal.",
        "- **No property age or developer:** the DLD projects file (completion dates, developers) "
        "isn't loaded (docs/08 Phase 0).",
        "- **One month of lag:** a sale is valued with data to the end of the previous month, so "
        "in a fast market the AVM trails the last few weeks.",
        "- **Off-plan prices** include payment-plan terms the register doesn't show.",
        "- **Villas** are the bedroom-known subset; villa areas mix plot and built-up sizes "
        "(findings F3.1).",
        "- **Rates:** Fed Funds is a proxy for EIBOR (not loaded); its effect is an association.",
        "- **Training rows are in sample**; out-of-sample accuracy is the validation and test figures.",
        "",
        "Decisions: docs/05 §8.",
        "",
        "*Source: Dubai Land Department open data (transactions), CC BY 4.0.*",
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make model-reports``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    P.apply_style()
    art = avm.artifacts()
    diag_path = art / "diagnostics.json"
    if not diag_path.exists():
        raise SystemExit(f"{diag_path} missing: run make train first")
    diag = json.loads(diag_path.read_text())
    snap = to_date(diag["snapshot"])
    perf = load_perf()
    imp = pl.DataFrame(diag["importance"]) if diag.get("importance") else pl.DataFrame()
    sample = pl.read_parquet(art / "shap_sample.parquet")
    examples = diag.get("examples", [])
    # Reasons are re-derived from each example's stored numbers, so a wording fix in
    # avm_explain.miss_reasons reaches the card and the website without re-training.
    for ex in examples:
        if ex["kind"] == "miss":
            ex["reasons"] = avm_explain.miss_reasons(ex)
    figs = {
        "month": fig_by_month(perf, snap),
        "segments": fig_segments(perf, snap),
        "importance": fig_importance(imp, snap),
        "dependence": fig_dependence(sample, snap),
        "gaps": fig_gaps(load_gaps(), snap),
        "examples": {ex["key"]: fig_example(ex, snap) for ex in examples},
    }
    plt.close("all")
    out = db.reports_dir()
    (out / EXAMPLES).write_text(
        json.dumps(
            {
                "model_version": config.AVM_MODEL_VERSION,
                "data_as_of": diag["snapshot"],
                "selection_rule": diag["selection_rule"],
                "attribution": "Dubai Land Department, CC BY 4.0",
                "examples": examples,
            },
            default=str,
            indent=1,
        )
        + "\n"  # end-of-file-fixer (pre-commit) expects a final newline
    )
    card = out / CARD
    study_path = art / "best_params.json"
    trials = json.loads(study_path.read_text()).get("trials", []) if study_path.exists() else []
    card.write_text(
        render(perf, imp, diag, load_score_summary(), figs, examples, tuning_summary(trials))
    )
    log.info("wrote %s and %s", card.relative_to(config.PROJECT_ROOT), EXAMPLES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
