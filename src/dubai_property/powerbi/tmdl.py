"""A small reader for the Power BI semantic model's TMDL files (docs/06 §2–3).

The PBIP project stores the semantic model as TMDL text under
``powerbi/DubaiProperty.SemanticModel/definition/``; Power BI Desktop reads and rewrites
these files, and they are the source of truth for tables, relationships and measures.
This module reads just enough of the format to check the model in CI
(``tests/test_powerbi_model.py``: every rpt view imported with the right columns, every
DAX reference resolves) and to export the measures as one readable file,
``powerbi/measures.dax`` (``make pbi-measures``), for people who review DAX on GitHub.

It is not a full TMDL parser: it understands tables, columns, measures (with ``///``
descriptions and multi-line expressions), partitions, expressions and relationships,
which is everything this model uses.

Usage::

    uv run python -m dubai_property.powerbi.tmdl   # writes powerbi/measures.dax
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dubai_property import config

POWERBI_DIR = config.PROJECT_ROOT / "powerbi"
DEFINITION = POWERBI_DIR / "DubaiProperty.SemanticModel" / "definition"
MEASURES_DAX = POWERBI_DIR / "measures.dax"

_NAME = r"(?:'(?:[^']|'')+'|[^\s=.']+)"


def unquote(name: str) -> str:
    """``'Area Month'`` -> ``Area Month`` (TMDL doubles a quote inside a quoted name)."""
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


@dataclass
class Column:
    """A column: imported (``source_column`` = the view's column) or calculated-table."""

    name: str
    props: dict[str, str] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)

    @property
    def source_column(self) -> str | None:
        """The source column name, without the ``[...]`` of a calculated table."""
        src = self.props.get("sourceColumn")
        return src.strip("[]") if src else None


@dataclass
class Measure:
    """A DAX measure with its description and properties."""

    name: str
    expression: str
    description: str = ""
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class Partition:
    """A table partition: ``m`` (Power Query) or ``calculated`` (DAX)."""

    name: str
    kind: str
    source: str


@dataclass
class Table:
    """One ``tables/*.tmdl`` file."""

    name: str
    description: str = ""
    columns: list[Column] = field(default_factory=list)
    measures: list[Measure] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)

    @property
    def rpt_view(self) -> str | None:
        """The rpt view an imported table reads (``Item = "<view>"`` in its M source)."""
        for p in self.partitions:
            m = re.search(r'Schema\s*=\s*"rpt",\s*Item\s*=\s*"([^"]+)"', p.source)
            if p.kind == "m" and m:
                return m.group(1)
        return None


def _block(lines: list[str], start: int, min_indent: int) -> tuple[list[str], int]:
    """Lines from ``start`` while blank or indented at least ``min_indent`` tabs."""
    out, i = [], start
    while i < len(lines) and (not lines[i].strip() or _indent(lines[i]) >= min_indent):
        out.append(lines[i])
        i += 1
    while out and not out[-1].strip():
        out.pop()
        i -= 1
    return out, i


def _dedent(lines: list[str]) -> str:
    body = [ln for ln in lines if ln.strip()]
    cut = min((_indent(ln) for ln in body), default=0)
    return "\n".join(ln[cut:] if ln.strip() else "" for ln in lines).strip("\n")


def parse_table(text: str) -> Table:
    """Parse one table file."""
    lines = text.replace("\r\n", "\n").split("\n")
    table: Table | None = None
    desc: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        level = _indent(line)
        if stripped.startswith("///"):
            desc.append(stripped[3:].strip())
            i += 1
            continue
        if level == 0 and stripped.startswith("table "):
            table = Table(unquote(stripped[6:]), " ".join(desc))
            desc = []
        elif table is not None and level == 1 and stripped.startswith("column "):
            col = Column(unquote(stripped[7:]))
            body, i = _block(lines, i + 1, 2)
            for b in body:
                bs = b.strip()
                if _indent(b) != 2 or not bs or bs.startswith(("annotation", "extendedProperty")):
                    continue
                if ":" in bs:
                    key, value = bs.split(":", 1)
                    col.props[key.strip()] = value.strip()
                else:
                    col.flags.add(bs)
            table.columns.append(col)
            desc = []
            continue
        elif table is not None and level == 1 and stripped.startswith("measure "):
            m = re.match(rf"measure\s+({_NAME})\s*=\s*(.*)$", stripped)
            if m is None:
                raise ValueError(f"unreadable measure line: {stripped}")
            name, first = unquote(m.group(1)), m.group(2)
            body, i = _block(lines, i + 1, 2)
            expr_lines = [first] if first else []
            props: dict[str, str] = {}
            for b in body:
                if _indent(b) >= 3 or (not b.strip() and not props):
                    expr_lines.append(b)
                elif _indent(b) == 2 and ":" in b and not b.strip().startswith("annotation"):
                    key, value = b.strip().split(":", 1)
                    props[key.strip()] = value.strip()
            expression = first if first else _dedent(expr_lines)
            table.measures.append(Measure(name, expression, " ".join(desc), props))
            desc = []
            continue
        elif table is not None and level == 1 and stripped.startswith("partition "):
            m = re.match(rf"partition\s+({_NAME})\s*=\s*(\w+)", stripped)
            if m is None:
                raise ValueError(f"unreadable partition line: {stripped}")
            body, i = _block(lines, i + 1, 2)
            source: list[str] = []
            for j, b in enumerate(body):
                if b.strip().startswith("source"):
                    inline = b.split("=", 1)[1].strip()
                    source = [inline] if inline else [x for x in body[j + 1 :] if _indent(x) >= 3]
                    break
            table.partitions.append(
                Partition(unquote(m.group(1)), m.group(2), _dedent(source) if source else "")
            )
            desc = []
            continue
        elif stripped:
            desc = []
        i += 1
    if table is None:
        raise ValueError("no table in file")
    return table


@dataclass
class Model:
    """Tables, relationships and M expressions of the semantic model."""

    tables: dict[str, Table]
    relationships: list[tuple[str, str, str, str]]  # from table, from col, to table, to col
    expressions: dict[str, str]

    def measures(self) -> list[tuple[str, Measure]]:
        """Every measure with its home table, in file order."""
        return [(t.name, m) for t in self.tables.values() for m in t.measures]


def _col_ref(ref: str) -> tuple[str, str]:
    m = re.match(rf"({_NAME})\.({_NAME})$", ref.strip())
    if m is None:
        raise ValueError(f"unreadable column reference: {ref}")
    return unquote(m.group(1)), unquote(m.group(2))


def load(definition: Path = DEFINITION) -> Model:
    """Read every table file, relationships.tmdl and expressions.tmdl."""
    tables = {}
    for path in sorted((definition / "tables").glob("*.tmdl")):
        t = parse_table(path.read_text(encoding="utf-8-sig"))
        tables[t.name] = t
    rels = []
    rel_path = definition / "relationships.tmdl"
    if rel_path.exists():
        cur: dict[str, str] = {}
        for line in rel_path.read_text(encoding="utf-8-sig").splitlines() + ["relationship end"]:
            s = line.strip()
            if s.startswith("relationship "):
                if cur:
                    rels.append((*_col_ref(cur["fromColumn"]), *_col_ref(cur["toColumn"])))
                cur = {}
            elif ":" in s:
                key, value = s.split(":", 1)
                cur[key.strip()] = value.strip()
    exprs = {}
    expr_path = definition / "expressions.tmdl"
    if expr_path.exists():
        for line in expr_path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(rf"expression\s+({_NAME})\s*=\s*(.*)$", line.strip())
            if m:
                exprs[unquote(m.group(1))] = m.group(2)
    return Model(tables, rels, exprs)


# --- DAX references --------------------------------------------------------------------

_STRING = re.compile(r'"(?:[^"]|"")*"')
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_COLUMN_REF = re.compile(r"'((?:[^']|'')+)'\[([^\]]+)\]")
_MEASURE_REF = re.compile(r"(?<!['\w\]])\[([^\]]+)\]")


def dax_references(expression: str) -> tuple[set[tuple[str, str]], set[str]]:
    """``('Table', 'Column')`` and ``[Measure]`` references in a DAX expression.

    String literals and comments are ignored; ``[@name]`` (a column added with
    ADDCOLUMNS inside the measure) is not a measure reference.
    """
    code = _COMMENT.sub(" ", _STRING.sub('""', expression))
    columns = {(t.replace("''", "'"), c) for t, c in _COLUMN_REF.findall(code)}
    bare = _COLUMN_REF.sub(" ", code)
    measures = {m for m in _MEASURE_REF.findall(bare) if not m.startswith("@")}
    return columns, measures


# --- measures.dax export ---------------------------------------------------------------


def export_measures(model: Model) -> str:
    """Every measure as ``Name = expression``, grouped by display folder (a review copy)."""
    by_folder: dict[str, list[Measure]] = {}
    for _, m in model.measures():
        by_folder.setdefault(m.props.get("displayFolder", "(none)"), []).append(m)
    out = [
        "// Power BI measures of the Dubai property report, exported from the semantic model",
        "// (powerbi/DubaiProperty.SemanticModel/definition/tables/_Measures.tmdl) by",
        "// `make pbi-measures`. A read-only review copy: edit the TMDL (or Power BI Desktop),",
        "// not this file. tests/test_powerbi_model.py fails when the two drift apart.",
        "",
    ]
    for folder, measures in by_folder.items():
        out += [f"// ---------- {folder} ----------", ""]
        for m in measures:
            if m.description:
                out.append(f"// {m.description}")
            fmt = m.props.get("formatString")
            if fmt:
                out.append(f"// Format: {fmt}")
            name = m.name.replace("]", "]]")
            if "\n" in m.expression:
                out.append(f"[{name}] =")
                out += ["    " + ln.replace("\t", "    ") for ln in m.expression.split("\n")]
            else:
                out.append(f"[{name}] = {m.expression}")
            out.append("")
    return "\n".join(out)


# --- KPI guide (a calculated table generated from the measure descriptions) -----------------

KPI_GUIDE_TABLE = "KPI Guide"
KPI_GUIDE_TMDL = DEFINITION / "tables" / f"{KPI_GUIDE_TABLE}.tmdl"
_PARTS = ("Calculation:", "Source:", "Caveat:")


@dataclass
class KpiEntry:
    """One KPI tile of the report, explained from its measure's description."""

    page: str
    page_order: int
    kpi: str
    kpi_order: int
    measure: str
    meaning: str
    calculation: str
    source: str
    caveat: str


def split_description(text: str) -> dict[str, str]:
    """``Meaning. Calculation: … Source: … Caveat: …`` -> its parts ('' when absent)."""
    out = {"meaning": "", "calculation": "", "source": "", "caveat": ""}
    pattern = r"\s*(" + "|".join(re.escape(p) for p in _PARTS) + r")\s*"
    pieces = re.split(pattern, text.strip())
    out["meaning"] = pieces[0].strip()
    for key, value in zip(pieces[1::2], pieces[2::2], strict=True):
        out[key.rstrip(":").lower()] = value.strip()
    return out


def kpi_entries(model: Model | None = None) -> list[KpiEntry]:
    """Every KPI tile on the report pages, in page and tile order (PBIR ``*_t<n>_kpi`` cards)."""
    import json

    from dubai_property.powerbi import pbir

    model = model or load()
    descriptions = {m.name: m.description for _, m in model.measures()}
    pages_meta = json.loads(
        (pbir.REPORT_DEFINITION / "pages" / "pages.json").read_text(encoding="utf-8")
    )
    out: list[KpiEntry] = []
    order = 0
    for page_name in pages_meta["pageOrder"]:
        page_dir = pbir.REPORT_DEFINITION / "pages" / page_name
        page = json.loads((page_dir / "page.json").read_text(encoding="utf-8"))
        tiles = []
        for path in sorted((page_dir / "visuals").glob("*/visual.json")):
            m = re.search(r"_t(\d+)_kpi$", path.parent.name)
            if not m:
                continue
            v = json.loads(path.read_text(encoding="utf-8"))
            proj = v["visual"]["query"]["queryState"]["Data"]["projections"][0]
            tiles.append(
                (int(m.group(1)), proj["field"]["Measure"]["Property"], proj.get("displayName"))
            )
        if not tiles:
            continue
        order += 1
        for n, measure, label in sorted(tiles):
            parts = split_description(descriptions.get(measure, ""))
            out.append(KpiEntry(page["displayName"], order, label or measure, n, measure, **parts))
    return out


def _dax_string(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def _existing_lineage_tags() -> dict[str, str]:
    """Lineage tags Desktop gave the KPI Guide table and its columns (kept on regeneration)."""
    tags: dict[str, str] = {}
    if not KPI_GUIDE_TMDL.exists():
        return tags
    owner = "table"
    for line in KPI_GUIDE_TMDL.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if s.startswith("column "):
            owner = unquote(s[7:])
        elif s.startswith("lineageTag:"):
            tags[owner] = s.split(":", 1)[1].strip()
    return tags


def kpi_guide_tmdl(entries: list[KpiEntry]) -> str:
    """The 'KPI Guide' calculated table (DATATABLE), in TMDL with CRLF line endings.

    Desktop adds lineage tags when it saves the model; they are read back and kept, so
    regenerating the table doesn't churn the identities Desktop assigned.
    """
    tags = _existing_lineage_tags()
    columns = [
        ("Page", "STRING", False, "Page Order"),
        ("Page Order", "INTEGER", True, None),
        # KPI names repeat across pages (e.g. "Prices YoY"), so KPI can't sort by a per-row
        # column (Power BI rejects it); the visual sorts by the global order "#" instead.
        ("KPI", "STRING", False, None),
        ("KPI Sort", "INTEGER", False, None),
        ("Meaning", "STRING", False, None),
        ("How it is calculated", "STRING", False, None),
        ("Source table", "STRING", False, None),
        ("Caveats", "STRING", False, None),
    ]
    lines = [
        "/// The KPI guide page: every KPI tile of the report with its meaning, calculation,",
        "/// source table and caveats. Generated from the _Measures descriptions by",
        "/// `make pbi-measures` (dubai_property.powerbi.tmdl); do not edit by hand.",
        f"table '{KPI_GUIDE_TABLE}'",
        *([f"\tlineageTag: {tags['table']}"] if "table" in tags else []),
        "",
    ]
    for name, _, hidden, sort in columns:
        lines.append(f"\tcolumn '{name}'" if " " in name else f"\tcolumn {name}")
        if hidden:
            lines.append("\t\tisHidden")
        if name in tags:
            lines.append(f"\t\tlineageTag: {tags[name]}")
        lines += ["\t\tsummarizeBy: none", "\t\tisNameInferred", f"\t\tsourceColumn: [{name}]"]
        if sort:
            lines.append(f"\t\tsortByColumn: '{sort}'")
        lines += ["", "\t\tannotation SummarizationSetBy = User", ""]
    lines += [
        f"\tpartition '{KPI_GUIDE_TABLE}' = calculated",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tDATATABLE (",
    ]
    lines += [f"\t\t\t\t\t{_dax_string(name)}, {dtype}," for name, dtype, _, _ in columns]
    lines.append("\t\t\t\t\t{")
    rows = []
    for i, e in enumerate(entries):
        values = [
            _dax_string(e.page),
            str(e.page_order),
            _dax_string(e.kpi),
            str(i + 1),
            _dax_string(e.meaning),
            _dax_string(e.calculation),
            _dax_string(e.source),
            _dax_string(e.caveat),
        ]
        rows.append("\t\t\t\t\t\t{ " + ", ".join(values) + " }")
    lines.append(",\r\n".join(rows))
    lines += ["\t\t\t\t\t}", "\t\t\t\t)", "", ""]  # Desktop ends the file with a blank line
    return "\r\n".join(lines)


def main() -> int:
    """CLI: write powerbi/measures.dax and the KPI Guide table from the TMDL and PBIR."""
    model = load()
    MEASURES_DAX.write_text(export_measures(model), encoding="utf-8")
    print(f"wrote {MEASURES_DAX.relative_to(config.PROJECT_ROOT)}")
    KPI_GUIDE_TMDL.write_bytes(kpi_guide_tmdl(kpi_entries(model)).encode())
    print(f"wrote {KPI_GUIDE_TMDL.relative_to(config.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
