"""Data dictionary: every dbt model and seed, its columns, types, descriptions and tests.

Writes ``docs/data-dictionary.md`` (``make dictionary``; ``make dbt`` runs it). Two sources
are merged so the dictionary can't drift from the database:

* the dbt manifest (``dbt/target/manifest.json``) for model / column descriptions and the
  tests attached to each column, i.e. the YAML docs;
* ``information_schema.columns`` for the column list and types actually built, so a column
  that exists but isn't documented in YAML still appears (with a blank description).

Only the small catalogue comes back from Postgres; no table data is read.
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from dubai_property import config, db
from dubai_property.quality.dq_report import MANIFEST_PATH, PACKAGE, load_manifest, md_table

log = logging.getLogger(__name__)

DICTIONARY_PATH = config.PROJECT_ROOT / "docs" / "data-dictionary.md"

# Layers in reading order: schema -> heading and what the layer is for (docs/03 §3).
LAYERS = {
    "silver": "Silver: seeds, staging views and intermediate tables (typed, cleaned, flagged)",
    "gold": "Gold: star schema (dimensions, facts, aggregates)",
    "rpt": "rpt: reporting views, the only objects Power BI reads",
}


@dataclass
class Relation:
    """One model or seed as documented in the manifest."""

    name: str
    schema: str
    alias: str
    kind: str  # model materialisation or "seed"
    description: str
    columns: dict[str, str] = field(default_factory=dict)  # name -> description
    tests: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    parents: list[str] = field(default_factory=list)  # upstream model / seed unique ids
    inherited: dict[str, str] = field(default_factory=dict)  # name -> "desc (from `model`)"


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _test_label(node: dict[str, Any]) -> str:
    meta = node.get("test_metadata") or {}
    name = meta.get("name") or node.get("name", "")
    return name.replace("expect_column_values_to_be_", "")  # dbt_expectations: be_between


def relations_from_manifest(manifest: dict[str, Any]) -> list[Relation]:
    """This project's models and seeds, with column descriptions and column tests."""
    rels: dict[str, Relation] = {}
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("package_name") != PACKAGE or node.get("resource_type") not in (
            "model",
            "seed",
        ):
            continue
        kind = "seed" if node["resource_type"] == "seed" else node["config"]["materialized"]
        rels[uid] = Relation(
            name=node["name"],
            schema=node["schema"],
            alias=node.get("alias") or node["name"],
            kind=kind,
            description=_clean(node.get("description")),
            columns={c["name"]: _clean(c.get("description")) for c in node["columns"].values()},
            parents=list((node.get("depends_on") or {}).get("nodes", [])),
        )
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") != "test" or not node.get("column_name"):
            continue
        target = node.get("attached_node")
        if target in rels:
            rels[target].tests[node["column_name"]].append(_test_label(node))
    _inherit_descriptions(rels)
    order = list(LAYERS)
    return sorted(
        (r for r in rels.values() if r.schema in LAYERS),
        key=lambda r: (order.index(r.schema), r.kind, r.alias),
    )


def _inherit_descriptions(rels: dict[str, Relation]) -> None:
    """Fill undocumented columns from the nearest upstream model with the same column.

    Gold passes most silver columns through unchanged, so their YAML description lives on
    the silver model. Breadth-first over depends_on, so the closest ancestor wins.
    """
    for rel in rels.values():
        seen: set[str] = set()
        queue = list(rel.parents)
        while queue:
            uid = queue.pop(0)
            if uid in seen or uid not in rels:
                continue
            seen.add(uid)
            parent = rels[uid]
            for column, desc in parent.columns.items():
                if desc and not rel.columns.get(column) and column not in rel.inherited:
                    rel.inherited[column] = f"{desc} (from `{parent.name}`)"
            queue += parent.parents


def catalogue(conn: psycopg.Connection) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """``{(schema, table): [(column, type), ...]}`` for the dbt schemas, in column order."""
    rows = conn.execute(
        "select table_schema, table_name, column_name, data_type from information_schema.columns"
        " where table_schema = any(%s) order by table_schema, table_name, ordinal_position",
        [list(LAYERS)],
    ).fetchall()
    out: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for schema, table, column, dtype in rows:
        out[(schema, table)].append((column, dtype))
    return out


def render(relations: list[Relation], cat: dict[tuple[str, str], list[tuple[str, str]]]) -> str:
    """The dictionary as markdown: one section per layer, one table per relation."""
    lines = [
        "# Data dictionary",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/data_dictionary.py` from "
        "the dbt manifest (descriptions, tests) and the database catalogue (columns, types). "
        "Regenerate with `make dictionary` (after `make dbt`). Rules C1-C22 are in docs/04 §2; "
        "the star schema in docs/04 §3. Bronze is raw text (docs/04 §1) and not listed.",
        "",
    ]
    for schema, heading in LAYERS.items():
        in_layer = [r for r in relations if r.schema == schema]
        if not in_layer:
            continue
        lines += [f"## {heading}", ""]
        lines += md_table(
            ["Object", "Type", "Description"],
            [
                (f"[`{schema}.{r.alias}`](#{schema}{r.alias})", r.kind, r.description)
                for r in in_layer
            ],
        )
        lines.append("")
        for r in in_layer:
            lines += [f'<a id="{schema}{r.alias}"></a>', f"### `{schema}.{r.alias}`", ""]
            if r.alias != r.name:
                lines += [f"dbt model `{r.name}`.", ""]
            if r.description:
                lines += [r.description, ""]
            built = cat.get((schema, r.alias), [])
            if not built:
                lines += ["_Not built in this database._", ""]
                continue
            rows = []
            for column, dtype in built:
                desc = r.columns.get(column) or r.inherited.get(column, "")
                tests = ", ".join(sorted(set(r.tests.get(column, []))))
                rows.append((f"`{column}`", dtype, desc, tests))
            lines += md_table(["Column", "Type", "Description", "Tests"], rows)
            lines.append("")
    return "\n".join(lines)


def run(path: Path = DICTIONARY_PATH, manifest_path: Path = MANIFEST_PATH) -> Path:
    """Read the manifest and catalogue, write the dictionary."""
    relations = relations_from_manifest(load_manifest(manifest_path))
    with db.connect() as conn:
        cat = catalogue(conn)
    path.write_text(render(relations, cat))
    log.info("data dictionary written to %s (%d objects)", path, len(relations))
    return path


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
