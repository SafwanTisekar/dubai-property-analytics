"""Phase 4c reports: ``reports/stress_test.md``, ``reports/forecast.md`` and their figures.

Every number comes from the model outputs (``ml.stress_grid``, ``ml.stress_replay``,
``ml.forecast``, ``ml.forecast_backtest``), the diagnostics the models wrote
(``artifacts/stress_test/diagnostics.json``, ``artifacts/forecast/diagnostics.json``) or
the LTV seed. Nothing is typed in by hand; wording that depends on a result (beats / loses
to the baseline, the sign of the rate effect) is chosen from the numbers.

Usage::

    uv run python -m dubai_property.models.report_4c      # make model-reports
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
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from dubai_property import config, db  # noqa: E402
from dubai_property.analysis import plotting as P  # noqa: E402
from dubai_property.models import forecast as fc  # noqa: E402
from dubai_property.models import stress_test as st  # noqa: E402
from dubai_property.models.report_4a import (  # noqa: E402
    date_axis,
    footer,
    month,
    num,
    pct,
    rel,
    table,
    to_date,
)

log = logging.getLogger(__name__)

STRESS_REPORT = "stress_test.md"
FORECAST_REPORT = "forecast.md"
TYPE_LABEL = {101: "Apartments", 102: "Villas / townhouses"}
TYPE_COLOR = {101: P.NAVY, 102: P.MAGENTA}
SEG_LABEL = {"dubai": "Dubai (all residential)", "apartment": "Apartments", "villa": "Villas"}
SEG_COLOR = {"dubai": P.TEAL, "apartment": P.NAVY, "villa": P.MAGENTA}
MODEL_LABEL = {
    "naive_rw": "Naive (last value)",
    "naive_seasonal": "Seasonal naive",
    "sarimax": "SARIMAX + lagged Fed Funds",
}
SCENARIO_LABEL = {
    "rates_flat": "Rates flat",
    "rates_up_100bp": "Rates +100bp",
    "rates_down_100bp": "Rates −100bp",
}
ILLUSTRATIVE = "Illustrative, not a regulatory stress test."
SHOCKS_SHOWN = (0, -10, -20, -30, -40, -50)


# --- Data -----------------------------------------------------------------------------
def read(sql: str) -> pl.DataFrame:
    """Small result set from Postgres."""
    return cx.read_sql(db.connectorx_uri(), sql, return_type="polars")


def load_json(path: Path) -> dict:
    """A diagnostics file written by make train / make score."""
    if not path.exists():
        raise SystemExit(f"{path} missing: run make train score first")
    return json.loads(path.read_text())


def load_grid() -> pl.DataFrame:
    """``ml.stress_grid`` (current model version), floats for the money and shares."""
    df = read(
        f"select * from {config.SCHEMA_ML}.{st.GRID_TABLE}"
        f" where model_version = '{config.STRESS_MODEL_VERSION}'"
    )
    floats = ["applied_shock", "loan_aed", "current_value_aed", "negative_equity_share",
              "negative_equity_aed", "index_zone_share"]  # fmt: skip
    return df.with_columns(pl.col(floats).cast(pl.Float64))


def load_replay() -> pl.DataFrame:
    """``ml.stress_replay``."""
    df = read(
        f"select * from {config.SCHEMA_ML}.{st.REPLAY_TABLE}"
        f" where model_version = '{config.STRESS_MODEL_VERSION}' order by segment_level, segment_id"
    )
    return df.with_columns(
        pl.col("peak_index", "trough_index", "drawdown").cast(pl.Float64),
        pl.col("first_period", "peak_period", "trough_period").cast(pl.Date),
    )


def load_rules() -> pl.DataFrame:
    """The seed rows behind the CBUAE cap reference (for the citations)."""
    return read(
        "select rule_id, borrower, property_status, home_number, value_band,"
        " max_ltv::float8 as max_ltv, effective_from, effective_to, source_citation, source_url"
        " from silver.seed_ltv_rules order by effective_from desc, rule_id"
    )


def load_forecast() -> tuple[pl.DataFrame, pl.DataFrame]:
    """``ml.forecast`` and ``ml.forecast_backtest``."""
    f = read(
        f"select * from {config.SCHEMA_ML}.{fc.FORECAST_TABLE}"
        f" where model_version = '{config.FORECAST_MODEL_VERSION}'"
    )
    vals = ["actual", "forecast", "lower_80", "upper_80", "lower_95", "upper_95", "rate_path"]
    f = f.with_columns(pl.col(vals).cast(pl.Float64), pl.col("month").cast(pl.Date))
    b = read(
        f"select * from {config.SCHEMA_ML}.{fc.BACKTEST_TABLE}"
        f" where model_version = '{config.FORECAST_MODEL_VERSION}'"
    )
    b = b.with_columns(pl.col("mape", "mdape", "coverage_80", "coverage_95").cast(pl.Float64))
    return f, b


def cell(grid: pl.DataFrame, **where) -> dict | None:
    """The one grid row matching ``where`` (None-valued keys match NULL)."""
    g = grid
    for k, v in where.items():
        g = g.filter(pl.col(k).is_null() if v is None else pl.col(k) == v)
    return g.row(0, named=True) if g.height == 1 else None


def share(grid, level="type", **where) -> float | None:
    """Negative-equity share of one row (None if absent or under min-n)."""
    row = cell(grid, segment_level=level, **where)
    return row["negative_equity_share"] if row else None


# --- Stress figures ---------------------------------------------------------------------
def margins(fig, left: float = 0.08, title_in: float = 1.05, footer_in: float = 0.6) -> None:
    """Margins in inches, so tall figures don't get a tall empty band under the title."""
    h = fig.get_figheight()
    fig.subplots_adjust(top=1 - title_in / h, bottom=footer_in / h, left=left)


def fig_stress_heatmap(grid: pl.DataFrame, snapshot: date) -> Path:
    """Share of ready buyers in negative equity, shock × assumed LTV, per type."""
    fig, axes = P.figure(1, 2, size=(11, 4.8))
    ltvs, shocks = list(config.STRESS_LTV_GRID), list(config.STRESS_SHOCKS)
    for ax, key in zip(axes, (101, 102), strict=True):
        m = np.full((len(ltvs), len(shocks)), np.nan)
        for i, ltv in enumerate(ltvs):
            for j, s in enumerate(shocks):
                v = share(grid, property_type_key=key, is_offplan=False, scenario="grid",
                          shock_pct=s, ltv_basis="grid", ltv_pct=ltv)  # fmt: skip
                m[i, j] = np.nan if v is None else v
        ax.imshow(m, cmap=P.SEQUENTIAL, vmin=0, vmax=1, aspect="auto")
        for i in range(len(ltvs)):
            for j in range(len(shocks)):
                if not np.isnan(m[i, j]):
                    ax.text(j, i, f"{100 * m[i, j]:.0f}", ha="center", va="center", fontsize=7.5,
                            color=P.TEXT if m[i, j] < 0.55 else P.SURFACE)  # fmt: skip
        ax.set_xticks(range(len(shocks)), [f"{s}%" for s in shocks], fontsize=8)
        ax.set_yticks(range(len(ltvs)), [f"{v}%" for v in ltvs])
        ax.set_xlabel("Price shock on today's value")
        ax.set_title(f"{TYPE_LABEL[key]}, ready", loc="left", fontsize=10)
        ax.grid(False)
    axes[0].set_ylabel("Assumed LTV at purchase")
    P.titled(
        fig,
        "Share of recent ready buyers in negative equity (%)",
        "Purchases of the last 36 months, marked to market with the hedonic index; loan held "
        "at origination. 85% = UAE national first-home cap (worst case).",
    )
    footer(fig, snapshot, ILLUSTRATIVE)
    return P.save(fig, "stress_heatmap")


def fig_stress_zones(grid: pl.DataFrame, snapshot: date, shock: int, ltv: int) -> Path:
    """Negative-equity share by zone × type (ready) at one shock and LTV, plus the replay."""
    z = grid.filter(
        (pl.col("segment_level") == "zone") & ~pl.col("is_offplan") & pl.col("is_published")
        & (pl.col("ltv_basis") == "grid") & (pl.col("ltv_pct") == ltv)
    )  # fmt: skip
    at = z.filter((pl.col("scenario") == "grid") & (pl.col("shock_pct") == shock)).select(
        "zone", "property_type_key", "purchases", s=pl.col("negative_equity_share")
    )
    dw = z.filter(pl.col("scenario") == config.STRESS_REPLAY_DUBAI_NAME).select(
        "zone", "property_type_key", w=pl.col("negative_equity_share")
    )
    rp = z.filter(pl.col("scenario") == config.STRESS_REPLAY_NAME).select(
        "zone", "property_type_key", r=pl.col("negative_equity_share"),
        d=pl.col("applied_shock"),
    )  # fmt: skip
    d = (
        at.join(rp, on=["zone", "property_type_key"], how="left")
        .join(dw, on=["zone", "property_type_key"], how="left")
        .sort("s")
    )
    fig, ax = P.figure(size=(10, max(4.5, 0.32 * d.height + 2)))
    margins(fig, left=0.40, title_in=1.75)
    y = np.arange(d.height)
    colors = [TYPE_COLOR[k] for k in d["property_type_key"]]
    ax.barh(y, d["s"].to_numpy(), color=colors, height=0.6)
    w_, r_ = d["w"].fill_null(np.nan).to_numpy(), d["r"].fill_null(np.nan).to_numpy()
    ax.hlines(y, w_, r_, color=P.TEXT_2, lw=1, zorder=2)
    ax.scatter(w_, y, marker="o", s=26, facecolor=P.SURFACE, edgecolor=P.TEXT, lw=1.2, zorder=3,
               label="2014-2020 replay, Dubai-wide (lower)")  # fmt: skip
    ax.scatter(r_, y, marker="D", s=26, color=P.TEXT, zorder=3,
               label="2014-2020 replay, own series (upper)")  # fmt: skip
    labels = [f"{zn} · {'apt' if k == 101 else 'villa'} (n={n:,})"
              for zn, k, n in d.select("zone", "property_type_key", "purchases").iter_rows()]  # fmt: skip
    ax.set_yticks(y, labels, fontsize=8)
    ax.set_xlim(0, 1)
    P.pct_axis(ax, "x")
    ax.grid(False, axis="y")
    from matplotlib.patches import Patch

    handles = [Patch(color=P.NAVY, label=f"Apartments, {shock}% shock"),
               Patch(color=P.MAGENTA, label=f"Villas, {shock}% shock"),
               *ax.get_legend_handles_labels()[0][:2]]  # fmt: skip
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False,
              fontsize=8)  # fmt: skip
    P.titled(
        fig,
        f"Negative equity by zone: ready buyers at {ltv}% LTV",
        f"Bars: a {abs(shock)}% fall from today's value. Line: a 2014-2020 replay, from the "
        "Dubai-wide fall (circle) to the zone's own drawdown\n(diamond; type series where the zone "
        "wasn't published in 2014), usually the upper end because noisy series overstate "
        "drawdowns. Zones with n ≥ 20.",
    )
    footer(fig, snapshot, ILLUSTRATIVE)
    return P.save(fig, "stress_by_zone")


def fig_replay(replay: pl.DataFrame, snapshot: date) -> Path:
    """The 2014 → 2020 drawdown of each series the replay uses."""
    r = replay.filter(pl.col("is_used") & pl.col("drawdown").is_not_null()).sort("drawdown",
                                                                                   descending=True)  # fmt: skip
    fig, ax = P.figure(size=(10, max(4, 0.32 * r.height + 2)))
    margins(fig, left=0.52)
    y = np.arange(r.height)
    colors = [P.MUTED if k is None else TYPE_COLOR[k] for k in r["property_type_key"]]
    ax.barh(y, r["drawdown"].to_numpy(), color=colors, height=0.6)
    labels = [
        f"{seg} ({month(p)} to {month(t)})"
        for seg, p, t in r.select("segment_id", "peak_period", "trough_period").iter_rows()
    ]
    ax.set_yticks(y, labels, fontsize=8)
    P.pct_axis(ax, "x")
    ax.grid(False, axis="y")
    P.titled(
        fig,
        "Historical replay: each series' fall from its peak, 2014–2021",
        "Grey = Dubai overall, blue = apartments, orange = villas. Zone series are noisier than "
        "type series, so their drawdowns are deeper.",
    )
    footer(fig, snapshot, "Index: hedonic, rolling-window (reports/price_index.md).")
    return P.save(fig, "stress_replay")


# --- Forecast figures ---------------------------------------------------------------------
def fig_fan(f: pl.DataFrame, target: str, snapshot: date, years_back: int = 5) -> Path:
    """History plus the 12-month forecast with 80% / 95% bands, one panel per segment."""
    segs = [s for s in fc.SEGMENTS if f.filter((pl.col("target") == target)
                                               & (pl.col("segment") == s)).height]  # fmt: skip
    fig, axes = P.figure(len(segs), 1, size=(10, 2.6 * len(segs) + 1.6), sharex=True, squeeze=False)
    margins(fig, title_in=1.15)
    fig.subplots_adjust(hspace=0.35)
    for ax, seg in zip(axes[:, 0], segs, strict=True):
        d = f.filter((pl.col("target") == target) & (pl.col("segment") == seg))
        hist = d.filter(~pl.col("is_forecast")).sort("month")
        last = hist["month"].max()
        hist = hist.filter(pl.col("month") >= date(last.year - years_back, last.month, 1))
        flat = d.filter(pl.col("scenario") == "rates_flat").sort("month")
        anchor = hist.tail(1)
        x = [anchor["month"][0], *flat["month"].to_list()]
        a = anchor["actual"][0]
        color = SEG_COLOR[seg]
        ax.fill_between(x, [a, *flat["lower_95"]], [a, *flat["upper_95"]], color=color,
                        alpha=0.15, lw=0, label="95% interval")  # fmt: skip
        ax.fill_between(x, [a, *flat["lower_80"]], [a, *flat["upper_80"]], color=color,
                        alpha=0.30, lw=0, label="80% interval")  # fmt: skip
        ax.plot(hist["month"], hist["actual"], color=P.TEXT, lw=1.6, label="Actual")
        ax.plot(x, [a, *flat["forecast"]], color=color, lw=2, label="Forecast, rates flat")
        for scen, style in (("rates_up_100bp", "--"), ("rates_down_100bp", ":")):
            s = d.filter(pl.col("scenario") == scen).sort("month")
            ax.plot(x, [a, *s["forecast"]], color=color, lw=1.2, ls=style,
                    label=SCENARIO_LABEL[scen])  # fmt: skip
        ax.set_title(SEG_LABEL[seg], loc="left", fontsize=10)
        if target == "volume":
            P.count_axis(ax)
        date_axis(ax, 1)
    axes[0, 0].legend(loc="upper left", frameon=False, fontsize=7.5, ncol=3)
    what = (
        "Hedonic price index (Jan 2019 = 100)"
        if target == "index"
        else "Clean residential market sales per month"
    )
    P.titled(
        fig,
        f"12-month outlook: {what.lower() if target == 'volume' else what}",
        "SARIMAX with Fed Funds lagged "
        f"{config.FORECAST_RATE_LAG} months (EIBOR proxy). Scenarios step rates by ±100bp from the\n"
        "first forecast month, so they only part after the lag. Bands: 80% and 95%, assuming the "
        "model is right.",
    )
    footer(fig, snapshot, "Forecast from the last complete month.")
    return P.save(fig, f"forecast_fan_{target}")


def fig_backtest(b: pl.DataFrame, snapshot: date) -> Path:
    """Backtest MAPE by horizon per model, one panel per target × segment."""
    keys = b.select("target", "segment").unique().sort("target", "segment").rows()
    fig, axes = P.figure(2, 3, size=(11, 7.2), squeeze=False)
    margins(fig)
    fig.subplots_adjust(hspace=0.55, wspace=0.25)
    styles = {"naive_rw": (P.MUTED, "--"), "naive_seasonal": (P.MUTED, ":"),
              "sarimax": (P.NAVY, "-")}  # fmt: skip
    for ax in axes.ravel():
        ax.set_visible(False)
    for target, seg in keys:
        ax = axes[0 if target == "index" else 1, fc.SEGMENTS.index(seg)]
        ax.set_visible(True)
        for model, (color, ls) in styles.items():
            d = b.filter((pl.col("target") == target) & (pl.col("segment") == seg)
                         & (pl.col("model") == model)).sort("horizon")  # fmt: skip
            ax.plot(d["horizon"], d["mape"], color=color, ls=ls, marker="o", ms=4, lw=1.8,
                    label=MODEL_LABEL[model])  # fmt: skip
        ax.set_xticks(config.FORECAST_HORIZONS)
        ax.set_title(f"{'Index' if target == 'index' else 'Volume'}: {SEG_LABEL[seg]}",
                     loc="left", fontsize=9.5)  # fmt: skip
        P.pct_axis(ax)
        ax.set_xlabel("Months ahead")
    first = next(a for a in axes.ravel() if a.get_visible())
    first.legend(frameon=False, fontsize=7.5)
    P.titled(
        fig,
        "Backtest: mean absolute % error by horizon",
        "Rolling origin over the last 24 complete months; index forecasts fitted on the real-time "
        "vintage of each origin.",
    )
    footer(fig, snapshot)
    return P.save(fig, "forecast_backtest")


# --- Stress report ------------------------------------------------------------------------
def stress_report(grid, replay, rules, diag, figs) -> str:
    """``reports/stress_test.md``."""
    snapshot = to_date(diag["snapshot"])
    w0, w1 = (to_date(x) for x in diag["window"])
    as_of = to_date(diag["index_as_of"]) if diag.get("index_as_of") else None
    loans = diag["loans"]

    def s(key, offplan, shock, ltv=80, basis="grid", scenario="grid"):
        return share(grid, property_type_key=key, is_offplan=offplan, scenario=scenario,
                     shock_pct=shock, ltv_basis=basis, ltv_pct=ltv if basis == "grid" else None)  # fmt: skip

    def rp(key, offplan, ltv=80, basis="grid", scenario=config.STRESS_REPLAY_NAME):
        row = cell(grid, segment_level="type", property_type_key=key, is_offplan=offplan,
                   scenario=scenario, shock_pct=None, ltv_basis=basis,
                   ltv_pct=ltv if basis == "grid" else None)  # fmt: skip
        return row

    def rpd(key, offplan, ltv=80, basis="grid"):
        return rp(key, offplan, ltv, basis, config.STRESS_REPLAY_DUBAI_NAME)

    def share_of(row):
        return (row or {}).get("negative_equity_share")

    apt_rp, villa_rp = rp(101, False), rp(102, False)
    apt_dw, villa_dw = rpd(101, False), rpd(102, False)
    dubai_dd = (apt_dw or villa_dw or {}).get("applied_shock")
    counts = {(r["property_type_key"], r["is_offplan"]): r["len"] for r in diag["by_type_offplan"]}
    total = diag["scored_rows"]
    zone_share = next((r["len"] for r in diag["by_basis"] if r["index_basis"] == "zone"), 0)
    lines = [
        "# Collateral stress test",
        "",
        f"Phase 4c (docs/05 §4). **{ILLUSTRATIVE}** It answers docs/01 Q7: if prices fell X%, "
        "what share of recent buyers would owe more than their home is worth, at typical "
        "loan-to-value ratios, and where? Every number below rests on stated assumptions "
        "(next section); none is a forecast of losses.",
        "",
        f"- **Data:** clean residential market sales, {month(w0)} to {month(w1)} (36 complete "
        f"months; {month(snapshot)} is partial and left out), marked to market with the hedonic "
        f"index as of **{month(as_of)}**. Model `{config.STRESS_MODEL_VERSION}`, run "
        f"{str(diag['fitted_at'])[:16]}.",
        "- **Tables:** `ml.stress_grid`, `ml.stress_replay`; Power BI views `rpt.stress_grid`, "
        "`rpt.stress_replay` (Shock % and LTV % are integer keys for the what-if slicers).",
        "- **Regenerate:** `make score model-reports`. Code: `src/dubai_property/models/stress_test.py`; "
        "this report: `models/report_4c.py`.",
        "",
        "## Summary",
        "",
        f"1. **Almost no recent buyer is under water today.** With the index as of "
        f"{month(as_of)}, a ready apartment bought in the window at 80% LTV is in negative equity "
        f"in {pct(s(101, False, 0), 1, False)} of cases, a ready villa in "
        f"{pct(s(102, False, 0), 1, False)}, and {pct(s(101, False, 0, basis='actual_loan'), 1, False)} "
        f"of matched apartment loans: prices are above most purchase prices (median "
        f"mark-to-market {num(diag['mtm_ratio']['median'], 3)}× the price paid).",
        f"2. **A 20% fall is the threshold that matters.** At 80% LTV, a 10% fall puts "
        f"{pct(s(101, False, -10), 1, False)} of ready apartment buyers under water, a 20% fall "
        f"{pct(s(101, False, -20), 0, False)} and a 30% fall {pct(s(101, False, -30), 0, False)} "
        f"(villas {pct(s(102, False, -10), 1, False)} / {pct(s(102, False, -20), 0, False)} / "
        f"{pct(s(102, False, -30), 0, False)}). Recent buyers have little equity cushion beyond "
        "their deposit, so negative equity jumps once the fall exceeds 1 − LTV. "
        f"([chart]({rel(figs['heatmap'])}))",
        f"3. **A repeat of 2014→2020 would leave {pct(share_of(apt_dw), 0, False)} to "
        f"{pct(share_of(apt_rp), 0, False)} of ready apartment buyers at 80% LTV in negative "
        f"equity** (villas {pct(share_of(villa_dw), 0, False)} to {pct(share_of(villa_rp), 0, False)}). "
        f"The lower figure applies the Dubai-wide fall ({pct(dubai_dd, 0)}) to everyone; the upper "
        "one each buyer's own zone × type series (average applied "
        f"{pct((apt_rp or {}).get('applied_shock'), 0)} for apartments, "
        f"{pct((villa_rp or {}).get('applied_shock'), 0)} for villas). Zone series are noisier, and "
        "a maximum drawdown measured on a noisy series overstates the true fall, so the "
        "own-series figure is the **upper end of the range** (exceptions noted in the replay section). "
        f"([chart]({rel(figs['zones'])}))",
        f"4. **Registered loans tell the same story.** {num(loans['matched_loans'], 0)} of "
        f"{num(loans['ready_purchases'], 0)} ready purchases ({pct(loans['match_rate'], 0, False)}, "
        f"a lower bound) are matched to their mortgage. Median LTV at purchase "
        f"{pct(loans.get('purchase_ltv_median'), 0, False)}, today {pct(loans.get('current_ltv_median'), 0, False)}; "
        f"a 20% fall would put {pct(s(101, False, -20, basis='actual_loan'), 0, False)} of "
        f"matched apartment loans and {pct(s(102, False, -20, basis='actual_loan'), 0, False)} of "
        "villa loans under water.",
        f"5. **Off-plan is a separate risk.** {num(counts.get((101, True), 0) + counts.get((102, True), 0), 0)} "
        f"of the {num(total, 0)} purchases are off-plan. At the 50% off-plan cap, a 20% fall leaves "
        f"{pct(s(101, True, -20, basis='cbuae_cap'), 1, False)} of off-plan apartment buyers under "
        f"water and a 50% fall {pct(s(101, True, -50, basis='cbuae_cap'), 0, False)}; and most "
        "buyers pay the developer in instalments, so the exposure is the developer's and the "
        "buyer's more than a bank's.",
        "",
        "## Assumptions",
        "",
        table(
            ["Item", "Assumption"],
            [
                [
                    "Population",
                    f"Clean residential market sales (apartments, villas / townhouses), {month(w0)}–{month(w1)}: {num(total, 0)} purchases"
                    + (
                        f"; {num(diag['dropped_no_index'], 0)} left out because no published index series covers them"
                        if diag["dropped_no_index"]
                        else ""
                    ),
                ],
                [
                    "Current value",
                    f"Price × index now / index at purchase. Series: the zone × type index where it is published and has a point for the purchase period ({pct(zone_share / total if total else None, 0, False)} of purchases), else the type index. *Now* = the series' latest complete period ({month(as_of)} monthly; quarterly zones: their last complete quarter)",
                ],
                [
                    "Loan",
                    "Held at the origination amount: **no amortisation**. Real balances are lower, so negative equity is overstated (conservative)",
                ],
                [
                    "Assumed LTV grid",
                    "50 / 60 / 70 / 80 / 85% of the price. **85% = UAE national first home cap (worst case)**: the most permissive CBUAE cap",
                ],
                [
                    "CBUAE cap reference",
                    "The cap in force on the sale date for an **expatriate's first home** (nationality and first/second home aren't in the register; the observed median loan/price since 2020 is 0.80, findings F2.4): ready 80% up to AED 5M, 70% above (75% / 65% before 2020-04-08); off-plan 50%",
                ],
                [
                    "Registered loan",
                    "Purchase mortgages matched to their sale on the same day and unit key (`int_purchase_mortgage_pairs`, Phase 3): ready sales only, a lower bound",
                ],
                [
                    "Shocks",
                    "0 to −50% in 5-point steps, applied to today's value. −40% / −50% stand in for a 2008-size crash (hypothetical: the index starts in 2011)",
                ],
                [
                    "Historical replay",
                    f"Two depths of the 2014→2020 episode, each a series' deepest fall from its running peak between {month(config.STRESS_REPLAY_START)} and {month(config.STRESS_REPLAY_END)}: **Dubai-wide** ({pct(dubai_dd, 1)} for every buyer, the lower range) and **own series** (the buyer's zone × type series if published from {month(config.STRESS_REPLAY_PEAK_BY)} or earlier, else the type series; the upper range, as noisy series overstate drawdowns)",
                ],
                [
                    "Negative equity",
                    "Loan > shocked value. AED = Σ (loan − value) over those buyers",
                ],
                [
                    "Min-n",
                    f"Segments with fewer than {config.MIN_N} purchases keep their count but no share or AED",
                ],
            ],
        ),
        "",
        "**LTV caps used (seed `seed_ltv_rules`, verified by the owner against the CBUAE rulebook):**",
        "",
    ]
    cap_rules = rules.filter(
        (pl.col("borrower").is_in([config.STRESS_CAP_BORROWER, "Any"])
         & pl.col("home_number").is_in([config.STRESS_CAP_HOME, "any"]))
        | ((pl.col("borrower") == "UAE national") & (pl.col("home_number") == "first")
           & (pl.col("value_band") == "up to AED 5M") & pl.col("effective_to").is_null())
    )  # fmt: skip
    lines += [
        table(
            ["Borrower", "Status", "Value band", "Max LTV", "In force", "Source"],
            [
                [
                    r["borrower"],
                    r["property_status"],
                    r["value_band"],
                    pct(r["max_ltv"], 0, False),
                    f"{r['effective_from']} → {r['effective_to'] or 'now'}",
                    f"[{r['source_citation'].split(',')[0]}]({r['source_url']})",
                ]
                for r in cap_rules.iter_rows(named=True)
            ],
            "lllrll",
        ),
        "",
        "## Results: ready buyers, assumed LTV",
        "",
        "Share of the window's ready buyers in negative equity, by assumed LTV and price shock "
        "(type level).",
        "",
    ]
    for key in (101, 102):
        n = counts.get((key, False), 0)
        lines += [
            f"**{TYPE_LABEL[key]}** ({num(n, 0)} ready purchases)",
            "",
            table(
                [
                    "LTV",
                    *[f"{x}%" for x in SHOCKS_SHOWN],
                    f"Replay, Dubai-wide ({pct(dubai_dd, 0)})",
                    "Replay, own series (upper)",
                ],  # fmt: skip
                [
                    [
                        f"{ltv}%" + (" (worst case)" if ltv in config.STRESS_LTV_LABELS else ""),
                        *[pct(s(key, False, x, ltv), 1, False) for x in SHOCKS_SHOWN],
                        pct(share_of(rpd(key, False, ltv)), 1, False),
                        pct((rp(key, False, ltv) or {}).get("negative_equity_share"), 1, False),
                    ]
                    for ltv in config.STRESS_LTV_GRID
                ]
                + [
                    [
                        "CBUAE cap",
                        *[pct(s(key, False, x, basis="cbuae_cap"), 1, False) for x in SHOCKS_SHOWN],
                        pct(share_of(rpd(key, False, basis="cbuae_cap")), 1, False),
                        pct(
                            (rp(key, False, basis="cbuae_cap") or {}).get("negative_equity_share"),
                            1,
                            False,
                        ),
                    ],
                    [
                        "Registered loan",
                        *[
                            pct(s(key, False, x, basis="actual_loan"), 1, False)
                            for x in SHOCKS_SHOWN
                        ],
                        pct(share_of(rpd(key, False, basis="actual_loan")), 1, False),
                        pct(
                            (rp(key, False, basis="actual_loan") or {}).get(
                                "negative_equity_share"
                            ),
                            1,
                            False,
                        ),
                    ],
                ],
            ),
            "",
        ]
    neg_aed = cell(grid, segment_level="dubai", is_offplan=False, scenario="grid", shock_pct=-20,
                   ltv_basis="grid", ltv_pct=80)  # fmt: skip
    if neg_aed:
        lines += [
            f"In AED: at a 20% fall and 80% LTV, ready buyers in negative equity would owe "
            f"**AED {num(neg_aed['negative_equity_aed'] / 1e9, 2)}bn** more than their homes' value, "
            f"against AED {num(neg_aed['loan_aed'] / 1e9, 1)}bn of assumed loans "
            f"({pct(neg_aed['negative_equity_aed'] / neg_aed['loan_aed'], 1, False)}). Because the "
            "loan is held at origination, this is an upper bound for the same assumptions.",
            "",
        ]
    lines += [
        f"![Heatmap]({rel(figs['heatmap'])})",
        "",
        "## Registered loans",
        "",
        f"- **Match rate:** {pct(loans['match_rate'], 1, False)} of ready purchases "
        f"({num(loans['matched_loans'], 0)} of {num(loans['ready_purchases'], 0)}). A **lower "
        "bound** on mortgaged purchases: a loan registered on another day or with a key field "
        "typed differently isn't matched, and the matched loans may not be representative.",
        f"- **LTV at purchase:** median {pct(loans.get('purchase_ltv_median'), 1, False)}; "
        f"{pct(loans.get('purchase_ltv_over_cap'), 0, False)} of matched loans are above the "
        "expatriate first-home cap used as the reference, consistent with UAE nationals' higher "
        "caps (85%) or financed fees. The register doesn't say which.",
        f"- **Estimated current LTV** (loan at origination / today's value): median "
        f"{pct(loans.get('current_ltv_median'), 1, False)}, 90th percentile "
        f"{pct(loans.get('current_ltv_p90'), 1, False)}; {pct(loans.get('current_ltv_over_80'), 1, False)} "
        f"above 80% and {pct(loans.get('current_ltv_over_100'), 2, False)} above 100%.",
        "",
        "## Historical replay: 2014 → 2020",
        "",
        "The one historical decline the index covers (it starts in 2011, so there is no 2008–11 "
        "replay; docs/05 §8). Each series' deepest fall from its running peak inside "
        f"{month(config.STRESS_REPLAY_START)}–{month(config.STRESS_REPLAY_END)}:",
        "",
        table(
            ["Series", "Peak", "Trough", "Drawdown", "Used"],
            [
                [
                    f"`{r['segment_id']}`",
                    month(r["peak_period"]),
                    month(r["trough_period"]),
                    pct(r["drawdown"], 1),
                    "yes" if r["is_used"] else f"no: {r['note']}",
                ]
                for r in replay.iter_rows(named=True)
            ],
            "lrrrl",
        ),
        "",
        "**Two replays bracket the episode.** The *Dubai-wide* replay applies the Dubai series' "
        f"fall ({pct(dubai_dd, 1)}) to every buyer: the lower end of the range. The *own-series* "
        "replay applies each buyer's zone × type drawdown (type where the zone isn't covered): "
        "the upper end. Zone series move more than the type and Dubai series (fewer sales per "
        "period, so more sampling noise, plus local cycles), and the maximum drawdown of a noisy "
        "series overstates the true fall, because noise adds a spurious high before the peak and "
        "a spurious low at the trough. A zone's deepest fall in the window can also start from a "
        "later peak than June 2014 (Downtown peaked in 2016). Read the own-series figures as an "
        "upper range, not a central estimate."
        + (
            " **Exception:** "
            + "; ".join(
                f"`{r['segment_id']}` fell {pct(r['drawdown'], 0)} ({month(r['peak_period'])} → "
                f"{month(r['trough_period'])}), less than Dubai"
                for r in replay.filter(
                    pl.col("is_used")
                    & (pl.col("segment_level") == "zone")
                    & (pl.col("drawdown") > (dubai_dd or -1))
                ).iter_rows(named=True)
            )
            + ": for those buyers the Dubai-wide replay is the harsher of the two."
            if replay.filter(
                pl.col("is_used")
                & (pl.col("segment_level") == "zone")
                & (pl.col("drawdown") > (dubai_dd or -1))
            ).height
            else ""
        ),
        "",
        f"![Replay]({rel(figs['replay'])})",
        "",
        "## Where: zones",
        "",
        f"![Zones]({rel(figs['zones'])})",
        "",
    ]
    z = grid.filter(
        (pl.col("segment_level") == "zone") & ~pl.col("is_offplan") & pl.col("is_published")
        & (pl.col("ltv_basis") == "grid") & (pl.col("ltv_pct") == 80)
    )  # fmt: skip
    rows = []
    for (zone, key), g in z.group_by(["zone", "property_type_key"]):

        def at(x, g=g):
            r = g.filter((pl.col("scenario") == "grid") & (pl.col("shock_pct") == x))
            return r["negative_equity_share"][0] if r.height else None

        rep = g.filter(pl.col("scenario") == config.STRESS_REPLAY_NAME)
        dw = g.filter(pl.col("scenario") == config.STRESS_REPLAY_DUBAI_NAME)
        rows.append([zone, "Apartments" if key == 101 else "Villas", g["purchases"][0], at(-10),
                     at(-20), at(-30),
                     dw["negative_equity_share"][0] if dw.height else None,
                     rep["applied_shock"][0] if rep.height else None,
                     rep["negative_equity_share"][0] if rep.height else None])  # fmt: skip
    rows.sort(key=lambda r: -(r[4] or 0))
    lines += [
        "Ready buyers at 80% LTV, zones with ≥ 20 purchases (sorted by the −20% share):",
        "",
        table(
            [
                "Zone",
                "Type",
                "Purchases",
                "−10%",
                "−20%",
                "−30%",
                f"Replay, Dubai-wide ({pct(dubai_dd, 0)})",
                "Own-series shock",
                "Replay, own series (upper)",
            ],  # fmt: skip
            [
                [
                    r[0],
                    r[1],
                    num(r[2], 0),
                    pct(r[3], 1, False),
                    pct(r[4], 1, False),
                    pct(r[5], 1, False),
                    pct(r[6], 1, False),
                    pct(r[7], 0),
                    pct(r[8], 1, False),
                ]
                for r in rows
            ],  # fmt: skip
            "llrrrrrrr",
        ),
        "",
        "Differences between zones at the same shock come from how far each zone's index has "
        "moved since its buyers bought: a zone whose prices rose after the purchases has a bigger "
        "cushion. Area-level rows (min-n applied) are in `rpt.stress_grid` for the Power BI map.",
        "",
        "## Off-plan",
        "",
    ]
    off = [
        [TYPE_LABEL[k], num(counts.get((k, True), 0), 0),
         pct(s(k, True, -20, 50), 1, False), pct(s(k, True, -30, 80), 1, False),
         pct(s(k, True, -20, basis="cbuae_cap"), 1, False), pct(s(k, True, -50, basis="cbuae_cap"), 1, False)]
        for k in (101, 102)
    ]  # fmt: skip
    lines += [
        "Off-plan purchases are reported apart from ready ones and never pooled with them. "
        "Banks cap off-plan lending at **50%**, and most off-plan buyers pay the developer in "
        "instalments over construction rather than borrowing the price up front, so an assumed "
        "LTV on the full price overstates what a bank has at risk. The index carries an off-plan "
        "control, so marking an off-plan purchase to market with it is like for like; whether an "
        "off-plan unit can be sold at that value before handover is a separate question.",
        "",
        table(
            [
                "Type",
                "Off-plan purchases",
                "−20% at 50% LTV",
                "−30% at 80% LTV (hypothetical)",
                "CBUAE cap (50%), −20%",
                "CBUAE cap (50%), −50%",
            ],
            off,
        ),
        "",
        "## Caveats",
        "",
        f"- **{ILLUSTRATIVE}** The LTVs are assumptions (except the matched loans), loans are "
        "held at origination, and there is no income, rate or default model: negative equity is "
        "not loss.",
        f"- **The latest index months are the least certain.** *Current value* uses the index as "
        f"of {month(as_of)}: the rolling-window index revises its most recent months as new sales "
        "arrive (most for villas, the noisiest series; reports/price_index.md, *Limitations*), so "
        "the 0-shock results, and every shock applied on top, can shift when new data arrives.",
        "- **Mark-to-market is like for like.** The hedonic index holds the unit's characteristics "
        "fixed; a unit that is better or worse than its segment's average moves the same %.",
        "- **Area cap and villas.** The index's villa series is built on bedroom-known villas; "
        "a bedroom-less (plot-sized) villa sale is marked to market with it too.",
        "- **Matched loans are a lower bound and may be selective** (same-day registrations of "
        "the two legs only).",
        "- **The replay is one episode** (2014→2020, slow: 6 years peak to trough), applied as an "
        "instant fall; a 2008-style crash is only covered hypothetically by the −40% / −50% steps.",
        "",
        "Decisions: docs/05 §8.",
        "",
        "*Source: Dubai Land Department open data (transactions, CC BY 4.0); LTV caps: CBUAE "
        "Regulations Regarding Mortgage Loans (cited above).*",
        "",
    ]
    return "\n".join(lines)


# --- Forecast report ----------------------------------------------------------------------
def forecast_report(f, b, diag, figs) -> str:
    """``reports/forecast.md``."""
    snapshot = to_date(diag["snapshot"])
    last = to_date(diag["last_actual"])
    o0, o1, n_origins = diag["origins"]
    series = diag["series"]

    def bt(target, seg, model, hz):
        r = b.filter((pl.col("target") == target) & (pl.col("segment") == seg)
                     & (pl.col("model") == model) & (pl.col("horizon") == hz))  # fmt: skip
        return r.row(0, named=True) if r.height else None

    def baseline(target, seg):
        r = b.filter(
            (pl.col("target") == target) & (pl.col("segment") == seg) & pl.col("is_baseline")
        )
        return r["model"][0] if r.height else None

    def endpoint(target, seg, scenario):
        d = f.filter((pl.col("target") == target) & (pl.col("segment") == seg))
        a = d.filter(~pl.col("is_forecast")).sort("month").tail(1)
        e = d.filter(pl.col("scenario") == scenario).sort("month").tail(1)
        if not a.height or not e.height:
            return None
        r = e.row(0, named=True)
        base = a["actual"][0]
        return {"last": base, "month": r["month"], "point": r["forecast"] / base - 1,
                "lo80": r["lower_80"] / base - 1, "hi80": r["upper_80"] / base - 1,
                "lo95": r["lower_95"] / base - 1, "hi95": r["upper_95"] / base - 1}  # fmt: skip

    def verdict(target, seg, hz):
        s, base = bt(target, seg, "sarimax", hz), baseline(target, seg)
        nb = bt(target, seg, base, hz) if base else None
        if not s or not nb:
            return "–"
        return "beats" if s["mape"] < nb["mape"] else "loses to"

    wins = [(t, s, hz) for t in fc.TARGETS for s in fc.SEGMENTS for hz in config.FORECAST_HORIZONS
            if verdict(t, s, hz) == "beats"]  # fmt: skip
    scored = [(t, s, hz) for t in fc.TARGETS for s in fc.SEGMENTS for hz in config.FORECAST_HORIZONS
              if verdict(t, s, hz) != "–"]  # fmt: skip
    idx = {s: endpoint("index", s, "rates_flat") for s in fc.SEGMENTS}
    rate_rows = {k: v["rate"] for k, v in series.items() if v.get("rate")}
    signs = [v["beta"] for v in rate_rows.values()]
    sig = [k for k, v in rate_rows.items() if v["p_value"] < 0.05]
    lines = [
        "# Market outlook: 12-month forecast",
        "",
        "Phase 4c (docs/05 §5). Where are prices and sales volumes heading over the next 12 months "
        "under different rate paths (docs/01 Q8)? A statistical extrapolation with honest "
        "uncertainty, **not investment advice**.",
        "",
        f"- **Data:** the hedonic index (`ml.fct_price_index`, Dubai / apartments / villas, monthly) "
        f"and clean residential market sales per month, to **{month(last)}** ({month(snapshot)} is "
        f"partial and dropped). Model `{config.FORECAST_MODEL_VERSION}`, run {str(diag['fitted_at'])[:16]}.",
        "- **Tables:** `ml.forecast` (history + 12 months per scenario, 80% / 95% intervals), "
        "`ml.forecast_backtest`; views `rpt.forecast`, `rpt.forecast_backtest`.",
        "- **Regenerate:** `make train` (forecast step) then `make score model-reports`. Code: "
        "`src/dubai_property/models/forecast.py`.",
        "",
        "## Summary",
        "",
    ]

    def yoy(seg):
        d = f.filter((pl.col("target") == "index") & (pl.col("segment") == seg)
                     & ~pl.col("is_forecast")).sort("month")  # fmt: skip
        return d["actual"][-1] / d["actual"][-13] - 1 if d.height > 12 else None

    def cover(target, col):
        d = b.filter((pl.col("model") == "sarimax") & (pl.col("target") == target))
        return d[col].mean() if d.height else None

    if all(idx.values()):
        drift = series.get("index:dubai", {}).get("drift_annual")
        lines.append(
            f"1. **Central path with rates flat: Dubai {pct(idx['dubai']['point'], 1)} over 12 "
            f"months** (to {month(idx['dubai']['month'])}; "
            + "; ".join(
                f"{SEG_LABEL[s]} {pct(idx[s]['point'], 1)}, 80% band {pct(idx[s]['lo80'], 0)} to "
                f"{pct(idx[s]['hi80'], 0)}"
                for s in fc.SEGMENTS
            )
            + "). "
            + (
                f"The model carries a drift of {pct(drift, 1)} a year (the 2011–2026 average "
                "growth) forward, "
                if drift is not None
                else ""
            )
            + f"while the index's latest year-on-year change is {pct(yoy('dubai'), 1)}: the central "
            "path assumes the 2026 pause gives way to the long-run trend. It is a statistical "
            "baseline, not a call on the 2026 turn; the bands include a fall."
        )
    c80i, c95i = cover("index", "coverage_80"), cover("index", "coverage_95")
    c80v, c95v = cover("volume", "coverage_80"), cover("volume", "coverage_95")
    lines += [
        "2. **Backtest (last 24 months):** SARIMAX beats the better naive baseline in "
        + " and ".join(
            f"{sum(w[0] == t for w in wins)} of {sum(x[0] == t for x in scored)} "
            f"{'index' if t == 'index' else 'volume'} cells"
            for t in fc.TARGETS
        )
        + " (segment × horizon; table below). "
        + (
            "On volume it mostly does not: monthly sales swing with launches and the 2026 "
            "slowdown, which a seasonal model with one rate driver can't anticipate, and last "
            "month's count is the better guide. "
            if sum(w[0] == "volume" for w in wins) < sum(x[0] == "volume" for x in scored) / 2
            else ""
        )
        + "Errors grow with the horizon for every model.",
        f"3. **Interval coverage in the backtest:** the 80% interval contained the outcome in "
        f"{pct(c80i, 0, False)} of index forecasts and {pct(c80v, 0, False)} of volume forecasts "
        f"(95%: {pct(c95i, 0, False)} / {pct(c95v, 0, False)}). "
        + (
            "Coverage at or above nominal over 24 origins is reassuring but covers one market "
            "phase; "
            if (c80i or 0) >= 0.8 and (c80v or 0) >= 0.8
            else "Below nominal coverage means the bands are too narrow: "
        )
        + "read the bands as a floor on uncertainty, not a ceiling.",
    ]
    if signs:
        pos = sum(x > 0 for x in signs)
        lines.append(
            f"4. **The rate effect has the wrong sign and isn't significant.** The lagged Fed "
            f"Funds coefficient is positive (higher rates, higher prices and volumes) in {pos} of "
            f"{len(signs)} series and significant (p < 0.05) in {len(sig)}"
            + (f" ({', '.join(f'`{k}`' for k in sig)})" if sig else "")
            + ". 2022–23 had rising rates *and* a boom, so the data can't separate a rate effect "
            "from the cycle; the ±100bp paths show the model's sensitivity, not a causal estimate."
            if pos
            else f"4. **Rates:** the lagged Fed Funds coefficient is negative in all {len(signs)} series "
            f"(higher rates, lower prices) and significant (p < 0.05) in {len(sig)}."
        )
    lines += [
        "",
        "## Method",
        "",
        "**Targets.** The monthly hedonic index for Dubai, apartments and villas, and the monthly "
        "count of clean residential market sales (same three segments), both modelled in logs.",
        "",
        "**Models.**",
        "",
        "- *Naive (last value)*: next month = this month. *Seasonal naive*: next month = the same "
        "month a year earlier. The better of the two (lower mean MAPE over the horizons) is each "
        "series' baseline.",
        f"- *SARIMAX*: ARIMA with the Fed Funds rate lagged {config.FORECAST_RATE_LAG} months as the "
        "exogenous driver. Fed Funds stands in for EIBOR (docs/01: the AED is pegged to the US "
        "dollar, so EIBOR tracks it; the CBUAE EIBOR file isn't loaded yet). With the index "
        "differenced, the coefficient is the % change in prices per unit change in the rate, a "
        f"permanent level effect arriving {config.FORECAST_RATE_LAG} months later. The order is "
        "picked by AIC once, on data before the first backtest origin, then held fixed; the "
        "published forecast uses the same order, so the backtest scores the published model.",
        "- *LightGBM on lags*: not built (docs/05 makes it optional): ~190 monthly points are too "
        "few for trees to add anything over these, and doing it honestly (lags only, out-of-time "
        "tuning) isn't simple.",
        "",
        table(
            [
                "Series",
                "Specification",
                "AIC (pre-backtest)",
                "Drift a year",
                "Rate β",
                "p",
                "+100bp → level",
            ],  # fmt: skip
            [
                [
                    f"`{k}`",
                    v["spec"],
                    num(v["aic_pre_backtest"], 1),
                    pct(v.get("drift_annual"), 1),
                    num(v["rate"].get("beta"), 3),
                    num(v["rate"].get("p_value"), 2),
                    pct(v["rate"].get("effect_per_100bp"), 2),
                ]
                for k, v in series.items()
            ],  # fmt: skip
            "llrrrrr",
        ),
        "",
        "## Backtest: rolling origin, real-time vintages",
        "",
        f"{n_origins} origins, {month(to_date(o0))} to {month(to_date(o1))}: at each origin O the "
        "models see only data dated before O and forecast 1–12 months ahead; horizons 1, 3, 6 "
        "and 12 are scored where the target month has happened (so h = 12 has 13 origins).",
        "",
        "**Why vintages.** The published index is not what a forecaster had at the time. Each "
        "published point comes from 36-month regression windows that also contain *later* sales, "
        "and the latest window is re-fitted every month, so recent points get revised. "
        "Backtesting on today's series would give every origin a smoothed, revised history it "
        "couldn't have known, and flatter the models. So the index at origin O is the **real-time "
        "vintage**: the same rolling-window method re-chained on sales before O only (the 4b AVM "
        "code, `features/asof_index.py`). Forecasts are scored on the *change* they predicted "
        "against the change in today's published series (vintage levels aren't rebased, so only "
        "changes compare). Sales volumes aren't revised, so they're simply cut at O. Future rates "
        "are held flat at the origin's last value (no look-ahead; `tests/test_forecast.py` proves "
        "a forecast at O ignores everything dated O or later).",
        "",
    ]
    for target in fc.TARGETS:
        rows = []
        for seg in fc.SEGMENTS:
            base = baseline(target, seg)
            for hz in config.FORECAST_HORIZONS:
                s_ = bt(target, seg, "sarimax", hz)
                if not s_:
                    continue
                rw, sn = bt(target, seg, "naive_rw", hz), bt(target, seg, "naive_seasonal", hz)
                rows.append([SEG_LABEL[seg], hz, s_["n_origins"], pct(rw["mape"], 2, False),
                             pct(sn["mape"], 2, False), pct(s_["mape"], 2, False),
                             verdict(target, seg, hz), MODEL_LABEL.get(base, "–"),
                             pct(s_["coverage_80"], 0, False), pct(s_["coverage_95"], 0, False)])  # fmt: skip
        if rows:
            lines += [
                f"**{'Price index' if target == 'index' else 'Sales volume'}** (MAPE)",
                "",
                table(
                    [
                        "Segment",
                        "h",
                        "Origins",
                        "Naive",
                        "Seasonal naive",
                        "SARIMAX",
                        "SARIMAX vs baseline",
                        "Baseline",
                        "80% cover",
                        "95% cover",
                    ],
                    rows,
                    "lrrrrrlrrr",
                ),  # fmt: skip
                "",
            ]
    lines += [
        f"![Backtest]({rel(figs['backtest'])})",
        "",
        "## Scenarios: rates flat, +100bp, −100bp",
        "",
        "Rates step from the first forecast month and stay there. The rate enters with a "
        f"{config.FORECAST_RATE_LAG}-month lag, so the three paths are identical for the first "
        f"{config.FORECAST_RATE_LAG} months and part only after that. Change over 12 months, from "
        f"{month(last)}:",
        "",
    ]
    rows = []
    for target in fc.TARGETS:
        for seg in fc.SEGMENTS:
            ends = {sc: endpoint(target, seg, sc) for sc in config.FORECAST_RATE_SCENARIOS}
            if not all(ends.values()):
                continue
            e = ends["rates_flat"]
            rows.append([("Index: " if target == "index" else "Volume: ") + SEG_LABEL[seg],
                         num(e["last"], 1 if target == "index" else 0),
                         *[pct(ends[sc]["point"], 1) for sc in config.FORECAST_RATE_SCENARIOS],
                         f"{pct(e['lo80'], 0)} to {pct(e['hi80'], 0)}",
                         f"{pct(e['lo95'], 0)} to {pct(e['hi95'], 0)}"])  # fmt: skip
    lines += [
        table(
            [
                "Series",
                f"Last ({month(last)})",
                *SCENARIO_LABEL.values(),
                "80% (flat)",
                "95% (flat)",
            ],
            rows,
        ),  # fmt: skip
        "",
        f"![Index fan]({rel(figs['fan_index'])})",
        "",
        f"![Volume fan]({rel(figs['fan_volume'])})",
        "",
        "## Limitations",
        "",
        "- **2026 is a turning point and the models extrapolate.** Villas are ~8% below their "
        "December 2025 peak and 2026 sales volumes run below 2025 (findings F3.x, "
        "reports/price_index.md). ARIMA-type models project the recent drift and mean-revert the "
        "momentum; they don't know about supply pipelines, policy or sentiment, and the backtest "
        "window (2024–26) holds only one turn.",
        "- **Intervals understate uncertainty**: they assume the specification and its parameters "
        "are right and ignore index revisions; the backtest coverage above is the honest measure.",
        "- **Rate sensitivity is not causal.** One driver, Fed Funds as an EIBOR proxy, lagged a "
        f"fixed {config.FORECAST_RATE_LAG} months; Dubai's market also moves with oil, population "
        "and foreign demand, none modelled here.",
        "- **Index revisions:** the forecast starts from today's published index, whose last months "
        "will be revised; a rerun next month starts from a slightly different point.",
        "- **Nominal AED**; volumes are counts of clean market sales (registrations), not "
        "contracts agreed.",
        "",
        "Decisions: docs/05 §8.",
        "",
        "*Source: Dubai Land Department open data (transactions, CC BY 4.0); Fed Funds: FRED "
        "(Board of Governors of the Federal Reserve System).*",
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make model-reports``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    P.apply_style()
    sdiag = load_json(st.diagnostics_path())
    snapshot = to_date(sdiag["snapshot"])
    grid, replay, rules = load_grid(), load_replay(), load_rules()
    out = []
    if grid.height:
        figs = {
            "heatmap": fig_stress_heatmap(grid, snapshot),
            "zones": fig_stress_zones(grid, snapshot, -20, 80),
            "replay": fig_replay(replay, snapshot),
        }
        path = db.reports_dir() / STRESS_REPORT
        path.write_text(stress_report(grid, replay, rules, sdiag, figs))
        out += [path, *figs.values()]
    else:
        log.warning("ml.stress_grid is empty: stress report skipped")
    fdiag = load_json(fc.artifacts() / "diagnostics.json")
    f, b = load_forecast()
    if f.height and b.height:
        figs = {
            "fan_index": fig_fan(f, "index", snapshot),
            "fan_volume": fig_fan(f, "volume", snapshot),
            "backtest": fig_backtest(b, snapshot),
        }
        path = db.reports_dir() / FORECAST_REPORT
        path.write_text(forecast_report(f, b, fdiag, figs))
        out += [path, *figs.values()]
    else:
        log.warning("ml.forecast is empty: forecast report skipped")
    for p in out:
        log.info("wrote %s", p.relative_to(config.PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
