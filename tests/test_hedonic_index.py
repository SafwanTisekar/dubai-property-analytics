"""Hedonic price index: the method on synthetic data (CI), and the published table (DB).

The synthetic market has a known price path and a mix shift (more cheap small off-plan
units over time), so the tests can check that the time-dummy regression recovers the
path while a raw median doesn't, that rolling windows survive a drifting off-plan premium,
and that the publishing rules (base = 100, min-n, frequency fallback) hold.
"""

import math
from datetime import date

import numpy as np
import polars as pl
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.models import hedonic_index as h

START, END = date(2016, 1, 1), date(2021, 12, 1)
BASE = config.INDEX_BASE_MONTH


def true_log_index(t: np.ndarray) -> np.ndarray:
    """Known market path by month number: a rise, a dip and a recovery."""
    return 0.012 * t - 0.25 * np.clip((t - 30) / 12, 0, 1) + 0.2 * np.clip((t - 48) / 12, 0, 1)


def synthetic_sales(
    per_month: int = 150,
    offplan_premium=lambda t: 0.2 + 0 * t,
    months: list[date] | None = None,
    seed: int = 7,
) -> pl.DataFrame:
    """Sales with area, bedroom, size and off-plan effects and a mix shift over time."""
    rng = np.random.default_rng(seed)
    months = months or h.period_grid(START, END, "month")
    rows = []
    for t, m in enumerate(months):
        n = per_month if isinstance(per_month, int) else per_month(t)
        share_offplan = 0.1 + 0.6 * t / len(months)  # mix shift towards off-plan ...
        offplan = rng.random(n) < share_offplan
        bedrooms = np.where(offplan, rng.integers(0, 2, n), rng.integers(0, 4, n))  # ... small
        area_key = rng.integers(1, 6, n)
        ln_area = np.log(40 + 35 * bedrooms + rng.normal(0, 5, n).clip(-10, 10))
        y = (
            9.0
            + true_log_index(np.array([t]))[0]
            + 0.15 * area_key
            + 0.05 * bedrooms
            - 0.25 * ln_area
            + offplan_premium(t) * offplan
            - 0.3 * offplan  # off-plan stock sits in cheaper locations within an area
            + rng.normal(0, 0.02, n)  # small noise: the tests check bias, not luck
        )
        for i in range(n):
            rows.append(
                {
                    "month": m,
                    "area_key": int(area_key[i]),
                    "zone": "Zone A",
                    "property_type_key": h.APARTMENT,
                    "bedrooms": int(bedrooms[i]),
                    "ln_area": float(ln_area[i]),
                    "is_offplan": bool(offplan[i]),
                    "has_parking": True,
                    "is_penthouse": False,
                    "ln_ppsqm": float(y[i]),
                }
            )
    return pl.DataFrame(rows)


def truth(months: list[date]) -> dict[date, float]:
    path = true_log_index(np.arange(len(months)))
    base = path[months.index(BASE)]
    return {m: 100 * math.exp(v - base) for m, v in zip(months, path, strict=True)}


SEGMENT = h.Segment("apartment", "type", h.APARTMENT, None, START)


@pytest.fixture(scope="module")
def sales():
    return synthetic_sales()


def test_time_dummy_recovers_the_path_where_the_median_does_not(sales):
    fit = h.fit_pooled(SEGMENT, sales, "month")
    months = h.period_grid(START, END, "month")
    expected = truth(months)
    index = {p: 100 * math.exp(b) for p, b in fit.effects.items()}
    assert index[BASE] == 100
    assert max(abs(index[m] / expected[m] - 1) for m in months) < 0.01
    # The raw median, rebased the same way, is pulled down by the shift to off-plan.
    med = sales.group_by("month").agg(pl.col("ln_ppsqm").median()).sort("month")
    med = dict(zip(med["month"], med["ln_ppsqm"], strict=True))
    raw = {m: 100 * math.exp(med[m] - med[BASE]) for m in months}
    assert max(abs(raw[m] / expected[m] - 1) for m in months) > 0.05


def test_rolling_windows_recover_the_path(sales):
    effects, windows = h.rolling_window_index(SEGMENT, sales, END, "month")
    months = h.period_grid(START, END, "month")
    expected = truth(months)
    assert effects[BASE] == 0
    assert len(windows) >= 3 and all(w["linked_on"] >= 12 for w in windows[1:])
    assert max(abs(100 * math.exp(effects[m]) / expected[m] - 1) for m in months) < 0.015


def test_rolling_windows_handle_a_drifting_offplan_premium():
    """The off-plan premium rises from 0 to 0.4: one pooled fit misreads it as price change."""
    months = h.period_grid(START, END, "month")
    sales = synthetic_sales(offplan_premium=lambda t: 0.4 * t / len(months))
    expected = truth(months)
    pooled = h.fit_pooled(SEGMENT, sales, "month").effects
    rtd, _ = h.rolling_window_index(SEGMENT, sales, END, "month")

    def worst(effects):
        return max(abs(100 * math.exp(effects[m]) / expected[m] - 1) for m in months)

    assert worst(rtd) < worst(pooled)


def test_index_series_publishes_only_periods_with_min_n():
    effects = {date(2019, 1, 1): 0.0, date(2019, 2, 1): 0.1, date(2019, 3, 1): 0.2}
    counts = {date(2019, 1, 1): 25, date(2019, 2, 1): 19, date(2019, 3, 1): 20}
    s = h.index_series(effects, counts, date(2019, 1, 1), date(2019, 4, 1), "month")
    assert s["index_value"].to_list()[0] == 100
    assert s["index_value"].is_null().to_list() == [False, True, False, True]


def test_frequency_falls_back_to_quarterly_then_drops():
    months = h.period_grid(START, END, "month")
    dense = h.choose_frequency(synthetic_sales(per_month=30), START, END)
    assert (dense.frequency, dense.start) == ("month", START)
    # 10 a month: no month passes, every quarter does.
    sparse = h.choose_frequency(synthetic_sales(per_month=10), START, END)
    assert sparse.frequency == "quarter"
    # 2 a month: nothing passes.
    thin = h.choose_frequency(synthetic_sales(per_month=2), START, END)
    assert thin.frequency is None and thin.reason.startswith("not published")
    # A segment that starts trading in 2018 is judged from its first period with min-n.
    late = synthetic_sales(per_month=30, months=[m for m in months if m >= date(2018, 1, 1)])
    assert h.choose_frequency(late, START, END).start == date(2018, 1, 1)
    # The base month under min-n while the rest is dense: quarterly instead.
    no_base = synthetic_sales(per_month=lambda t: 10 if months[t] == BASE else 30)
    assert h.choose_frequency(no_base, START, END).frequency == "quarter"


def test_noise_gate_measures_consecutive_published_changes():
    months = h.period_grid(date(2019, 1, 1), date(2019, 6, 1), "month")
    calm = pl.DataFrame({"period": months, "index_value": [100.0, 101, 102, None, 103, 104]})
    jumpy = pl.DataFrame({"period": months, "index_value": [100.0, 150, 90, 160, 80, 170]})
    assert h.period_change_sd(calm) < 0.01  # the gap is skipped, not bridged
    assert h.period_change_sd(jumpy) > config.NOISE_MAX_SD


def test_metrics_yoy_drawdown_and_running_peak():
    months = h.period_grid(date(2018, 1, 1), date(2020, 12, 1), "month")
    values = [100 * 1.01**i for i in range(24)] + [100 * 1.01**23 * 0.98**i for i in range(12)]
    values[5] = None  # an unpublished month
    s = pl.DataFrame(
        {"period": months, "index_value": values}, schema_overrides={"index_value": pl.Float64}
    )
    out, episodes = h.add_metrics(s, "month")
    assert out["yoy"][12] == pytest.approx(1.01**12 - 1)
    assert out["mom"][5] is None and out["mom"][6] is None and out["yoy"][17] is None
    assert out["index_3m"][2] == pytest.approx(sum(values[:3]) / 3)
    assert (out["drawdown"].drop_nulls() <= 1e-12).all()
    peak, idx = out["running_peak"].to_list(), out["index_value"].to_list()
    assert all(p >= v for p, v in zip(peak, idx, strict=True) if v is not None)
    assert len(episodes) == 1 and episodes[0].recovery_period is None
    assert episodes[0].depth == pytest.approx(0.98**11 - 1)
    # The flat step at month 24 equals the peak, so the episode starts there.
    assert out["episode_id"][24] == 1 and out["episode_id"][23] is None


def test_episodes_are_what_the_rule_finds():
    months = h.period_grid(date(2020, 1, 1), date(2020, 9, 1), "month")
    values = [100, 110, 95, None, 99, 111, 105, 90, 92]
    episodes = h.find_episodes(months, values, 0.10)
    assert [(e.peak_index, e.trough_index) for e in episodes] == [(110, 95), (111, 90)]
    assert episodes[0].recovery_period == date(2020, 6, 1)
    assert episodes[1].recovery_period is None
    # A 5% dip is not an episode.
    assert h.find_episodes(months[:3], [100, 95, 101], 0.10) == []


def test_validation_aligns_a_trailing_average():
    """If DLD were our index averaged over 12 months, the aligned correlation is ~1."""
    months = h.period_grid(date(2010, 1, 1), date(2024, 5, 1), "month")
    rng = np.random.default_rng(1)
    level = np.exp(np.cumsum(rng.normal(0.004, 0.02, len(months))))
    ours = pl.DataFrame({"period": months, "index_value": 100 * level})
    trailing = np.convolve(level, np.ones(12) / 12, mode="full")[: len(months)]
    dld = pl.DataFrame({"period": months[11:], "index_ratio": trailing[11:]})
    metrics, joined = h.compare_with_dld(ours, dld, date(2012, 1, 1), date(2024, 5, 1))
    assert metrics["yoy_corr_aligned"] == pytest.approx(1.0, abs=1e-9)
    assert metrics["yoy_corr_aligned"] > metrics["yoy_corr"]
    assert metrics["best_lead_months"] > 0
    assert joined["period"].min() == date(2012, 1, 1)


def test_segment_ids_are_slugs():
    assert h.slug("Marina, JBR & JLT") == "marina-jbr-jlt"


# --- Published table (skipped until make train has run) ------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        if c.execute("select to_regclass('ml.fct_price_index')").fetchone()[0] is None:
            pytest.skip("ml.fct_price_index not built yet (run make train)")
        yield c


@pytest.mark.db
def test_every_published_segment_is_100_in_its_base_period(conn):
    rows = conn.execute(
        """
        select segment_id, max(index_value) filter (where period_start = %s)
        from ml.fct_price_index where model_version = %s group by 1
        """,
        [BASE, config.HEDONIC_MODEL_VERSION],
    ).fetchall()
    assert all(v is not None and float(v) == 100 for _, v in rows), rows


@pytest.mark.db
def test_no_published_period_below_min_n(conn):
    (bad,) = conn.execute(
        "select count(*) from ml.fct_price_index where n_obs < %s", [config.MIN_N]
    ).fetchone()
    assert bad == 0


@pytest.mark.db
def test_drawdown_and_partial_period_flags(conn):
    (bad_dd,) = conn.execute(
        "select count(*) from ml.fct_price_index where drawdown > 0 or index_value > running_peak"
    ).fetchone()
    (multi_partial,) = conn.execute(
        """
        select count(*) from (
            select segment_id from ml.fct_price_index where is_partial_period
            group by 1 having count(*) > 1
        ) as t
        """
    ).fetchone()
    assert bad_dd == 0 and multi_partial == 0
