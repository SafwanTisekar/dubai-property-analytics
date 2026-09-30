"""Phase 3 analysis functions (src/dubai_property/analysis).

Unit tests cover the pure logic (min-n masking, the like-for-like mix-shift maths, the
yield roll-up, formats, partial-year labels) and need no database. The DB tests run every
query function against whatever is loaded, which is the CI fixtures in CI, and check
shapes, ranges and one reconciliation to rpt. They skip until `make dbt` has built rpt;
CI runs them again after the build.
"""

from datetime import date

import numpy as np
import pandas as pd
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.analysis import common, financing, market_cycles, plotting, prices_rents
from dubai_property.quality import kpi_reconciliation as kpi

SNAP = date(2026, 9, 25)


# --- Unit tests (no database) -----------------------------------------------------------
def test_apply_min_n_blanks_thin_segments_and_keeps_n():
    df = pd.DataFrame({"n": [19, 20, None], "median": [1.0, 2.0, 3.0]})
    out = common.apply_min_n(df, "n", ["median"])
    assert out["median"].isna().tolist() == [True, False, True]
    assert out["n"].tolist()[:2] == [19, 20]
    assert df["median"].notna().all()  # input untouched


def test_apply_min_n_requires_every_n_column():
    df = pd.DataFrame({"a": [50, 50], "b": [50, 5], "y": [0.05, 0.06]})
    out = common.apply_min_n(df, ["a", "b"], ["y"])
    assert out["y"].isna().tolist() == [False, True]


def test_partial_year_and_labels():
    assert common.is_partial_year(2026, SNAP)
    assert not common.is_partial_year(2025, SNAP)
    assert not common.is_partial_year(2026, date(2026, 12, 31))
    assert plotting.year_label(2026, SNAP) == "2026*"
    assert plotting.year_label(2025, SNAP) == "2025"
    assert "25 Sep 2026" in plotting.partial_note(SNAP)
    assert common.last_12_months(SNAP) == (date(2025, 9, 26), SNAP)


def test_fmt_aed():
    assert plotting.fmt_aed(668_299_000_000) == "AED 668.3bn"
    assert plotting.fmt_aed(700e9) == "AED 700bn"
    assert plotting.fmt_aed(350_400_000, prefix=False) == "350m"
    assert plotting.fmt_aed(18_500) == "AED 18,500"
    assert plotting.fmt_aed(float("nan")) == ""


def _cells(rows):
    return pd.DataFrame(rows, columns=["year", "zone", "bedrooms", "n", "median_ppsqm_aed"])


def test_like_for_like_is_zero_under_a_pure_mix_shift():
    # Same cell prices both years; sales move from the cheap zone to the dear one.
    cells = _cells(
        [
            (2022, "cheap", 1, 80, 10_000.0),
            (2022, "dear", 1, 20, 20_000.0),
            (2023, "cheap", 1, 20, 10_000.0),
            (2023, "dear", 1, 80, 20_000.0),
        ]
    )
    raw = pd.DataFrame({"year": [2022, 2023], "n": [100, 100], "median_ppsqm_aed": [1e4, 2e4]})
    out = prices_rents.like_for_like(cells, raw).set_index("year")
    assert out.loc[2023, "raw_change"] == pytest.approx(1.0)
    assert out.loc[2023, "lfl_change"] == pytest.approx(0.0)
    assert out.loc[2023, "mix_effect"] == pytest.approx(1.0)
    assert out.loc[2023, "cells_used"] == 2
    assert out.loc[2023, "coverage"] == pytest.approx(1.0)


def test_like_for_like_recovers_a_uniform_price_change_and_skips_thin_cells():
    cells = _cells(
        [
            (2022, "a", 1, 50, 10_000.0),
            (2022, "b", 2, 50, 20_000.0),
            (2022, "thin", 1, 5, 99_000.0),
            (2023, "a", 1, 50, 11_000.0),
            (2023, "b", 2, 50, 22_000.0),
            (2023, "thin", 1, 5, 1.0),  # would dominate if min-n were ignored
        ]
    )
    raw = pd.DataFrame({"year": [2022, 2023], "n": [105, 105], "median_ppsqm_aed": [1.5e4, 1.6e4]})
    out = prices_rents.like_for_like(cells, raw).set_index("year")
    assert out.loc[2023, "lfl_change"] == pytest.approx(0.10)
    assert out.loc[2023, "cells_used"] == 2


def test_yield_by_zone_prefers_bedroom_cells_then_rolls_up():
    label = "Residential · Apartment"
    cells = pd.DataFrame(
        [
            # zone A: two passing bedroom cells, one outside the sanity band
            ("A", label, 1.0, False, 100, 0.05, False),
            ("A", label, 2.0, False, 300, 0.07, False),
            ("A", label, 3.0, False, 40, 0.30, True),
            ("A", label, None, True, 440, 0.06, False),
            # zone B: no passing cell, roll-up passes
            ("B", label, 1.0, False, 10, np.nan, False),
            ("B", label, None, True, 30, 0.04, False),
            # zone C: nothing passes
            ("C", label, None, True, 5, np.nan, False),
        ],
        columns=[
            "zone",
            "property_type_label",
            "bedrooms",
            "is_rollup",
            "sales_n",
            "gross_yield",
            "is_outside_sanity",
        ],
    )
    cells["rent_n"] = 100
    out = prices_rents.yield_by_zone(cells).set_index("zone")
    assert out.loc["A", "gross_yield"] == pytest.approx((0.05 * 100 + 0.07 * 300) / 400)
    assert out.loc["A", "method"] == "bedroom cells"
    assert out.loc["A", "cells_flagged"] == 1
    assert out.loc["B", "gross_yield"] == pytest.approx(0.04)
    assert out.loc["B", "method"] == "zone roll-up"
    assert np.isnan(out.loc["C", "gross_yield"])
    assert out.loc["C", "method"] == "below min-n"


def test_registration_lag_summary():
    lag = pd.DataFrame(
        {
            "year": [2009, 2009, 2009, 2012],
            "is_offplan": [True, True, True, False],
            "id_year": [2007, 2008, 2009, 2012],
            "market_sales": [60, 30, 10, 5],
        }
    )
    lag["lag_years"] = lag["year"] - lag["id_year"]
    out = market_cycles.registration_lag_summary(lag).set_index(["year", "is_offplan"])
    assert out.loc[(2009, True), "share_id_year_earlier"] == pytest.approx(0.9)
    assert out.loc[(2009, True), "median_lag_years"] == 2
    assert out.loc[(2012, False), "share_id_year_earlier"] == 0


def test_share_rate_correlation_uses_levels_and_changes():
    months = pd.date_range("2010-01-01", periods=48, freq="MS")
    rate = np.linspace(0.0, 0.05, 48)
    df = pd.DataFrame(
        {"month": months, "fed_funds_rate": rate, "purchase_share_12m": 0.3 - 2 * rate}
    )
    out = financing.share_rate_correlation(df)
    assert out["months"] == 48
    assert out["corr_levels"] == pytest.approx(-1.0)


def test_mortgage_indicators_are_ratios_of_sums():
    months = pd.date_range("2025-01-01", periods=2, freq="MS")
    monthly = pd.DataFrame(
        {
            "month": months,
            "market_sales": [100.0, 300.0],
            "ready_sales": [40.0, 60.0],
            "purchase_mortgages": [10.0, 20.0],
            "new_mortgages": [20.0, 40.0],
            "ready_unit_mortgages": [25.0, 35.0],
            "fed_funds_rate": [0.04, 0.05],
        }
    )
    y = financing.mortgage_indicators_by_year(monthly).set_index("year").loc[2025]
    assert y["purchase_share"] == pytest.approx(30 / 100)  # not the mean of 0.25 and 0.33
    assert y["upper_share"] == pytest.approx(60 / 100)
    assert y["match_rate"] == pytest.approx(30 / 60)
    assert y["new_per_100_sales"] == pytest.approx(15.0)
    assert y["purchase_share"] <= y["upper_share"]


def test_last_full_month_and_ytd_summary():
    assert market_cycles.last_full_month(SNAP) == 8
    assert market_cycles.last_full_month(date(2026, 8, 31)) == 8
    by_zone = pd.DataFrame(
        {
            "zone": ["a", "a", "b"],
            "is_offplan": [True, False, False],
            "sales_prev": [100, 100, 50],
            "sales_cur": [120, 60, 50],
            "value_prev_aed": [1e9, 1e9, 5e8],
            "value_cur_aed": [1.2e9, 0.5e9, 5e8],
        }
    )
    total = market_cycles.ytd_summary(by_zone).iloc[0]
    assert total["sales_change"] == pytest.approx(230 / 250 - 1)
    by_type = market_cycles.ytd_summary(by_zone, ["is_offplan"]).set_index("is_offplan")
    assert by_type.loc[False, "sales_change"] == pytest.approx(110 / 150 - 1)


def test_snapshot_tail_ratio_detects_a_thin_tail():
    days = pd.bdate_range("2026-08-01", "2026-09-25")
    daily = pd.DataFrame(
        {"txn_date": days, "iso_dow": days.isocalendar().day.values, "transaction_lines": 100}
    )
    assert market_cycles.snapshot_tail_ratio(daily, SNAP) == pytest.approx(1.0)
    daily.loc[daily["txn_date"] > "2026-09-18", "transaction_lines"] = 40
    assert market_cycles.snapshot_tail_ratio(daily, SNAP) == pytest.approx(0.4)


def test_cycle_phases_are_ordered_and_cover_the_named_cycles():
    starts = [p.start_year for p in market_cycles.CYCLE_PHASES]
    assert starts == sorted(starts)
    assert market_cycles.CYCLE_PHASES[-1].end_year is None


def test_save_writes_a_png(tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    plotting.apply_style()
    fig, ax = plotting.figure()
    plotting.year_bars(ax, [2025, 2026], [1, 2], SNAP)
    plotting.titled(fig, "t", "s")
    plotting.add_source(fig, SNAP)
    path = plotting.save(fig, "test_chart", directory=tmp_path)
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# --- DB tests (skip until rpt is built) -----------------------------------------------
@pytest.fixture(scope="module")
def snapshot():
    try:
        with db.connect(connect_timeout=3) as conn:
            if not kpi.rpt_available(conn):
                pytest.skip("rpt views not built yet (run make dbt)")
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    return common.snapshot_date()


@pytest.mark.db
def test_sales_by_year_reconciles_to_rpt(snapshot):
    yearly = market_cycles.sales_by_year(config.REPORT_SCOPE_START, snapshot)
    rpt = common.query(
        'select count(*) as n, coalesce(sum("AED Counted Once"), 0) as aed '
        'from rpt.transactions where "Is Market Sale"'
    )
    assert yearly["market_sales"].sum() == rpt["n"].iloc[0]
    # rpt rounds AED to whole dirhams per row.
    assert abs(yearly["market_value_aed"].sum() - float(rpt["aed"].iloc[0])) <= 0.5 * max(
        rpt["n"].iloc[0], 1
    )
    assert yearly["year"].max() <= snapshot.year
    shares = yearly[["offplan_share_count", "offplan_share_value"]].dropna()
    assert shares.stack().between(0, 1).all()


@pytest.mark.db
def test_market_cycle_queries(snapshot):
    monthly = market_cycles.sales_by_month(config.REPORT_SCOPE_START, snapshot)
    assert monthly["month"].max() <= pd.Timestamp(snapshot)
    assert (monthly[["ready_sales", "offplan_sales"]] >= 0).all().all()
    proc = market_cycles.sales_by_procedure(2004, snapshot.year)
    assert set(proc.columns) >= {"year", "procedure_name", "is_offplan", "market_sales"}
    assert proc["market_sales"].sum() == monthly["market_sales"].sum()
    lag = market_cycles.registration_lag(2004, snapshot.year)
    assert lag["market_sales"].sum() == proc["market_sales"].sum()
    market_cycles.offplan_by_project_first_year(2009)
    ytd = market_cycles.ytd_by_zone(snapshot)
    assert set(ytd.columns) >= {"zone", "is_offplan", "sales_prev", "sales_cur"}
    daily = market_cycles.daily_registrations(date(2004, 1, 1), snapshot)
    assert daily["txn_date"].max() <= pd.Timestamp(snapshot)
    market_cycles.ppsqm_offplan_vs_ready(2004, snapshot.year)


@pytest.mark.db
def test_financing_queries(snapshot):
    mi = financing.mortgage_indicators_monthly(config.REPORT_SCOPE_START, snapshot)
    assert mi["month"].max() <= pd.Timestamp(snapshot)
    assert (mi["purchase_mortgages"] <= mi["ready_sales"]).all()
    assert (mi["purchase_mortgages"] <= mi["ready_unit_mortgages"]).all()
    assert (mi["ready_sales"] <= mi["market_sales"]).all()
    # Same numerator and denominator as the aggregate Power BI reads.
    agg = common.query(
        "select sum(purchase_mortgages) as pm, sum(market_sales) filter (where not is_offplan)"
        " as ready from gold.agg_area_month"
    )
    assert mi["purchase_mortgages"].sum() == agg["pm"].iloc[0]
    assert mi["ready_sales"].sum() == agg["ready"].iloc[0]
    financing.mortgage_indicators_by_year(mi)
    port = financing.portfolio_by_year(config.REPORT_SCOPE_START, snapshot)
    assert (port["portfolio_deals"] <= port["portfolio_lines"]).all()
    ltv = financing.ltv_by_year()
    assert set(ltv.columns) >= {"year", "pairs", "median", "share_at_0_75", "share_at_0_80"}
    shares = ltv.filter(like="share_").stack()
    assert shares.between(0, 1).all()
    clusters = financing.ltv_cluster_shares_monthly(date(2004, 1, 1), snapshot)
    assert clusters.filter(like="share_").stack().between(0, 1).all()
    assert clusters["pairs"].sum() == ltv["pairs"].sum()
    hist = financing.ltv_histogram([2024, 2025])
    if not hist.empty:
        assert hist.groupby("year")["share"].sum().round(9).eq(1).all()


@pytest.mark.db
def test_price_and_rent_queries(snapshot):
    pp = prices_rents.ppsqm_by_year()
    assert set(pp["property_type_key"]) <= set(config.RESIDENTIAL_HOMES_KEYS)
    zone = prices_rents.ppsqm_by_zone_year()
    assert zone.loc[zone["clean_sales"] < config.MIN_N, "median_ppsqm_aed"].isna().all()
    rent = prices_rents.rent_ppsqm_by_zone_year()
    assert rent.loc[rent["rent_n"] < config.MIN_N, "median_rent_ppsqm_aed"].isna().all()
    top = prices_rents.top_areas_by_value(snapshot, n=10)
    assert len(top) <= 10
    assert top["market_value_aed"].is_monotonic_decreasing
    cells, raw = prices_rents.mix_shift_inputs()
    if len(raw) > 1:
        prices_rents.like_for_like(cells, raw)
    yc = prices_rents.yield_preview_cells(snapshot)
    thin = (yc["sales_n"] < config.MIN_N) | (yc["rent_n"] < config.MIN_N)
    assert yc.loc[thin, "gross_yield"].isna().all()
    prices_rents.yield_by_zone(yc)
    basis = prices_rents.area_basis()
    assert basis["share_no_bedrooms"].between(0, 1).all()
