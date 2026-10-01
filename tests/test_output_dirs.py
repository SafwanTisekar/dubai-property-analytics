"""Scratch-DB guard: only the main database writes the committed reports.

In Phase 4a a CI-style run against a scratch database overwrote
reports/kpi_reconciliation.md with fixture numbers. Every DB-derived writer now resolves
its directory through db.reports_dir() / figures_dir() / artifacts_dir() at run time.
"""

import pytest

from dubai_property import config, db
from dubai_property.analysis import plotting
from dubai_property.ingest import load_bronze
from dubai_property.models import hedonic_index
from dubai_property.quality import (
    data_dictionary,
    dq_report,
    investigate,
    kpi_reconciliation,
    reconcile,
    unzoned_areas,
)

REPORT_MODULES = [kpi_reconciliation, dq_report, reconcile, investigate, unzoned_areas]


@pytest.fixture
def scratch_db(monkeypatch, tmp_path):
    monkeypatch.setenv("PG_DB", "dpa_scratch")
    # Keep the test from creating folders in the repo.
    monkeypatch.setattr(config, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(config, "ARTIFACTS", tmp_path / "artifacts")
    return tmp_path


def test_main_db_writes_the_committed_reports(monkeypatch):
    monkeypatch.setenv("PG_DB", config.MAIN_DB)
    assert db.is_main_db()
    assert db.reports_dir() == config.REPORTS
    assert db.figures_dir() == config.FIGURES
    assert db.artifacts_dir() == config.ARTIFACTS
    assert kpi_reconciliation.report_path() == config.REPORTS / "kpi_reconciliation.md"
    assert data_dictionary.dictionary_path() == data_dictionary.DICTIONARY_PATH


def test_scratch_db_never_resolves_to_a_committed_report(scratch_db):
    assert not db.is_main_db()
    scratch = config.REPORTS / config.SCRATCH_DIRNAME / "dpa_scratch"
    assert db.reports_dir() == scratch
    assert db.figures_dir() == scratch / "figures"
    assert db.artifacts_dir() == config.ARTIFACTS / config.SCRATCH_DIRNAME / "dpa_scratch"
    for module in REPORT_MODULES:
        path = module.report_path()
        assert path.parent == scratch, module.__name__
        assert path != config.REPORTS / path.name
    assert hedonic_index.diagnostics_path().is_relative_to(db.artifacts_dir())
    assert data_dictionary.dictionary_path().parent == scratch


def test_scratch_db_figures_and_ingest_log(scratch_db, monkeypatch):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    path = plotting.save(fig, "probe")
    plt.close(fig)
    assert path.parent == db.figures_dir()
    assert config.SCRATCH_DIRNAME in path.parts

    load_bronze.append_ingest_log([dict.fromkeys(load_bronze.LOG_FIELDS, "x")])
    assert (db.reports_dir() / config.INGEST_LOG.name).exists()
    assert not (config.REPORTS / config.INGEST_LOG.name).exists()


def test_odd_database_names_make_safe_folder_names(scratch_db, monkeypatch):
    monkeypatch.setenv("PG_DB", "scratch db/../x")
    assert db.reports_dir().parent == config.REPORTS / config.SCRATCH_DIRNAME
    assert "/" not in db.reports_dir().name


def test_ingest_log_on_the_main_db_follows_config(monkeypatch, tmp_path):
    # Tests redirect config.INGEST_LOG; only its folder was being swapped, which leaked a
    # reports/log.csv into the repo on every pytest run.
    monkeypatch.setenv("PG_DB", config.MAIN_DB)
    monkeypatch.setattr(config, "INGEST_LOG", tmp_path / "log.csv")
    load_bronze.append_ingest_log([{"dataset": "probe", "status": "skipped"}])
    assert (tmp_path / "log.csv").exists()
