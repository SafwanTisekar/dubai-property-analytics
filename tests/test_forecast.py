"""Forecast: no look-ahead in the backtest, interval sanity, scenarios, scoring (CI + DB).

The look-ahead proof is behavioural, as for the AVM: what a forecaster at origin O
produces must not change when anything dated O or later is rewritten (the series and the
rates), and must change when something before O does (power check).
"""

import math
from datetime import date

import numpy as np
import polars as pl
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.features import asof_index
from dubai_property.models import forecast as fc
from dubai_property.models import hedonic_index as h

START, LAST = date(2011, 1, 1), date(2026, 8, 1)
MONTHS = fc.months_between(START, LAST)
SPEC = fc.Spec((1, 1, 0), (0, 0, 0, 0), "c")


def synthetic_log_series(seed: int = 5, seasonal: float = 0.0) -> dict[date, float]:
    rng = np.random.default_rng(seed)
    y, out = 4.5, {}
    for i, m in enumerate(MONTHS):
        y += 0.004 + rng.normal(0, 0.01)
        out[m] = y + seasonal * math.sin(2 * math.pi * m.month / 12) + 0 * i
    return out


def synthetic_rates() -> dict[date, float]:
    months = fc.months_between(date(2004, 1, 1), LAST)
    return {m: 0.01 + 0.04 * (0.5 + 0.5 * math.sin(i / 20)) for i, m in enumerate(months)}


def history(series: dict[date, float], origin: date) -> tuple[list[date], np.ndarray]:
    months = [m for m in sorted(series) if m < origin]
    return months, np.array([series[m] for m in months])


@pytest.fixture(scope="module")
def series():
    return synthetic_log_series()


@pytest.fixture(scope="module")
def rates():
    return synthetic_rates()


# --- Rates: the only door a future value could come through ---------------------------------
def test_lagged_rates_use_the_rate_lag_months_earlier(rates):
    m = date(2020, 7, 1)
    out = fc.lagged_rates([m], rates, last_known=LAST, lag=6)
    assert out[0, 0] == pytest.approx(rates[date(2020, 1, 1)])


def test_lagged_rates_never_read_a_rate_after_the_origin(rates):
    origin_last = date(2025, 6, 1)
    ahead = [h.add_months(origin_last, k) for k in range(1, 13)]
    poisoned = {**rates, **{m: 9.99 for m in rates if m > origin_last}}
    a = fc.lagged_rates(ahead, rates, origin_last, shift=0.01)
    b = fc.lagged_rates(ahead, poisoned, origin_last, shift=0.01)
    np.testing.assert_array_equal(a, b)
    # Beyond the lag the scenario path is the last known rate plus the step.
    assert a[-1, 0] == pytest.approx(rates[origin_last] + 0.01)
    # Within the lag the rate is one already observed.
    assert a[0, 0] == pytest.approx(rates[h.add_months(ahead[0], -config.FORECAST_RATE_LAG)])


# --- No look-ahead in the backtest ------------------------------------------------------
@pytest.mark.parametrize("origin", [date(2024, 9, 1), date(2026, 1, 1)])
def test_forecast_at_origin_ignores_everything_from_the_origin_on(series, rates, origin):
    months, y = history(series, origin)
    base = fc.forecast_paths(months, y, rates, SPEC)
    # Rewrite the future: the series from the origin on and every later rate.
    future_series = {m: (v + 0.5 if m >= origin else v) for m, v in series.items()}
    future_rates = {m: (r + 0.03 if m >= origin else r) for m, r in rates.items()}
    m2, y2 = history(future_series, origin)
    other = fc.forecast_paths(m2, y2, future_rates, SPEC)
    for model in base:
        for key, values in base[model].items():
            np.testing.assert_allclose(values, other[model][key], atol=1e-10, err_msg=key)


def test_power_check_forecast_moves_when_the_past_changes(series, rates):
    origin = date(2026, 1, 1)
    months, y = history(series, origin)
    base = fc.forecast_paths(months, y, rates, SPEC)["sarimax"]["mean"]
    y_changed = y.copy()
    y_changed[-1] += 0.05  # the month before the origin
    moved = fc.forecast_paths(months, y_changed, rates, SPEC)["sarimax"]["mean"]
    assert np.abs(moved - base).max() > 0.01


def test_volume_history_is_cut_at_the_origin():
    series = {m: math.log(i + 1) for i, m in enumerate(MONTHS)}  # log volume, as run() passes
    origin = date(2025, 3, 1)
    months, y = fc.origin_history("volume", "dubai", origin, series, pl.DataFrame())
    assert months[-1] == date(2025, 2, 1)
    # Taken as given (already logs): logging it again was a bug in the first full run.
    assert y[-1] == pytest.approx(series[date(2025, 2, 1)])
    assert len(y) == len(months) == MONTHS.index(date(2025, 2, 1)) + 1


def test_index_history_is_the_vintage_of_the_origin_not_the_published_series():
    origin = date(2025, 3, 1)
    rows = []
    for vintage, shift in ((origin, 0.0), (h.add_months(origin, 1), 9.0)):
        for m in fc.months_between(START, h.add_months(vintage, -1)):
            rows.append({"segment_id": "dubai", "vintage": vintage, "period": m,
                         "log_index": 1.0 + shift, "n_obs": 50})  # fmt: skip
    vint = pl.DataFrame(rows, schema=asof_index.VINTAGE_SCHEMA)
    published = {m: 99.0 for m in MONTHS}
    months, y = fc.origin_history("index", "dubai", origin, published, vint)
    assert months[-1] == date(2025, 2, 1) and (y == 1.0).all()
    # A vintage whose chain doesn't reach O-1 is not used.
    short = vint.filter(pl.col("period") < date(2025, 2, 1))
    assert fc.origin_history("index", "dubai", origin, published, short) is None


def test_vintages_keep_the_whole_chain_and_agree_with_the_avm_default():
    from test_avm_features import START as SYN_START
    from test_avm_features import synthetic_population

    population = synthetic_population()
    segment = h.Segment("apartment", "type", 101, None, start=SYN_START)
    vintages = [date(2020, 1, 1), date(2020, 4, 1)]
    full, _ = asof_index.realtime_index(segment, population, vintages, keep_periods=None)
    short, _ = asof_index.realtime_index(segment, population, vintages)
    for v in vintages:
        f = full.filter(pl.col("vintage") == v).sort("period")
        s = short.filter(pl.col("vintage") == v).sort("period")
        assert f["period"].min() == SYN_START and f["period"].max() == h.add_months(v, -1)
        assert s.height == asof_index.KEEP_PERIODS
        np.testing.assert_allclose(
            f.tail(asof_index.KEEP_PERIODS)["log_index"].to_numpy(), s["log_index"].to_numpy()
        )


# --- Intervals and scenarios ---------------------------------------------------------------
def test_intervals_contain_the_point_forecast(series, rates):
    months, y = history(series, date(2026, 9, 1))
    p = fc.forecast_paths(months, y, rates, SPEC)["sarimax"]
    assert (p["lower_95"] <= p["lower_80"]).all() and (p["lower_80"] <= p["mean"]).all()
    assert (p["mean"] <= p["upper_80"]).all() and (p["upper_80"] <= p["upper_95"]).all()
    widths = p["upper_95"] - p["lower_95"]
    assert widths[-1] > widths[0]  # uncertainty grows with the horizon


def test_rate_scenarios_only_diverge_after_the_lag(series, rates):
    months, y = history(series, date(2026, 9, 1))
    flat = fc.forecast_paths(months, y, rates, SPEC, shift=0.0)["sarimax"]["mean"]
    up = fc.forecast_paths(months, y, rates, SPEC, shift=0.01)["sarimax"]["mean"]
    lag = config.FORECAST_RATE_LAG
    np.testing.assert_allclose(flat[:lag], up[:lag], atol=1e-12)
    assert np.abs(up[lag:] - flat[lag:]).max() > 0


def test_naive_baselines():
    months = MONTHS[-30:]
    y = np.arange(len(months), dtype=float)
    paths = fc.forecast_paths(months, y, synthetic_rates(), SPEC)
    assert (paths["naive_rw"]["mean"] == y[-1]).all()
    # Seasonal naive: month t+k is the same month a year earlier.
    np.testing.assert_array_equal(paths["naive_seasonal"]["mean"], y[-12:])


# --- Scoring -------------------------------------------------------------------------------
def test_scoring_skips_targets_that_have_not_happened():
    last = date(2026, 6, 1)
    hist_months = fc.months_between(START, last)
    truth = {m: 1.0 for m in fc.months_between(START, date(2026, 9, 1))}
    paths = {"naive_rw": {"mean": np.full(12, 1.0)}}
    rows = fc.score_origin("volume", h.add_months(last, 1), hist_months, np.ones(len(hist_months)),
                           truth, paths, horizons=(1, 3, 6))  # fmt: skip
    assert sorted(r["horizon"] for r in rows) == [1, 3]


def test_index_scoring_compares_changes_so_vintage_levels_do_not_matter():
    last = date(2026, 1, 1)
    hist_months = fc.months_between(START, last)
    truth = {last: math.log(150.0), h.add_months(last, 1): math.log(153.0)}
    out = []
    for level in (0.0, 7.0):  # the vintage chain at any level
        hist_y = np.full(len(hist_months), level)
        paths = {"m": {"mean": np.full(12, level + math.log(1.01))}}
        out.append(fc.score_origin("index", h.add_months(last, 1), hist_months, hist_y, truth,
                                   paths, horizons=(1,))[0]["ape"])  # fmt: skip
    assert out[0] == pytest.approx(out[1])
    assert out[0] == pytest.approx(abs(1.01 / 1.02 - 1))


def test_summary_marks_the_better_naive_model_as_the_baseline():
    rows = pl.DataFrame(
        {
            "target": ["index"] * 3,
            "segment": ["dubai"] * 3,
            "model": ["naive_rw", "naive_seasonal", "sarimax"],
            "horizon": [1, 1, 1],
            "ape": [0.02, 0.05, 0.01],
            "covered_80": [None, None, True],
            "covered_95": [None, None, True],
        }
    )
    s = fc.summarise_backtest(rows)
    assert s.filter(pl.col("is_baseline"))["model"].to_list() == ["naive_rw"]
    assert s.filter(pl.col("model") == "sarimax")["coverage_80"].to_list() == [1.0]


def test_origins_are_the_last_24_complete_months():
    o = fc.backtest_origins(LAST)
    assert len(o) == config.FORECAST_ORIGINS and o[-1] == LAST
    assert o[0] == h.add_months(LAST, -(config.FORECAST_ORIGINS - 1))


# --- Written tables (skipped until make train has run) -------------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        if c.execute("select to_regclass('ml.forecast')").fetchone()[0] is None:
            pytest.skip("ml.forecast not built yet (run make train)")
        yield c


@pytest.mark.db
def test_written_forecast_intervals_contain_the_point(conn):
    (bad,) = conn.execute(
        """
        select count(*) from ml.forecast
        where model_version = %s and is_forecast
          and not (lower_95 <= lower_80 and lower_80 <= forecast and forecast <= upper_80
                   and upper_80 <= upper_95)
        """,
        [config.FORECAST_MODEL_VERSION],
    ).fetchone()
    assert bad == 0


@pytest.mark.db
def test_written_forecast_starts_after_the_last_actual(conn):
    rows = conn.execute(
        """
        select target, segment, max(month) filter (where not is_forecast),
               min(month) filter (where is_forecast), count(*) filter (where is_forecast)
        from ml.forecast where model_version = %s group by 1, 2
        """,
        [config.FORECAST_MODEL_VERSION],
    ).fetchall()
    for _target, _segment, last_actual, first_fc, n_fc in rows:
        assert first_fc == h.add_months(last_actual, 1)
        assert n_fc == config.FORECAST_STEPS * len(config.FORECAST_RATE_SCENARIOS)


def test_volume_path_end_to_end_scores_a_perfect_naive_forecast_as_zero(rates):
    """History -> forecast -> score on log volumes: a constant series is forecast exactly by
    the naive model. Guards the double-log bug of the first full run (APE ~ 99.9%)."""
    series = {m: math.log(1_000.0) for m in MONTHS}
    origin = date(2025, 9, 1)
    months, y = fc.origin_history("volume", "dubai", origin, series, pl.DataFrame())
    paths = fc.forecast_paths(months, y, rates, fc.Spec((0, 1, 1), (0, 1, 1, 12), "n"))
    rows = fc.score_origin("volume", origin, months, y, series, paths)
    naive = [r for r in rows if r["model"] == "naive_rw"]
    assert naive and all(r["ape"] == pytest.approx(0) for r in naive)
    assert all(r["ape"] < 0.05 for r in rows)


def test_drift_is_a_constant_monthly_change_not_an_accelerating_trend(rates):
    """The index grid uses SARIMAX trend "c" (a constant drift after differencing); "t" made
    the drift grow with time and the first full run forecast +8.8% instead of ~+5%."""
    assert {s.trend for s in fc.candidate_specs("index")} == {"n", "c"}
    rng = np.random.default_rng(1)
    y = np.cumsum(0.004 + rng.normal(0, 0.002, len(MONTHS)))
    mean = fc.forecast_paths(MONTHS, y, rates, SPEC, steps=24)["sarimax"]["mean"]
    steps = np.diff(mean)
    assert steps[-1] == pytest.approx(steps[-12], abs=2e-4)  # constant, not growing
    assert steps[-1] == pytest.approx(0.004, abs=0.0015)
    res = fc.fit_sarimax(y, fc.lagged_rates(MONTHS, rates, MONTHS[-1]), SPEC)
    assert fc.drift_annual(res) == pytest.approx(math.exp(12 * 0.004) - 1, abs=0.02)
