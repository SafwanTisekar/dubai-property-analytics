"""Integration tests for `make db`: schemas, encoding and pbi_reader's rpt-only access.

Skipped when the database isn't reachable (e.g. a laptop without Postgres running).
CI runs them against a postgres:18 service container after `make db`.
"""

import os

import psycopg
import pytest

from dubai_property import db
from dubai_property.config import SCHEMAS

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def settings():
    try:
        s = db.PgSettings.from_env()
        with db.connect(s, connect_timeout=3):
            pass
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    return s


@pytest.fixture(scope="module")
def reader_settings(settings):
    password = os.environ.get("PBI_READER_PASSWORD")
    if not password:
        pytest.skip("PBI_READER_PASSWORD not set")
    return db.PgSettings(settings.host, settings.port, settings.dbname, "pbi_reader", password)


def test_all_schemas_exist_and_owned_by_dpa_owner(settings):
    with db.connect(settings) as conn:
        rows = conn.execute(
            "select nspname, pg_get_userbyid(nspowner) from pg_namespace where nspname = any(%s)",
            [list(SCHEMAS)],
        ).fetchall()
    assert dict(rows) == {schema: "dpa_owner" for schema in SCHEMAS}


def test_database_is_utf8(settings):
    with db.connect(settings) as conn:
        (encoding,) = conn.execute(
            "select pg_encoding_to_char(encoding) from pg_database"
            " where datname = current_database()"
        ).fetchone()
    assert encoding == "UTF8"


def test_pbi_reader_can_use_rpt_only(reader_settings):
    with db.connect(reader_settings) as conn:
        for schema in SCHEMAS:
            (has_usage,) = conn.execute(
                "select has_schema_privilege(current_user, %s, 'USAGE')", [schema]
            ).fetchone()
            assert has_usage is (schema == "rpt"), schema


def test_future_rpt_views_are_readable_by_pbi_reader(settings, reader_settings):
    """Default privileges: a view dbt (as dpa_owner) creates later is SELECT-able."""
    with db.connect(settings, autocommit=True) as owner, db.connect(reader_settings) as reader:
        owner.execute("drop view if exists rpt._grant_probe")
        owner.execute("drop table if exists gold._grant_probe")
        try:
            owner.execute("create table gold._grant_probe as select 1 as x")
            owner.execute("create view rpt._grant_probe as select x from gold._grant_probe")
            assert reader.execute("select x from rpt._grant_probe").fetchone() == (1,)
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                reader.execute("select x from gold._grant_probe")
        finally:
            owner.execute("drop view if exists rpt._grant_probe")
            owner.execute("drop table if exists gold._grant_probe")
