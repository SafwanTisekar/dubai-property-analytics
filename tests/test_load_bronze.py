"""Tests for the bronze loader: pure helpers, plus a round trip through Postgres."""

import csv
import json
from datetime import date

import psycopg
import pytest

from dubai_property import config, db
from dubai_property.ingest import load_bronze as lb

ARABIC = "حدائق الشيخ محمد بن راشد"

# Record 2 has a line break inside a quoted field: 3 records, but 4 data lines.
CSV_TEXT = (
    '"transaction_id","area_name_en","area_name_ar","actual_worth"\n'
    f'"1-102-2024-1","Dubai Marina","{ARABIC}","4433600.00"\n'
    '"1-102-2024-2","Line one\nline two","","1950000.00"\n'
    '"1-102-2024-3","Business Bay","",""\n'
)


def write_csv(path, text, *, bom=False, encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode(encoding)
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    return path


# --- Pure helpers ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TRANS_VALUE", "trans_value"),
        ("actual_worth", "actual_worth"),
        ("\ufeffTRANSACTION_NUMBER", "transaction_number"),
        ("Area (sq m)", "area_sq_m"),
        ("observation_date", "observation_date"),
        ("contractAmount", "contract_amount"),
        ("3M EIBOR", "c_3m_eibor"),
    ],
)
def test_snake_case(raw, expected):
    assert lb.snake_case(raw) == expected


def test_normalise_header_deduplicates():
    assert lb.normalise_header(["A", "a", "B"]) == ["a", "a_2", "b"]


def test_source_columns_never_collide_with_metadata():
    assert lb.normalise_header(["_source_file", "_row_hash"]) == ["source_file", "row_hash"]


def test_snapshot_date_from_filename(tmp_path):
    f = tmp_path / "rent_contracts_2026-09-30_00-46-44_0001.csv"
    f.write_text("a\n")
    assert lb.snapshot_date_for(f) == date(2026, 9, 30)


def test_snapshot_date_falls_back_to_mtime(tmp_path):
    f = tmp_path / "no_date.csv"
    f.write_text("a\n")
    assert isinstance(lb.snapshot_date_for(f), date)


def test_inspect_counts_records_not_lines(tmp_path):
    info = lb.inspect_file(write_csv(tmp_path / "t.csv", CSV_TEXT))
    assert info.records == 3
    assert info.physical_lines == 5  # header + 3 records + 1 embedded newline
    assert info.columns == ["transaction_id", "area_name_en", "area_name_ar", "actual_worth"]
    assert info.encoding == "utf-8" and not info.had_bom
    assert info.sha256 == lb.file_sha256(tmp_path / "t.csv")


def test_inspect_detects_bom(tmp_path):
    info = lb.inspect_file(write_csv(tmp_path / "t.csv", CSV_TEXT, bom=True))
    assert info.had_bom
    assert info.header[0] == "transaction_id"  # BOM not glued to the first column name


def test_inspect_falls_back_to_windows_1256(tmp_path):
    info = lb.inspect_file(write_csv(tmp_path / "t.csv", CSV_TEXT, encoding="cp1256"))
    assert info.encoding == "cp1256" and info.pg_encoding == "WIN1256"
    assert info.records == 3


def test_discover_ignores_non_csv(tmp_path):
    (tmp_path / "README.txt").write_text("x")
    (tmp_path / "b.csv").write_text("a\n")
    (tmp_path / "a.CSV").write_text("a\n")
    assert [p.name for p in lb.discover_files(tmp_path)] == ["a.CSV", "b.csv"]
    assert lb.discover_files(tmp_path / "missing") == []


def test_source_prefix_names_data_and_repo_roots(tmp_path, monkeypatch):
    # Under data/: relative to data/. Elsewhere in the repo (CI fixtures): relative to the
    # project root, so _source_file never holds a machine-specific absolute path.
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    (tmp_path / "data" / "sample").mkdir(parents=True)
    (tmp_path / "tests" / "fixtures").mkdir(parents=True)
    assert lb._source_prefix(tmp_path / "data" / "sample") == "sample/"
    assert lb._source_prefix(tmp_path / "tests" / "fixtures") == "tests/fixtures/"


def test_every_dataset_targets_a_unique_bronze_table():
    tables = [d.table for d in config.DATASETS]
    assert len(tables) == len(set(tables))
    assert config.DATASETS_BY_NAME["transactions"].table == "dld_transactions"
    assert config.DATASETS_BY_NAME["rents"].table == "dld_rent_contracts"


# --- Round trip through Postgres ------------------------------------------------------

TEST_DATASET = config.Dataset("pytest_probe", "dld/pytest_probe", "_pytest_probe", "bulk")


@pytest.fixture
def conn():
    try:
        connection = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with connection:
        lb.ensure_manifest_table(connection)
        lb.reset_dataset(connection, TEST_DATASET)
        yield connection
        connection.rollback()
        lb.reset_dataset(connection, TEST_DATASET)


@pytest.mark.db
def test_load_round_trip(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    root = tmp_path / "raw"
    folder = root / TEST_DATASET.subdir
    write_csv(folder / "probe_2026-09-29_0001.csv", CSV_TEXT, bom=True)
    write_csv(
        folder / "probe_2026-09-30_0002.csv", CSV_TEXT.replace('-1"', '-9"'), encoding="cp1256"
    )
    log_path = tmp_path / "ingest_log.csv"
    monkeypatch.setattr(config, "INGEST_LOG", log_path)

    rows = lb.load_dataset(conn, TEST_DATASET, root)
    assert [r["status"] for r in rows] == ["loaded", "loaded"]
    assert all(r["rows_in_file"] == r["rows_loaded"] == 3 for r in rows)

    t = f"bronze.{TEST_DATASET.table}"
    got = conn.execute(
        f"select _source_file, _source, _snapshot_date, count(*), count(distinct _row_hash)"
        f" from {t} group by 1, 2, 3 order by 1"
    ).fetchall()
    assert got == [
        ("raw/dld/pytest_probe/probe_2026-09-29_0001.csv", "bulk", date(2026, 9, 29), 3, 3),
        ("raw/dld/pytest_probe/probe_2026-09-30_0002.csv", "bulk", date(2026, 9, 30), 3, 3),
    ]
    # Arabic survives both the UTF-8 file and the Windows-1256 file; embedded newline kept.
    arabic = conn.execute(f"select distinct area_name_ar from {t} where area_name_ar <> ''")
    assert arabic.fetchall() == [(ARABIC,)]
    (multiline,) = conn.execute(
        f"select area_name_en from {t} where transaction_id = '1-102-2024-2' limit 1"
    ).fetchone()
    assert multiline == "Line one\nline two"
    # Quoted empty fields stay '' in bronze (no transformation); NULL handling is silver's job.
    (empty,) = conn.execute(
        f"select actual_worth from {t} where transaction_id = '1-102-2024-3' limit 1"
    ).fetchone()
    assert empty == ""
    # Column defaults used for metadata are removed after each load.
    defaults = conn.execute(
        "select count(*) from information_schema.columns where table_schema = 'bronze'"
        " and table_name = %s and column_name in ('_source_file', '_source', '_snapshot_date')"
        " and column_default is not null",
        [TEST_DATASET.table],
    ).fetchone()
    assert defaults == (0,)

    # Re-running is a no-op: both files are skipped via the manifest.
    again = lb.load_dataset(conn, TEST_DATASET, root)
    assert [r["status"] for r in again] == ["skipped", "skipped"]
    assert conn.execute(f"select count(*) from {t}").fetchone() == (6,)

    # The manifest lists these files (and any real ones already loaded under raw/).
    manifest = json.loads(lb.export_manifest_json(conn, root).read_text())
    probe = {k: v for k, v in manifest["files"].items() if "pytest_probe" in k}
    assert set(probe) == {
        "raw/dld/pytest_probe/probe_2026-09-29_0001.csv",
        "raw/dld/pytest_probe/probe_2026-09-30_0002.csv",
    }
    assert {v["encoding"] for v in probe.values()} == {"UTF8", "WIN1256"}

    lb.append_ingest_log(rows + again, log_path)
    with log_path.open() as fh:
        logged = list(csv.DictReader(fh))
    assert [r["status"] for r in logged] == ["loaded", "loaded", "skipped", "skipped"]


@pytest.mark.db
def test_schema_drift_is_refused(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    root = tmp_path / "raw"
    folder = root / TEST_DATASET.subdir
    write_csv(folder / "a_2026-01-01.csv", CSV_TEXT)
    lb.load_dataset(conn, TEST_DATASET, root)
    write_csv(folder / "b_2026-02-01.csv", '"transaction_id","new_col"\n"x","y"\n')
    monkeypatch.setattr(config, "INGEST_LOG", tmp_path / "log.csv")
    with pytest.raises(lb.IngestError, match="schema drift"):
        lb.load_dataset(conn, TEST_DATASET, root)
    # The failed file left nothing behind.
    assert conn.execute(f"select count(*) from bronze.{TEST_DATASET.table}").fetchone() == (3,)


# --- Main-database guard ------------------------------------------------------------------
def test_guard_refuses_a_non_raw_root_on_the_main_database():
    fixtures = config.PROJECT_ROOT / "tests" / "fixtures"
    with pytest.raises(lb.IngestError, match="only"):
        lb.check_target(config.MAIN_DB, fixtures, reset=False, env={})
    # Even with the reset switch: the switch allows a reload of data/raw, nothing else.
    with pytest.raises(lb.IngestError, match="only"):
        lb.check_target(config.MAIN_DB, fixtures, reset=True, env={"ALLOW_MAIN_RESET": "1"})


def test_guard_refuses_reset_on_the_main_database_without_the_switch():
    with pytest.raises(lb.IngestError, match="ALLOW_MAIN_RESET"):
        lb.check_target(config.MAIN_DB, config.DATA_RAW, reset=True, env={})
    with pytest.raises(lb.IngestError, match="ALLOW_MAIN_RESET"):
        lb.check_target(config.MAIN_DB, config.DATA_RAW, reset=True, env={"CI": "true"})
    lb.check_target(config.MAIN_DB, config.DATA_RAW, reset=True, env={"ALLOW_MAIN_RESET": "1"})


def test_guard_allows_incremental_raw_loads_ci_fixtures_and_scratch_databases():
    fixtures = config.PROJECT_ROOT / "tests" / "fixtures"
    lb.check_target(config.MAIN_DB, config.DATA_RAW, reset=False, env={})
    lb.check_target(config.MAIN_DB, fixtures, reset=False, env={"CI": "true"})
    lb.check_target("dubai_property_scratch", fixtures, reset=True, env={})


def test_run_checks_the_target_before_connecting(monkeypatch):
    monkeypatch.setattr(lb.db, "current_dbname", lambda: config.MAIN_DB)
    monkeypatch.delenv("CI", raising=False)

    def no_connect(*args, **kwargs):
        raise AssertionError("connected before the guard")

    monkeypatch.setattr(lb.db, "connect", no_connect)
    with pytest.raises(lb.IngestError):
        lb.run(config.PROJECT_ROOT / "tests" / "fixtures", list(config.DATASETS), reset=True)
