"""The Power BI semantic model (TMDL) stays in line with the rpt views (docs/06 §2–3).

Offline: reads the TMDL files and the dbt reporting SQL, no database or Power BI needed,
so CI catches a renamed rpt column, a measure pointing at a column that doesn't exist, or
a what-if table that no longer matches the stress grid, before Desktop does.
"""

from __future__ import annotations

import re

import pytest

from dubai_property import config
from dubai_property.powerbi import tmdl

REPORTING = config.DBT_DIR / "models" / "reporting"

# Display folders by page topic (docs/06 §2); subfolders (Risk\Outlook) count by top level.
FOLDERS = {"Market", "Financing", "Prices", "Yields", "Valuation", "Risk", "Rates", "Report"}
# Model outputs at mixed grains (Dubai / zone / area rows, NULL keys): never related, so an
# area slicer can't silently drop their Dubai and zone rows. Measures bridge with TREATAS.
DISCONNECTED = {
    "Price Index",
    "DLD Price Index",
    "Yield Quarter",
    "Stress Grid",
    "Stress Replay",
    "Forecast",
    "Forecast Backtest",
    "AVM Performance",
    "Feature Importance",
    "Report Info",
}


@pytest.fixture(scope="module")
def model() -> tmdl.Model:
    return tmdl.load()


def view_columns() -> dict[str, list[str]]:
    """rpt view -> its output column names, from the dbt SQL (the last SELECT's aliases)."""
    out = {}
    for path in sorted(REPORTING.glob("rpt_*.sql")):
        sql = path.read_text()
        alias = re.search(r"alias\s*=\s*'([^']+)'", sql).group(1)
        code = re.sub(r"--[^\n]*", "", sql)
        # Aliases of the final SELECT (CTE-internal aliases are unquoted in these views).
        out[alias] = re.findall(r'\bas\s+"([^"]+)"', code)
    return out


def test_every_rpt_view_is_imported_once(model):
    imported = [t.rpt_view for t in model.tables.values() if t.rpt_view]
    assert sorted(imported) == sorted(view_columns())


def test_table_columns_equal_the_view_columns(model):
    views = view_columns()
    for t in model.tables.values():
        if t.rpt_view:
            cols = [c.source_column for c in t.columns]
            assert sorted(cols) == sorted(views[t.rpt_view]), t.name


def test_partitions_use_the_server_parameters(model):
    assert {"PgServer", "PgDatabase"} <= set(model.expressions)
    for t in model.tables.values():
        for p in t.partitions:
            if p.kind == "m":
                assert "PostgreSQL.Database(PgServer, PgDatabase)" in p.source, t.name
                assert not re.search(r'PostgreSQL\.Database\("', p.source), t.name


def test_relationships_resolve_and_leave_model_outputs_disconnected(model):
    for f, fc, t, tc in model.relationships:
        assert fc in {c.name for c in model.tables[f].columns}, (f, fc)
        assert tc in {c.name for c in model.tables[t].columns}, (t, tc)
        assert f not in DISCONNECTED and t not in DISCONNECTED, (f, t)
    pairs = [(f, t) for f, _, t, _ in model.relationships]
    assert len(pairs) == len(set(pairs)), "two relationships between the same tables"
    # The shared slicers reach every fact they apply to.
    for fact in ("Transactions", "Area Month", "AVM Score"):
        assert {"Date", "Area", "Property Type", "Bedrooms", "Ready Off-Plan"} <= {
            t for f, t in pairs if f == fact
        }, fact


def test_date_table_is_marked():
    text = (tmdl.DEFINITION / "tables" / "Date.tmdl").read_text(encoding="utf-8-sig")
    assert "dataCategory: Time" in text
    date = next(c for c in tmdl.parse_table(text).columns if c.name == "Date")
    assert "isKey" in date.flags


def test_every_dax_reference_resolves(model):
    columns = {(t.name, c.name) for t in model.tables.values() for c in t.columns}
    measures = {m.name for _, m in model.measures()}
    for _, m in model.measures():
        cols, refs = tmdl.dax_references(m.expression)
        assert cols <= columns, (m.name, cols - columns)
        assert refs <= measures | {"Value"}, (m.name, refs - measures)


def test_measures_have_a_folder_and_a_description(model):
    names = [m.name for _, m in model.measures()]
    assert len(names) == len(set(names))
    for _, m in model.measures():
        folder = m.props.get("displayFolder", "")
        assert folder.split("\\")[0] in FOLDERS, (m.name, folder)
        assert m.description, m.name


def test_what_if_tables_match_the_stress_grid(model):
    shock = model.tables["Price Shock %"].partitions[0].source
    series = re.search(r"GENERATESERIES\s*\(\s*(-?\d+),\s*(-?\d+),\s*(\d+)", shock)
    start, end, step = map(int, series.groups())
    assert set(range(start, end + 1, step)) == set(config.STRESS_SHOCKS)
    ltv = model.tables["LTV %"].partitions[0].source
    assert tuple(int(x) for x in re.findall(r"\{\s*(\d+)\s*,", ltv)) == config.STRESS_LTV_GRID
    for value, label in config.STRESS_LTV_LABELS.items():
        assert label in ltv and str(value) in ltv
    replay = model.tables["Replay Depth"].partitions[0].source
    assert "Replay: 2014-2020, Dubai-wide" in replay and "Replay: 2014-2020, own series" in replay


def test_measures_dax_is_current(model):
    assert tmdl.MEASURES_DAX.read_text(encoding="utf-8") == tmdl.export_measures(model), (
        "powerbi/measures.dax is stale: run `make pbi-measures`"
    )


def test_dax_references_ignore_strings_and_local_columns():
    cols, refs = tmdl.dax_references(
        """VAR _t = ADDCOLUMNS ( 'Area Month', "@n", [Market Sales] )
        RETURN SUMX ( _t, [@n] ) & "[Not A Measure]" // [Comment]
        + SUM ( 'Rent Month'[Contracts] )"""
    )
    assert cols == {("Rent Month", "Contracts")}  # 'Area Month' alone is a table, not a column
    assert refs == {"Market Sales"}


def test_parse_table_reads_multiline_measures():
    text = "\r\n".join(
        [
            "table _Measures",
            "\t/// Doc line.",
            "\tmeasure 'A b' =",
            "\t\t\tVAR _x = 1",
            "\t\t\tRETURN",
            "\t\t\t\t_x",
            "\t\tformatString: 0.0%",
            "\t\tdisplayFolder: Risk\\Outlook",
            "",
            "\tmeasure C = [A b] * 2",
            "\t\tdisplayFolder: Market",
            "",
        ]
    )
    t = tmdl.parse_table(text)
    a, c = t.measures
    assert a.name == "A b" and a.expression == "VAR _x = 1\nRETURN\n\t_x"
    assert a.description == "Doc line." and a.props["displayFolder"] == "Risk\\Outlook"
    assert c.expression == "[A b] * 2" and c.description == ""


def tmdl_format_value(raw: str) -> str:
    """A TMDL property value as Power BI reads it: outer quotes off, doubled quotes single."""
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1].replace('""', '"')
    return raw


def test_no_format_string_uses_comma_scaling():
    """Excel-style scaling commas ('#,0.0,,,"bn"') render literally in Power BI: a card showed
    "AED 3.6,,,Tbn" (Phase 5). AED amounts use "AED "#,0 and the card's display units scale.

    A comma is only allowed as the thousands separator, i.e. directly before a digit
    placeholder (``#,0``); anything else (``0,,``, ``0,"bn"``, a trailing comma) is scaling.
    """
    scaling = re.compile(r",(?![0#])")
    for path in sorted((tmdl.DEFINITION / "tables").glob("*.tmdl")):
        for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            s = line.strip()
            if s.startswith("formatString:"):
                value = tmdl_format_value(s.split(":", 1)[1])
                # Literal text inside quotes ("AED ", "bn") may contain anything.
                code = re.sub(r'"[^"]*"', "", value)
                assert not scaling.search(code), f"{path.name}:{n}: {value}"
                if "AED" in value:
                    assert value == '"AED "#,0', f"{path.name}:{n}: {value}"


def test_format_value_decoding():
    assert tmdl_format_value('"""AED ""#,0"') == '"AED "#,0'
    assert tmdl_format_value("0.0%") == "0.0%"
    assert re.search(r",(?![0#])", re.sub(r'"[^"]*"', "", '"AED "#,0.0,,,"bn"'))
