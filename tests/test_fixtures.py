"""The committed CI fixtures (tests/fixtures) still cover what the dbt tests need.

``make fixtures`` rebuilds them from full bronze. These tests catch a rebuild that
silently lost an edge case, since CI's dbt build is only as good as its input.
"""

import csv
from collections import Counter

import pytest

from dubai_property import config
from dubai_property.ingest import fixtures

ROOT = fixtures.FIXTURES_ROOT
MAX_LINES = 3000  # "about 2k lines per table": keep the repo small


def read(dataset: str) -> tuple[list[str], list[dict[str, str]]]:
    folder = ROOT / config.DATASETS_BY_NAME[dataset].subdir
    files = sorted(folder.glob("*.csv"))
    assert len(files) == 1, f"expected one fixture file in {folder}"
    with files[0].open(newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


@pytest.fixture(scope="module")
def transactions():
    return read("transactions")


@pytest.fixture(scope="module")
def rents():
    return read("rents")


def test_attribution_is_committed_with_the_data():
    text = (ROOT / "README.md").read_text()
    assert "Dubai Land Department" in text
    assert "CC BY 4.0" in text


def test_every_field_is_quoted_like_the_dld_files():
    for dataset in ("transactions", "rents"):
        folder = ROOT / config.DATASETS_BY_NAME[dataset].subdir
        first_data_line = next(iter(folder.glob("*.csv"))).read_text().splitlines()[1]
        assert first_data_line.startswith('"') and first_data_line.endswith('"')


def test_transactions_cover_every_year_and_the_edge_cases(transactions):
    header, rows = transactions
    assert len(header) == 47 and "transaction_id" in header
    assert len(rows) <= MAX_LINES
    years = {r["instance_date"][:4] for r in rows}
    assert {str(y) for y in range(2004, 2027)} <= years
    assert any(r["instance_date"] < "1900" for r in rows), "Hijri dates (C18)"
    assert any("1900" <= r["instance_date"] < "2004" for r in rows), "pre-2004 (C18)"
    assert any(r["property_usage_en"] == "أخرى" for r in rows), "swapped usage label (C19)"
    pairs = {(r["trans_group_en"], r["procedure_id"]) for r in rows}
    assert len(pairs) >= 50, "nearly every (group, procedure) pair (C2)"
    lto = {r["procedure_id"] for r in rows if r["trans_group_en"] == "Sales"} & {"110", "107"}
    assert lto, "lease-to-own Sales legs (C17)"


def test_transactions_keep_portfolio_groups_whole(transactions):
    # C16 needs every line of a repeated-value group: at least one candidate group with
    # several lines and different unit sizes must be present.
    _, rows = transactions
    groups = Counter(
        (
            r["trans_group_en"],
            r["procedure_id"],
            r["instance_date"],
            r["actual_worth"],
            r["transaction_id"].split("-")[2],
        )
        for r in rows
    )
    assert sum(1 for n in groups.values() if n > 1) >= 10


def test_rents_cover_multi_unit_contracts_and_non_market_types(rents):
    header, rows = rents
    assert len(header) == 41 and "contract_id" in header
    assert len(rows) <= MAX_LINES
    lines = Counter(r["contract_id"] for r in rows)
    multi = [c for c, n in lines.items() if n > 1]
    assert len(multi) >= 10, "multi-line contracts (C11)"
    for cid in multi:  # whole contracts: line numbers 1..n
        numbers = sorted(int(r["line_number"]) for r in rows if r["contract_id"] == cid)
        assert numbers == list(range(1, len(numbers) + 1)), cid
    assert any(r["ejari_bus_property_type_en"] == "Virtual Unit" for r in rows), "C20"
    assert any(r["ejari_property_type_en"] == "Labor Camps" for r in rows), "C20"
    assert any(r["actual_area"] in ("", "0.00", "1.00") for r in rows), "C21"
    assert any(r["area_id"] == "" for r in rows), "blank area_id"
    assert any(r["contract_end_date"] > "2040" for r in rows), "implausible end date (C18)"
