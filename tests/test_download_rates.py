from datetime import date

import pytest

from dubai_property.ingest import download_rates as dr

FEDFUNDS_CSV = b"observation_date,FEDFUNDS\n1954-07-01,0.80\n1954-08-01,1.22\n"


def test_check_fred_csv_counts_observations():
    assert dr.check_fred_csv("FEDFUNDS", FEDFUNDS_CSV) == 2


def test_check_fred_csv_rejects_error_page():
    with pytest.raises(ValueError):
        dr.check_fred_csv("FEDFUNDS", b"<!DOCTYPE html><html>Not found</html>")


def test_download_fred_writes_dated_snapshot_once(tmp_path):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return FEDFUNDS_CSV

    day = date(2026, 9, 30)
    path = dr.download_fred("FEDFUNDS", root=tmp_path, today=day, fetcher=fake_fetch)
    assert path == tmp_path / "fred" / "fedfunds" / "FEDFUNDS_2026-09-30.csv"
    assert path.read_bytes() == FEDFUNDS_CSV
    assert calls == ["https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS"]
    # Same day again: no second request, same file.
    assert dr.download_fred("FEDFUNDS", root=tmp_path, today=day, fetcher=fake_fetch) == path
    assert len(calls) == 1


def test_eibor_is_skipped_when_no_files(tmp_path):
    assert dr.eibor_files(tmp_path) == []
