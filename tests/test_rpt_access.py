"""rpt is what Power BI sees: pbi_reader reads every rpt view and nothing else.

Skipped until `make dbt` has built the rpt views (CI runs this file again after the build).
"""

import os

import psycopg
import pytest

from dubai_property import db
from dubai_property.config import SCHEMAS

pytestmark = pytest.mark.db

# Every view Power BI imports (docs/06 §1). A missing or extra view fails the test, so the
# list here and the dbt reporting folder can't drift apart.
EXPECTED_VIEWS = {
    "area_month",
    "dim_area",
    "dim_date",
    "dim_procedure",
    "dim_project",
    "dim_property_type",
    "price_index",
    "rates_monthly",
    "rent_month",
    "report_info",
    "transactions",
    "yield_quarter",
}


@pytest.fixture(scope="module")
def owner():
    try:
        conn = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with conn:
        (n,) = conn.execute("select count(*) from pg_views where schemaname = 'rpt'").fetchone()
        if n == 0:
            pytest.skip("rpt views not built yet (run make dbt)")
        yield conn


@pytest.fixture(scope="module")
def reader(owner):
    password = os.environ.get("PBI_READER_PASSWORD")
    if not password:
        pytest.skip("PBI_READER_PASSWORD not set")
    s = db.PgSettings.from_env()
    with db.connect(db.PgSettings(s.host, s.port, s.dbname, "pbi_reader", password)) as conn:
        yield conn


def rpt_views(conn) -> set[str]:
    rows = conn.execute("select viewname from pg_views where schemaname = 'rpt'").fetchall()
    return {r[0] for r in rows}


def test_rpt_holds_exactly_the_power_bi_views(owner):
    assert rpt_views(owner) == EXPECTED_VIEWS


def test_rpt_has_only_views(owner):
    (tables,) = owner.execute("select count(*) from pg_tables where schemaname = 'rpt'").fetchone()
    assert tables == 0


def test_pbi_reader_can_read_every_rpt_view(reader):
    for view in sorted(EXPECTED_VIEWS):
        reader.execute(f'select * from rpt."{view}" limit 1').fetchall()


def test_pbi_reader_cannot_read_other_layers(owner, reader):
    """No schema other than rpt is usable, and no table outside rpt is selectable."""
    for schema in SCHEMAS:
        (usage,) = reader.execute(
            "select has_schema_privilege(current_user, %s, 'USAGE')", [schema]
        ).fetchone()
        assert usage is (schema == "rpt"), schema
    (readable,) = reader.execute(
        "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = any(%s) and n.nspname <> 'rpt' and c.relkind in ('r', 'v', 'm')"
        " and has_table_privilege(current_user, c.oid, 'SELECT')",
        [list(SCHEMAS)],
    ).fetchone()
    assert readable == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader.execute("select 1 from gold.fct_transaction limit 1")


def test_rpt_columns_are_friendly(owner):
    """Title Case names only: no snake_case, no _ar columns, no raw C-rule flags."""
    rows = owner.execute(
        "select table_name, column_name from information_schema.columns where table_schema = 'rpt'"
    ).fetchall()
    assert rows
    bad = [(t, c) for t, c in rows if "_" in c or c != c.strip() or not c[:1].isupper()]
    assert bad == []


def test_rpt_transactions_has_no_text_ids(owner):
    """High-cardinality ids stay in gold to keep the Power BI model small (docs/06 §1)."""
    rows = owner.execute(
        "select column_name from information_schema.columns"
        " where table_schema = 'rpt' and table_name = 'transactions'"
    ).fetchall()
    names = {r[0].lower() for r in rows}
    assert not {n for n in names if "transaction id" in n or "group id" in n or "building" in n}
