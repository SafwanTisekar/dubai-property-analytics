"""One chart style for every Phase 3 figure (reports/figures/*.png, reused by the website).

Design rules (kept deliberately few):

* **Colour follows the entity.** Ready and apartments are navy, off-plan and villas are
  magenta, a third series is teal, context is grey: the Power BI report's palette
  (powerbi/theme.json, Phase 5), so the report, the figures and the website match. Navy and
  magenta differ strongly in lightness, so they stay apart for colour-blind readers too, and
  each clears 3:1 on white (magenta 4.75:1, so it also works as text). Magnitude (heatmaps)
  uses one navy ramp, light to dark.
* **One y-axis per panel.** Two measures on different scales (e.g. mortgage share and the
  Fed Funds rate) go in stacked panels sharing the time axis, never a dual axis.
* **Every chart is labelled for scope**: 2026 is partial (hatched bars, "2026*" ticks)
  and the footer states the source (DLD, CC BY 4.0) and the snapshot date.
* Money is AED (``AED 1.2bn``, ``AED 350m``, ``18,500``); areas are sq m.

Inline figures render at 72 dpi to keep the committed notebooks small; ``save`` writes
150 dpi PNGs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, PercentFormatter

from dubai_property import db

# --- Tokens ---------------------------------------------------------------------------
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
PHASE_FILLS = ("#efeeea", "#f6f5f2")  # alternate so adjacent phases stay distinct

NAVY, MAGENTA, TEAL, GREY = "#1b2a4a", "#d6247f", "#0f8b8d", "#6b7280"
SERIES = {
    "ready": NAVY,
    "offplan": MAGENTA,
    "apartment": NAVY,
    "villa": MAGENTA,
    "third": TEAL,
    "total": NAVY,
    "neutral": MUTED,
}
# Sequential navy ramp (light → dark) for heatmaps.
NAVY_RAMP = ["#e3e8f2", "#c2cde3", "#9aaacd", "#6f84b1", "#4a6294", "#2f4573", "#1b2a4a"]
SEQUENTIAL = LinearSegmentedColormap.from_list("dpa_navy", NAVY_RAMP)

INLINE_DPI = 72
SAVE_DPI = 150
SOURCE = "Source: Dubai Land Department open data (CC BY 4.0); analysis: dubai-property-analytics."


def apply_style() -> None:
    """Set matplotlib rcParams for the project style (call once per notebook)."""
    mpl.rcParams.update(
        {
            "figure.dpi": INLINE_DPI,
            "savefig.dpi": SAVE_DPI,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 9,
            "axes.labelcolor": TEXT_2,
            "axes.edgecolor": GRID,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": TEXT_2,
            "ytick.color": TEXT_2,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "ytick.left": False,
            "text.color": TEXT,
            "lines.linewidth": 2,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
        }
    )


# --- Number formats -----------------------------------------------------------------
def fmt_aed(value: float, prefix: bool = True, decimals: int = 0) -> str:
    """Format AED compactly: 1.2bn, 350m, 18,500 (``AED`` prefix unless disabled).

    ``decimals`` applies to millions: 0 gives "1m"; 2 gives "1.06m", for charts whose
    values all sit between 1m and 2m.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    a = abs(value)
    if a >= 1e9:
        text = f"{value / 1e9:,.1f}".removesuffix(".0") + "bn"
    elif a >= 1e6:
        text = f"{value / 1e6:,.{decimals}f}m"
    else:
        text = f"{value:,.0f}"
    return f"AED {text}" if prefix else text


def aed_axis(ax, axis: str = "y", prefix: bool = False, decimals: int = 0) -> None:
    """Format an axis in compact AED (the axis label carries the unit by default)."""
    fmt = FuncFormatter(lambda v, _pos: fmt_aed(v, prefix=prefix, decimals=decimals))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def count_axis(ax, axis: str = "y") -> None:
    """Thousands separators on a count axis (e.g. 120,000)."""
    fmt = FuncFormatter(lambda v, _pos: f"{v:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def pct_axis(ax, axis: str = "y", decimals: int = 0) -> None:
    """Percent axis for values stored as fractions (0.25 → 25%)."""
    fmt = PercentFormatter(1.0, decimals=decimals)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


# --- Scope labelling ----------------------------------------------------------------
def year_label(year: int, snapshot: date) -> str:
    """Tick label for a year; the partial snapshot year gets an asterisk ("2026*")."""
    return f"{year}*" if year == snapshot.year and snapshot < date(year, 12, 31) else str(year)


def partial_note(snapshot: date) -> str:
    """Footnote text explaining the partial year."""
    return f"* {snapshot.year} is partial: 1 Jan – {snapshot:%-d %b %Y}."


def year_bars(
    ax,
    years: Sequence[int],
    values: Sequence[float],
    snapshot: date,
    color: str = NAVY,
    label: str | None = None,
    bottom: Sequence[float] | None = None,
    width: float = 0.8,
    offset: float = 0.0,
):
    """Bars by year; the partial snapshot year is hatched and lighter."""
    years = list(years)
    partial = [year_label(y, snapshot).endswith("*") for y in years]
    bars = ax.bar(
        np.array(years) + offset,
        values,
        width=width,
        bottom=bottom,
        color=color,
        label=label,
        edgecolor=SURFACE,
        linewidth=0.8,
    )
    for bar, is_partial in zip(bars, partial, strict=True):
        if is_partial:
            bar.set_alpha(0.55)
            bar.set_hatch("///")
    return bars


def year_ticks(ax, years: Iterable[int], snapshot: date, step: int = 2) -> None:
    """Year ticks every ``step`` years, always including the partial final year."""
    years = sorted(set(years))
    ticks = [y for y in years if (y - years[0]) % step == 0]
    if years[-1] not in ticks:
        ticks.append(years[-1])
    ax.set_xticks(ticks)
    ax.set_xticklabels([year_label(y, snapshot) for y in ticks])
    ax.grid(False, axis="x")


def shade_phases(ax, phases, snapshot: date, by: str = "year", label: bool = True) -> None:
    """Shade the market phases (``market_cycles.CYCLE_PHASES``) behind the data.

    Args:
        ax: Axes.
        phases: Iterable of phases with ``label``, ``start_year``, ``end_year``.
        snapshot: Data snapshot date (a running phase ends there).
        by: ``"year"`` for a numeric year axis, ``"month"`` for a datetime axis.
        label: Write the phase label at the top of each band.
    """
    import pandas as pd

    for i, p in enumerate(phases):
        end_year = p.end_year or snapshot.year
        if by == "year":
            x0, x1 = p.start_year - 0.5, end_year + 0.5
        else:
            x0 = pd.Timestamp(p.start_year, 1, 1)
            x1 = pd.Timestamp(snapshot) if p.end_year is None else pd.Timestamp(end_year, 12, 31)
        ax.axvspan(x0, x1, color=PHASE_FILLS[i % 2], zorder=0, linewidth=0)
        ax.axvline(x0, color=GRID, lw=0.8, ls=(0, (3, 3)), zorder=0)
        if label:
            ax.text(
                x0 + (x1 - x0) * 0.02 if by == "year" else x0,
                1.0,
                f" {p.label}",
                transform=ax.get_xaxis_transform(),
                va="bottom" if i % 2 == 0 else "top",
                ha="left",
                fontsize=7.5,
                color=TEXT_2,
            )


# --- Figure furniture ---------------------------------------------------------------
def titled(fig, title: str, subtitle: str | None = None) -> None:
    """Figure title (bold) and an optional subtitle, placed in inches from the top.

    Fixed inch offsets keep the title block the same on short and tall figures; the
    plotting area is pushed down if it would run into the title block.
    """
    h = fig.get_figheight()
    fig.suptitle(
        title, x=0.01, y=1 - 0.08 / h, ha="left", va="top", fontsize=12.5, fontweight="bold"
    )
    if subtitle:
        fig.text(0.01, 1 - 0.40 / h, subtitle, ha="left", va="top", fontsize=9, color=TEXT_2)
    max_top = 1 - 1.0 / h
    if fig.subplotpars.top > max_top:
        fig.subplots_adjust(top=max_top)


def add_source(fig, snapshot: date, note: str | None = None, partial: bool = True) -> None:
    """Footer: source and attribution, snapshot date, partial-year note, extra note."""
    parts = [f"{SOURCE} Data to {snapshot:%-d %b %Y}."]
    if partial:
        parts.append(partial_note(snapshot))
    if note:
        parts.append(note)
    fig.text(
        0.01, 0.005, "  ".join(parts), ha="left", va="bottom", fontsize=7, color=MUTED, wrap=True
    )


def figure(nrows: int = 1, ncols: int = 1, size=(10, 5.2), **kwargs):
    """New figure with room reserved for the title block and the footer."""
    fig, axes = plt.subplots(nrows, ncols, figsize=size, **kwargs)
    fig.subplots_adjust(top=0.84, bottom=0.14, left=0.08, right=0.98)
    return fig, axes


def direct_label(ax, x, y, text: str, color: str = TEXT, **kwargs) -> None:
    """Label a series at a point, in text ink (the adjacent mark carries the colour)."""
    style = {"xytext": (4, 0), "textcoords": "offset points", "va": "center", "fontsize": 8.5}
    ax.annotate(text, (x, y), color=color, **{**style, **kwargs})


def save(fig, name: str, directory: Path | None = None) -> Path:
    """Save ``fig`` as ``<directory>/<name>.png`` at ``SAVE_DPI`` and return the path.

    ``directory`` defaults to ``db.figures_dir()``: ``reports/figures`` on the main
    database, a scratch folder otherwise.
    """
    directory = directory or db.figures_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path, dpi=SAVE_DPI)
    return path
