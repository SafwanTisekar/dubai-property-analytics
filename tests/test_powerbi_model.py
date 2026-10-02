"""The Power BI semantic model (TMDL) stays in line with the rpt views (docs/06 §2–3).

Offline: reads the TMDL files and the dbt reporting SQL, no database or Power BI needed,
so CI catches a renamed rpt column, a measure pointing at a column that doesn't exist, or
a what-if table that no longer matches the stress grid, before Desktop does.
"""

from __future__ import annotations

import json
import re

import pytest

from dubai_property import config
from dubai_property.powerbi import pbir, tmdl

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
                if "AED" in value:  # plain amounts, or thousands as a literal "K" suffix
                    assert value in ('"AED "#,0', '"AED "#,0"K"'), f"{path.name}:{n}: {value}"


def test_format_value_decoding():
    assert tmdl_format_value('"""AED ""#,0"') == '"AED "#,0'
    assert tmdl_format_value("0.0%") == "0.0%"
    assert re.search(r",(?![0#])", re.sub(r'"[^"]*"', "", '"AED "#,0.0,,,"bn"'))


# --- Report (PBIR): pages and visuals --------------------------------------------------

CANVAS = (1280, 720)
# docs/06 §5: at most 8 charts / tables per page (KPI tiles, text and the frame excluded)
MAX_DATA_VISUALS = 8
SYNCED_SLICERS = {"Year", "Area", "PropertyType", "Bedrooms", "ReadyOffPlan"}


def visuals() -> list[tuple[str, dict]]:
    return [
        (p.parent.parent.parent.name, json.loads(p.read_text("utf-8"))) for p in pbir.visual_files()
    ]


def test_report_files_validate_against_the_official_schemas():
    files = [
        *sorted((pbir.REPORT_DEFINITION / "bookmarks").glob("*.json")),
        pbir.REPORT_DEFINITION / "report.json",
        pbir.REPORT_DEFINITION / "pages" / "pages.json",
        *pbir.page_files(),
        *pbir.visual_files(),
    ]
    for path in files:
        assert pbir.schema_errors(path) == [], path.relative_to(pbir.REPORT_DEFINITION)


def test_every_field_a_visual_uses_exists_in_the_model(model):
    columns = {(t.name, c.name) for t in model.tables.values() for c in t.columns}
    measures = {(t, m.name) for t, m in model.measures()}
    for page, v in visuals():
        for ref in pbir.field_refs(v):
            known = columns if ref.kind == "Column" else measures
            assert (ref.entity, ref.prop) in known, (page, v["name"], ref)


def test_visual_formatting_matches_the_theme_schema():
    index = json.loads(pbir.VISUAL_OBJECTS.read_text("utf-8"))["visuals"]
    for page, v in visuals():
        assert pbir.object_errors(v["visual"], index) == [], (page, v["name"])


def test_formatting_values_are_valid_query_expressions():
    for page, v in visuals():
        assert pbir.expression_errors(v["visual"]) == [], (page, v["name"])


def test_slicer_selections_are_valid_filters():
    for page, v in visuals():
        for entry in v["visual"].get("objects", {}).get("general", []):
            saved = entry.get("properties", {}).get("filter")
            if saved:
                assert pbir.filter_errors(saved["filter"]) == [], (page, v["name"])


def test_visuals_fit_the_canvas_have_alt_text_and_respect_the_cap():
    per_page: dict[str, int] = {}
    for page, v in visuals():
        pos = v["position"]
        assert pos["x"] >= 0 and pos["y"] >= 0, v["name"]
        assert pos["x"] + pos["width"] <= CANVAS[0] and pos["y"] + pos["height"] <= CANVAS[1], v[
            "name"
        ]
        general = v["visual"].get("visualContainerObjects", {}).get("general", [{}])
        assert pbir.literal_value(general[0].get("properties", {}).get("altText")), v["name"]
        if v["visual"]["visualType"] in CHART_TYPES and not v["name"].endswith("_text"):
            per_page[page] = per_page.get(page, 0) + 1
        folder = next(p for p in pbir.visual_files() if p.parent.name == v["name"])
        assert folder.parent.name == v["name"]
    assert per_page and max(per_page.values()) <= MAX_DATA_VISUALS, per_page


REPORT_PAGES = {"p1Executive", "p2Financing", "p3Prices", "p4Yields", "p5Valuation", "p6Risk"}


def test_built_pages_carry_the_synced_slicer_panel():
    groups: dict[str, set[str]] = {}
    for page, v in visuals():
        sync = v["visual"].get("syncGroup")
        if sync:
            groups.setdefault(page, set()).add(sync["groupName"])
    built = {page for page, _ in visuals()} & REPORT_PAGES  # guide pages have no slicers
    for page in built:
        assert groups.get(page) == SYNCED_SLICERS, page


def test_visual_interactions_name_existing_visuals():
    names: dict[str, set[str]] = {}
    for page, v in visuals():
        names.setdefault(page, set()).add(v["name"])
    for path in pbir.page_files():
        doc = json.loads(path.read_text("utf-8"))
        for i in doc.get("visualInteractions", []):
            assert {i["source"], i["target"]} <= names.get(doc["name"], set()), (doc["name"], i)


def test_theme_is_registered_in_the_report():
    report = json.loads((pbir.REPORT_DEFINITION / "report.json").read_text("utf-8"))
    custom = report["themeCollection"]["customTheme"]
    package = next(p for p in report["resourcePackages"] if p["type"] == "RegisteredResources")
    item = next(i for i in package["items"] if i["type"] == "CustomTheme")
    assert custom["name"] == item["name"] and custom["type"] == "RegisteredResources"
    registered = (
        pbir.REPORT_DEFINITION.parent / "StaticResources" / "RegisteredResources" / item["path"]
    )
    source = config.PROJECT_ROOT / "powerbi" / "theme.json"
    assert json.loads(registered.read_text("utf-8")) == json.loads(source.read_text("utf-8")), (
        "the registered theme differs from powerbi/theme.json: copy it over"
    )


def test_pbir_checks_catch_mistakes():
    bad = {
        "visualType": "cardVisual",
        "objects": {
            "value": [
                {
                    "properties": {
                        "labelDisplayUnits": {"expr": {"Literal": {"Value": "7D"}}},
                        "displayUnitz": {"expr": {"Literal": {"Value": "1D"}}},
                    }
                }
            ],
            "nope": [{"properties": {}}],
        },
    }
    errors = pbir.object_errors(bad)
    assert any("displayUnitz" in e for e in errors) and any("nope" in e for e in errors)
    assert any("labelDisplayUnits: 7" in e for e in errors)
    assert pbir.literal_value({"expr": {"Literal": {"Value": "'Dropdown'"}}}) == "Dropdown"
    assert pbir.literal_value({"expr": {"Literal": {"Value": "1000000000D"}}}) == 1_000_000_000
    assert pbir.filter_errors({"Version": 2, "From": []}) != []  # no Where
    assert pbir.expression_errors(
        {"objects": {"x": [{"properties": {"y": {"expr": {"Nope": 1}}}}]}}
    )
    refs = list(pbir.field_refs({"From": [{"Name": "a", "Entity": "Area"}],
                                 "Where": [{"Column": {"Expression": {"SourceRef": {"Source": "a"}},
                                                       "Property": "Zone"}}]}))  # fmt: skip
    assert refs == [pbir.FieldRef("Area", "Zone", "Column")]


# Render limits calibrated on what Power BI Desktop drew at the final gates (Phase 5), not on
# the nominal PBIR sizes: below 240 x 180 a chart becomes a placeholder icon; a bar chart
# needs ~72 px of chrome + 24 px per bar (+36 with a subtitle); a table 72 + 32 per row
# (header included); a card the sum of its rendered lines (point size x ~1.73 px) + padding.
MIN_CHART = (240, 180)
PX_PER_PT = 1.73
CHART_TYPES = {
    "lineChart",
    "areaChart",
    "columnChart",
    "clusteredColumnChart",
    "clusteredBarChart",
    "hundredPercentStackedColumnChart",
    "scatterChart",
    "pivotTable",
    "tableEx",
}


def _shown(vco: dict, key: str) -> bool:
    entries = vco.get(key, [])
    return bool(entries) and pbir.literal_value(entries[0]["properties"].get("show")) is True


def _top_n(v: dict) -> int | None:
    for f in v.get("filterConfig", {}).get("filters", []):
        if f.get("type") == "TopN":
            return f["filter"]["From"][0]["Expression"]["Subquery"]["Query"]["Top"]
    return None


def test_charts_meet_the_minimum_render_size():
    for page, v in visuals():
        # "_text" tables are dynamic-text cards (one wrapped sentence), sized by their lines.
        if v["visual"]["visualType"] in CHART_TYPES and not v["name"].endswith("_text"):
            pos = v["position"]
            assert pos["width"] >= MIN_CHART[0] and pos["height"] >= MIN_CHART[1], (page, v["name"])


def test_top_n_bars_and_rows_fit_without_scrolling():
    for page, v in visuals():
        n = _top_n(v)
        vtype = v["visual"]["visualType"]
        subtitle = 36 if _shown(v["visual"]["visualContainerObjects"], "subTitle") else 0
        if n and vtype == "clusteredBarChart":
            needed = 72 + 24 * n + subtitle
        elif n and vtype == "tableEx":
            needed = 72 + 32 * (n + 1) + subtitle
        else:
            continue
        assert v["position"]["height"] >= needed, (page, v["name"], n, needed)


def _default_prop(entries: list, prop: str):
    for e in entries:
        if e.get("selector", {}).get("id") == "default" and prop in e["properties"]:
            return pbir.literal_value(e["properties"][prop])
    return None


def test_cards_fit_their_rendered_lines():
    """Title + subtitle + label + value must fit (gate 3: grouped cards clipped values)."""
    for page, v in visuals():
        vis = v["visual"]
        if vis["visualType"] != "cardVisual":
            continue
        objs, vco = vis.get("objects", {}), vis.get("visualContainerObjects", {})
        value_pt = _default_prop(objs.get("value", []), "fontSize") or 18
        label_shown = _default_prop(objs.get("label", []), "show") is not False
        label_pt = (_default_prop(objs.get("label", []), "fontSize") or 9) if label_shown else 0
        padded = _default_prop(objs.get("cardCalloutArea", []), "paddingUniform") != 0
        needed = (16 if padded else 0) + PX_PER_PT * value_pt + 8
        needed += PX_PER_PT * label_pt + 2 if label_pt else 0
        needed += (24 if _shown(vco, "title") else 0) + (20 if _shown(vco, "subTitle") else 0)
        assert v["position"]["height"] >= needed, (page, v["name"], round(needed))


def test_titles_fit_and_subtitles_have_a_title():
    for page, v in visuals():
        vco = v["visual"].get("visualContainerObjects", {})
        if _shown(vco, "subTitle"):
            assert _shown(vco, "title"), (page, v["name"], "a subtitle only shows under a title")
        if _shown(vco, "title"):
            text = pbir.literal_value(vco["title"][0]["properties"].get("text"))
            if isinstance(text, str):  # measure-bound titles are checked by eye
                assert len(text) <= v["position"]["width"] / 7, (page, v["name"], text)


def test_visual_inventory_is_current():
    assert pbir.VISUALS_MD.read_text(encoding="utf-8") == pbir.inventory_markdown(), (
        "powerbi/VISUALS.md is stale: run `make pbi-inventory`"
    )


def test_dynamic_text_tables_wrap_at_a_fixed_width():
    """Gate 1: card visuals cut dynamic text to one line; "_text" tables wrap it instead."""
    found = 0
    for _page, v in visuals():
        if not v["name"].endswith("_text"):
            continue
        found += 1
        objs = v["visual"]["objects"]
        assert pbir.literal_value(objs["values"][0]["properties"]["wordWrap"]) is True, v["name"]
        width = pbir.literal_value(objs["columnWidth"][0]["properties"]["value"])
        assert 0 < width <= v["position"]["width"] - 24, (v["name"], width)
        assert len(v["visual"]["query"]["queryState"]["Values"]["projections"]) == 1, v["name"]
    assert found


def test_every_kpi_tile_measure_is_explained():
    """The KPI guide comes from descriptions: each KPI tile needs meaning, calculation, source."""
    entries = tmdl.kpi_entries()
    assert {e.page for e in entries} >= {"1 Executive", "6 Risk"}
    for e in entries:
        assert e.meaning and e.calculation and e.source, (e.page, e.kpi, e.measure)


def test_kpi_guide_table_is_current():
    expected = tmdl.kpi_guide_tmdl(tmdl.kpi_entries())
    assert tmdl.KPI_GUIDE_TMDL.read_bytes().decode() == expected, (
        "the KPI Guide table is stale: run `make pbi-measures`"
    )


def test_split_description():
    parts = tmdl.split_description(
        "It is X. Calculation: a / b. Source: Area Month. Caveat: a lower bound: y."
    )
    assert parts == {"meaning": "It is X.", "calculation": "a / b.", "source": "Area Month.",
                     "caveat": "a lower bound: y."}  # fmt: skip


# --- Reset bookmarks ---------------------------------------------------------------------

BOOKMARKS_DIR = pbir.REPORT_DEFINITION / "bookmarks"


def test_bookmarks_validate_and_are_listed():
    files = sorted(BOOKMARKS_DIR.glob("*.bookmark.json"))
    assert files
    for path in [*files, BOOKMARKS_DIR / "bookmarks.json"]:
        assert pbir.schema_errors(path) == [], path.name
    listed = {
        i["name"]
        for i in json.loads((BOOKMARKS_DIR / "bookmarks.json").read_text("utf-8"))["items"]
    }
    assert listed == {p.name.removesuffix(".bookmark.json") for p in files}


def test_reset_buttons_restore_their_page_slicers():
    """Each Reset button opens its own page's bookmark, which sets every slicer on the page:
    defaults where a slicer has one (Year 2025, shock -20, LTV 80%, ...), cleared otherwise."""
    by_page: dict[str, list[dict]] = {}
    for page, v in visuals():
        by_page.setdefault(page, []).append(v)
    for page, vs in by_page.items():
        resets = [v for v in vs if v["name"].endswith("_hdr_reset")]
        slicers = {v["name"]: v for v in vs if v["visual"]["visualType"] == "slicer"}
        if not slicers:
            assert not resets, (page, "a reset button without filters to reset")
            continue
        assert len(resets) == 1, page
        link = resets[0]["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
        assert pbir.literal_value(link["type"]) == "Bookmark", page
        bm = json.loads(
            (BOOKMARKS_DIR / f"{pbir.literal_value(link['bookmark'])}.bookmark.json").read_text(
                "utf-8"
            )
        )
        state = bm["explorationState"]
        assert state["activeSection"] == page and set(state["sections"]) == {page}
        assert (
            bm["options"]["suppressDisplay"] is True
            and bm["options"]["applyOnlyToTargetVisuals"] is True
        )
        containers = state["sections"][page]["visualContainers"]
        assert set(containers) == set(slicers) == set(bm["options"]["targetVisualNames"]), page
        for name, st in containers.items():
            objs = st["singleVisual"]["objects"]
            default = slicers[name]["visual"].get("objects", {}).get("general")
            if default:
                saved = objs["merge"]["general"][0]["properties"]["filter"]
                assert saved == default[0]["properties"]["filter"], (page, name)
                assert pbir.filter_errors(saved["filter"]) == [], (page, name)
            else:
                assert objs == {"remove": [{"object": "general", "property": "filter"}]}, (
                    page,
                    name,
                )


# --- Slicer selection settings ------------------------------------------------------------

# One value at a time (owner): Year, and the page controls that pick a scenario or a series.
SINGLE_SELECT = ("_Year", "_Shock", "_LTV", "_StressSegment", "_IndexSegment", "_Breakdown")
MULTI_SELECT = ("_Area", "_PropertyType", "_Bedrooms", "_ReadyOffPlan", "p7Guide_Page")


def _selection(v: dict) -> dict:
    props = v["visual"].get("objects", {}).get("selection", [{}])[0].get("properties", {})
    return {k: pbir.literal_value(p) for k, p in props.items()}


def test_single_select_slicers_require_one_value():
    """Regression (gate 2): a Year slicer must not allow several years."""
    checked = 0
    for page, v in visuals():
        if v["visual"]["visualType"] != "slicer":
            continue
        sel = _selection(v)
        if v["name"].endswith(SINGLE_SELECT):
            checked += 1
            assert sel.get("singleSelect") is True and sel.get("strictSingleSelect") is True, (
                page,
                v["name"],
                sel,
            )
        else:
            assert v["name"].endswith(MULTI_SELECT), (
                page,
                v["name"],
                "add it to SINGLE_ or MULTI_SELECT",
            )
            assert sel.get("singleSelect") is False, (page, v["name"], sel)
    assert checked >= 6 + 3  # a Year slicer on each report page, plus page 3, 5 and 6 controls


def test_date_slicers_offer_only_years_with_data():
    """dim_date runs to the end of the forecast horizon: slicers stop at the snapshot year."""
    for page, v in visuals():
        if v["visual"]["visualType"] != "slicer":
            continue
        fields = [r for r in pbir.field_refs(v["visual"]["query"]) if r.entity == "Date"]
        if not fields:
            continue
        assert [f.prop for f in fields] == ["Year Label"], (page, v["name"])
        filters = v.get("filterConfig", {}).get("filters", [])
        cond = [f["filter"]["Where"][0]["Condition"]["In"] for f in filters
                if f["field"]["Column"]["Property"] == "Is Data Year"]  # fmt: skip
        assert cond and cond[0]["Values"] == [[{"Literal": {"Value": "true"}}]], (page, v["name"])
