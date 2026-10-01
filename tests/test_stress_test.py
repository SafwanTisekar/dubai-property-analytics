"""Collateral stress test: the mechanics on synthetic sales (CI) and the written grid (DB).

The invariants the brief asks for: shares in [0, 1]; negative equity can only grow as the
shock deepens or the LTV rises; with an unchanged index and no shock nobody with LTV < 100%
is under water. Plus the parts that decide which number a sale gets: the CBUAE cap in
force on its date, the zone -> type index fallback, the partial period never used as
"now", min-n, and the replay drawdown.
"""

from datetime import date

import numpy as np
import polars as pl
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.models import stress_test as st
from dubai_property.models.hedonic_index import add_months

APT, VILLA = 101, 102


# --- Synthetic inputs ---------------------------------------------------------------------
def index_rows(segment_id, level, type_key, zone, frequency, values: dict, partial=None):
    rows = []
    for period, value in values.items():
        rows.append(
            {
                "segment_id": segment_id,
                "segment_level": level,
                "property_type_key": type_key,
                "zone": zone,
                "frequency": frequency,
                "period_start": period,
                "index_value": float(value),
                "is_partial_period": period == partial,
            }
        )
    return rows


def months(start: date, end: date) -> list[date]:
    out, m = [], start
    while m <= end:
        out.append(m)
        m = add_months(m, 1)
    return out


def make_index(apt_level=lambda m: 100.0, villa_level=lambda m: 100.0) -> pl.DataFrame:
    """Monthly type series to Sep 2026 (partial, set to 1.0 so any use shows), a monthly
    Zone A apartment series and a quarterly Zone Q villa series to Q3 2026 (partial)."""
    span = months(date(2023, 1, 1), date(2026, 9, 1))
    rows = []
    for key, fn, sid in ((APT, apt_level, "apartment"), (VILLA, villa_level, "villa")):
        vals = {m: (1.0 if m == span[-1] else fn(m)) for m in span}
        rows += index_rows(sid, "type", key, None, "month", vals, partial=span[-1])
    zone_vals = {m: (1.0 if m == span[-1] else 200.0) for m in span}
    rows += index_rows(
        "apartment-zone-a", "zone", APT, "Zone A", "month", zone_vals, partial=span[-1]
    )
    quarters = [m for m in span if m.month in (1, 4, 7, 10)]
    q_vals = {q: 50.0 + i for i, q in enumerate(quarters)}
    rows += index_rows(
        "villa-zone-q", "zone", VILLA, "Zone Q", "quarter", q_vals, partial=quarters[-1]
    )
    return pl.DataFrame(rows).with_columns(pl.col("property_type_key").cast(pl.Int32))


def sale(tid, month, type_key=APT, zone="Zone A", offplan=False, price=1_000_000.0, loan=None,
         area_key=1):  # fmt: skip
    return {
        "transaction_id": tid,
        "txn_date": month.replace(day=15),
        "month": month,
        "area_key": area_key,
        "zone": zone,
        "property_type_key": type_key,
        "is_offplan": offplan,
        "price_aed": price,
        "loan_aed": loan,
    }


def frame(rows) -> pl.DataFrame:
    return pl.DataFrame(rows).with_columns(
        pl.col("area_key").cast(pl.Int32),
        pl.col("property_type_key").cast(pl.Int32),
        pl.col("loan_aed").cast(pl.Float64),
    )


RULES = pl.DataFrame(
    [
        # rule_id, borrower, status, home, band, ltv, from, to
        (4, "Expatriate", "ready", "first", "up to AED 5M", 0.80, date(2020, 4, 8), None),
        (5, "Expatriate", "ready", "first", "above AED 5M", 0.70, date(2020, 4, 8), None),
        (6, "Expatriate", "ready", "second or more", "any", 0.60, date(2020, 4, 8), None),
        (1, "UAE national", "ready", "first", "up to AED 5M", 0.85, date(2020, 4, 8), None),
        (7, "Any", "off-plan", "any", "any", 0.50, date(2020, 4, 8), None),
        (11, "Expatriate", "ready", "first", "up to AED 5M", 0.75, date(2013, 10, 28),
         date(2020, 4, 7)),
        (12, "Expatriate", "ready", "first", "above AED 5M", 0.65, date(2013, 10, 28),
         date(2020, 4, 7)),
        (14, "Any", "off-plan", "any", "any", 0.50, date(2013, 10, 28), date(2020, 4, 7)),
    ],
    schema=["rule_id", "borrower", "property_status", "home_number", "value_band", "max_ltv",
            "effective_from", "effective_to"],
    orient="row",
)  # fmt: skip


def random_book(n=600, seed=7) -> pl.DataFrame:
    """Scored sales with varied prices, mark-to-market ratios, segments and loans."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        offplan = bool(rng.random() < 0.5)
        price = float(rng.uniform(5e5, 8e6))
        rows.append(
            {
                "area_key": int(rng.integers(1, 5)),
                "zone": "Zone A" if rng.random() < 0.5 else "Zone B",
                "property_type_key": APT if rng.random() < 0.7 else VILLA,
                "is_offplan": offplan,
                "price_aed": price,
                "current_value_aed": price * float(rng.uniform(0.7, 1.4)),
                "loan_aed": None
                if offplan or rng.random() < 0.6
                else price * rng.uniform(0.5, 0.9),
                "cap_ltv": 0.5 if offplan else 0.8,
                "index_basis": "zone" if rng.random() < 0.8 else "type",
                "replay_shock": float(rng.uniform(-0.4, -0.2)),
            }
        )
    return pl.DataFrame(rows).with_columns(
        pl.col("area_key").cast(pl.Int32), pl.col("property_type_key").cast(pl.Int32)
    )


@pytest.fixture(scope="module")
def grid() -> pl.DataFrame:
    return st.roll_up(st.stress_cells(st.loan_book(random_book())), min_n=1)


# --- Window and cap -----------------------------------------------------------------------
def test_window_is_36_complete_months_before_a_partial_snapshot():
    assert st.last_complete_month(date(2026, 9, 25)) == date(2026, 8, 1)
    assert st.last_complete_month(date(2026, 9, 30)) == date(2026, 9, 1)
    assert st.window(date(2026, 9, 25)) == (date(2023, 9, 1), date(2026, 8, 1))


def test_cap_is_the_rule_in_force_on_the_sale_date_for_its_band_and_status():
    sales = frame(
        [
            sale("pre2020", date(2019, 6, 1)),
            sale("ready", date(2021, 6, 1)),
            sale("exactly5m", date(2021, 6, 1), price=5_000_000.0),
            sale("over5m", date(2021, 6, 1), price=6_000_000.0),
            sale("over5m-2019", date(2019, 6, 1), price=6_000_000.0),
            sale("offplan", date(2021, 6, 1), offplan=True, price=9_000_000.0),
        ]
    )
    out = st.cap_ltv(sales, RULES)
    got = dict(zip(out["transaction_id"], out["cap_ltv"], strict=True))
    assert got == {
        "pre2020": 0.75,
        "ready": 0.80,  # the expatriate cap, not the national's 0.85
        "exactly5m": 0.80,  # "up to AED 5M" includes 5M
        "over5m": 0.70,
        "over5m-2019": 0.65,
        "offplan": 0.50,
    }


def test_a_sale_before_any_rule_gets_no_cap():
    out = st.cap_ltv(frame([sale("old", date(2012, 1, 1))]), RULES)
    assert out["cap_ltv"].to_list() == [None]


# --- Mark-to-market -----------------------------------------------------------------------
def test_zone_series_marks_its_sales_and_the_partial_period_is_never_now():
    index = make_index(apt_level=lambda m: 100.0 + (m.year - 2023) * 12 + m.month)
    out = st.mark_to_market(frame([sale("z", date(2024, 1, 1))]), index)
    row = out.row(0, named=True)
    assert row["index_basis"] == "zone" and row["index_segment"] == "apartment-zone-a"
    assert row["mtm_ratio"] == pytest.approx(1.0)  # zone flat at 200 (Sep 2026 = 1.0 ignored)


def test_type_series_is_the_fallback_outside_a_published_zone():
    index = make_index(apt_level=lambda m: 100.0 if m < date(2025, 1, 1) else 110.0)
    out = st.mark_to_market(frame([sale("t", date(2024, 1, 1), zone="Zone Z")]), index)
    row = out.row(0, named=True)
    assert row["index_basis"] == "type"
    assert row["mtm_ratio"] == pytest.approx(1.10)  # Aug 2026 (complete) / Jan 2024
    assert row["current_value_aed"] == pytest.approx(1_100_000.0)


def test_quarterly_zone_marks_by_quarter_and_falls_back_after_its_last_complete_quarter():
    index = make_index()
    out = st.mark_to_market(
        frame(
            [
                sale("q", date(2024, 2, 1), type_key=VILLA, zone="Zone Q"),
                sale("late", date(2026, 8, 1), type_key=VILLA, zone="Zone Q"),
            ]
        ),
        index,
    ).sort("transaction_id")
    late, q = out.row(0, named=True), out.row(1, named=True)
    # Q1 2024 is 4 quarters after Q1 2023 (50 + 4); now = Q2 2026 (50 + 13).
    assert q["index_basis"] == "zone" and q["mtm_ratio"] == pytest.approx(63 / 54)
    # Q3 2026 is partial, so an Aug 2026 sale is after the zone's "now": type series.
    assert late["index_basis"] == "type"


def test_sales_no_series_can_mark_get_nulls():
    index = make_index().filter(pl.col("property_type_key") == APT)
    out = st.mark_to_market(frame([sale("v", date(2024, 1, 1), type_key=VILLA)]), index)
    assert out["mtm_ratio"].to_list() == [None] and out["index_basis"].to_list() == [None]


# --- Replay -------------------------------------------------------------------------------
def test_replay_is_the_deepest_fall_from_the_running_peak_inside_the_window():
    vals = [100, 120, 90, 110, 80, 130]
    periods = [date(2014, m, 1) for m in range(1, 7)]
    rows = index_rows(
        "apartment", "type", APT, None, "month", dict(zip(periods, vals, strict=True))
    )
    rows += index_rows("apartment-late", "zone", APT, "Late", "month", {date(2016, 1, 1): 100.0,
                       date(2016, 2, 1): 50.0})  # fmt: skip
    r = st.replay_drawdowns(
        pl.DataFrame(rows).with_columns(pl.col("property_type_key").cast(pl.Int32))
    )
    apt = r.filter(pl.col("segment_id") == "apartment").row(0, named=True)
    assert apt["drawdown"] == pytest.approx(80 / 120 - 1)
    assert apt["peak_period"] == date(2014, 2, 1) and apt["trough_period"] == date(2014, 5, 1)
    late = r.filter(pl.col("segment_id") == "apartment-late").row(0, named=True)
    assert not late["is_used"] and "after" in late["note"]  # started after the 2014 peak
    sales = pl.DataFrame({"property_type_key": [APT], "zone": ["Late"]}).with_columns(
        pl.col("property_type_key").cast(pl.Int32)
    )
    out = st.attach_replay(sales, r).row(0, named=True)
    assert out["replay_basis"] == "type" and out["replay_shock"] == pytest.approx(80 / 120 - 1)


# --- Negative equity invariants ---------------------------------------------------------------
def test_shares_are_between_zero_and_one(grid):
    shares = grid["negative_equity_share"].drop_nulls()
    assert shares.len() > 0 and shares.is_between(0, 1).all()


def test_negative_equity_never_falls_as_the_shock_deepens(grid):
    keys = ["segment_level", "property_type_key", "zone", "area_key", "is_offplan", "ltv_basis",
            "ltv_pct"]  # fmt: skip
    g = grid.filter(pl.col("scenario") == "grid").sort([*keys, "shock_pct"], descending=False)
    diffs = (
        g.sort("shock_pct", descending=True)
        .group_by(keys, maintain_order=True)
        .agg(
            pl.col("negative_equity_count").diff().drop_nulls().min().alias("count"),
            pl.col("negative_equity_aed").diff().drop_nulls().min().alias("aed"),
        )
    )
    assert (diffs["count"] >= 0).all() and (diffs["aed"] >= -1e-6).all()


def test_negative_equity_never_falls_as_the_ltv_rises(grid):
    keys = ["segment_level", "property_type_key", "zone", "area_key", "is_offplan", "shock_pct"]
    g = grid.filter((pl.col("scenario") == "grid") & (pl.col("ltv_basis") == "grid"))
    diffs = (
        g.sort("ltv_pct")
        .group_by(keys, maintain_order=True)
        .agg(
            pl.col("negative_equity_count").diff().drop_nulls().min().alias("count"),
            pl.col("negative_equity_aed").diff().drop_nulls().min().alias("aed"),
        )
    )
    assert (diffs["count"] >= 0).all() and (diffs["aed"] >= -1e-6).all()
    # ... and it does rise somewhere, so the test isn't vacuous.
    top = g.filter((pl.col("segment_level") == "dubai") & (pl.col("shock_pct") == -30))
    assert top.sort("ltv_pct")["negative_equity_count"].to_list()[-1] > 0


def test_unchanged_index_and_no_shock_means_no_negative_equity_below_100pct_ltv():
    book = random_book().with_columns(current_value_aed=pl.col("price_aed"))
    out = st.roll_up(st.stress_cells(st.loan_book(book), shocks=(0,)), min_n=1)
    base = out.filter(pl.col("scenario") == "grid")
    assert base.height > 0 and (base["negative_equity_count"] == 0).all()
    assert (base["negative_equity_aed"] == 0).all()


def test_off_plan_and_ready_are_never_pooled(grid):
    assert grid["is_offplan"].null_count() == 0
    # Matched loans are ready purchases only.
    assert grid.filter((pl.col("ltv_basis") == "actual_loan") & pl.col("is_offplan")).is_empty()


def test_levels_are_roll_ups_of_the_same_purchases(grid):
    g = grid.filter(
        (pl.col("scenario") == "grid") & (pl.col("shock_pct") == -20) & (pl.col("ltv_pct") == 80)
    )
    per_level = g.group_by("segment_level").agg(pl.col("purchases").sum(),
                                                 pl.col("negative_equity_count").sum())  # fmt: skip
    assert per_level["purchases"].n_unique() == 1
    assert per_level["negative_equity_count"].n_unique() == 1


def test_min_n_blanks_the_share_but_keeps_the_count_of_purchases():
    out = st.roll_up(st.stress_cells(st.loan_book(random_book(n=60))), min_n=config.MIN_N)
    thin = out.filter(pl.col("purchases") < config.MIN_N)
    assert thin.height > 0 and not thin["is_published"].any()
    assert thin["negative_equity_share"].null_count() == thin.height
    assert thin["negative_equity_aed"].null_count() == thin.height
    fat = out.filter(pl.col("purchases") >= config.MIN_N)
    assert fat["is_published"].all() and fat["negative_equity_share"].null_count() == 0


def test_replay_rows_carry_each_segments_applied_drawdown(grid):
    rp = grid.filter(pl.col("scenario") == config.STRESS_REPLAY_NAME)
    assert rp["shock_pct"].null_count() == rp.height
    assert rp["applied_shock"].is_between(-0.4, -0.2).all()


# --- Written grid (skipped until make score has run) ----------------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        if c.execute("select to_regclass('ml.stress_grid')").fetchone()[0] is None:
            pytest.skip("ml.stress_grid not built yet (run make score)")
        yield c


@pytest.mark.db
def test_written_grid_invariants(conn):
    (bad,) = conn.execute(
        """
        select count(*) from ml.stress_grid
        where model_version = %(v)s and (
              negative_equity_share not between 0 and 1
           or (is_published and purchases < %(n)s)
           or (not is_published and negative_equity_share is not null)
           or (scenario = 'grid' and shock_pct = 0 and ltv_basis = 'grid' and ltv_pct = 50
               and negative_equity_count > 0))
        """,
        {"v": config.STRESS_MODEL_VERSION, "n": config.MIN_N},
    ).fetchone()
    assert bad == 0


@pytest.mark.db
def test_written_grid_has_every_shock_and_ltv_key(conn):
    rows = conn.execute(
        "select distinct shock_pct, ltv_pct from ml.stress_grid"
        " where model_version = %s and scenario = 'grid' and ltv_basis = 'grid'",
        [config.STRESS_MODEL_VERSION],
    ).fetchall()
    if not rows:
        pytest.skip("no scored sales (fixtures without a published index)")
    assert {r[0] for r in rows} == set(config.STRESS_SHOCKS)
    assert {r[1] for r in rows} == set(config.STRESS_LTV_GRID)
