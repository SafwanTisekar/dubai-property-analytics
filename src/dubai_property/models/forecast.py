"""Market outlook (docs/05 §5): 12-month forecasts of the hedonic index and sales volume.

**Targets.** The monthly hedonic index (Dubai, apartments, villas: ``ml.fct_price_index``)
and the monthly number of clean residential market sales, both in logs. The snapshot's
partial month is dropped, so the last actual is the last complete month.

**Models.**

1. Baselines: a random walk (next = last) and a seasonal naive (next = same month a year
   earlier). Both are reported; the better one per target is "the baseline".
2. SARIMAX with the Fed Funds rate lagged ``FORECAST_RATE_LAG`` months as the exogenous
   driver (the EIBOR proxy while EIBOR isn't loaded: the AED is pegged to the USD, docs/01).
   Index: ARIMA(p, 1, q), with or without a constant drift; volume: seasonal (p, 1, q)(P, 1, 1, 12).
   The order is chosen by AIC once, on data before the first backtest origin, and then held
   fixed. The published forecast uses the same order, so the backtest scores the model that
   is published.
3. LightGBM on lags is **not built** (docs/05 allows it as optional): ~190 monthly points
   are too few for trees to beat these, and making it honest (lags only, out-of-time
   tuning) isn't simple (docs/05 §8).

**Backtest: rolling origin over the last 24 complete months**, horizons 1 / 3 / 6 / 12.
A forecast made at the start of month O sees data dated before O only:

* **Index: the real-time vintage of month O**, not today's published series. The
  published index is re-fitted with later sales (each point comes from 36-month windows
  that also hold later months, and the last window is re-fitted as months arrive), so
  backtesting on it would hand every origin information it couldn't have had. Vintage O
  is the same rolling-window method re-chained on sales before O
  (``features.asof_index.realtime_index``, the 4b code; cached in
  ``artifacts/forecast/vintages.parquet``).
* **Scoring the index:** the forecast *change* from the vintage's last point is compared
  with the realised change in today's published series (the best estimate of what
  happened). Vintage levels aren't rebased, so only changes are comparable:
  APE = |exp(forecast change − actual change) − 1|.
* **Volume** isn't revised: the series is cut at O.
* **Rates:** future values are held flat at the origin's last known rate (with the lag,
  the first ``FORECAST_RATE_LAG`` months use rates already observed).

**Scenarios.** Rates flat / +100 bp / −100 bp as a step from the first forecast month.
Because the rate enters with a lag, the scenarios only diverge after month
``FORECAST_RATE_LAG``. 80% and 95% intervals are computed on the log scale and
exponentiated, so the point forecast (a median) always lies inside. They assume the model
is right; the backtest's coverage shows how far that holds.

Usage::

    uv run python -m dubai_property.models.forecast      # part of make train
    uv run python -m dubai_property.models.forecast --refresh-vintages
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import sys
import time
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import connectorx as cx
import numpy as np
import polars as pl

from dubai_property import config, db
from dubai_property.features import asof_index
from dubai_property.models import hedonic_index as h
from dubai_property.models.stress_test import last_complete_month

log = logging.getLogger(__name__)

FORECAST_TABLE = "forecast"
BACKTEST_TABLE = "forecast_backtest"
ARTIFACTS_NAME = "forecast"
SEGMENTS = ("dubai", "apartment", "villa")
TARGETS = ("index", "volume")
MODELS = ("naive_rw", "naive_seasonal", "sarimax")
SEASON = 12


def artifacts() -> Path:
    """``artifacts/forecast/`` (scratch DBs: under artifacts/scratch/)."""
    path = db.artifacts_dir() / ARTIFACTS_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


VOLUME_SQL = """
select date_trunc('month', t.txn_date)::date as month,
       t.property_type_key,
       count(*) as sales
from gold.fct_transaction as t
where t.is_clean_market_sale
  and t.is_in_report_scope
  and t.property_type_key in ({apt}, {villa})
  and t.txn_date >= date '{start}'
  and t.txn_date < date '{end}'
group by 1, 2
"""

INDEX_SQL = """
select segment_id, period_start as month, index_value::float8 as index_value
from {ml}.fct_price_index
where model_version = '{version}' and frequency = 'month' and not is_partial_period
  and segment_id in ('dubai', 'apartment', 'villa')
"""

RATES_SQL = "select month, fed_funds_rate::float8 as rate from gold.fct_rates_monthly"

FORECAST_DDL = f"""
create table if not exists {config.SCHEMA_ML}.{FORECAST_TABLE} (
    model_version text          not null,
    fitted_at     timestamptz   not null,
    target        text          not null,
    segment       text          not null,
    month         date          not null,
    scenario      text          not null,
    is_forecast   boolean       not null,
    actual        numeric(14, 4),
    forecast      numeric(14, 4),
    lower_80      numeric(14, 4),
    upper_80      numeric(14, 4),
    lower_95      numeric(14, 4),
    upper_95      numeric(14, 4),
    rate_path     numeric(8, 6),
    primary key (model_version, target, segment, month, scenario)
)
"""

FORECAST_COLUMNS = [
    "model_version", "fitted_at", "target", "segment", "month", "scenario", "is_forecast",
    "actual", "forecast", "lower_80", "upper_80", "lower_95", "upper_95", "rate_path",
]  # fmt: skip

BACKTEST_DDL = f"""
create table if not exists {config.SCHEMA_ML}.{BACKTEST_TABLE} (
    model_version text          not null,
    fitted_at     timestamptz   not null,
    target        text          not null,
    segment       text          not null,
    model         text          not null,
    horizon       integer       not null,
    n_origins     integer       not null,
    mape          numeric(10, 6),
    mdape         numeric(10, 6),
    coverage_80   numeric(8, 6),
    coverage_95   numeric(8, 6),
    is_baseline   boolean       not null,
    primary key (model_version, target, segment, model, horizon)
)
"""

BACKTEST_COLUMNS = [
    "model_version", "fitted_at", "target", "segment", "model", "horizon", "n_origins",
    "mape", "mdape", "coverage_80", "coverage_95", "is_baseline",
]  # fmt: skip


# --- Series helpers ------------------------------------------------------------------
@dataclass(frozen=True)
class Spec:
    """A SARIMAX specification (chosen by AIC before the first origin)."""

    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    trend: str
    aic: float | None = None

    def label(self) -> str:
        """'ARIMA(1,1,0) + drift' / 'SARIMA(0,1,1)(1,1,1,12)'."""
        o = ",".join(map(str, self.order))
        if self.seasonal_order[3]:
            s = ",".join(map(str, self.seasonal_order))
            return f"SARIMA({o})({s})"
        return f"ARIMA({o})" + (" + drift" if self.trend == "c" else "")


def months_between(start: date, end: date) -> list[date]:
    """Every first-of-month from ``start`` to ``end`` inclusive."""
    return h.period_grid(start, end, "month")


def lagged_rates(
    months: Sequence[date],
    rates: dict[date, float],
    last_known: date,
    shift: float = 0.0,
    lag: int = config.FORECAST_RATE_LAG,
) -> np.ndarray:
    """The exog column for ``months``: the rate ``lag`` months earlier.

    A rate dated after ``last_known`` isn't known at the forecast origin: it is replaced
    by the last known rate plus ``shift`` (the scenario's step). That is the only place a
    future rate can enter, so a backtest at origin O (``last_known`` = O−1) never reads one.
    """
    known = {m: v for m, v in rates.items() if m <= last_known and v is not None}
    if not known:
        raise ValueError("no rate known at the origin")
    last_rate = known[max(known)]
    out = []
    for m in months:
        src = h.add_months(m, -lag)
        if src <= last_known:
            # Rates are monthly from 2004; carry the latest earlier value over any gap.
            prior = [k for k in known if k <= src]
            out.append(known[max(prior)] if prior else last_rate)
        else:
            out.append(last_rate + shift)
    return np.asarray(out, dtype=float).reshape(-1, 1)


def fit_sarimax(y: np.ndarray, exog: np.ndarray, spec: Spec):
    """Fit one SARIMAX (warnings about convergence are expected on short series)."""
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            y,
            exog=exog,
            order=spec.order,
            seasonal_order=spec.seasonal_order,
            trend=spec.trend,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        return model.fit(disp=False, maxiter=200)


def candidate_specs(target: str) -> list[Spec]:
    """The small AIC grid per target."""
    if target == "index":
        return [
            Spec((p, 1, q), (0, 0, 0, 0), trend)
            # SARIMAX applies the trend after differencing: "c" is a constant drift in the
            # monthly change. "t" would be a drift growing linearly with time (an
            # accelerating forecast); the first full run used it by mistake (docs/05 §8).
            for p, q, trend in itertools.product((0, 1, 2), (0, 1), ("n", "c"))
        ]
    return [
        Spec((p, 1, q), (sp, 1, 1, SEASON), "n")
        for p, q, sp in itertools.product((0, 1), (0, 1), (0, 1))
    ]


def select_spec(target: str, y: np.ndarray, exog: np.ndarray) -> Spec:
    """Lowest-AIC specification on the pre-backtest history."""
    best: Spec | None = None
    for spec in candidate_specs(target):
        try:
            res = fit_sarimax(y, exog, spec)
        except (ValueError, np.linalg.LinAlgError):
            continue
        if not np.isfinite(res.aic):
            continue
        if best is None or res.aic < best.aic:
            best = Spec(spec.order, spec.seasonal_order, spec.trend, float(res.aic))
    if best is None:
        raise ValueError(f"no {target} specification could be fitted")
    return best


def forecast_paths(
    months: Sequence[date],
    y: np.ndarray,
    rates: dict[date, float],
    spec: Spec,
    steps: int = config.FORECAST_STEPS,
    shift: float = 0.0,
    lag: int = config.FORECAST_RATE_LAG,
) -> dict[str, dict[str, np.ndarray]]:
    """Every model's log forecast for the ``steps`` months after ``months[-1]``.

    Only ``y`` (dated ``months``) and rates up to ``months[-1]`` are used: this is the
    function the no-look-ahead test perturbs. SARIMAX also returns the 80% / 95% bounds.
    """
    last = months[-1]
    ahead = [h.add_months(last, k) for k in range(1, steps + 1)]
    out: dict[str, dict[str, np.ndarray]] = {
        "naive_rw": {"mean": np.full(steps, y[-1])},
        # The same month a year earlier; beyond 12 steps, the year before that repeats.
        "naive_seasonal": {"mean": np.array([y[-SEASON + (k % SEASON)] for k in range(steps)])},
    }
    exog_hist = lagged_rates(months, rates, last, lag=lag)
    exog_future = lagged_rates(ahead, rates, last, shift=shift, lag=lag)
    res = fit_sarimax(y, exog_hist, spec)
    fc = res.get_forecast(steps=steps, exog=exog_future)
    mean = np.asarray(fc.predicted_mean)
    paths = {"mean": mean}
    for level in config.FORECAST_INTERVALS:
        ci = np.asarray(fc.conf_int(alpha=1 - level))
        paths[f"lower_{round(level * 100)}"] = ci[:, 0]
        paths[f"upper_{round(level * 100)}"] = ci[:, 1]
    out["sarimax"] = paths
    return out


def rate_effect(res, rate_shift_bp: int = 100) -> dict:
    """The fitted rate coefficient and the level effect of a ``rate_shift_bp`` step."""
    names = list(res.model.param_names)
    if "x1" not in names:  # statsmodels names an unnamed exog column x1
        return {}
    i = names.index("x1")
    beta = float(np.asarray(res.params)[i])
    se = float(np.asarray(res.bse)[i])
    p = float(np.asarray(res.pvalues)[i])
    return {
        "beta": beta,
        "se": se,
        "p_value": p,
        "effect_per_100bp": math.exp(beta * rate_shift_bp / 10_000) - 1,
    }


def drift_annual(res) -> float | None:
    """The long-run monthly change implied by the drift, as an annual % (None without one).

    With AR terms the constant isn't the mean change: mean = intercept / (1 − Σ AR).
    """
    names = list(res.model.param_names)
    if "intercept" not in names:
        return None
    params = np.asarray(res.params)
    ar = sum(params[i] for i, n in enumerate(names) if n.startswith("ar.L"))
    return math.exp(12 * float(params[names.index("intercept")]) / (1 - ar)) - 1


# --- Backtest -------------------------------------------------------------------------
def backtest_origins(last_actual: date, n: int = config.FORECAST_ORIGINS) -> list[date]:
    """The last ``n`` origins: a forecast made at the start of O has data to O−1."""
    return [h.add_months(last_actual, -k) for k in range(n - 1, -1, -1)]


def score_origin(
    target: str,
    origin: date,
    hist_months: list[date],
    hist_y: np.ndarray,
    truth: dict[date, float],
    paths: dict[str, dict[str, np.ndarray]],
    horizons: Sequence[int] = config.FORECAST_HORIZONS,
) -> list[dict]:
    """APE per model × horizon for one origin (only targets that have happened).

    ``truth`` is today's series (published index, or volume) in logs. Index forecasts are
    scored as changes from the origin's last point (vintage levels aren't comparable with
    the published level); volume forecasts as levels.
    """
    last = hist_months[-1]
    rows = []
    for hz in horizons:
        tm = h.add_months(last, hz)
        if tm not in truth or (target == "index" and last not in truth):
            continue
        if target == "index":
            actual = truth[tm] - truth[last]
            anchor = hist_y[-1]
        else:
            actual, anchor = truth[tm], 0.0
        for model, p in paths.items():
            pred = p["mean"][hz - 1] - anchor
            row = {
                "target": target,
                "origin": origin,
                "horizon": hz,
                "target_month": tm,
                "model": model,
                "pred_log": float(pred),
                "actual_log": float(actual),
                "ape": abs(math.exp(pred - actual) - 1),
                "covered_80": None,
                "covered_95": None,
            }
            for level in (80, 95):
                if f"lower_{level}" in p:
                    lo = p[f"lower_{level}"][hz - 1] - anchor
                    hi = p[f"upper_{level}"][hz - 1] - anchor
                    row[f"covered_{level}"] = bool(lo <= actual <= hi)
            rows.append(row)
    return rows


def summarise_backtest(rows: pl.DataFrame) -> pl.DataFrame:
    """MAPE, MdAPE and interval coverage per target × segment × model × horizon.

    The better naive model (lower mean MAPE over the horizons) is marked ``is_baseline``.
    """
    s = (
        rows.group_by("target", "segment", "model", "horizon")
        .agg(
            n_origins=pl.len(),
            mape=pl.col("ape").mean(),
            mdape=pl.col("ape").median(),
            coverage_80=pl.col("covered_80").cast(pl.Float64).mean(),
            coverage_95=pl.col("covered_95").cast(pl.Float64).mean(),
        )
        .sort("target", "segment", "model", "horizon")
    )
    best = (
        s.filter(pl.col("model").str.starts_with("naive"))
        .group_by("target", "segment", "model")
        .agg(pl.col("mape").mean())
        .sort("mape")
        .group_by("target", "segment", maintain_order=True)
        .first()
        .select("target", "segment", baseline=pl.col("model"))
    )
    return (
        s.join(best, on=["target", "segment"], how="left")
        .with_columns(is_baseline=(pl.col("model") == pl.col("baseline")).fill_null(False))
        .drop("baseline")
    )


# --- Data -----------------------------------------------------------------------------
def load_snapshot() -> date:
    """Data snapshot date (latest transaction date)."""
    with db.connect() as conn:
        (snap,) = conn.execute("select data_snapshot_date from silver.int_data_snapshot").fetchone()
    return snap


def load_index(last_actual: date) -> dict[str, dict[date, float]]:
    """Published monthly log index per headline segment, to the last complete month."""
    sql = INDEX_SQL.format(ml=config.SCHEMA_ML, version=config.HEDONIC_MODEL_VERSION)
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars").with_columns(
        pl.col("month").cast(pl.Date)
    )
    out: dict[str, dict[date, float]] = {}
    for (seg,), g in df.filter(pl.col("month") <= last_actual).group_by(["segment_id"]):
        out[seg] = {m: math.log(v) for m, v in g.select("month", "index_value").iter_rows()}
    return out


def load_volume(last_actual: date) -> dict[str, dict[date, float]]:
    """Monthly clean residential market sales (Dubai, apartments, villas), raw counts."""
    sql = VOLUME_SQL.format(
        apt=h.APARTMENT,
        villa=h.VILLA,
        start=config.HEDONIC_START.isoformat(),
        end=h.add_months(last_actual, 1).isoformat(),
    )
    df = cx.read_sql(db.connectorx_uri(), sql, return_type="polars").with_columns(
        pl.col("month").cast(pl.Date)
    )
    out: dict[str, dict[date, float]] = {"dubai": {}, "apartment": {}, "villa": {}}
    for m, key, n in df.iter_rows():
        seg = h.TYPE_NAMES[key]
        out[seg][m] = float(n)
        out["dubai"][m] = out["dubai"].get(m, 0.0) + float(n)
    return out


def load_rates() -> dict[date, float]:
    """Fed Funds by month (decimal); months without a value are skipped."""
    df = cx.read_sql(db.connectorx_uri(), RATES_SQL, return_type="polars")
    return {
        m: float(v)
        for m, v in df.with_columns(pl.col("month").cast(pl.Date)).iter_rows()
        if v is not None
    }


def complete_run(series: dict[date, float], start: date, end: date) -> bool:
    """True if every month from ``start`` to ``end`` has a value."""
    return all(m in series for m in months_between(start, end))


def vintages(origins: list[date], snapshot: date, refresh: bool = False) -> pl.DataFrame:
    """Real-time index vintages (full chains) for the headline segments, cached.

    The cache is reused only for the same snapshot, origins and index model version.
    """
    path, meta_path = artifacts() / "vintages.parquet", artifacts() / "vintages.json"
    meta = {
        "snapshot": snapshot.isoformat(),
        "origins": [o.isoformat() for o in origins],
        "hedonic_model_version": config.HEDONIC_MODEL_VERSION,
        "segments": list(SEGMENTS),
    }
    if not refresh and path.exists() and meta_path.exists():
        if json.loads(meta_path.read_text()) == meta:
            log.info("index vintages: reusing %s", path.relative_to(config.PROJECT_ROOT))
            return pl.read_parquet(path)
    t0 = time.perf_counter()
    population = h.load_population()
    frames = []
    for segment in h.segments_for(population)[:3]:
        frame, _ = asof_index.realtime_index(segment, population, origins, keep_periods=None)
        frames.append(frame)
        log.info("%s: %d vintage rows", segment.segment_id, frame.height)
    out = pl.concat(frames) if frames else pl.DataFrame(schema=asof_index.VINTAGE_SCHEMA)
    out.write_parquet(path)
    meta_path.write_text(json.dumps(meta, indent=1))
    log.info("index vintages: %d rows in %.0fs", out.height, time.perf_counter() - t0)
    return out


# --- Orchestration ------------------------------------------------------------------
def origin_history(
    target: str,
    segment: str,
    origin: date,
    series: dict[date, float],
    vint: pl.DataFrame,
) -> tuple[list[date], np.ndarray] | None:
    """What a forecaster at the start of ``origin`` knew: months < origin, in logs.

    ``series`` is already in logs (today's published log index, or log volume); for the
    index it is only used by the caller for scoring, the history comes from the vintage.
    """
    last = h.add_months(origin, -1)
    if target == "index":
        v = vint.filter((pl.col("segment_id") == segment) & (pl.col("vintage") == origin)).sort(
            "period"
        )
        if v.is_empty() or v["period"].max() != last:
            return None
        months, y = v["period"].to_list(), v["log_index"].to_numpy()
    else:
        months = sorted(m for m in series if m < origin)
        y = np.array([series[m] for m in months])
    if (
        not months
        or months[0] > config.HEDONIC_START
        or not complete_run(dict.fromkeys(months, 0.0), months[0], last)
    ):
        return None
    return months, y


def run(refresh_vintages: bool = False) -> dict:
    """Backtest, fit and write ``ml.forecast`` / ``ml.forecast_backtest``."""
    t0 = time.perf_counter()
    snapshot = load_snapshot()
    last_actual = last_complete_month(snapshot)
    origins = backtest_origins(last_actual)
    fitted_at = datetime.now().astimezone()
    rates = load_rates()
    index = load_index(last_actual)
    volume_raw = load_volume(last_actual)
    volume = {s: {m: math.log(v) for m, v in d.items()} for s, d in volume_raw.items()}
    log.info("last complete month %s; origins %s to %s", last_actual, origins[0], origins[-1])

    have_index = all(
        s in index and complete_run(index[s], config.HEDONIC_START, last_actual) for s in SEGMENTS
    )
    vint = vintages(origins, snapshot, refresh_vintages) if have_index else None
    diag: dict = {
        "model_version": config.FORECAST_MODEL_VERSION,
        "fitted_at": fitted_at,
        "snapshot": snapshot,
        "last_actual": last_actual,
        "origins": [origins[0], origins[-1], len(origins)],
        "rate_lag": config.FORECAST_RATE_LAG,
        "last_rate": rates[max(m for m in rates if m <= last_actual)] if rates else None,
        "series": {},
        "skipped": [],
    }
    bt_rows: list[dict] = []
    fc_rows: list[dict] = []
    for target in TARGETS:
        for seg in SEGMENTS:
            truth = index.get(seg, {}) if target == "index" else volume.get(seg, {})
            levels = index.get(seg, {}) if target == "index" else volume_raw.get(seg, {})
            key = f"{target}:{seg}"
            # Volume months need min-n sales (a log of a handful of sales is noise).
            if target == "volume" and (
                not levels
                or min(levels.values()) < config.MIN_N
                or not complete_run(levels, config.HEDONIC_START, last_actual)
            ):
                diag["skipped"].append({"series": key, "reason": "months under min-n or missing"})
                continue
            if target == "index" and vint is None:
                diag["skipped"].append({"series": key, "reason": "headline index not published"})
                continue
            first = origin_history(
                target, seg, origins[0], truth, vint if vint is not None else pl.DataFrame()
            )
            if first is None or len(first[0]) < config.FORECAST_MIN_MONTHS:
                diag["skipped"].append({"series": key, "reason": "too little history"})
                continue
            t1 = time.perf_counter()
            spec = select_spec(target, first[1], lagged_rates(first[0], rates, first[0][-1]))
            n_scored = 0
            for origin in origins:
                hist = origin_history(target, seg, origin, truth, vint)
                if hist is None:
                    continue
                paths = forecast_paths(hist[0], hist[1], rates, spec)
                rows = score_origin(target, origin, hist[0], hist[1], truth, paths)
                for r in rows:
                    r["segment"] = seg
                bt_rows += rows
                n_scored += 1
            # Published forecast: the same specification on today's series.
            months = sorted(truth)
            y = np.array([truth[m] for m in months])
            res = fit_sarimax(y, lagged_rates(months, rates, last_actual), spec)
            info = {
                "spec": spec.label(),
                "aic_pre_backtest": spec.aic,
                "origins_scored": n_scored,
                "history_months": len(months),
                "rate": rate_effect(res),
                "drift_annual": drift_annual(res),
                "seconds": time.perf_counter() - t1,
            }
            for scenario, bp in config.FORECAST_RATE_SCENARIOS.items():
                shift = bp / 10_000
                paths = forecast_paths(months, y, rates, spec, shift=shift)["sarimax"]
                ahead = [h.add_months(last_actual, k) for k in range(1, config.FORECAST_STEPS + 1)]
                path_rates = lagged_rates(ahead, rates, last_actual, shift=shift).ravel()
                for k, m in enumerate(ahead):
                    fc_rows.append(
                        {
                            "target": target,
                            "segment": seg,
                            "month": m,
                            "scenario": scenario,
                            "is_forecast": True,
                            "actual": None,
                            "forecast": math.exp(paths["mean"][k]),
                            "lower_80": math.exp(paths["lower_80"][k]),
                            "upper_80": math.exp(paths["upper_80"][k]),
                            "lower_95": math.exp(paths["lower_95"][k]),
                            "upper_95": math.exp(paths["upper_95"][k]),
                            "rate_path": path_rates[k],
                        }
                    )
                info[f"{scenario}_12m"] = math.exp(paths["mean"][-1] - y[-1]) - 1
            for m in months:
                fc_rows.append(
                    {
                        "target": target,
                        "segment": seg,
                        "month": m,
                        "scenario": "actual",
                        "is_forecast": False,
                        "actual": levels[m] if target == "volume" else math.exp(truth[m]),
                    }
                )
            diag["series"][key] = info
            log.info(
                "%s: %s, %d origins scored, rate beta %+.3f (p %.2f), flat 12m %+.1f%%",
                key,
                spec.label(),
                n_scored,
                info["rate"].get("beta", float("nan")),
                info["rate"].get("p_value", float("nan")),
                100 * info["rates_flat_12m"],
            )

    bt = pl.DataFrame(
        bt_rows,
        schema={
            "target": pl.Utf8,
            "origin": pl.Date,
            "horizon": pl.Int32,
            "target_month": pl.Date,
            "model": pl.Utf8,
            "pred_log": pl.Float64,
            "actual_log": pl.Float64,
            "ape": pl.Float64,
            "covered_80": pl.Boolean,
            "covered_95": pl.Boolean,
            "segment": pl.Utf8,
        },  # fmt: skip
    )
    bt.write_parquet(artifacts() / "backtest.parquet")
    summary = summarise_backtest(bt) if bt.height else pl.DataFrame()
    stamp = {
        "model_version": pl.lit(config.FORECAST_MODEL_VERSION),
        "fitted_at": pl.lit(fitted_at.isoformat()),
    }
    if summary.height:
        bt_out = summary.with_columns(**stamp).select(BACKTEST_COLUMNS)
    else:
        bt_out = pl.DataFrame(schema=dict.fromkeys(BACKTEST_COLUMNS, pl.Utf8))
    fc_schema = {
        "target": pl.Utf8, "segment": pl.Utf8, "month": pl.Date, "scenario": pl.Utf8,
        "is_forecast": pl.Boolean, "actual": pl.Float64, "forecast": pl.Float64,
        "lower_80": pl.Float64, "upper_80": pl.Float64, "lower_95": pl.Float64,
        "upper_95": pl.Float64, "rate_path": pl.Float64,
    }  # fmt: skip
    fc = pl.DataFrame(fc_rows, schema=fc_schema).with_columns(
        pl.col("actual", "forecast", "lower_80", "upper_80", "lower_95", "upper_95").round(4),
        pl.col("rate_path").round(6),
        **stamp,
    )
    fc = fc.select(FORECAST_COLUMNS)
    with db.connect() as conn:
        n_fc = write_table(conn, FORECAST_DDL, FORECAST_TABLE, fc)
        n_bt = write_table(conn, BACKTEST_DDL, BACKTEST_TABLE, bt_out)
        conn.commit()
    log.info(
        "%s.%s: %d rows, %s.%s: %d rows in %.0fs",
        config.SCHEMA_ML,
        FORECAST_TABLE,
        n_fc,
        config.SCHEMA_ML,
        BACKTEST_TABLE,
        n_bt,
        time.perf_counter() - t0,
    )
    diag["rows_written"] = {"forecast": n_fc, "backtest": n_bt}
    diag["seconds"] = time.perf_counter() - t0
    (artifacts() / "diagnostics.json").write_text(json.dumps(diag, default=str, indent=1))
    return diag


def write_table(conn, ddl: str, table: str, frame: pl.DataFrame) -> int:
    """Replace this model version's rows in ``ml.<table>`` (caller commits)."""
    conn.execute(ddl)
    conn.execute(
        f"delete from {config.SCHEMA_ML}.{table} where model_version = %s",
        [config.FORECAST_MODEL_VERSION],
    )
    n = db.copy_frame(conn, frame, config.SCHEMA_ML, table)
    conn.execute(f"analyze {config.SCHEMA_ML}.{table}")
    return n


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make train``)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--refresh-vintages", action="store_true", help="recompute the cached index vintages"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(refresh_vintages=args.refresh_vintages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
