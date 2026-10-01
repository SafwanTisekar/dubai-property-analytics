"""Real-time ("vintage") hedonic index: what the index looked like at the start of a month.

Why not read ``ml.fct_price_index``: every published point comes from a 36-month window
fit that also contains *later* sales, which estimate the area, bedroom and off-plan
coefficients the point depends on. The last window is even re-fitted as new months arrive,
so published recent points get revised. Feeding that series to the AVM would let a 2025
sale's features depend on sales registered after it (and on the sale itself).

So for every **vintage** V (a first-of-month), the same rolling-window method
(``hedonic_index.window_starts`` / ``fit_window`` / ``link_window``) is re-chained on sales
dated in months **before V only**. A sale in month V reads vintage V. That is the index a
valuer could have computed on the morning of the 1st of V.

Cost: the stepped 36-month windows that end before V are identical in every later
vintage (their data is all < V), so their fits are cached and each vintage adds just one
fit, the truncated last window ``[V-36, V-1]``. That last window's full fit also prices
sales in month V for the AVM's rolling hedonic OLS (docs/05 §1, model c).

Vintage levels are not rebased (they don't reach the 2019 base early on): only log
differences *within one vintage* are meaningful, and that is all the features use.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import polars as pl

from dubai_property import config
from dubai_property.models import hedonic_index as h

log = logging.getLogger(__name__)

# Periods kept per vintage: enough for a 12-month change (13 points) and 12 months of
# index-adjusted comparables.
KEEP_PERIODS = 13

VINTAGE_SCHEMA = {
    "segment_id": pl.Utf8,
    "vintage": pl.Date,
    "period": pl.Date,
    "log_index": pl.Float64,
    "n_obs": pl.Int64,
}


@dataclass(frozen=True)
class PricingFit:
    """A vintage's last-window fit, kept to price that month's sales (model c)."""

    fit: h.FitResult
    period: date  # the latest period with >= min-n sales in the window (usually V-1)
    categoricals: tuple[str, ...]
    numerics: tuple[str, ...]


def _recurs(
    start: date, ws: date, we: date, window: int, step: int = config.RTD_STEP_MONTHS
) -> bool:
    """True for a full window on the step grid: later vintages refit exactly this one."""
    offset = (ws.year - start.year) * 12 + ws.month - start.month
    return offset % step == 0 and h.add_months(ws, window - 1) == we


def feature_segments(population: pl.DataFrame) -> list[h.Segment]:
    """The two types and every zone x type: the index's segments, without Dubai overall.

    The set is not the published list (that was chosen with all data, to 2026): any zone
    x type can serve a vintage if its own history before V supports a chain.
    """
    return [s for s in h.segments_for(population) if s.level != "dubai"]


def vintage_months(start: date, end: date) -> list[date]:
    """Every vintage from the month after ``start`` to ``end`` (first-of-months)."""
    return h.period_grid(h.add_months(start, 1), end, "month")


def realtime_index(
    segment: h.Segment,
    population: pl.DataFrame,
    vintages: Iterable[date],
    keep_fits: bool = False,
    min_n: int = config.MIN_N,
    window: int = config.RTD_WINDOW_MONTHS,
    keep_periods: int | None = KEEP_PERIODS,
) -> tuple[pl.DataFrame, dict[date, PricingFit]]:
    """The segment's index as known at each vintage.

    Args:
        segment: Index segment (its ``start`` is the first window's start).
        population: Sales with ``month`` and the index model's columns (any dates: rows
            in or after a vintage's month are dropped before that vintage is fitted).
        vintages: First-of-months.
        keep_fits: Also return each vintage's last-window fit for pricing.
        min_n: Sales a period needs to enter the chain.
        window: Window length in months.
        keep_periods: Chained periods kept per vintage (the last ones); None keeps the
            whole chain (the forecast backtest fits each vintage's full history).

    Returns:
        One row per (vintage, period) for the last ``keep_periods`` chained periods
        (columns as ``VINTAGE_SCHEMA``), and ``{vintage: PricingFit}`` if asked.
    """
    data = segment.select(population)
    cats_nums = None
    cache: dict[tuple[date, date], tuple[dict[date, float], h.FitResult] | None] = {}
    rows: list[dict] = []
    fits: dict[date, PricingFit] = {}
    for v in vintages:
        end = h.add_months(v, -1)
        if end < segment.start:
            continue
        # Strictly before the vintage month. Every window below ends <= end anyway; the
        # filter makes the rule explicit and is what the no-look-ahead test relies on.
        hist = data.filter(pl.col("month") < v)
        if hist.is_empty():
            continue
        counts = h.counts_by_period(hist, "month")
        chain: dict[date, float] = {}
        last: tuple[dict[date, float], h.FitResult] | None = None
        try:
            for ws in h.window_starts(segment.start, end, "month", window):
                we = min(h.add_months(ws, window - 1), end)
                key = (ws, we)
                if key not in cache:
                    cache[key] = h.fit_window(segment, hist, ws, we, "month", min_n, keep_fits)
                fitted = cache[key]
                if fitted is None:
                    continue
                h.link_window(chain, fitted[0])
                last = fitted
        except ValueError:
            continue  # a window that can't be linked: no index this vintage
        if not chain:
            continue
        periods = sorted(chain)
        for p in periods if keep_periods is None else periods[-keep_periods:]:
            rows.append(
                {
                    "segment_id": segment.segment_id,
                    "vintage": v,
                    "period": p,
                    "log_index": chain[p],
                    "n_obs": counts.get(p, 0),
                }
            )
        if keep_fits and last is not None:
            if cats_nums is None:
                _, cats, nums = h.segment_features(segment, hist.head(1))
                cats_nums = (tuple(cats), tuple(nums))
            fits[v] = PricingFit(last[1], max(last[0]), *cats_nums)
        # Only full stepped windows recur in later vintages; drop this vintage's last
        # window (off the step grid, or cut short at ``end``) so the cache stays small.
        for key in [k for k in cache if k[1] == end and not _recurs(segment.start, *k, window)]:
            del cache[key]
    return pl.DataFrame(rows, schema=VINTAGE_SCHEMA), fits


def build_vintages(
    population: pl.DataFrame, vintages: list[date]
) -> tuple[pl.DataFrame, dict[int, dict[date, PricingFit]]]:
    """Vintage index for every feature segment, plus the type-level pricing fits.

    Returns:
        The stacked vintage frame and ``{property_type_key: {vintage: PricingFit}}``.
    """
    t0 = time.perf_counter()
    frames, pricing = [], {}
    for segment in feature_segments(population):
        is_type = segment.level == "type"
        frame, fits = realtime_index(segment, population, vintages, keep_fits=is_type)
        frames.append(frame)
        if is_type:
            pricing[segment.property_type_key] = fits
        log.debug("%s: %d vintage rows", segment.segment_id, frame.height)
    out = pl.concat(frames) if frames else pl.DataFrame(schema=VINTAGE_SCHEMA)
    log.info(
        "index vintages: %d segments x %d vintages -> %d rows in %.0fs",
        len(frames),
        len(vintages),
        out.height,
        time.perf_counter() - t0,
    )
    return out, pricing
