"""Power BI card checklist (quality/pbi_cards.py), §7 of reports/kpi_reconciliation.md."""

from __future__ import annotations

import psycopg
import pytest

from dubai_property import db
from dubai_property.powerbi import tmdl
from dubai_property.quality import kpi_reconciliation as kr
from dubai_property.quality import pbi_cards as pc

SILVER = {
    "2024": {"market_sales": 10, "market_value": 2e9, "ready_sales": 4, "purchase_mortgages": 1},
    "2025": {
        "market_sales": 211_007,
        "market_value": 668_312_345_678,
        "median_ppsqm": 17_828.4,
        "ready_sales": 77_154,
        "purchase_mortgages": 21_537,
        "new_mortgages": 37_715,
        "offplan_sales": 133_853,
        "offplan_value": 291_400_000_000,
        "portfolio_deals": 345,
        "aw_value": 2_000,
        "aw_area": 1,
        "market_rents": 307_680,
        "rent_aw_value": 852,
        "rent_aw_area": 1,
    },
    "2026": {"market_sales": 1},
    "all": {"market_sales": 5, "market_value": 1e9},
}


def test_formatting_matches_the_measure_format_strings():
    assert pc.pct(0.27914) == "27.9%" and pc.pct(0.06831, 2) == "6.83%"
    assert pc.signed_pct(0.046) == "+4.6%" and pc.signed_pct(-0.051) == "-5.1%"
    assert pc.aed_bn(668_312_345_678) == "AED 668.3bn"
    assert pc.aed(17_828.4) == "AED 17,828"
    assert pc.num(211_007) == "211,007" and pc.num(17.94, 1) == "17.9"
    assert pc.pct(None) == pc.aed(None) == "(blank)"


def test_default_year_is_the_latest_complete_year():
    assert pc.latest_complete_year(SILVER, 2026) == "2025"
    assert pc.latest_complete_year({"2026": {}}, 2026) == "2026"  # fixtures: no full year


def test_pre_ml_cards_use_the_reconciled_kpis():
    cards = {(c.card, c.filters): c.expected for c in pc.pre_ml_cards(SILVER, kr.derive, "2025")}
    assert cards[("Market Sales", "Year = 2025")] == "211,007"
    assert cards[("Market Sales Value", "Year = 2025")] == "AED 668.3bn"
    assert cards[("Purchase Mortgage Share", "Year = 2025")] == "27.9%"
    assert cards[("New Mortgages per 100 Sales", "Year = 2025")] == "17.9"
    assert cards[("Market Sales", "no Year selected")] == "5"


def test_pre_ml_cards_name_measures_in_the_model():
    measures = {m.name for _, m in tmdl.load().measures()}
    names = {c.card for c in pc.pre_ml_cards(SILVER, kr.derive, "2025")}
    assert names <= measures, names - measures


def test_render_without_models_says_where_the_rest_comes_from():
    lines = pc.render(pc.pre_ml_cards(SILVER, kr.derive, "2025"), None, "2025")
    text = "\n".join(lines)
    assert text.startswith("## 7. Power BI card checklist")
    assert "Year = 2025" in text and "make score" in text


@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        if not pc.post_ml_available(c):
            pytest.skip("post_ml views not built (make score)")
        yield c


@pytest.mark.db
def test_post_ml_cards_have_values_on_the_full_data(conn):
    (lines,) = conn.execute("select count(*) from rpt.transactions").fetchone()
    if lines < kr.DIVERGENCE_MIN_LINES:
        pytest.skip("fixture-sized data: model cards may be legitimately blank")
    cards = pc.post_ml_cards(conn, "2025")
    measures = {m.name for _, m in tmdl.load().measures()}
    assert {c.card for c in cards} <= measures, {c.card for c in cards} - measures
    blank = [c for c in cards if "(blank)" in c.expected]
    assert not blank, blank
    by = {(c.card, c.filters): c.expected for c in cards}
    # Spot checks against the published reports (avm_model_card.md, stress_test.md).
    assert by[("AVM Test MdAPE", "none")] == "6.83%"
    key = ("Negative Equity Share", "Stress segment = Apartments; Ready; Shock -20; LTV 80")
    assert by[key] == "22.4%"
