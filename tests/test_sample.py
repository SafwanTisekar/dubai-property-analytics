"""`make sample`: stratified, deterministic, whole-group sampling that the loader can reload."""

import csv

import psycopg
import pytest

from dubai_property import config, db
from dubai_property.ingest import load_bronze as lb
from dubai_property.ingest import sample

pytestmark = pytest.mark.db

PROBE = config.Dataset(
    "pytest_sample_probe",
    "dld/pytest_sample_probe",
    "_pytest_sample_probe",
    "bulk",
    sample_key="contract_id",
    sample_date="contract_start_date",
)


def build_csv(path):
    """200 contracts in one big stratum (2024 x area 1) plus 1 contract in a tiny one.

    Every 10th contract has 3 lines, like a multi-unit Ejari contract.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["contract_id", "line_number", "contract_start_date", "area_id"])
        for i in range(200):
            for line in range(1, 4 if i % 10 == 0 else 2):
                w.writerow([f"CNT{i}", line, "2024-03-01", "1"])
        w.writerow(["CNT_RARE", 1, "2009-06-01", "2"])


@pytest.fixture
def conn():
    try:
        connection = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with connection:
        lb.ensure_manifest_table(connection)
        lb.reset_dataset(connection, PROBE)
        yield connection
        connection.rollback()
        lb.reset_dataset(connection, PROBE)


def read_rows(path):
    with path.open() as fh:
        return list(csv.DictReader(fh))


def test_sample_is_stratified_whole_group_and_deterministic(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "INGEST_LOG", tmp_path / "log.csv")
    build_csv(tmp_path / "raw" / PROBE.subdir / "probe_2026-09-30.csv")
    lb.load_dataset(conn, PROBE, tmp_path / "raw")

    out = tmp_path / "sample"
    path = sample.write_sample(conn, PROBE, 0.1, out)
    rows = read_rows(path)
    contracts = {r["contract_id"] for r in rows}

    # 10% of 200 contracts in the big stratum, plus the only contract in the tiny one.
    assert len(contracts) == 21
    assert "CNT_RARE" in contracts
    # Whole groups: a sampled multi-line contract keeps all 3 of its lines.
    for cid in contracts:
        lines = [r for r in rows if r["contract_id"] == cid]
        expected = 1 if cid == "CNT_RARE" else (3 if int(cid[3:]) % 10 == 0 else 1)
        assert len(lines) == expected, cid
    # Deterministic: a second run gives the same file.
    assert sample.write_sample(conn, PROBE, 0.1, out).read_bytes() == path.read_bytes()
    # The sample loads with the same loader (same column set, every field quoted).
    info = lb.inspect_file(path)
    assert info.columns == ["contract_id", "line_number", "contract_start_date", "area_id"]
    assert info.records == len(rows)
