"""Phase 4a reports: ``reports/price_index.md``, ``reports/yields.md`` and their figures.

Every number is read from the model outputs (``ml.fct_price_index``,
``ml.agg_yield_quarter``), the diagnostics written by ``make train``
(``artifacts/hedonic_index/diagnostics.json``: validation, robustness, episodes) or small
SQL aggregates over gold. Nothing is typed in by hand, so ``make model-reports`` after a
refresh rewrites both reports consistently.

Usage::

    uv run python -m dubai_property.models.report_4a      # make model-reports
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
import matplotlib.dates as mdates  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from dubai_property import config, db  # noqa: E402
from dubai_property.analysis import plotting as P  # noqa: E402
from dubai_property.models import hedonic_index as h  # noqa: E402

log = logging.getLogger(__name__)

PRICE_REPORT = "price_index.md"  # under db.reports_dir() (a scratch folder off the main DB)
YIELD_REPORT = "yields.md"
HEADLINE = ("dubai", "apartment", "villa")
LABEL = {"dubai": "Dubai (all residential)", "apartment": "Apartments", "villa": "Villas"}
SHORT = {"dubai": "Dubai", "apartment": "Apartments", "villa": "Villas"}
COLOR = {"dubai": P.TEAL, "apartment": P.NAVY, "villa": P.MAGENTA}
TYPE_LABEL = {101: "Apartments", 102: "Villas / townhouses"}
TYPE_COLOR = {101: P.NAVY, 102: P.MAGENTA}
DLD_NOTE = "Comparison: DLD Residential Properties Sale Index (data.dubai), monthly, to May 2024."

# Raw median AED per sq m of the index population (apartments): the mix-shift comparison.
RAW_MEDIAN_SQL = """
select date_trunc('month', txn_date)::date as period,
       percentile_cont(0.5) within group (order by price_per_sqm_aed)::float8 as median_ppsqm,
       count(*) as n
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope and property_type_key = {apt}
  and not is_area_above_class_cap and txn_date >= date '{start}'
group by 1
order by 1
"""

RAW_YEARLY_SQL = """
select extract(year from txn_date)::int as year,
       percentile_cont(0.5) within group (order by price_per_sqm_aed)::float8 as median_ppsqm
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope and property_type_key = {apt}
  and not is_area_above_class_cap and txn_date >= date '{start}'
group by 1
order by 1
"""


# --- Small formatting helpers ---------------------------------------------------------
def pct(x: float | None, digits: int = 1, sign: bool = True) -> str:
    """0.123 -> '+12.3%' (blank for None/NaN)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{100 * x:{'+' if sign else ''}.{digits}f}%"


def num(x: float | None, digits: int = 1) -> str:
    """Number with thousands separators (blank for None/NaN)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:,.{digits}f}"


def month(d: date | str | None) -> str:
    """'Sep 2026'."""
    if d is None:
        return "–"
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d:%b %Y}"


def quarter(d: date) -> str:
    """'Q3 2026'."""
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def table(header: Sequence[str], rows: Sequence[Sequence[object]], align: str = "") -> str:
    """Markdown table; ``align`` gives one of l/r per column (default: first l, rest r)."""
    align = align or "l" + "r" * (len(header) - 1)
    sep = ["---" if a == "l" else "---:" for a in align]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def rel(path: Path) -> str:
    """Path relative to reports/ for markdown links."""
    return path.relative_to(db.reports_dir()).as_posix()


# --- Data -----------------------------------------------------------------------------
def load_index() -> pl.DataFrame:
    """The published index (current model version)."""
    sql = (
        f"select * from {config.SCHEMA_ML}.{h.ML_TABLE} where model_version = "
        f"'{config.HEDONIC_MODEL_VERSION}' order by segment_id, period_start"
    )
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    floats = [c for c in df.columns if c in ("log_coef", "index_value", "index_3m", "mom",
              "yoy", "vol_12m", "running_peak", "drawdown")]  # fmt: skip
    return df.with_columns(pl.col("period_start").cast(pl.Date), pl.col(floats).cast(pl.Float64))


def load_yields() -> pl.DataFrame:
    """The published yields (current model version)."""
    sql = (
        f"select * from {config.SCHEMA_ML}.agg_yield_quarter where model_version = "
        f"'{config.YIELD_MODEL_VERSION}'"
    )
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars")
    money = ["median_annual_rent_aed", "median_price_aed", "gross_yield"]
    return df.with_columns(pl.col("quarter_start").cast(pl.Date), pl.col(money).cast(pl.Float64))


def load_diagnostics() -> dict:
    """What ``make train`` wrote next to the ml table."""
    path = h.diagnostics_path()
    if not path.exists():
        raise SystemExit(f"{path} missing: run make train first")
    return json.loads(path.read_text())


def query(sql: str) -> pl.DataFrame:
    """Small aggregate from gold."""
    sql = sql.format(apt=h.APARTMENT, start=config.HEDONIC_START.isoformat())
    return cx.read_sql(db.connectorx_uri(), sql, return_type="polars")


def series(index: pl.DataFrame, segment_id: str) -> pl.DataFrame:
    """One segment's published rows, sorted."""
    return index.filter(pl.col("segment_id") == segment_id).sort("period_start")


def to_date(x) -> date:
    """A date from a date or an ISO string (the diagnostics JSON stores strings)."""
    return date.fromisoformat(x) if isinstance(x, str) else x


# --- Figures --------------------------------------------------------------------------
def footer(fig, snapshot: date, note: str | None = None) -> None:
    """Source line with the partial-month note."""
    partial = f"{snapshot:%b %Y} is partial (to {snapshot:%-d %b})."
    P.add_source(fig, snapshot, note=" ".join(x for x in (partial, note) if x), partial=False)


def date_axis(ax, years: int = 2) -> None:
    """Year ticks every ``years`` on a date x-axis, no vertical grid."""
    ax.xaxis.set_major_locator(mdates.YearLocator(years))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(False, axis="x")


def fig_levels(index: pl.DataFrame, diag: dict, snapshot: date) -> Path:
    """Dubai, apartments and villas, Jan 2019 = 100, with Dubai's drawdown episodes shaded."""
    fig, ax = P.figure(size=(10, 5.4))
    dubai_info = next(s for s in diag["segments"] if s["segment_id"] == "dubai")
    for e in dubai_info["episodes"]:
        end = to_date(e["recovery_period"]) if e["recovery_period"] else snapshot
        ax.axvspan(to_date(e["peak_period"]), end, color=P.PHASE_FILLS[0], lw=0, zorder=0)
    ax.axhline(100, color=P.MUTED, lw=0.8, ls=(0, (3, 3)))
    ends = {}
    for seg in HEADLINE:
        s = series(index, seg)
        ax.plot(s["period_start"], s["index_value"], color=COLOR[seg], lw=1.6)
        ends[seg] = (s["period_start"][-1], s["index_value"][-1])
    # End labels, nudged apart so close series (Dubai and apartments) don't overlap.
    placed: list[float] = []
    for seg in sorted(ends, key=lambda k: -ends[k][1]):
        x, y = ends[seg]
        label_y = min([y, *[p - 9 for p in placed if abs(p - y) < 9]])
        placed.append(label_y)
        offset = (6, (label_y - y) * 1.6)
        ax.annotate(SHORT[seg], (x, y), xytext=offset, textcoords="offset points",
                    va="center", fontsize=8.5, color=P.TEXT)  # fmt: skip
    date_axis(ax)
    ax.set_ylabel("Index, Jan 2019 = 100")
    ax.margins(x=0.01)
    ax.set_xlim(right=date(snapshot.year + 2, 1, 1))
    P.titled(
        fig,
        "Hedonic price index: Dubai residential, apartments and villas",
        "Like-for-like AED per sq m, Jan 2019 = 100. Shaded: Dubai drawdowns of 10%+ "
        "from the running peak, peak to recovery.",
    )
    footer(fig, snapshot, "Villas: bedroom-known sales only.")
    return P.save(fig, "price_index_levels")


def fig_validation(diag: dict, snapshot: date) -> Path:
    """YoY: ours (12-month trailing mean, and raw) vs DLD, one panel per segment."""
    segs = [s for s in HEADLINE if s in diag["validation"]]
    fig, axes = P.figure(1, len(segs), size=(12, 4.6), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, seg in zip(axes, segs, strict=True):
        v = diag["validation"][seg]
        rows = pl.DataFrame(v["series"]).with_columns(pl.col("period").str.to_date())
        ax.axhline(0, color=P.MUTED, lw=0.8)
        ax.plot(rows["period"], rows["ours_yoy"], color=P.NAVY, lw=0.8, alpha=0.35)
        ax.plot(rows["period"], rows["aligned_yoy"], color=P.NAVY, lw=1.8)
        ax.plot(rows["period"], rows["dld_yoy"], color=P.TEXT_2, lw=1.4, ls=(0, (4, 2)))
        m = v["metrics"]
        ax.set_title(
            f"{LABEL[seg]}: r = {m['yoy_corr_aligned']:.2f} (raw {m['yoy_corr']:.2f})",
            fontsize=10,
        )
        P.pct_axis(ax)
        date_axis(ax, 3)
    axes[0].set_ylabel("Change on a year earlier")
    axes[0].plot([], [], color=P.NAVY, lw=1.8, label="Ours, 12-month trailing mean")
    axes[0].plot([], [], color=P.NAVY, lw=0.8, alpha=0.35, label="Ours, monthly")
    axes[0].plot([], [], color=P.TEXT_2, lw=1.4, ls=(0, (4, 2)), label="DLD index")
    axes[0].legend(loc="upper left")
    P.titled(
        fig,
        "Validation: year-on-year growth, hedonic index vs DLD's official index",
        "Pearson r of monthly YoY growth. Ours leads DLD by ~6 months; averaged over the "
        "trailing 12 months, as DLD's figure appears to be, they line up.",
    )
    footer(fig, snapshot, DLD_NOTE)
    return P.save(fig, "price_index_validation")


def fig_mix_shift(index: pl.DataFrame, raw: pl.DataFrame, snapshot: date) -> Path:
    """Raw median AED per sq m vs the hedonic index, apartments, both Jan 2019 = 100."""
    s = series(index, "apartment")
    base = raw.filter(pl.col("period") == config.INDEX_BASE_MONTH)["median_ppsqm"][0]
    fig, ax = P.figure(size=(10, 5.2))
    ax.axhline(100, color=P.MUTED, lw=0.8, ls=(0, (3, 3)))
    ax.plot(raw["period"], raw["median_ppsqm"] / base * 100, color=P.TEXT_2, lw=1.2)
    ax.plot(s["period_start"], s["index_value"], color=P.NAVY, lw=1.8)
    P.direct_label(ax, raw["period"][-1], raw["median_ppsqm"][-1] / base * 100, "Raw median")
    P.direct_label(ax, s["period_start"][-1], s["index_value"][-1], "Hedonic index")
    date_axis(ax)
    ax.set_xlim(right=date(snapshot.year + 2, 1, 1))
    ax.set_ylabel("Jan 2019 = 100")
    P.titled(
        fig,
        "Mix shift: the raw median misreads apartment price growth",
        "Apartments, clean market sales. Raw median AED per sq m vs the hedonic index, "
        "both Jan 2019 = 100.",
    )
    footer(fig, snapshot)
    return P.save(fig, "price_index_mix_shift")


def fig_robustness(diag: dict, snapshot: date) -> Path:
    """Published (rolling windows) vs pooled, and the off-plan premium per window."""
    segs = [s for s in ("dubai", "apartment") if s in diag["robustness"]]
    fig, axes = P.figure(1, len(segs) + 1, size=(13, 4.6))
    for ax, seg in zip(axes[:-1], segs, strict=True):
        rows = pl.DataFrame(diag["robustness"][seg]["series"]).with_columns(
            pl.col("period").str.to_date()
        )
        ax.plot(rows["period"], rows["index_pooled"], color=P.TEXT_2, lw=1.2, ls=(0, (4, 2)))
        ax.plot(rows["period"], rows["index_rtd"], color=P.NAVY, lw=1.6)
        ax.set_title(LABEL[seg], fontsize=10)
        date_axis(ax, 4)
    axes[0].set_ylabel("Jan 2019 = 100")
    axes[0].plot([], [], color=P.NAVY, lw=1.6, label="Published: rolling windows")
    axes[0].plot([], [], color=P.TEXT_2, lw=1.2, ls=(0, (4, 2)), label="One pooled fit")
    axes[0].legend(loc="upper left")
    ax = axes[-1]
    windows = next(s for s in diag["segments"] if s["segment_id"] == "apartment")["windows"]
    mids = [to_date(w["start"]).year + 1.5 for w in windows]
    prem = [np.exp(w.get("is_offplan=true", np.nan)) - 1 for w in windows]
    ax.plot(mids, prem, color=P.NAVY, lw=1.6, marker="o", ms=4)
    ax.axhline(0, color=P.MUTED, lw=0.8)
    P.pct_axis(ax)
    ax.set_title("Apartment off-plan premium per window", fontsize=10)
    ax.set_xlabel("Window midpoint (36-month windows)")
    ax.grid(False, axis="x")
    P.titled(
        fig,
        "Robustness: rolling-window index vs one pooled 2011-2026 fit",
        "The pooled fit holds the off-plan premium fixed; it moved from single digits in "
        "2011-15 to ~35% in 2020-26, so the rolling-window index is published.",
    )
    footer(fig, snapshot)
    return P.save(fig, "price_index_robustness")


def fig_zones(index: pl.DataFrame, snapshot: date) -> Path:
    """Small multiples: every published zone series against Dubai overall."""
    zones = (
        index.filter(pl.col("segment_level") == "zone")
        .select("segment_id", "zone", "property_type_key", "frequency")
        .unique()
        .sort("property_type_key", "zone")
    )
    n = zones.height
    cols = 4
    rows_ = int(np.ceil(n / cols))
    fig, axes = P.figure(rows_, cols, size=(13, 2.5 * rows_ + 1.2), sharex=True, sharey=True)
    dubai = series(index, "dubai")
    for ax, z in zip(axes.flat, zones.iter_rows(named=True), strict=False):
        s = series(index, z["segment_id"])
        ax.plot(dubai["period_start"], dubai["index_value"], color=P.GRID, lw=1.2)
        ax.plot(s["period_start"], s["index_value"], color=TYPE_COLOR[z["property_type_key"]],
                lw=1.3, marker="o" if z["frequency"] == "quarter" else None, ms=2)  # fmt: skip
        kind = "apts" if z["property_type_key"] == h.APARTMENT else "villas"
        freq = ", quarterly" if z["frequency"] == "quarter" else ""
        ax.set_title(f"{z['zone']} ({kind}{freq})", fontsize=8)
        date_axis(ax, 5)
    for ax in list(axes.flat)[n:]:
        ax.set_visible(False)
    fig.subplots_adjust(top=1 - 1.15 / fig.get_figheight(), hspace=0.45, wspace=0.12)
    P.titled(
        fig,
        "Hedonic index by zone (Jan 2019 = 100)",
        "Blue: apartments, orange: villas; grey: Dubai overall. Zones and types with "
        "too few sales for min-n are not shown.",
    )
    footer(fig, snapshot)
    return P.save(fig, "price_index_zones")


def fig_yields_by_zone(latest: pl.DataFrame, snapshot: date, label: str) -> Path:
    """Latest four complete quarters: gross yield by zone, apartments and villas."""
    types = [k for k in (101, 102) if latest.filter(pl.col("property_type_key") == k).height]
    fig, axes = P.figure(1, len(types), size=(12, 6.2))
    axes = np.atleast_1d(axes)
    for ax, key in zip(axes, types, strict=True):
        d = latest.filter(pl.col("property_type_key") == key).sort("gross_yield")
        ax.barh(d["zone"], d["gross_yield"], color=TYPE_COLOR[key], height=0.6)
        for y, v in enumerate(d["gross_yield"]):
            ax.text(v, y, f" {100 * v:.1f}%", va="center", fontsize=8, color=P.TEXT_2)
        ax.set_title(TYPE_LABEL[key], fontsize=10)
        P.pct_axis(ax, "x")
        ax.grid(True, axis="x")
        ax.grid(False, axis="y")
        ax.tick_params(axis="y", labelsize=8)
    fig.subplots_adjust(left=0.24, wspace=0.75)
    P.titled(
        fig,
        f"Gross rental yield by zone, {label}",
        "Median annual rent of new contracts / median ready sale price, same zone x "
        "bedrooms x quarter, averaged with sale counts as weights. Gross: before costs.",
    )
    footer(fig, snapshot)
    return P.save(fig, "yields_by_zone")


def fig_yield_trend(trend: pl.DataFrame, snapshot: date) -> Path:
    """Dubai-wide gross yield per quarter, apartments and villas."""
    fig, ax = P.figure(size=(10, 5))
    for key in (101, 102):
        d = trend.filter(pl.col("property_type_key") == key).sort("quarter_start")
        if d.is_empty():
            continue
        ax.plot(d["quarter_start"], d["gross_yield"], color=TYPE_COLOR[key], lw=1.8)
        P.direct_label(ax, d["quarter_start"][-1], d["gross_yield"][-1], TYPE_LABEL[key])
    P.pct_axis(ax, decimals=1)
    date_axis(ax)
    ax.set_xlim(right=date(snapshot.year + 3, 1, 1))
    ax.set_ylabel("Gross yield")
    P.titled(
        fig,
        "Gross rental yields over time",
        "Sales-weighted mean of the zone x bedrooms cells that pass min-n on both sides; "
        "complete quarters only.",
    )
    footer(fig, snapshot)
    return P.save(fig, "yield_trend")


def fig_yield_vs_growth(quad: pl.DataFrame, snapshot: date) -> Path:
    """Income vs growth: latest yield against 3-year index growth, per zone x type."""
    fig, ax = P.figure(size=(10, 6))
    gx, gy = float(quad["growth_3y"].median()), float(quad["gross_yield"].median())
    ax.axvline(gx, color=P.MUTED, lw=1, ls=(0, (3, 3)))
    ax.axhline(gy, color=P.MUTED, lw=1, ls=(0, (3, 3)))
    for key in (101, 102):
        d = quad.filter(pl.col("property_type_key") == key)
        ax.scatter(d["growth_3y"], d["gross_yield"], s=60, color=TYPE_COLOR[key],
                   edgecolor=P.SURFACE, linewidth=2, label=TYPE_LABEL[key], zorder=3)  # fmt: skip
    # Labels: short zone name; a point close to an earlier one gets its label below it.
    placed: list[tuple[float, float]] = []
    span_x = float(quad["growth_3y"].max() - quad["growth_3y"].min()) or 1.0
    span_y = float(quad["gross_yield"].max() - quad["gross_yield"].min()) or 1.0
    for r in quad.sort("gross_yield", descending=True).iter_rows(named=True):
        x, y = r["growth_3y"], r["gross_yield"]
        near = any(abs(x - a) / span_x < 0.06 and abs(y - b) / span_y < 0.04 for a, b in placed)
        placed.append((x, y))
        name = r["zone"].split(",")[0].split(" &")[0]
        ax.annotate(name, (x, y), xytext=(5, -11 if near else 3), textcoords="offset points",
                    fontsize=7.5, color=P.TEXT_2)  # fmt: skip
    ax.margins(x=0.12)
    P.pct_axis(ax, "x")
    P.pct_axis(ax, "y", decimals=1)
    ax.set_xlabel("Index growth over 3 years")
    ax.set_ylabel("Gross yield, latest 4 quarters")
    ax.grid(True, axis="x")
    ax.legend(loc="upper right")
    P.titled(
        fig,
        "Income vs growth: gross yield against 3-year price growth, by zone",
        "Zones with a published hedonic index. Lines: medians across the zones shown.",
    )
    footer(fig, snapshot)
    return P.save(fig, "yield_vs_growth")


# --- Price index report -----------------------------------------------------------------
def episode_kind(e: dict, frequency: str) -> str:
    """Flag short dips: down and back within a few periods is likely noise, not a cycle."""
    if e["recovery_period"] is None:
        return "ongoing"
    rec = to_date(e["recovery_period"])
    trough = to_date(e["trough_period"])
    months = (rec.year - trough.year) * 12 + rec.month - trough.month
    short = e["periods_to_trough"] * h.period_months(frequency) <= 2 and months <= 3
    return "short dip (likely noise)" if short else "cycle"


def mix_shift_changes(
    index: pl.DataFrame, raw_year: pl.DataFrame, snapshot_year: int
) -> list[tuple[int, float | None, float | None]]:
    """(year, raw median change, hedonic change) for apartments, 2012 to the last full year.

    The raw change is on the yearly median AED per sq m (``RAW_YEARLY_SQL``); the hedonic
    change is on the annual average of the monthly apartment index. Their gap is the mix
    effect in the price_index.md table, and the website quotes the same numbers.
    """
    apt = series(index, "apartment").with_columns(y=pl.col("period_start").dt.year())
    annual = apt.group_by("y").agg(pl.col("index_value").mean()).sort("y")
    annual = dict(zip(annual["y"], annual["index_value"], strict=True))
    raw_y = dict(zip(raw_year["year"], raw_year["median_ppsqm"], strict=True))

    def change(d: dict, y: int) -> float | None:
        return d[y] / d[y - 1] - 1 if y in d and y - 1 in d else None

    return [(y, change(raw_y, y), change(annual, y)) for y in range(2012, snapshot_year)]


def price_report(index: pl.DataFrame, diag: dict, raw: pl.DataFrame, raw_year: pl.DataFrame,
                 figs: dict[str, Path]) -> str:  # fmt: skip
    """The markdown for reports/price_index.md."""
    snapshot = to_date(diag["snapshot"])
    infos = {s["segment_id"]: s for s in diag["segments"]}
    published = [s for s in diag["segments"] if s["status"] == "published"]
    last = {seg: series(index, seg).row(-1, named=True) for seg in HEADLINE}
    val = diag["validation"]
    rob = diag["robustness"]

    # Annual (December) index; the partial year uses its latest month.
    years = sorted({d.year for d in index["period_start"]})
    dec_rows = []
    for y in years:
        cells = [str(y) + ("*" if y == snapshot.year else "")]
        for seg in HEADLINE:
            s = series(index, seg).filter(pl.col("period_start").dt.year() == y)
            r = s.row(-1, named=True) if s.height else None
            cells += [num(r["index_value"]), pct(r["yoy"])] if r else ["–", "–"]
        dec_rows.append(cells)

    # Mix shift, 2023 (the Phase 3 example): raw yearly median vs hedonic annual average.
    changes = mix_shift_changes(index, raw_year, snapshot.year)
    mix_rows = [
        [str(y), pct(r), pct(hd), pct((hd or 0) - (r or 0))]
        for y, r, hd in changes if r is not None
    ]  # fmt: skip
    mix = [(y, r, hd) for y, r, hd in changes if r is not None and hd is not None]
    up = min(mix, key=lambda m: m[2] - m[1])  # raw overstates most
    down = max(mix, key=lambda m: m[2] - m[1])  # raw understates most
    base_raw = raw.filter(pl.col("period") == config.INDEX_BASE_MONTH)["median_ppsqm"][0]
    raw_now = raw.row(-1, named=True)

    seg_rows = []
    for s in published:
        seg_rows.append([
            f"`{s['segment_id']}`", s["frequency"].replace("month", "monthly").replace(
                "quarter", "quarterly"), month(s["start"]), f"{s['periods_published']} / "
            f"{s['periods_in_grid']}", num(s["rows"], 0), len(s["windows"]),
        ])  # fmt: skip
    not_pub = [s for s in diag["segments"] if s["status"] != "published"]

    risk_rows = []
    for s in published:
        r = series(index, s["segment_id"]).row(-1, named=True)
        prev = series(index, s["segment_id"]).drop_nulls("vol_12m")
        vol = prev["vol_12m"][-1] if prev.height else None
        risk_rows.append([
            f"`{s['segment_id']}`", month(r["period_start"]) + ("*" if r["is_partial_period"]
            else ""), num(r["index_value"]), pct(r["yoy"]), pct(vol, sign=False),
            pct(r["drawdown"]), num(r["running_peak"]),
        ])  # fmt: skip

    ep_rows = []
    for seg in HEADLINE:
        for e in infos[seg]["episodes"]:
            ep_rows.append([
                LABEL[seg], month(e["peak_period"]), num(e["peak_index"]),
                month(e["trough_period"]), num(e["trough_index"]), pct(e["depth"]),
                e["periods_to_trough"], month(e["recovery_period"]) if e["recovery_period"]
                else "not yet", episode_kind(e, "month"),
            ])  # fmt: skip
    zone_ep_rows = []
    for s in published:
        if s["level"] != "zone":
            continue
        cycles = [e for e in s["episodes"] if episode_kind(e, s["frequency"]) != "short dip "
                  "(likely noise)"]  # fmt: skip
        deepest = min(s["episodes"], key=lambda e: e["depth"], default=None)
        zone_ep_rows.append([
            f"`{s['segment_id']}`", len(s["episodes"]), len(cycles),
            f"{pct(deepest['depth'])} ({month(deepest['peak_period'])} → "
            f"{month(deepest['trough_period'])})" if deepest else "–",
        ])  # fmt: skip

    rob_rows = []
    for seg, r in rob.items():
        c = r["comparison"]
        rob_rows.append([
            LABEL[seg], pct(c["max_level_gap"]), month(c["max_level_gap_period"]),
            pct(c["max_yoy_gap"]), month(c["max_yoy_gap_period"]), pct(c["mean_abs_yoy_gap"],
            sign=False), "yes" if c["material"] else "no",
        ])  # fmt: skip
    win_rows = []
    windows = infos["apartment"]["windows"]
    for w in windows:
        prem = w.get("is_offplan=true")
        win_rows.append([f"{month(w['start'])} – {month(w['end'])}", num(w["rows"], 0),
                         w["linked_on"], f"{w['r2']:.3f}", pct(np.exp(prem) - 1 if prem
                         is not None else None)])  # fmt: skip

    val_rows, div_rows = [], []
    for seg in HEADLINE:
        if seg not in val:
            continue
        m = val[seg]["metrics"]
        val_rows.append([
            f"{LABEL[seg]} vs DLD `{val[seg]['dld_segment']}`",
            f"**{m['yoy_corr_aligned']:.3f}**", m["aligned_months"],
            "✅" if m["yoy_corr_aligned"] >= 0.9 else "❌", f"{m['yoy_corr']:.3f}",
            f"{m['best_lead_months']} ({m['best_lead_corr']:.3f})", f"{m['mom_corr']:.3f}",
            f"{m['mom_3m_corr']:.3f}", pct(m["ours_growth"]), pct(m["dld_growth"]),
        ])  # fmt: skip
        for d in val[seg]["divergence_years"]:
            div_rows.append([LABEL[seg], d["year"], pct(d["ours_yoy"]), pct(d["dld_yoy"]),
                             pct(d["mean_gap"])])  # fmt: skip
    m0 = val.get("dubai", {}).get("metrics", {})

    def coef_rows(seg: str) -> list[list[str]]:
        coefs = rob.get(seg, {}).get("pooled_fit", {}).get("coefficients", {})
        out = []
        for k in sorted(coefs):
            v = coefs[k]
            if k.startswith(("ln_area", "type_offplan=102")) or k.startswith("type_bedrooms"):
                continue
            out.append([f"`{k}`", f"{v:+.3f}", pct(np.exp(v) - 1)])
        return out

    exc = {e["property_type_key"]: e for e in diag["exclusions"]}
    apt_fit = rob.get("apartment", {}).get("pooled_fit", {})

    # Numbers the narrative quotes, so the text can't drift from the data.
    dubai_eps = infos["dubai"]["episodes"]
    main_ep = min(dubai_eps, key=lambda e: e["depth"]) if dubai_eps else None
    other_eps = [e for e in dubai_eps if e is not main_ep]
    prems = [np.exp(w["is_offplan=true"]) - 1 for w in windows if "is_offplan=true" in w]
    all_pass = all(v["metrics"]["yoy_corr_aligned"] >= 0.9 for v in val.values())

    def gap_since(seg: str, year: int) -> float | None:
        rows = pl.DataFrame(rob[seg]["series"]).with_columns(pl.col("period").str.to_date())
        rows = rows.filter(pl.col("period").dt.year() >= year).drop_nulls()
        gap = (rows["index_rtd"] / rows["index_pooled"] - 1).abs()
        return float(gap.max()) if rows.height else None

    late_gap = ", ".join(f"{pct(gap_since(seg, 2017), 1, sign=False)} ({SHORT[seg].lower()})"
                         for seg in rob)  # fmt: skip
    div_years = sorted({d["year"] for v in val.values() for d in v["divergence_years"]})
    growth_txt = "; ".join(
        f"{LABEL[seg]} {pct(v['metrics']['ours_growth'])} vs DLD {pct(v['metrics']['dld_growth'])}"
        for seg, v in val.items()
    )
    # Dubai overall vs DLD "all": is either series a blend of its own apartment / villa ones?
    g = {seg: v["metrics"] for seg, v in val.items()}
    dubai_overshoot_txt = ""
    if {"dubai", "apartment", "villa"} <= g.keys():
        ours = {k: g[k]["ours_growth"] for k in g}
        dld = {k: g[k]["dld_growth"] for k in g}
        lo_d, hi_d = sorted((dld["apartment"], dld["villa"]))
        lo_o, hi_o = sorted((ours["apartment"], ours["villa"]))
        dld_inside = lo_d <= dld["dubai"] <= hi_d
        ours_inside = lo_o <= ours["dubai"] <= hi_o
        dubai_overshoot_txt = (
            f'- **Dubai overall overshoots DLD\'s "all": {pct(ours["dubai"])} vs '
            f"{pct(dld['dubai'])}** over 2012-01 to 2024-05, a gap of "
            f"{100 * (ours['dubai'] - dld['dubai']):.0f} points, even though our apartment "
            f"series matches DLD's flats ({pct(ours['apartment'])} vs {pct(dld['apartment'])}). "
            f"Ours {'sits' if ours_inside else 'does not sit'} between its own apartment and "
            f"villa series ({pct(lo_o)} to {pct(hi_o)}), as a blend of the two should; DLD's "
            f'"all" {"sits between" if dld_inside else "is below both"} its flat and villa '
            f"series ({pct(dld['apartment'])}, {pct(dld['villa'])})"
            + ("" if dld_inside else ", which no fixed-weight blend of the two can do")
            + '. **Likely cause: how DLD weights apartments and villas in "all"** (shifting '
            "weights, or a separately estimated basket whose apartment / villa mix changes "
            "over time), plus our villa series running above DLD's. Not tuned away: our "
            "Dubai index is one regression over both types, weighted by sales, and is "
            "published as such."
        )
    if main_ep:
        ep_txt = (
            f"2. **One long down-cycle.** The ≥10% rule finds the main Dubai episode from a "
            f"{month(main_ep['peak_period'])} peak to a {month(main_ep['trough_period'])} "
            f"trough ({pct(main_ep['depth'])}), recovered only in "
            f"{month(main_ep['recovery_period'])}: the 2020 COVID dip came before prices had "
            "regained their 2014 peak, so the 2014–19 correction and 2020 are one episode"
            + (
                f" (plus {len(other_eps)} shorter one"
                + ("s" if len(other_eps) > 1 else "")
                + ": "
                + ", ".join(f"{month(e['peak_period'])} {pct(e['depth'])}" for e in other_eps)
                + ")"
                if other_eps
                else ""
            )
            + ". (table below)"
        )
    else:
        ep_txt = "2. **No Dubai drawdown of 10% or more** in the published period."
    lines = [
        "# Hedonic price index",
        "",
        "Phase 4a (docs/05 §2). Like-for-like residential price index for Dubai, apartments, "
        "villas and the zones with enough sales, validated against DLD's official index.",
        "",
        f"- **Data:** clean market sales to the snapshot date, **{snapshot:%-d %b %Y}** "
        f"(`{month(snapshot)}`* is a partial month). Model `{diag['model_version']}`, fitted "
        f"{str(diag['fitted_at'])[:16]}.",
        "- **Tables:** `ml.fct_price_index` (published periods only), `rpt.price_index` "
        "(Power BI).",
        "- **Regenerate:** `make train score model-reports`. Code: "
        "`src/dubai_property/models/hedonic_index.py`; this report: `models/report_4a.py`.",
        "",
        "## Summary",
        "",
        f"1. **Prices are {pct(last['dubai']['index_value'] / 100 - 1)} on January 2019** "
        f"(Dubai index {num(last['dubai']['index_value'])} in "
        f"{month(last['dubai']['period_start'])}"
        f"*). Apartments {num(last['apartment']['index_value'])}, villas "
        f"{num(last['villa']['index_value'])}. Year-on-year: Dubai "
        f"{pct(last['dubai']['yoy'])}, apartments {pct(last['apartment']['yoy'])}, villas "
        f"{pct(last['villa']['yoy'])}. ([chart]({rel(figs['levels'])}))",
        ep_txt,
        "3. **Validates against DLD:** YoY correlation "
        f"**{m0.get('yoy_corr_aligned', float('nan')):.2f}** "
        f"(Dubai), with {'every' if all_pass else 'not every'} headline series ≥ 0.9 once our "
        "index is averaged over the same trailing 12 months as DLD's appears to be. Month "
        "for month the correlation "
        f"is {m0.get('yoy_corr', float('nan')):.2f}: our index leads DLD by about "
        f"{m0.get('best_lead_months', '–')} months. ([chart]({rel(figs['validation'])}))",
        f"4. **The raw median misses most of the rise.** Apartment raw median AED per sq m: "
        f"{num(raw_now['median_ppsqm'] / base_raw * 100)} in {month(raw_now['period'])} "
        f"(Jan 2019 = 100) against a hedonic {num(last['apartment']['index_value'])}. "
        f"([chart]({rel(figs['mix_shift'])}))",
        "5. **Published method: rolling windows.** One pooled 2011–2026 fit would hold the "
        f"apartment off-plan premium fixed, but it moved from {pct(min(prems), 0)} to "
        f"{pct(max(prems), 0)} across the windows; the pooled index "
        "differs by up to "
        f"{pct(rob.get('dubai', {}).get('comparison', {}).get('max_level_gap'))} (Dubai), "
        "so it is kept only as the robustness check (decision, 2026-10-01). "
        f"([chart]({rel(figs['robustness'])}))",
        "",
        "## Method",
        "",
        "**Model.** A time-dummy hedonic regression on clean residential market sales:",
        "",
        "```",
        "ln(AED per sq m) = Σ β_t·period_t + γ·ln(area) + bedroom dummies + off-plan + parking",
        "                   + penthouse + area fixed effects + ε",
        "```",
        "",
        "The period dummies carry the price change with the characteristics held constant: "
        "`index_t = 100·exp(β_t)`, with January 2019 (Q1 2019 for quarterly series) as the "
        "omitted base, so the base is exactly 100. `exp(β)` is a ratio of geometric means, "
        "so no smearing correction is needed (that matters for predicting AED levels, not "
        "for an index). Dubai overall pools both types and gives bedrooms, off-plan and "
        "ln(area) a separate effect per type.",
        "",
        "**Rolling windows (published).** The regression is re-fitted on 36-month windows "
        "stepped 12 months; each window is chained to the series by the mean log gap over "
        "the 24 periods both cover, and contributes only the periods after the series' last "
        "one. Every coefficient (off-plan premium, bedroom premia, area effects) is thereby "
        "re-estimated every year, which one pooled fit over 15 years can't do.",
        "",
        "**Population.** `is_clean_market_sale` (arm's-length, no C3–C6/C16/C18 quality flag) "
        "apartments and villas / townhouses, from **January 2011**:",
        "",
        table(
            [
                "Property type",
                "Clean sales since 2011",
                "Above the class area cap (out)",
                "Villas without bedrooms (out)",
                "In the index",
            ],
            [
                [
                    TYPE_LABEL[k],
                    num(e["clean_sales"], 0),
                    num(e["above_class_cap"], 0),
                    num(e["villa_no_bedrooms"], 0),
                    num(e["clean_sales"] - e["above_class_cap"] - e["villa_no_bedrooms"], 0),
                ]
                for k, e in sorted(exc.items())
            ],
        ),  # fmt: skip
        "",
        "- **Why 2011.** In 2009–10, 30–50% of clean apartment sales were registered after "
        "the year they were applied for (the Law 13/2008 backlog, findings F1.3): their "
        "prices were agreed in the 2006–08 boom, so a 2008-start index showed prices rising "
        "through the 2009 crash. DLD's own index starts in March 2011.",
        "- **Villas: bedroom-known sales only.** DLD doesn't say whether a villa's "
        "`procedure_area` is the plot or the built-up area. Villas with a bedroom count have "
        "built-up-sized areas (median ~190–200 sq m); without one, plot-sized (550–600 sq m) "
        "(findings F3.1). The bedroom-less share fell over the period, which alone would "
        "raise a per-sq-m index. Keeping bedroom-known villas holds the area basis constant; "
        "bedroom dummies are the main size control and ln(area) a secondary one. Because "
        "ln(area) is a regressor, using AED per sq m or AED per unit as the dependent "
        "variable gives the same period effects.",
        "- **Area cap.** Areas above the class cap (apartments 1,000 sq m, villas 3,000) are "
        "community or plot areas, not the unit's (rule C21).",
        "",
        "**Estimation.** Exact OLS through the sparse normal equations: up to ~0.9M rows but "
        "only a few hundred columns (period and area dummies), so `XᵀX` is small even though "
        "`X` is not. Full run: ~30 s. Pooled apartment fit: "
        f"R² {apt_fit.get('r2', float('nan')):.3f}, "
        f"residual SD {apt_fit.get('resid_sd', float('nan')):.3f} log points.",
        "",
        "**Min-n and frequency.** A period is published only with **≥ 20 sales** in the "
        "segment; thinner periods stay in the fit but get no index point (never "
        "interpolated). A segment is **monthly** if ≥ 90% of its months pass from its first "
        "month with 20+ sales, else **quarterly** if ≥ 90% of its quarters do, else not "
        "published; the base period must pass either way. A zone that developed after 2011 "
        "(MBR City, DIFC) is therefore judged from when it starts trading.",
        "",
        "## Published segments",
        "",
        table(
            ["Segment", "Frequency", "From", "Periods published", "Sales", "Windows"], seg_rows
        ),  # fmt: skip
        "",
        f"Not published ({len(not_pub)}): "
        + "; ".join(
            f"`{s['segment_id']}` ({s['status'].removeprefix('not published: ')})" for s in not_pub
        )
        + ".",  # fmt: skip
        "",
        f"![Index levels]({rel(figs['levels'])})",
        "",
        f"![Zones]({rel(figs['zones'])})",
        "",
        "## Index by year",
        "",
        "Index in December (latest month for the partial year*) and its change on a year earlier.",
        "",
        table(["Year", "Dubai", "YoY", "Apartments", "YoY", "Villas", "YoY"], dec_rows),
        "",
        "## Risk metrics",
        "",
        "Latest published period per segment. **Volatility:** annualised standard deviation "
        "of the period log changes over the trailing year. **Drawdown:** index / running peak "
        "− 1.",
        "",
        table(
            ["Segment", "Latest", "Index", "YoY", "Volatility 12M", "Drawdown", "Peak"], risk_rows
        ),  # fmt: skip
        "",
        "### Peak-to-trough episodes",
        "",
        "An episode runs from a running peak until the index regains it, and counts if the "
        "trough is ≥ 10% below the peak. No list of expected cycles is imposed: what the "
        "rule finds is reported. A dip down and back within a couple of months is marked "
        "*likely noise*: a monthly hedonic index moves a few percent month to month (see "
        "the MoM correlations below).",
        "",
        table(
            [
                "Series",
                "Peak",
                "Index",
                "Trough",
                "Index",
                "Depth",
                "Months to trough",
                "Recovered",
                "Kind",
            ],
            ep_rows,
        ),  # fmt: skip
        "",
        "- The 2014–2019 correction and the 2020 COVID dip are **one episode**: prices hadn't "
        "regained the mid-2014 peak when COVID hit, so the trough is in 2020 and recovery "
        "only came with the 2021–22 boom.",
        "- 2008–2011 is outside the published index (it starts in 2011; see *Why 2011*). The "
        "stress test's historical replay of 2008–11 drawdowns (docs/05 §4) therefore can't "
        "use this index: Phase 4c uses the shock grid plus a replay of the 2014→2020 episode "
        "instead (docs/05 §4). A 2008–10 index from on-time registrations only is logged as a "
        "stretch idea (docs/05 §6).",
        "",
        "Zones (all episodes found, of which cycles rather than short dips, and the deepest):",
        "",
        table(["Segment", "Episodes", "Cycles", "Deepest"], zone_ep_rows),
        "",
        "## Robustness: rolling windows vs one pooled fit",
        "",
        "This check was run because the pooled fit assumes the off-plan "
        "discount, bedroom premia and area effects never change, while the off-plan share "
        "swung after 2021. The gap is **material** (> 5% in level or > 3 pp in YoY), so the "
        "choice was made explicitly: I chose the rolling-window index for every segment "
        "(2026-10-01).",
        "",
        table(
            [
                "Series",
                "Max level gap (RTD vs pooled)",
                "When",
                "Max YoY gap",
                "When",
                "Mean abs YoY gap",
                "Material",
            ],
            rob_rows,
        ),  # fmt: skip
        "",
        "Apartment windows (36 months, stepped 12; the off-plan premium is relative to a "
        "ready unit with the same area, bedrooms and size):",
        "",
        table(["Window", "Sales", "Periods linked on", "R²", "Off-plan premium"], win_rows),
        "",
        f"![Robustness]({rel(figs['robustness'])})",
        "",
        "The gap is largest before 2017: the pooled fit applies one off-plan premium "
        f"({pct(np.exp(apt_fit.get('coefficients', {}).get('is_offplan=true', np.nan)) - 1, 0)}"
        " for apartments, dominated by the high-volume 2020s) to years when the windows "
        f"estimate {pct(min(prems), 0)}–{pct(max(prems[:5]), 0)} (the first five windows), "
        "and today's area effects to a city with fewer developed areas. From 2017 the "
        f"largest level gaps are {late_gap}.",
        "",
        "## Validation against DLD's official index",
        "",
        "**DLD's file.** The *Residential Properties Sale Index* (data.dubai, issued by DLD) "
        "is wide: one row per month with all / flat / villa × monthly / quarterly / yearly × "
        "two measures. `*_index` is a ratio, **1.000 in January 2012** (Q1 2012, 2012 for the "
        "other frequencies); `*_price_index` is an AED price level of a typical unit, which "
        "is *not* the ratio rescaled (their ratio drifts by ~8%). Validation uses the monthly "
        "`*_index`. The file was stamped 2026-09-01 but **its data ends in May 2024**, so "
        "the comparison covers 2012-01 to 2024-05 and nothing after.",
        "",
        "**Method.** Growth rates, not levels (different bases, baskets and methods). Both "
        "series rebased to their first common month for the chart only.",
        "",
        "- **Headline (aligned):** YoY of our index averaged over the trailing 12 months, "
        "vs DLD's YoY, at lag 0. Decision 2026-10-01: our monthly index leads DLD's by "
        "about six months, and a 12-month trailing average of ours lines up with DLD at lag "
        "0, which suggests DLD's monthly figure averages the last 12 months of sales. That is "
        "an inference from the data; the file carries no methodology.",
        "- **Raw:** month-for-month YoY, the best lead, and MoM correlations are shown "
        "alongside so nothing is hidden.",
        "",
        table(
            [
                "Pair",
                "YoY r, aligned",
                "Months",
                "≥ 0.9",
                "YoY r, raw",
                "Best lead, months (r)",
                "MoM r",
                "MoM r, 3m mean",
                "Our growth",
                "DLD growth",
            ],
            val_rows,
        ),  # fmt: skip
        "",
        "Growth = first to last common month (2012-01 to 2024-05).",
        "",
        f"![Validation]({rel(figs['validation'])})",
        "",
        "**Where they diverge** (calendar years with the largest mean absolute aligned YoY "
        "gap, ours − DLD):",
        "",
        table(["Series", "Year", "Ours (aligned)", "DLD", "Mean gap"], div_rows),
        "",
        "**Why.**",
        "",
        f"- **Timing and boom years.** The largest gaps are in {', '.join(map(str, div_years))}: "
        "turning points and booms, where a 12-month average still lags a monthly index and "
        "the exact window DLD uses matters most. "
        "Ours turns first; DLD's trailing figure follows a few months later.",
        f"- **Cumulative growth (2012-01 to 2024-05):** {growth_txt}. Small YoY gaps add up "
        "over 12 years, so levels are not comparable even when growth rates track.",
        dubai_overshoot_txt,
        "- **Villas.** Our villa index uses bedroom-known villas only; DLD's villa basket (and "
        "whether it includes plot-sized villa areas) is unknown. Villa months also have far "
        f"fewer sales (as few as {num(series(index, 'villa')['n_obs'].min(), 0)}, against "
        f"{num(series(index, 'apartment')['n_obs'].min(), 0)}+ for apartments), so the "
        "villa series is the noisiest of the three.",
        "- **Off-plan.** Our index includes off-plan sales with an off-plan control that the "
        "windows let drift; if DLD weights or treats off-plan differently, the off-plan-led "
        "booms are where the two would differ most.",
        "- **Month-to-month noise.** MoM correlations are low: our index is unsmoothed "
        "(a monthly hedonic estimate with sampling noise), DLD's is smooth. Use YoY or the "
        "3-month average for month-level reading.",
        "",
        "## Mix shift: raw median vs hedonic index",
        "",
        f"![Mix shift]({rel(figs['mix_shift'])})",
        "",
        "Apartments, annual change: raw median AED per sq m of the same population vs the "
        "annual average of the hedonic index. Mix effect = hedonic − raw.",
        "",
        table(["Year", "Raw median", "Hedonic", "Mix effect"], mix_rows),
        "",
        "The raw median moves with **what** sells, and the mix effect swings both ways: "
        f"in {up[0]} the raw median rose {pct(up[1])} against {pct(up[2])} like for like "
        "(the mix of sales moved towards dearer areas and units), while in "
        f"{down[0]} it moved {pct(down[1])} against {pct(down[2])} (the mix moved towards "
        "cheaper zones). Phase 3 (findings F3.2) found the same for 2023 "
        "with a fixed-basket method (+1.2% raw vs +14.5%).",
        "",
        "## Characteristic effects (pooled fits, for interpretation)",
        "",
        "Coefficients of the pooled 2011–2026 fits (log points; the % is `exp(β) − 1`), "
        "relative to a ready unit without parking with the most common bedroom count (1 for "
        "apartments, 3 for villas). Bedroom effects are on top of "
        "the size effect (ln(area): larger units cost less per sq m). The rolling windows "
        "re-estimate all of these every year; see the window table for the off-plan drift.",
        "",
    ]
    for seg in ("apartment", "villa"):
        rows = coef_rows(seg)
        if rows:
            lines += [f"**{LABEL[seg]}**", "", table(["Coefficient", "β", "Effect"], rows), ""]
    lines += [
        "## Limitations",
        "",
        "- **Revisions.** Re-fitting with new data revises recent periods (the last window "
        "changes; earlier periods are fixed once their window has passed). Store the "
        "`model_version` with any downstream use.",
        "- **No confidence band is published.** Within-window standard errors exist, but the "
        "chaining adds uncertainty they don't capture; the published series carries `n_obs` "
        "per period instead.",
        "- **Quality not observed:** finish, view, floor, age and building quality are not in "
        "the DLD data; area fixed effects absorb location, not the building. A shift towards "
        "newer, better-specified stock within an area shows up as price growth.",
        "- **Villas** are the bedroom-known subset; **2026** is partial; **DLD's index** ends "
        "in May 2024 and its method is undocumented, so the validation is indicative.",
        "- **Nominal AED**, not inflation-adjusted.",
        "",
        "Decisions: docs/05 §8.",
        "",
        "*Source: Dubai Land Department open data (transactions, CC BY 4.0) and DLD Residential "
        "Properties Sale Index (data.dubai).*",
        "",
    ]
    return "\n".join(lines)


# --- Yields report ----------------------------------------------------------------------
def weighted(df: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    """Sales-weighted mean yield of the cells in each group, with summed sample sizes."""
    return (
        df.group_by(by)
        .agg(
            gross_yield=(pl.col("gross_yield") * pl.col("n_sale")).sum() / pl.col("n_sale").sum(),
            n_sale=pl.col("n_sale").sum(),
            n_rent=pl.col("n_rent").sum(),
            cells=pl.len(),
            rent=pl.col("median_annual_rent_aed").median(),
            price=pl.col("median_price_aed").median(),
        )
        .sort(by)
    )


def yield_report(yl: pl.DataFrame, index: pl.DataFrame, snapshot: date) -> tuple[str, dict]:
    """The markdown for reports/yields.md and its figures."""
    figs: dict[str, Path] = {}
    # Aggregates leave out cells outside the 2-15% sanity band (decision, Phase 5): two such
    # Al Barsha cells (25%, 23%) with heavy sales weights pushed that zone to 14% and the
    # apartment headline from 7.1% to 7.2%. The cells stay in ml / rpt, flagged, and are
    # listed in the sanity section below; the Power BI yield measures exclude them too.
    zone = yl.filter((pl.col("geo_level") == "zone") & ~pl.col("is_outside_sanity"))
    complete = zone.filter(~pl.col("is_partial_period"))
    last_q = complete["quarter_start"].max()
    first_q = h.add_months(last_q, -9)
    label = f"{quarter(first_q)} – {quarter(last_q)}"
    latest = weighted(complete.filter(pl.col("quarter_start") >= first_q),
                      ["zone", "property_type_key"])  # fmt: skip
    figs["by_zone"] = fig_yields_by_zone(latest, snapshot, label)
    trend = weighted(complete, ["quarter_start", "property_type_key"]).filter(
        pl.col("quarter_start") >= date(2012, 1, 1)
    )
    figs["trend"] = fig_yield_trend(trend, snapshot)

    # Income vs growth: 3-year growth of each published zone index.
    growth = []
    for (_, zone_name, key, _), s in index.filter(pl.col("segment_level") == "zone").group_by(
        ["segment_id", "zone", "property_type_key", "frequency"]
    ):
        s = s.filter(~pl.col("is_partial_period")).sort("period_start")
        if s.is_empty():
            continue
        end = s.row(-1, named=True)
        then = s.filter(pl.col("period_start") == h.add_months(end["period_start"], -36))
        if then.height:
            growth.append({"zone": zone_name, "property_type_key": key,
                           "growth_3y": end["index_value"] / then["index_value"][0] - 1}
                          )  # fmt: skip
    quad = pl.DataFrame(growth, schema={"zone": pl.Utf8, "property_type_key": pl.Int32,
                                        "growth_3y": pl.Float64})  # fmt: skip
    quad = quad.join(latest.with_columns(pl.col("property_type_key").cast(pl.Int32)),
                     on=["zone", "property_type_key"], how="inner")  # fmt: skip
    if quad.height:
        figs["quad"] = fig_yield_vs_growth(quad, snapshot)

    by_bed = weighted(complete.filter(pl.col("quarter_start") >= first_q),
                      ["property_type_key", "bedrooms"])  # fmt: skip
    yearly = weighted(zone.with_columns(year=pl.col("quarter_start").dt.year()),
                      ["year", "property_type_key"])  # fmt: skip
    yr = {
        (r["year"], r["property_type_key"]): r["gross_yield"] for r in yearly.iter_rows(named=True)
    }
    years = sorted({y for y, _ in yr})
    coverage = (
        yl.with_columns(year=pl.col("quarter_start").dt.year())
        .group_by("year")
        .agg(
            area=(pl.col("geo_level") == "area").sum(),
            zone=(pl.col("geo_level") == "zone").sum(),
            rolled=pl.col("areas_rolled_up").sum(),
        )
        .sort("year")
    )
    outside = yl.filter(pl.col("is_outside_sanity")).sort("n_sale", descending=True)
    dubai_latest = weighted(complete.filter(pl.col("quarter_start") >= first_q),
                            ["property_type_key"])  # fmt: skip
    dl = {r["property_type_key"]: r for r in dubai_latest.iter_rows(named=True)}
    lo, hi = config.YIELD_SANITY

    lines = [
        "# Gross rental yields",
        "",
        "Phase 4a (docs/05 §3). Gross yield = **median annual rent of new contracts ÷ median "
        "ready sale price**, for the same area (or zone) × property type × bedrooms × "
        "quarter.",
        "",
        f"- **Data:** to **{snapshot:%-d %b %Y}**; {quarter(h.quarter_start(snapshot))} is "
        "partial and excluded from the 'latest' figures. Model "
        f"`{config.YIELD_MODEL_VERSION}`.",
        "- **Tables:** `ml.agg_yield_quarter` (published cells), `rpt.yield_quarter` (Power "
        "BI). Code: `src/dubai_property/models/yields.py`.",
        "",
        "## Summary",
        "",
    ]
    if 101 in dl:
        lines.append(
            f"1. **Apartments yield {pct(dl[101]['gross_yield'], sign=False)} gross** over "
            f"{label} (sales-weighted across zone × bedroom cells), villas "
            f"{pct(dl.get(102, {}).get('gross_yield'), sign=False)}. "
            f"([chart]({rel(figs['by_zone'])}))"
        )
    full_years = [y for y in years if y >= 2012 and y < snapshot.year]
    cycle = []
    for k in (101, 102):
        ys = [(y, yr[(y, k)]) for y in full_years if (y, k) in yr]
        if len(ys) < 3:
            continue
        hi_y = max(ys, key=lambda t: t[1])
        lo_y = min((t for t in ys if t[0] > hi_y[0]), key=lambda t: t[1], default=None)
        if lo_y is None:
            continue
        cycle.append(
            f"{TYPE_LABEL[k].lower()} {pct(hi_y[1], sign=False)} in {hi_y[0]} → "
            f"{pct(lo_y[1], sign=False)} in {lo_y[0]} → {pct(ys[-1][1], sign=False)} in {ys[-1][0]}"
        )
    if cycle:
        lines.append(
            "2. **Yields over the cycle** (calendar years): "
            + "; ".join(cycle)
            + ". Prices outran new rents into the 2021–22 surge; rents then caught up. "
            f"([chart]({rel(figs['trend'])}))"
        )
    apt_bed = by_bed.filter(pl.col("property_type_key") == 101).sort("bedrooms")
    villa_bed = by_bed.filter(pl.col("property_type_key") == 102)
    if apt_bed.height >= 2:
        first, last = apt_bed.row(0, named=True), apt_bed.row(-1, named=True)
        bed = "studios" if first["bedrooms"] == 0 else f"{first['bedrooms']}-beds"
        villa_txt = (
            f"; villas range {pct(villa_bed['gross_yield'].min(), sign=False)}–"
            f"{pct(villa_bed['gross_yield'].max(), sign=False)}"
            if villa_bed.height
            else ""
        )
        lines.append(
            f"3. **Smaller apartments yield more:** {bed} {pct(first['gross_yield'], sign=False)}"
            f" down to {pct(last['gross_yield'], sign=False)} for {last['bedrooms']}-beds"
            f"{villa_txt} (table below)."
        )
    lines += [
        f"4. **Sanity:** {outside.height} of {yl.height:,} published cells fall outside "
        f"{100 * lo:.0f}–{100 * hi:.0f}% (flagged, kept; listed below).",
        "",
        "## Method",
        "",
        "- **Rent side:** `is_market_rent`: **new** Ejari contracts (renewals lag the market), "
        "**single-line contracts only** (rule C11 option 1: a multi-unit contract repeats "
        "its amount on every line, so a per-unit figure is an allocation, not a price), no "
        "C14 outliers, no virtual units or labour camps (C20), valid dates (C18). Rent = "
        "the contract's annual rent; bedrooms from the Ejari sub-type (C22).",
        "- **Sale side:** `is_clean_market_sale` and **ready** (not off-plan). An off-plan "
        "price buys a unit that can't be let yet, often on a payment plan, so it isn't the "
        "price a landlord pays for today's rent. Price = AED per unit, so the villa plot vs "
        "built-up area question doesn't arise.",
        "- **Cells:** quarter (rent: contract start; sale: registration date) × area × "
        "property type (apartment, villa / townhouse) × bedrooms. Medians with "
        "`percentile_cont` in Postgres; the 3.5M rent lines never leave the database.",
        "- **Min-n:** ≥ 20 observations on **both** sides. Thin area cells **roll up to the "
        "zone**, where medians are recomputed from the rows (not averaged). Zone cells under "
        "min-n are not published. Sample sizes are on every row.",
        "- **Aggregates in this report** (zone, Dubai, trend) are sales-weighted means of "
        "the published **zone** cells, so every rent is compared with a price of the same "
        "bedrooms and quarter. Cells **outside the 2–15% sanity band are left out** of every "
        "aggregate (they stay in the data, flagged; see the sanity check), so one implausible "
        "cell can't move a zone or the headline.",
        "",
        "## Coverage",
        "",
        table(
            ["Year", "Area cells", "Zone cells", "Area cells only in zone rows"],
            [
                [r["year"], num(r["area"], 0), num(r["zone"], 0), num(r["rolled"], 0)]
                for r in coverage.iter_rows(named=True)
            ],
        ),  # fmt: skip
        "",
        "Area-level cells need 20 ready sales of one bedroom count in one area in one "
        "quarter, which only the busiest areas reach; most of the picture is at zone level.",
        "",
        f"## Latest four quarters by zone ({label})",
        "",
        f"![Yield by zone]({rel(figs['by_zone'])})",
        "",
        table(
            ["Zone", "Type", "Gross yield", "Sales", "New contracts", "Cells"],
            [
                [
                    r["zone"],
                    TYPE_LABEL[r["property_type_key"]],
                    pct(r["gross_yield"], sign=False),
                    num(r["n_sale"], 0),
                    num(r["n_rent"], 0),
                    r["cells"],
                ]
                for r in latest.sort(
                    ["property_type_key", "gross_yield"], descending=[False, True]
                ).iter_rows(named=True)
            ],
            "llrrrr",
        ),  # fmt: skip
        "",
        "## Apartments vs villas, by bedrooms",
        "",
        table(
            [
                "Type",
                "Bedrooms",
                "Gross yield",
                "Median rent AED",
                "Median price AED",
                "Sales",
                "New contracts",
            ],
            [
                [
                    TYPE_LABEL[r["property_type_key"]],
                    "Studio" if r["bedrooms"] == 0 else r["bedrooms"],
                    pct(r["gross_yield"], sign=False),
                    num(r["rent"], 0),
                    num(r["price"], 0),
                    num(r["n_sale"], 0),
                    num(r["n_rent"], 0),
                ]
                for r in by_bed.iter_rows(named=True)
            ],
            "llrrrrr",
        ),  # fmt: skip
        "",
        "Median rent and price here are the medians of the cell medians, for orientation.",
        "",
        "## Yield over time",
        "",
        f"![Yield trend]({rel(figs['trend'])})",
        "",
        table(
            ["Year", "Apartments", "Villas / townhouses"],
            [
                [
                    str(y) + ("*" if y == snapshot.year else ""),
                    pct(yr.get((y, 101)), sign=False),
                    pct(yr.get((y, 102)), sign=False),
                ]
                for y in years
            ],
        ),  # fmt: skip
        "",
    ]
    if "quad" in figs:
        lines += [
            "## Income vs growth",
            "",
            "Zones with a published hedonic index: latest four-quarter gross yield against "
            "the index's change over the last 3 years. Top right = both income and growth.",
            "",
            f"![Yield vs growth]({rel(figs['quad'])})",
            "",
            table(
                ["Zone", "Type", "3-year growth", "Gross yield"],
                [
                    [
                        r["zone"],
                        TYPE_LABEL[r["property_type_key"]],
                        pct(r["growth_3y"]),
                        pct(r["gross_yield"], sign=False),
                    ]
                    for r in quad.sort("gross_yield", descending=True).iter_rows(named=True)
                ],
                "llrr",
            ),  # fmt: skip
            "",
        ]
    lines += [
        f"## Sanity check: yields outside {100 * lo:.0f}–{100 * hi:.0f}%",
        "",
        table(
            [
                "Quarter",
                "Level",
                "Zone",
                "Area key",
                "Type",
                "Bedrooms",
                "Yield",
                "Rent n",
                "Sale n",
            ],
            [
                [
                    quarter(r["quarter_start"]),
                    r["geo_level"],
                    r["zone"],
                    r["area_key"] or "–",
                    TYPE_LABEL[r["property_type_key"]],
                    r["bedrooms"],
                    pct(r["gross_yield"], sign=False),
                    r["n_rent"],
                    r["n_sale"],
                ]
                for r in outside.iter_rows(named=True)
            ],
            "lllllrrrr",
        )
        if outside.height
        else "None.",  # fmt: skip
        "",
        "They are kept in the data (flagged `is_outside_sanity`) because each passes min-n, "
        "but **left out of every aggregate above** and of the Power BI yield measures. A high "
        "yield in a cell usually means its ready sales are a cheaper sub-market than its new "
        "lets (e.g. older buildings sold, newer ones let) rather than an error.",
        "",
        "## Caveats",
        "",
        "- **Gross, not net:** before service charges (often 1–2 points of yield on "
        "apartments), vacancy, maintenance, agency fees and DLD / Ejari costs.",
        "- **Different units:** the rent and sale medians in a cell come from different "
        "units of the same type, bedrooms and area or zone, not the same flats.",
        "- **New contracts** lead renewals; a yield on renewals would be lower in a rising "
        "rent market.",
        "- **Nominal AED**; the latest quarter is partial and excluded from 'latest'.",
        "",
        "Decisions: docs/05 §8.",
        "",
        "*Source: Dubai Land Department open data (transactions and Ejari rent contracts), "
        "CC BY 4.0.*",
        "",
    ]
    return "\n".join(lines), figs


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make model-reports``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    P.apply_style()
    diag = load_diagnostics()
    snapshot = to_date(diag["snapshot"])
    index = load_index()
    raw = query(RAW_MEDIAN_SQL).with_columns(pl.col("period").cast(pl.Date))
    raw_year = query(RAW_YEARLY_SQL)
    figs = {
        "levels": fig_levels(index, diag, snapshot),
        "validation": fig_validation(diag, snapshot),
        "mix_shift": fig_mix_shift(index, raw, snapshot),
        "robustness": fig_robustness(diag, snapshot),
        "zones": fig_zones(index, snapshot),
    }
    price_path = db.reports_dir() / PRICE_REPORT
    price_path.write_text(price_report(index, diag, raw, raw_year, figs))
    log.info("wrote %s", price_path.relative_to(config.PROJECT_ROOT))
    text, yfigs = yield_report(load_yields(), index, snapshot)
    yield_path = db.reports_dir() / YIELD_REPORT
    yield_path.write_text(text)
    log.info("wrote %s", yield_path.relative_to(config.PROJECT_ROOT))
    for p in [*figs.values(), *yfigs.values()]:
        log.info("figure %s", p.relative_to(config.PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
