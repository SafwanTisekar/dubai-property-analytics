import pytest

from dubai_property import db

ENV = {
    "PG_HOST": "db.example",
    "PG_PORT": "5433",
    "PG_DB": "dubai_property",
    "PG_USER": "dpa_owner",
    "PG_PASSWORD": "p@ss:w/rd#1",
}


@pytest.fixture
def env(monkeypatch):
    # Stop python-dotenv from reading the developer's real .env during unit tests.
    monkeypatch.setattr(db, "load_dotenv", lambda *a, **k: False)
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_settings_from_env(env):
    s = db.PgSettings.from_env()
    assert (s.host, s.port, s.dbname, s.user) == ("db.example", 5433, "dubai_property", "dpa_owner")


def test_urls_encode_special_characters(env):
    s = db.PgSettings.from_env()
    encoded = "dpa_owner:p%40ss%3Aw%2Frd%231@db.example:5433/dubai_property"
    assert s.sqlalchemy_url() == f"postgresql+psycopg://{encoded}"
    assert s.connectorx_uri() == f"postgresql://{encoded}"
    assert db.connectorx_uri() == f"postgresql://{encoded}"


def test_conninfo_contains_all_parts(env):
    info = db.PgSettings.from_env().conninfo()
    for part in ("host=db.example", "port=5433", "dbname=dubai_property", "user=dpa_owner"):
        assert part in info


def test_missing_setting_raises(env):
    env.delenv("PG_PASSWORD")
    with pytest.raises(RuntimeError, match="PG_PASSWORD"):
        db.PgSettings.from_env()
