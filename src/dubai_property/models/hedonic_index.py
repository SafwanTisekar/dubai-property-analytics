"""Hedonic price index (docs/05 §2): Dubai, apartments, villas and zones.

Why hedonic: a raw median AED per sq m moves when the *mix* of what sells changes (more
cheap off-plan studios in a boom drag it down even while like-for-like prices rise). A
time-dummy regression holds the characteristics fixed and lets the period dummies carry
the pure price change:

    ln(AED per sq m) = Σ β_t·period_t + γ·ln(area) + bedrooms + off-plan + parking
                       + penthouse + area fixed effects + ε

``exp(β_t)`` is a ratio of geometric means between period t and the base, so no smearing
correction is needed (that matters for predicting AED levels, not for an index).

**Published method: rolling-window time dummy (RTD)** (decision, 2026-10-01). The regression
is re-fitted on 36-month windows stepped 12 months, and the windows are chained on the
periods they share. One pooled fit over 2011-2026 assumes the off-plan premium, bedroom
premia and area effects never change, but they do (the apartment off-plan premium went
from ~6% in 2011-13 to ~31% in 2021-26). The pooled fit is kept as the robustness
comparison in ``reports/price_index.md``.

Other choices (docs/05 §8):

* **Population:** clean residential market sales (``is_clean_market_sale``), apartments
  and villas / townhouses, inside the class area cap, from Jan 2011 (2009-10 prices are
  dominated by backlog registrations of earlier deals).
* **Villas:** only sales with a known bedroom count. Phase 3 (findings F3.1) showed those
  areas are built-up-sized while bedroom-less villa areas are plots, and the bedroom-less
  share kept falling, which alone would move a per-sq-m index.
* **Estimation:** exact OLS through the sparse normal equations. The design has up to ~1M
  rows but only a few hundred columns, so ``XᵀX`` is small even though ``X`` is not.
* **Min-n:** a period is published only with ≥ 20 sales in the segment. A segment is
  monthly if ≥ 90% of its months pass, else quarterly if ≥ 90% of its quarters pass, else
  not published. Thin periods stay in the fit but get no index point.
* **Base:** Jan 2019 = 100 (Q1 2019 for quarterly segments).

Usage::

    uv run python -m dubai_property.models.hedonic_index      # part of make train
"""

from __future__ import annotations

import json
import logging
import math
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime
from pathlib import Path

import connectorx as cx
import numpy as np
import polars as pl
import scipy.sparse as sp

from dubai_property import config, db

log = logging.getLogger(__name__)

ML_TABLE = "fct_price_index"
ARTIFACTS_NAME = "hedonic_index"


def diagnostics_path() -> Path:
    """``artifacts/hedonic_index/diagnostics.json`` (scratch DBs: under artifacts/scratch/)."""
    return db.artifacts_dir() / ARTIFACTS_NAME / "diagnostics.json"


APARTMENT, VILLA = config.RESIDENTIAL_APARTMENT_KEY, 102
TYPE_NAMES = {APARTMENT: "apartment", VILLA: "villa"}
BEDROOMS_CAP = 6  # 6+ bedrooms share one dummy (thin above that)

# One row per clean residential sale. Villas without a bedroom count are left out (their
# areas are plots); plot-sized areas above the class cap are left out for every type.
POPULATION_SQL = """
select date_trunc('month', t.txn_date)::date as month,
       t.area_key,
       a.zone,
       t.property_type_key,
       coalesce(least(t.bedrooms, {cap}), -1) as bedrooms,
       ln(t.area_sqm::float8) as ln_area,
       t.is_offplan,
       t.has_parking,
       t.is_penthouse,
       ln(t.price_per_sqm_aed::float8) as ln_ppsqm
from gold.fct_transaction as t
join gold.dim_area as a on a.area_key = t.area_key
where t.is_clean_market_sale
  and t.is_in_report_scope
  and t.property_type_key in ({apt}, {villa})
  and t.txn_date >= date '{start}'
  and not t.is_area_above_class_cap
  and (t.property_type_key = {apt} or t.bedrooms is not null)
"""

# Row counts in and out, with the reason (docs/01 §7: log every filtering step).
EXCLUSIONS_SQL = """
select property_type_key,
       count(*) as clean_sales,
       count(*) filter (where is_area_above_class_cap) as above_class_cap,
       count(*) filter (where not is_area_above_class_cap and property_type_key = {villa}
                        and bedrooms is null) as villa_no_bedrooms
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope
  and property_type_key in ({apt}, {villa}) and txn_date >= date '{start}'
group by 1
order by 1
"""

DDL = f"""
create table if not exists {config.SCHEMA_ML}.{ML_TABLE} (
    model_version     text           not null,
    fitted_at         timestamptz    not null,
    segment_id        text           not null,
    segment_level     text           not null,
    property_type_key integer,
    zone              text,
    frequency         text           not null,
    period_start      date           not null,
    n_obs             integer        not null,
    log_coef          numeric(12, 8) not null,
    index_value       numeric(10, 4) not null,
    index_3m          numeric(10, 4),
    mom               numeric(10, 6),
    yoy               numeric(10, 6),
    vol_12m           numeric(10, 6),
    running_peak      numeric(10, 4) not null,
    drawdown          numeric(10, 6) not null,
    episode_id        integer,
    is_partial_period boolean        not null,
    primary key (model_version, segment_id, period_start)
)
"""

COLUMNS = [
    "model_version", "fitted_at", "segment_id", "segment_level", "property_type_key", "zone",
    "frequency", "period_start", "n_obs", "log_coef", "index_value", "index_3m", "mom", "yoy",
    "vol_12m", "running_peak", "drawdown", "episode_id", "is_partial_period",
]  # fmt: skip


# --- Segments ---------------------------------------------------------------------
@dataclass(frozen=True)
class Segment:
    """One index series.

    Attributes:
        segment_id: Stable key, e.g. ``dubai``, ``apartment``, ``villa-dubailand``.
        level: ``dubai``, ``type`` or ``zone``.
        property_type_key: 101 / 102, or None for Dubai overall.
        zone: Zone name for zone segments.
        start: First month in the fit.
    """

    segment_id: str
    level: str
    property_type_key: int | None
    zone: str | None
    start: date = config.HEDONIC_START

    def select(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rows of the population that belong to this segment."""
        out = df.filter(pl.col("month") >= self.start)
        if self.property_type_key is not None:
            out = out.filter(pl.col("property_type_key") == self.property_type_key)
        if self.zone is not None:
            out = out.filter(pl.col("zone") == self.zone)
        return out


def slug(text: str) -> str:
    """Lowercase ASCII slug for segment ids ("Marina, JBR & JLT" -> "marina-jbr-jlt")."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def segments_for(df: pl.DataFrame) -> list[Segment]:
    """Dubai, the two types, then every zone x type present in the population."""
    out = [
        Segment("dubai", "dubai", None, None),
        Segment("apartment", "type", APARTMENT, None),
        Segment("villa", "type", VILLA, None),
    ]
    pairs = (
        df.filter(pl.col("zone").is_not_null() & (pl.col("zone") != "Unknown"))
        .select("property_type_key", "zone")
        .unique()
        .sort("property_type_key", "zone")
    )
    for key, zone in pairs.iter_rows():
        out.append(Segment(f"{TYPE_NAMES[key]}-{slug(zone)}", "zone", key, zone))
    return out


# --- Periods and the frequency rule -----------------------------------------------
def quarter_start(d: date) -> date:
    """First day of the quarter containing ``d``."""
    return date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)


def add_months(d: date, months: int) -> date:
    """``d`` (a first-of-month) shifted by ``months``."""
    m = d.year * 12 + d.month - 1 + months
    return date(m // 12, m % 12 + 1, 1)


def period_months(frequency: str) -> int:
    """Months per period."""
    return 1 if frequency == "month" else 3


def period_grid(start: date, end: date, frequency: str) -> list[date]:
    """Every period start from ``start`` to ``end`` inclusive (``month`` or ``quarter``)."""
    first = start if frequency == "month" else quarter_start(start)
    out, d = [], first
    while d <= end:
        out.append(d)
        d = add_months(d, period_months(frequency))
    return out


def base_period(frequency: str, base: date = config.INDEX_BASE_MONTH) -> date:
    """The base period: Jan 2019, or Q1 2019 for a quarterly segment."""
    return base if frequency == "month" else quarter_start(base)


def with_period(df: pl.DataFrame, frequency: str) -> pl.DataFrame:
    """Add a ``period`` column: the month, or the quarter's first day."""
    expr = pl.col("month") if frequency == "month" else pl.col("month").dt.truncate("1q")
    return df.with_columns(expr.alias("period"))


def counts_by_period(df: pl.DataFrame, frequency: str) -> dict[date, int]:
    """Sales per period."""
    g = with_period(df, frequency).group_by("period").len()
    return dict(zip(g["period"].to_list(), g["len"].to_list(), strict=True))


@dataclass(frozen=True)
class FrequencyChoice:
    """Outcome of the frequency rule for one segment.

    Attributes:
        frequency: ``month``, ``quarter`` or None (not published).
        start: First period with ≥ min-n sales at that frequency (the published span
            starts here, so a zone developed after 2011 isn't judged on empty years).
        coverage: Share of periods from ``start`` that pass min-n, per frequency tried.
        reason: Why the segment isn't published (None if it is).
    """

    frequency: str | None
    start: date | None
    coverage: dict[str, float]
    reason: str | None = None


def choose_frequency(
    df: pl.DataFrame,
    start: date,
    end: date,
    min_n: int = config.MIN_N,
    coverage: float = config.PERIOD_COVERAGE_MIN,
    base: date = config.INDEX_BASE_MONTH,
) -> FrequencyChoice:
    """Monthly if enough months pass min-n, else quarterly if enough quarters do, else None.

    For each frequency the span starts at the first period with ≥ ``min_n`` sales (from
    ``start`` on) and must include the base period (Jan 2019 / Q1 2019) with ≥ ``min_n``
    sales. Periods with no sale count as failing, so a segment that only trades now and
    then can't qualify on its few busy periods.
    """
    shares: dict[str, float] = {}
    reasons = []
    for frequency in ("month", "quarter"):
        counts = counts_by_period(df, frequency)
        grid = period_grid(start, end, frequency)
        passing = [p for p in grid if counts.get(p, 0) >= min_n]
        if not passing:
            shares[frequency] = 0.0
            reasons.append(f"no {frequency} with {min_n}+ sales")
            continue
        span = [p for p in grid if p >= passing[0]]
        shares[frequency] = len(passing) / len(span)
        bp = base_period(frequency, base)
        if passing[0] > bp or counts.get(bp, 0) < min_n:
            reasons.append(f"base {frequency} {bp} under min-n")
        elif shares[frequency] < coverage:
            reasons.append(f"{shares[frequency]:.0%} of {frequency}s pass min-n")
        else:
            return FrequencyChoice(frequency, passing[0], shares)
    return FrequencyChoice(None, None, shares, "not published: " + "; ".join(reasons))


# --- The regression ---------------------------------------------------------------
@dataclass
class FitResult:
    """Output of one time-dummy fit: log period effects relative to the base period."""

    effects: dict[date, float]
    n_by_period: dict[date, int]
    n_obs: int
    n_params: int
    r2: float
    resid_sd: float
    coefficients: dict[str, float] = field(default_factory=dict)
    # Everything needed to price a new sale with this fit (the AVM's rolling hedonic OLS,
    # docs/05 §1): every coefficient by name, each categorical's reference level and each
    # numeric's centring mean. Filled only with ``fit_time_dummy(..., keep_params=True)``.
    params: dict[str, float] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    numeric_means: dict[str, float] = field(default_factory=dict)
    resid_median: float = 0.0


def _one_hot(values: np.ndarray, reference: object) -> tuple[sp.csr_matrix, list]:
    """Dummy columns for every level except ``reference``."""
    levels, codes = np.unique(values, return_inverse=True)
    keep = [i for i, lv in enumerate(levels) if lv != reference]
    remap = np.full(len(levels), -1)
    remap[keep] = np.arange(len(keep))
    col = remap[codes]
    rows = np.nonzero(col >= 0)[0]
    mat = sp.csr_matrix((np.ones(len(rows)), (rows, col[rows])), shape=(len(values), len(keep)))
    return mat, [levels[i] for i in keep]


def _reference_level(values: np.ndarray) -> object:
    """``false`` for a flag (so coefficients read as premia), else the most frequent level."""
    levels, counts = np.unique(values, return_counts=True)
    return "false" if "false" in levels else levels[np.argmax(counts)]


def fit_time_dummy(
    df: pl.DataFrame,
    base: date,
    categoricals: Sequence[str],
    numerics: Sequence[str] = (),
    y: str = "ln_ppsqm",
    keep_params: bool = False,
) -> FitResult:
    """Fit ``y ~ period dummies + categoricals + numerics`` by OLS; return the period effects.

    Args:
        df: One row per sale with a ``period`` column, ``y`` and the feature columns.
        base: The omitted period (effect 0).
        categoricals: Columns turned into dummies. The reference level is ``false`` for
            flags and the most frequent level otherwise. A column with one level adds
            nothing (e.g. no penthouses among villas).
        numerics: Columns entered as they are, centred (that doesn't change the period
            effects but keeps XᵀX well conditioned).
        y: Dependent variable.
        keep_params: Also return every coefficient, reference level and centring mean,
            so the fit can price new sales (``predict_log``).

    Raises:
        ValueError: If the base period has no observations.
    """
    periods = df["period"].to_numpy()
    if not (periods == np.datetime64(base)).any():
        raise ValueError(f"base period {base} has no observations")
    n = df.height

    blocks: list[sp.csr_matrix] = [sp.csr_matrix(np.ones((n, 1)))]
    names: list[str] = ["intercept"]
    period_mat, period_levels = _one_hot(periods, np.datetime64(base))
    blocks.append(period_mat)
    names += [f"period:{p}" for p in period_levels]
    references: dict[str, str] = {}
    means: dict[str, float] = {}
    for col in categoricals:
        values = df[col].cast(pl.Utf8).fill_null("null").to_numpy()
        references[col] = str(_reference_level(values))
        mat, levels = _one_hot(values, references[col])
        if mat.shape[1]:
            blocks.append(mat)
            names += [f"{col}={lv}" for lv in levels]
    for col in numerics:
        v = df[col].to_numpy().astype("float64")
        means[col] = float(v.mean())
        blocks.append(sp.csr_matrix((v - means[col]).reshape(-1, 1)))
        names.append(col)
    X = sp.hstack(blocks, format="csr")
    yv = df[y].to_numpy().astype("float64")

    xtx = (X.T @ X).toarray()
    beta = np.linalg.pinv(xtx) @ (X.T @ yv)  # pinv: robust to a dummy that is collinear
    resid = yv - X @ beta
    p = int(np.linalg.matrix_rank(xtx))
    ss_tot = float(((yv - yv.mean()) ** 2).sum())

    effects = {base: 0.0}
    for i, lv in enumerate(period_levels, start=1):
        effects[lv.astype("datetime64[D]").astype(date)] = float(beta[i])
    counts = df.group_by("period").len()
    return FitResult(
        effects=dict(sorted(effects.items())),
        n_by_period=dict(zip(counts["period"].to_list(), counts["len"].to_list(), strict=True)),
        n_obs=n,
        n_params=p,
        r2=1 - float((resid**2).sum()) / ss_tot if ss_tot > 0 else float("nan"),
        resid_sd=float(np.sqrt((resid**2).sum() / max(n - p, 1))),
        coefficients={
            name: float(b)
            for name, b in zip(names, beta, strict=True)
            if not name.startswith(("period:", "area_key=", "intercept"))
        },
        params=dict(zip(names, map(float, beta), strict=True)) if keep_params else {},
        references=references if keep_params else {},
        numeric_means=means if keep_params else {},
        resid_median=float(np.median(resid)) if keep_params else 0.0,
    )


def predict_log(
    fit: FitResult,
    df: pl.DataFrame,
    period: date,
    categoricals: Sequence[str],
    numerics: Sequence[str],
) -> np.ndarray:
    """Price sales with a kept fit at ``period``'s effect: ln y-hat, NaN if unpriceable.

    ln y-hat = intercept + β_period + Σ categorical effects + Σ γ·(x − fit mean). A level
    the fit never saw (an area with no sale in the window, say) has no coefficient, so
    the sale can't be priced and gets NaN rather than a silent reference-level guess.
    The fit's median residual is added (median calibration: the result is a median, not
    a mean, estimate, which is what MdAPE and hit rates measure).
    """
    if not fit.params:
        raise ValueError("fit has no params: fit with keep_params=True")
    if period == min(fit.effects):  # the base period: effect 0, no dummy
        b_period = 0.0
    else:
        b_period = fit.params.get(f"period:{np.datetime64(period)}")
        if b_period is None:
            return np.full(df.height, np.nan)
    out = np.full(df.height, fit.params["intercept"] + b_period + fit.resid_median)
    for col in categoricals:
        values = df[col].cast(pl.Utf8).fill_null("null").to_numpy()
        ref = fit.references.get(col)
        effect = np.array(
            [0.0 if v == ref else fit.params.get(f"{col}={v}", np.nan) for v in values]
        )
        out = out + effect
    for col in numerics:
        v = df[col].to_numpy().astype("float64")
        out = out + fit.params[col] * (v - fit.numeric_means[col])
    return out


def segment_features(segment: Segment, df: pl.DataFrame) -> tuple[pl.DataFrame, list, list]:
    """The model's columns for a segment (data, categoricals, numerics).

    Single-type segments: bedrooms, off-plan, parking and penthouse dummies, area fixed
    effects and ln(area). Dubai overall pools both types, so bedrooms and off-plan are
    interacted with the type and ln(area) gets a slope per type: a villa's bedroom or size
    premium isn't an apartment's.
    """
    cats = ["area_key", "has_parking", "is_penthouse"]
    if segment.property_type_key is not None:
        return df, ["bedrooms", "is_offplan", *cats], ["ln_area"]
    is_apt = pl.col("property_type_key") == APARTMENT
    df = df.with_columns(
        pl.concat_str([pl.col("property_type_key"), pl.col("bedrooms")], separator="|").alias(
            "type_bedrooms"
        ),
        pl.concat_str([pl.col("property_type_key"), pl.col("is_offplan")], separator="|").alias(
            "type_offplan"
        ),
        pl.when(is_apt).then(pl.col("ln_area")).otherwise(0.0).alias("ln_area_apartment"),
        pl.when(is_apt).then(0.0).otherwise(pl.col("ln_area")).alias("ln_area_villa"),
    )
    return df, ["type_bedrooms", "type_offplan", *cats], ["ln_area_apartment", "ln_area_villa"]


def fit_pooled(segment: Segment, df: pl.DataFrame, frequency: str) -> FitResult:
    """One time-dummy fit over the whole span (the robustness comparison)."""
    data, cats, nums = segment_features(segment, with_period(df, frequency))
    return fit_time_dummy(data, base_period(frequency), cats, nums)


def window_starts(
    start: date,
    end: date,
    frequency: str = "month",
    window: int = config.RTD_WINDOW_MONTHS,
    step: int = config.RTD_STEP_MONTHS,
) -> list[date]:
    """Rolling-window starts from ``start`` to ``end``.

    Every ``step`` months while a full window fits, plus a last window ending at ``end``,
    so the latest months are always covered.
    """
    starts, s = [], start
    while add_months(s, window - 1) <= end:
        starts.append(s)
        s = add_months(s, step)
    last = add_months(end, -(window - 1))
    if frequency == "quarter":
        last = quarter_start(last)
    if not starts or starts[-1] < last:
        starts.append(max(last, start))
    return starts


def fit_window(
    segment: Segment,
    df: pl.DataFrame,
    ws: date,
    we: date,
    frequency: str = "month",
    min_n: int = config.MIN_N,
    keep_params: bool = False,
) -> tuple[dict[date, float], FitResult] | None:
    """One window's time-dummy fit on the sales dated ``ws``..``we`` (months, inclusive).

    Returns the effects of the periods with ≥ ``min_n`` sales (relative to the first of
    them) and the fit, or None if no period passes min-n.
    """
    part = with_period(df.filter(pl.col("month").is_between(ws, we)), frequency)
    good = sorted(p for p, c in counts_by_period(part, frequency).items() if c >= min_n)
    if not good:
        return None
    data, cats, nums = segment_features(segment, part)
    fit = fit_time_dummy(data, good[0], cats, nums, keep_params=keep_params)
    return {p: b for p, b in fit.effects.items() if p in good}, fit


def link_window(chain: dict[date, float], effects: dict[date, float]) -> int:
    """Chain a window's effects onto ``chain`` in place; return the periods linked on.

    The window is shifted by the mean log gap over the periods both cover (the geometric
    mean ratio) and contributes only the periods after the chain's last one.

    Raises:
        ValueError: If the chain is non-empty and shares no period with the window.
    """
    overlap = [p for p in effects if p in chain]
    if chain and not overlap:
        raise ValueError(f"window from {min(effects)} shares no published period with the chain")
    link = float(np.mean([chain[p] - effects[p] for p in overlap])) if chain else 0.0
    chain_end = max(chain) if chain else None
    for p, b in effects.items():
        if chain_end is None or p > chain_end:
            chain[p] = b + link
    return len(overlap)


def rolling_window_index(
    segment: Segment,
    df: pl.DataFrame,
    end: date,
    frequency: str = "month",
    window: int = config.RTD_WINDOW_MONTHS,
    step: int = config.RTD_STEP_MONTHS,
    min_n: int = config.MIN_N,
) -> tuple[dict[date, float], list[dict]]:
    """Rolling-window time-dummy (RTD) index: log effects relative to the base period.

    Each window re-estimates every coefficient (off-plan premium, bedroom premia, area
    effects), so drifting characteristic prices can't leak into the period effects the
    way they can in one long pooled fit. Each new window is linked to the chain by the
    mean log gap over the periods both cover (the geometric mean ratio) and adds only the
    periods after the chain's last one. Periods under min-n in a window are not used, for
    linking or otherwise.

    Args:
        segment: The segment (its ``start`` is the first window's start).
        df: The segment's sales (``month`` column).
        end: Last month of data.
        frequency: ``month`` or ``quarter`` (windows are 36 months either way).
        window: Window length in months.
        step: Months between window starts.
        min_n: Sales a period needs to be used.

    Returns:
        ``{period: log index}`` with the base period at 0, and one dict per window (start,
        end, rows, periods linked on, R², the off-plan coefficient).

    Raises:
        ValueError: If a window can't be linked (no shared period) or the chain misses
            the base period.
    """
    starts = window_starts(segment.start, end, frequency, window, step)
    chain: dict[date, float] = {}
    windows = []
    for ws in starts:
        we = add_months(ws, window - 1)
        fitted = fit_window(segment, df, ws, we, frequency, min_n)
        if fitted is None:
            continue
        effects, fit = fitted
        overlap = link_window(chain, effects)
        windows.append(
            {
                "start": ws,
                "end": we,
                "rows": fit.n_obs,
                "linked_on": overlap,
                "r2": fit.r2,
                **{k: v for k, v in fit.coefficients.items() if "offplan" in k},
            }
        )
    base = base_period(frequency)
    if base not in chain:
        raise ValueError(f"rolling-window chain has no base period {base}")
    shift = chain[base]
    return {p: v - shift for p, v in sorted(chain.items())}, windows


# --- Published series and risk metrics ---------------------------------------------
def index_series(
    effects: dict[date, float],
    n_by_period: dict[date, int],
    start: date,
    end: date,
    frequency: str,
    min_n: int = config.MIN_N,
) -> pl.DataFrame:
    """Index on the full period grid; periods under min-n get a null (not published).

    Columns: period, n_obs, log_coef, index_value (= 100·exp(log_coef)).
    """
    rows = []
    for p in period_grid(start, end, frequency):
        n = n_by_period.get(p, 0)
        b = effects.get(p)
        ok = b is not None and n >= min_n
        rows.append(
            {
                "period": p,
                "n_obs": n,
                "log_coef": b if ok else None,
                "index_value": config.INDEX_BASE_VALUE * math.exp(b) if ok else None,
            }
        )
    schema = {"period": pl.Date, "n_obs": pl.Int64, "log_coef": pl.Float64}
    return pl.DataFrame(rows, schema={**schema, "index_value": pl.Float64})


@dataclass(frozen=True)
class Episode:
    """A fall of at least ``EPISODE_MIN_DRAWDOWN`` from a running peak."""

    episode_id: int
    peak_period: date
    peak_index: float
    trough_period: date
    trough_index: float
    depth: float
    periods_to_trough: int
    recovery_period: date | None


def find_episodes(
    periods: Sequence[date],
    index: Sequence[float | None],
    min_drawdown: float = config.EPISODE_MIN_DRAWDOWN,
) -> list[Episode]:
    """Peak-to-trough episodes: from a running peak until the index regains it.

    A drawdown counts as an episode only if its trough is at least ``min_drawdown`` below
    the peak. No list of expected episodes is imposed: a decline that runs into the next
    one without regaining the peak is one episode. Missing (unpublished) periods are
    skipped, not filled. An episode still under water at the end has no recovery period.
    """
    out: list[Episode] = []
    peak_i: int | None = None
    trough_i: int | None = None

    def close(recovery: date | None) -> None:
        depth = index[trough_i] / index[peak_i] - 1
        if depth <= -min_drawdown:
            out.append(
                Episode(
                    len(out) + 1,
                    periods[peak_i],
                    float(index[peak_i]),
                    periods[trough_i],
                    float(index[trough_i]),
                    float(depth),
                    trough_i - peak_i,
                    recovery,
                )
            )

    for i, v in enumerate(index):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        if peak_i is None or v >= index[peak_i]:
            if trough_i is not None:
                close(periods[i])
            peak_i, trough_i = i, None
        elif trough_i is None or v < index[trough_i]:
            trough_i = i
    if peak_i is not None and trough_i is not None:
        close(None)
    return out


def period_change_sd(series: pl.DataFrame) -> float | None:
    """Standard deviation of the log changes between consecutive published periods.

    The noise gate (``config.NOISE_MAX_SD``): a thin segment's index is mostly sampling
    noise, and since every level is relative to one base period, a noisy base distorts the
    whole series even when its growth rates average out.
    """
    logs = np.log(series["index_value"].to_numpy().astype("float64"))
    d = np.diff(logs)
    d = d[~np.isnan(d)]
    return float(d.std(ddof=1)) if len(d) > 2 else None


def add_metrics(
    series: pl.DataFrame,
    frequency: str,
    min_drawdown: float = config.EPISODE_MIN_DRAWDOWN,
) -> tuple[pl.DataFrame, list[Episode]]:
    """MoM, YoY, 3-month mean, 12-month volatility, drawdown and episodes on a period grid.

    ``series`` must hold every period in order (nulls where unpublished). A change is null
    when either end is missing; nothing is interpolated.

    * ``mom``: change on the previous period (month or quarter).
    * ``yoy``: change on the same period a year earlier (12 months or 4 quarters).
    * ``index_3m``: trailing 3-month mean (monthly segments only).
    * ``vol_12m``: annualised standard deviation of the log changes over the trailing
      year (12 monthly or 4 quarterly changes, all present).
    * ``running_peak``, ``drawdown``: index / running peak − 1 (≤ 0).
    * ``episode_id``: set from an episode's peak until the period before recovery.
    """
    lag = 12 if frequency == "month" else 4
    idx = series["index_value"].to_numpy().astype("float64")  # nulls become NaN
    n = len(idx)

    def change(k: int) -> np.ndarray:
        out = np.full(n, np.nan)
        out[k:] = idx[k:] / idx[:-k] - 1
        return out

    logret = np.full(n, np.nan)
    logret[1:] = np.log(idx[1:] / idx[:-1])
    vol = np.full(n, np.nan)
    for i in range(lag, n):
        window = logret[i - lag + 1 : i + 1]
        if not np.isnan(window).any():
            vol[i] = window.std(ddof=1) * math.sqrt(lag)
    idx3 = np.full(n, np.nan)
    if frequency == "month":
        idx3[2:] = (idx[2:] + idx[1:-1] + idx[:-2]) / 3
    peak = np.fmax.accumulate(np.where(np.isnan(idx), -np.inf, idx))
    peak = np.where(np.isnan(idx), np.nan, peak)

    periods = series["period"].to_list()
    episodes = find_episodes(periods, [None if np.isnan(v) else v for v in idx], min_drawdown)
    episode_id: list[int | None] = [None] * n
    pos = {p: i for i, p in enumerate(periods)}
    for e in episodes:
        stop = pos[e.recovery_period] if e.recovery_period else n
        for i in range(pos[e.peak_period], stop):
            if not np.isnan(idx[i]):
                episode_id[i] = e.episode_id

    def col(a: np.ndarray) -> pl.Series:
        return pl.Series(a, dtype=pl.Float64).fill_nan(None)

    out = series.with_columns(
        mom=col(change(1)),
        yoy=col(change(lag)),
        index_3m=col(idx3),
        vol_12m=col(vol),
        running_peak=col(peak),
        drawdown=col(idx / peak - 1),
        episode_id=pl.Series(episode_id, dtype=pl.Int32),
    )
    return out, episodes


# --- Comparisons: pooled vs rolling-window, ours vs DLD ------------------------------
def dense_monthly(frame: pl.DataFrame, start: date, end: date) -> pl.DataFrame:
    """Put ``frame`` (with a ``period`` column) on a gap-free monthly grid.

    A shift by k rows is then always k months; missing months become nulls.
    """
    grid = pl.DataFrame({"period": period_grid(start, end, "month")}, schema={"period": pl.Date})
    return grid.join(frame, on="period", how="left").sort("period")


def compare_series(
    published: pl.DataFrame,
    pooled: pl.DataFrame,
    level_limit: float = config.RTD_MATERIAL_LEVEL_GAP,
    yoy_limit: float = config.RTD_MATERIAL_YOY_GAP,
) -> tuple[dict, pl.DataFrame]:
    """Largest level and YoY gaps between the published (RTD) and pooled monthly indices.

    Both are Jan 2019 = 100 and have ``period`` and ``index_value``. ``material`` is True
    when the level gap exceeds ``level_limit`` (relative to pooled) or any month's YoY gap
    exceeds ``yoy_limit``.
    """
    j = published.select("period", pl.col("index_value").alias("index_rtd")).join(
        pooled.select("period", pl.col("index_value").alias("index_pooled")),
        on="period",
        how="full",
        coalesce=True,
    )
    j = (
        dense_monthly(j, j["period"].min(), j["period"].max())
        .with_columns(
            level_gap=pl.col("index_rtd") / pl.col("index_pooled") - 1,
            yoy_rtd=pl.col("index_rtd") / pl.col("index_rtd").shift(12) - 1,
            yoy_pooled=pl.col("index_pooled") / pl.col("index_pooled").shift(12) - 1,
        )
        .with_columns(yoy_gap=pl.col("yoy_rtd") - pl.col("yoy_pooled"))
    )
    both = j.drop_nulls(["index_rtd", "index_pooled"])
    lvl = both.sort(pl.col("level_gap").abs(), descending=True).row(0, named=True)
    yoy = j.drop_nulls("yoy_gap").sort(pl.col("yoy_gap").abs(), descending=True)
    yoy_row = yoy.row(0, named=True) if yoy.height else {"period": None, "yoy_gap": None}
    max_yoy = abs(yoy_row["yoy_gap"]) if yoy_row["yoy_gap"] is not None else 0.0
    return (
        {
            "months_compared": both.height,
            "max_level_gap": lvl["level_gap"],
            "max_level_gap_points": lvl["index_rtd"] - lvl["index_pooled"],
            "max_level_gap_period": lvl["period"],
            "max_yoy_gap": yoy_row["yoy_gap"],
            "max_yoy_gap_period": yoy_row["period"],
            "mean_abs_yoy_gap": float(j["yoy_gap"].abs().mean() or 0.0),
            "material": abs(lvl["level_gap"]) > level_limit or max_yoy > yoy_limit,
        },
        j,
    )


DLD_PAIRS = {"dubai": "all", "apartment": "flat", "villa": "villa"}


def compare_with_dld(
    ours: pl.DataFrame,
    dld: pl.DataFrame,
    start: date,
    end: date,
    align_months: int = config.DLD_ALIGN_MONTHS,
    max_lead: int = 12,
) -> tuple[dict, pl.DataFrame]:
    """Growth-rate agreement between one of our monthly series and DLD's.

    Levels aren't compared (different bases, baskets and methods); growth rates are:

    * **raw**: our monthly index vs DLD's, month for month;
    * **aligned** (the headline, decision 2026-10-01): our index averaged over the trailing
      ``align_months`` vs DLD's. Ours leads DLD by ~6 months, and a 12-month trailing
      average of ours lines up at lag 0, which suggests DLD's monthly figure averages the
      last 12 months of sales (an inference: the file has no methodology);
    * **lead**: the lag (0..``max_lead`` months) at which our raw YoY best matches DLD's.

    Args:
        ours: Monthly series with ``period`` and ``index_value`` (published months only).
        dld: DLD monthly series with ``period`` and ``index_ratio``.
        start: First month of the comparison window.
        end: Last month DLD covers.
        align_months: Trailing window for the aligned comparison.
        max_lead: Largest lead tried.

    Returns:
        Metrics and the joined monthly frame (``start`` to ``end``) they come from.
    """
    first_ours = ours["period"].min()
    lo = min(add_months(start, -12 - align_months), first_ours)
    j = dense_monthly(
        ours.select("period", "index_value").join(
            dld.select("period", "index_ratio"), on="period", how="full", coalesce=True
        ),
        lo,
        end,
    )
    # Trailing means need every month in the window (rolling_mean leaves a null otherwise).
    j = j.with_columns(
        index_3m=pl.col("index_value").rolling_mean(3),
        index_aligned=pl.col("index_value").rolling_mean(align_months),
    ).with_columns(
        ours_yoy=pl.col("index_value") / pl.col("index_value").shift(12) - 1,
        aligned_yoy=pl.col("index_aligned") / pl.col("index_aligned").shift(12) - 1,
        dld_yoy=pl.col("index_ratio") / pl.col("index_ratio").shift(12) - 1,
        ours_mom=pl.col("index_value") / pl.col("index_value").shift(1) - 1,
        ours_3m_mom=pl.col("index_3m") / pl.col("index_3m").shift(1) - 1,
        dld_mom=pl.col("index_ratio") / pl.col("index_ratio").shift(1) - 1,
    )
    leads = {
        k: j.with_columns(pl.col("ours_yoy").shift(k).alias(f"ours_yoy_lead{k}"))
        .filter(pl.col("period").is_between(start, end))
        .select(f"ours_yoy_lead{k}", "dld_yoy")
        for k in range(max_lead + 1)
    }
    j = j.filter(pl.col("period").is_between(start, end)).with_columns(
        yoy_gap=pl.col("ours_yoy") - pl.col("dld_yoy"),
        aligned_yoy_gap=pl.col("aligned_yoy") - pl.col("dld_yoy"),
    )

    def corr(frame: pl.DataFrame, a: str, b: str) -> tuple[float, int]:
        k = frame.drop_nulls([a, b])
        if k.height < 3:
            return float("nan"), k.height
        return float(np.corrcoef(k[a].to_numpy(), k[b].to_numpy())[0, 1]), k.height

    lead_corr = {k: corr(f, f"ours_yoy_lead{k}", "dld_yoy")[0] for k, f in leads.items()}
    best_lead = max(lead_corr, key=lambda k: -1 if math.isnan(lead_corr[k]) else lead_corr[k])
    both = j.drop_nulls(["index_value", "index_ratio"])
    if both.is_empty():
        raise ValueError("no month where both indices are published")
    first, last = both.row(0, named=True), both.row(-1, named=True)
    j = j.with_columns(
        ours_rebased=pl.col("index_value") / first["index_value"] * 100,
        dld_rebased=pl.col("index_ratio") / first["index_ratio"] * 100,
    )
    yoy_corr, yoy_n = corr(j, "ours_yoy", "dld_yoy")
    aligned_corr, aligned_n = corr(j, "aligned_yoy", "dld_yoy")
    aligned_months = j.drop_nulls(["aligned_yoy", "dld_yoy"])["period"]
    return (
        {
            "start": start,
            "end": end,
            "yoy_corr_aligned": aligned_corr,
            "aligned_months": aligned_n,
            "aligned_first": aligned_months.min(),
            "yoy_corr": yoy_corr,
            "yoy_months": yoy_n,
            "best_lead_months": best_lead,
            "best_lead_corr": lead_corr[best_lead],
            "mom_corr": corr(j, "ours_mom", "dld_mom")[0],
            "mom_3m_corr": corr(j, "ours_3m_mom", "dld_mom")[0],
            "mean_abs_yoy_gap": float(j["yoy_gap"].abs().mean() or float("nan")),
            "mean_abs_aligned_yoy_gap": float(j["aligned_yoy_gap"].abs().mean() or float("nan")),
            "ours_growth": last["index_value"] / first["index_value"] - 1,
            "dld_growth": last["index_ratio"] / first["index_ratio"] - 1,
            "first_month": first["period"],
            "last_month": last["period"],
        },
        j,
    )


def divergence_years(joined: pl.DataFrame, top: int = 3) -> pl.DataFrame:
    """Calendar years with the largest mean absolute aligned YoY gap (ours − DLD)."""
    return (
        joined.drop_nulls("aligned_yoy_gap")
        .group_by(pl.col("period").dt.year().alias("year"))
        .agg(
            mean_gap=pl.col("aligned_yoy_gap").mean(),
            mean_abs_gap=pl.col("aligned_yoy_gap").abs().mean(),
            ours_yoy=pl.col("aligned_yoy").mean(),
            dld_yoy=pl.col("dld_yoy").mean(),
        )
        .sort("mean_abs_gap", descending=True)
        .head(top)
    )


# --- Database I/O -------------------------------------------------------------------
def _fmt(sql: str) -> str:
    return sql.format(
        cap=BEDROOMS_CAP, apt=APARTMENT, villa=VILLA, start=config.HEDONIC_START.isoformat()
    )


def load_population() -> pl.DataFrame:
    """Clean residential sales for the index (~1M rows x 10 columns) via connectorx."""
    df = cx.read_sql(db.connectorx_uri(), _fmt(POPULATION_SQL), return_type="polars")
    return df.with_columns(pl.col("month").cast(pl.Date))


def load_exclusions(conn) -> list[dict]:
    """Clean sales per type and the rows left out of the index, with the reason."""
    cur = conn.execute(_fmt(EXCLUSIONS_SQL))
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def load_snapshot(conn) -> date:
    """Data snapshot date (latest transaction date) from silver."""
    (snap,) = conn.execute("select data_snapshot_date from silver.int_data_snapshot").fetchone()
    return snap


def load_dld(conn) -> pl.DataFrame:
    """DLD's monthly index per segment (period, segment, index_ratio)."""
    rows = conn.execute(
        "select month_start, segment, index_ratio::float8 from silver.stg_dld_price_index"
        " where frequency = 'monthly' order by 1, 2"
    ).fetchall()
    schema = {"period": pl.Date, "segment": pl.Utf8, "index_ratio": pl.Float64}
    return pl.DataFrame(rows, schema=schema, orient="row")


def write_index(conn, frame: pl.DataFrame) -> int:
    """Replace this model version's rows in ``ml.fct_price_index`` (caller commits)."""
    conn.execute(DDL)
    conn.execute(
        f"delete from {config.SCHEMA_ML}.{ML_TABLE} where model_version = %s",
        [config.HEDONIC_MODEL_VERSION],
    )
    n = db.copy_frame(conn, frame, config.SCHEMA_ML, ML_TABLE)
    conn.execute(f"analyze {config.SCHEMA_ML}.{ML_TABLE}")
    return n


# --- Orchestration ------------------------------------------------------------------
def build_segment(
    segment: Segment, data: pl.DataFrame, end_month: date, snapshot: date
) -> tuple[pl.DataFrame | None, dict]:
    """Choose the frequency, fit the chained index, apply min-n and add the risk metrics.

    Returns the published rows (None if the segment isn't published) and a diagnostics
    dict explaining the outcome.
    """
    info: dict = {
        "segment_id": segment.segment_id,
        "level": segment.level,
        "property_type_key": segment.property_type_key,
        "zone": segment.zone,
        "rows": data.height,
    }
    choice = choose_frequency(data, segment.start, end_month)
    info["coverage"] = choice.coverage
    if choice.frequency is None:
        info["status"] = choice.reason
        return None, info
    frequency = choice.frequency
    segment = replace(segment, start=choice.start)
    data = segment.select(data)
    counts = counts_by_period(data, frequency)
    try:
        effects, windows = rolling_window_index(segment, data, end_month, frequency)
    except ValueError as exc:
        info["status"] = f"not published: {exc}"
        return None, info
    series, episodes = add_metrics(
        index_series(effects, counts, segment.start, end_month, frequency), frequency
    )
    noise = period_change_sd(series)
    info["period_change_sd"] = noise
    if noise is not None and noise > config.NOISE_MAX_SD:
        info["status"] = (
            f"not published: too noisy (period-change SD {noise:.2f} > {config.NOISE_MAX_SD})"
        )
        return None, info
    last = series["period"].max()
    last_day = date.fromordinal(add_months(last, period_months(frequency)).toordinal() - 1)
    published = series.drop_nulls("index_value").with_columns(
        is_partial_period=(pl.col("period") == last) & pl.lit(snapshot < last_day)
    )
    info.update(
        status="published",
        frequency=frequency,
        start=segment.start,
        periods_published=published.height,
        periods_in_grid=series.height,
        rows_in_published_periods=int(published["n_obs"].sum()),
        windows=windows,
        episodes=[asdict(e) for e in episodes],
        first_period=published["period"].min(),
        last_period=published["period"].max(),
    )
    out = published.rename({"period": "period_start"}).with_columns(
        segment_id=pl.lit(segment.segment_id),
        segment_level=pl.lit(segment.level),
        property_type_key=pl.lit(segment.property_type_key, dtype=pl.Int32),
        zone=pl.lit(segment.zone, dtype=pl.Utf8),
        frequency=pl.lit(frequency),
    )
    return out, info


def robustness_check(
    segment: Segment, data: pl.DataFrame, published: pl.DataFrame, end_month: date
) -> dict:
    """Pooled (one fit, fixed coefficients) vs the published rolling-window index."""
    fit = fit_pooled(segment, data, "month")
    pooled = index_series(fit.effects, fit.n_by_period, segment.start, end_month, "month")
    cmp, joined = compare_series(published.rename({"period_start": "period"}), pooled)
    log.info(
        "%s pooled vs rolling-window: max level gap %+.1f%% (%s), max YoY gap %+.1f pp (%s)%s",
        segment.segment_id,
        100 * cmp["max_level_gap"],
        cmp["max_level_gap_period"],
        100 * (cmp["max_yoy_gap"] or 0),
        cmp["max_yoy_gap_period"],
        " (material)" if cmp["material"] else "",
    )
    return {
        "comparison": cmp,
        "pooled_fit": {
            "rows": fit.n_obs,
            "params": fit.n_params,
            "r2": fit.r2,
            "resid_sd": fit.resid_sd,
            "coefficients": fit.coefficients,
        },
        "series": joined.select("period", "index_rtd", "index_pooled").to_dicts(),
    }


def run() -> dict:
    """Fit every segment, write ``ml.fct_price_index`` and the diagnostics JSON."""
    t0 = time.perf_counter()
    with db.connect() as conn:
        snapshot = load_snapshot(conn)
        exclusions = load_exclusions(conn)
        dld = load_dld(conn)
    for e in exclusions:
        log.info(
            "type %s: %d clean sales since %s; out: %d above the class area cap, %d villas "
            "without bedrooms",
            e["property_type_key"],
            e["clean_sales"],
            config.HEDONIC_START,
            e["above_class_cap"],
            e["villa_no_bedrooms"],
        )
    population = load_population()
    log.info("population: %d sales loaded in %.1fs", population.height, time.perf_counter() - t0)
    end_month = date(snapshot.year, snapshot.month, 1)
    fitted_at = datetime.now().astimezone()

    frames: dict[str, pl.DataFrame] = {}
    infos = []
    segments = segments_for(population)
    for segment in segments:
        data = segment.select(population)
        frame, info = build_segment(segment, data, end_month, snapshot)
        infos.append(info)
        if frame is None:
            log.info("%s: %s (%d rows)", segment.segment_id, info["status"], data.height)
            continue
        log.info(
            "%s: %s, %d rows, %d/%d periods published, %d windows",
            segment.segment_id,
            info["frequency"],
            data.height,
            info["periods_published"],
            info["periods_in_grid"],
            len(info["windows"]),
        )
        frames[segment.segment_id] = frame

    # Robustness and validation for the three headline series (monthly ones only).
    robustness, validation = {}, {}
    dld_end = dld["period"].max() if dld.height else None
    for segment in segments[:3]:
        frame = frames.get(segment.segment_id)
        if frame is None or frame["frequency"][0] != "month":
            log.info("%s: not monthly, robustness and validation skipped", segment.segment_id)
            continue
        robustness[segment.segment_id] = robustness_check(
            segment, segment.select(population), frame, end_month
        )
        dld_seg = dld.filter(pl.col("segment") == DLD_PAIRS[segment.segment_id])
        if dld_seg.is_empty():
            continue
        try:
            metrics, joined = compare_with_dld(
                frame.rename({"period_start": "period"}),
                dld_seg,
                config.DLD_INDEX_BASE_MONTH,
                dld_end,
            )
        except ValueError as exc:  # e.g. the CI fixtures: no common month
            log.info("%s: validation skipped: %s", segment.segment_id, exc)
            continue
        validation[segment.segment_id] = {
            "dld_segment": DLD_PAIRS[segment.segment_id],
            "metrics": metrics,
            "divergence_years": divergence_years(joined).to_dicts(),
            "series": joined.to_dicts(),
        }
        log.info(
            "%s vs DLD %s: aligned YoY corr %.3f (%d months); raw YoY %.3f, best at a %d-month"
            " lead (%.3f); MoM %.3f",
            segment.segment_id,
            DLD_PAIRS[segment.segment_id],
            metrics["yoy_corr_aligned"],
            metrics["aligned_months"],
            metrics["yoy_corr"],
            metrics["best_lead_months"],
            metrics["best_lead_corr"],
            metrics["mom_corr"],
        )

    if frames:
        out = pl.concat(list(frames.values()), how="diagonal_relaxed").with_columns(
            model_version=pl.lit(config.HEDONIC_MODEL_VERSION),
            fitted_at=pl.lit(fitted_at.isoformat()),
        )
        out = out.select(COLUMNS)
    else:
        out = pl.DataFrame(schema=dict.fromkeys(COLUMNS, pl.Utf8))
    with db.connect() as conn:
        written = write_index(conn, out)
        conn.commit()
    log.info(
        "%s.%s: %d rows written (%d of %d segments published) in %.0fs",
        config.SCHEMA_ML,
        ML_TABLE,
        written,
        len(frames),
        len(infos),
        time.perf_counter() - t0,
    )
    diagnostics = {
        "model_version": config.HEDONIC_MODEL_VERSION,
        "fitted_at": fitted_at,
        "snapshot": snapshot,
        "population_rows": population.height,
        "exclusions": exclusions,
        "segments": infos,
        "robustness": robustness,
        "validation": validation,
        "rows_written": written,
    }
    path = diagnostics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagnostics, default=str, indent=1))
    return diagnostics


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make train``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
