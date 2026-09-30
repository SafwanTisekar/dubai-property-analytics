"""KPI reconciliation (docs/01 §4, docs/06 §3): silver and the rpt views must agree.

The DB test computes every pre-ML KPI from silver and from rpt.transactions, rpt.area_month
and rpt.rent_month, writes reports/kpi_reconciliation.md (the numbers the Power BI cards
must match) and fails on any mismatch. It skips until `make dbt` has built rpt; CI runs it
again after the build. The helper tests need no database.
"""

import psycopg
import pytest

from dubai_property import db
from dubai_property.quality import kpi_reconciliation as kpi


@pytest.mark.db
def test_every_kpi_reconciles_silver_to_rpt():
    try:
        with db.connect(connect_timeout=3) as conn:
            available = kpi.rpt_available(conn)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    if not available:
        pytest.skip("rpt views not built yet (run make dbt)")
    result = kpi.run()
    assert kpi.REPORT_PATH.exists()
    assert result.silver["all"]["market_sales"] > 0
    assert all(n > 0 for n in result.checks.values())
    assert result.mismatches == []
    # No period after the data snapshot (rents registered ahead are excluded).
    snapshot_month = result.snapshot.strftime("%Y-%m")
    assert max(p for p in result.silver if len(p) == 7) == snapshot_month
    assert max(p for p in result.silver if len(p) == 4) == str(result.snapshot.year)


@pytest.mark.db
def test_apartment_area_weighted_price_tracks_the_median():
    """Residential apartments: area-weighted within ±40% of the median, every year 2010+.

    Only meaningful on the full register (the CI fixtures have a handful of sales a year),
    so it runs when at least kpi.DIVERGENCE_MIN_LINES transaction lines are in scope.
    """
    try:
        with db.connect(connect_timeout=3) as conn:
            if not kpi.rpt_available(conn):
                pytest.skip("rpt views not built yet (run make dbt)")
            result = kpi.compute(conn)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    if not kpi.divergence_applies(result.silver):
        pytest.skip("fixture or sample data: too few sales for yearly apartment figures")
    assert kpi.apartment_divergence(result.silver) == []


def test_tolerance_by_kind():
    assert kpi.tolerance("count", 1_000) == 0
    assert kpi.tolerance("aed", 1_000) == 500
    assert kpi.tolerance("area", 1_000) == 5
    assert kpi.tolerance("median", 1_000) == 1
    with pytest.raises(ValueError):
        kpi.tolerance("share", 1)


def test_compare_allows_rounding_but_not_count_differences():
    silver = {"2025": {"market_sales": 10, "market_value": 1000.4, "median_ppsqm": 100.2}}
    rounded = {"2025": {"_rows": 10, "market_sales": 10, "market_value": 1000, "median_ppsqm": 100}}
    assert kpi.compare("rpt.x", silver, rounded) == []

    off_by_one = {"2025": {**rounded["2025"], "market_sales": 9}}
    [m] = kpi.compare("rpt.x", silver, off_by_one)
    assert (m.period, m.metric) == ("2025", "market_sales")

    too_far = {"2025": {**rounded["2025"], "market_value": 1010}}  # > 0.5 AED x 10 rows
    assert [m.metric for m in kpi.compare("rpt.x", silver, too_far)] == ["market_value"]


def test_compare_flags_a_missing_period():
    silver = {"2025": {"market_sales": 1}, "2026": {"market_sales": 1}}
    other = {"2025": {"_rows": 1, "market_sales": 1}}
    [m] = kpi.compare("rpt.x", silver, other)
    assert (m.period, m.metric) == ("2026", "period")


def test_derive_kpis_follow_docs_01_definitions():
    row = {
        "market_sales": 80,
        "new_mortgages": 20,
        "offplan_sales": 40,
        "market_value": 1000,
        "offplan_value": 250,
        "aw_value": 500,
        "aw_area": 50,
    }
    d = kpi.derive(row)
    assert d["mortgage_share"] == 0.2  # 20 / (20 + 80)
    assert d["offplan_share_count"] == 0.5
    assert d["offplan_share_value"] == 0.25
    assert d["aw_ppsqm"] == 10
    assert d["rent_aw_sqm"] is None  # no rent inputs: blank, not zero


def test_apartment_divergence_flags_years_outside_40_percent():
    silver = {
        "2009": {"apt_median": 100, "apt_aw_value": 1000, "apt_aw_area": 1},  # before 2010
        "2010": {"apt_median": 100, "apt_aw_value": 139, "apt_aw_area": 1},  # +39%: ok
        "2011": {"apt_median": 100, "apt_aw_value": 50, "apt_aw_area": 1},  # -50%: fails
        "2012": {"apt_median": None},  # no data: fails
        "2012-01": {"apt_median": 1, "apt_aw_value": 9, "apt_aw_area": 1},  # months ignored
        "all": {"apt_median": 1, "apt_aw_value": 9, "apt_aw_area": 1},
    }
    assert [b[0] for b in kpi.apartment_divergence(silver)] == ["2011", "2012"]


def test_divergence_check_only_applies_to_the_full_register():
    bad_year = {"2011": {"apt_median": 100, "apt_aw_value": 50, "apt_aw_area": 1}}
    small = {"all": {"_rows": kpi.DIVERGENCE_MIN_LINES - 1}, **bad_year}
    full = {"all": {"_rows": kpi.DIVERGENCE_MIN_LINES}, **bad_year}
    assert kpi.divergence_failures(small) == []
    assert [b[0] for b in kpi.divergence_failures(full)] == ["2011"]
