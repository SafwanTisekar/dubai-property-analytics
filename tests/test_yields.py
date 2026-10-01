"""Gross yields: the publishing rules on synthetic cells (CI) and the written table (DB)."""

import logging
from datetime import date

import polars as pl
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.models import yields

Q = date(2025, 1, 1)


def cell(level, area_key, n_rent, n_sale, rent=80_000.0, price=1_200_000.0, bedrooms=1):
    return {
        "geo_level": level,
        "quarter_start": Q,
        "zone": "Zone A",
        "area_key": area_key,
        "property_type_key": 101,
        "bedrooms": bedrooms,
        "n_rent": n_rent,
        "n_sale": n_sale,
        "median_annual_rent_aed": rent,
        "median_price_aed": price,
    }


@pytest.fixture
def cells():
    return pl.DataFrame(
        [
            cell("area", 1, 40, 25),  # passes
            cell("area", 2, 40, 19),  # sales under min-n: zone only
            cell("area", 3, 5, 0, price=None),  # rent only: zone only
            cell("zone", None, 85, 44),  # recomputed from all three areas' rows
            cell("zone", None, 12, 30, bedrooms=2),  # zone under min-n: not published
            cell("area", 4, 30, 30, rent=400_000.0, price=1_000_000.0, bedrooms=3),  # 40%
        ]
    )


def test_only_cells_with_min_n_on_both_sides_are_published(cells):
    out = yields.publish(cells)
    assert out.filter(pl.col("geo_level") == "area")["area_key"].to_list() == [1, 4]
    zone = out.filter(pl.col("geo_level") == "zone")
    assert zone.height == 1 and zone["areas_rolled_up"].to_list() == [2]
    assert (out["n_rent"] >= config.MIN_N).all() and (out["n_sale"] >= config.MIN_N).all()


def test_yield_is_median_rent_over_median_price(cells):
    out = yields.publish(cells)
    first = out.filter(pl.col("area_key") == 1).row(0, named=True)
    assert first["gross_yield"] == pytest.approx(80_000 / 1_200_000)
    assert out["gross_yield"].is_between(0, 1).all()


def test_out_of_band_yields_are_flagged_and_logged(cells, caplog):
    out = yields.publish(cells)
    assert out.filter(pl.col("is_outside_sanity"))["area_key"].to_list() == [4]
    with caplog.at_level(logging.WARNING):
        assert yields.warn_outside_sanity(out) == 1
    assert "outside 2-15%" in caplog.text


def test_cell_query_uses_market_rents_and_ready_sales():
    sql = yields.cells_sql()
    assert "r.is_market_rent" in sql  # new, single-line contracts (C11)
    assert "not t.is_offplan" in sql and "t.is_clean_market_sale" in sql
    assert "grouping sets" in sql


# --- Written table (skipped until make train has run) --------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        if c.execute("select to_regclass('ml.agg_yield_quarter')").fetchone()[0] is None:
            pytest.skip("ml.agg_yield_quarter not built yet (run make train)")
        yield c


@pytest.mark.db
def test_written_yields_respect_min_n_and_range(conn):
    (bad,) = conn.execute(
        """
        select count(*) from ml.agg_yield_quarter
        where n_rent < %(n)s or n_sale < %(n)s or gross_yield not between 0 and 1
           or (geo_level = 'area') <> (area_key is not null)
        """,
        {"n": config.MIN_N},
    ).fetchone()
    assert bad == 0
