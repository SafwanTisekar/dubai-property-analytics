"""Offline checks for the report's PBIR files (``powerbi/DubaiProperty.Report/definition``).

The report (pages, visuals, slicers) is stored as PBIR JSON. Power BI Desktop is the only
real validator, so CI does the next best thing (``tests/test_powerbi_model.py``):

* **Schema**: every ``page.json`` / ``visual.json`` / ``report.json`` is validated against
  the official Microsoft schema its ``$schema`` names, from a vendored copy in
  ``powerbi/schemas/pbir/`` (github.com/microsoft/json-schemas, MIT). No network.
* **Fields**: every column / measure a visual, filter or sort references must exist in
  the semantic model (``tmdl.load()``), as the kind it is used as.
* **Formatting names**: the PBIR schema leaves a visual's ``objects`` open, so object and
  property names (``labelDisplayUnits`` …) are checked against an index extracted from
  Microsoft's report theme schema (``powerbi/schemas/visual_objects.json``), which lists
  every formatting card and property per visual type.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from dubai_property import config

POWERBI_DIR = config.PROJECT_ROOT / "powerbi"
REPORT_DEFINITION = POWERBI_DIR / "DubaiProperty.Report" / "definition"
SCHEMA_DIR = POWERBI_DIR / "schemas" / "pbir"
VISUAL_OBJECTS = POWERBI_DIR / "schemas" / "visual_objects.json"
SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"

# Visual types that hold no data (layout and controls): excluded from the per-page cap.
NON_DATA_VISUALS = {"slicer", "textbox", "shape", "image", "actionButton"}


def _registry() -> Registry:
    """Every vendored schema under its canonical URL (and its ``$id``, if different)."""
    resources = []
    for path in SCHEMA_DIR.rglob("*.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents, default_specification=DRAFT7)
        url = SCHEMA_BASE + path.relative_to(SCHEMA_DIR).as_posix()
        resources.append((url, resource))
        if contents.get("$id") and contents["$id"] != url:
            resources.append((contents["$id"], resource))
    return Registry().with_resources(resources)


_REGISTRY: Registry | None = None


def schema_errors(path: Path) -> list[str]:
    """Validation errors of one PBIR file against the schema its ``$schema`` names."""
    global _REGISTRY
    _REGISTRY = _REGISTRY or _registry()
    doc = json.loads(path.read_text(encoding="utf-8"))
    url = doc.get("$schema", "")
    if not url.startswith(SCHEMA_BASE):
        return [f"$schema is not an official PBIR schema: {url!r}"]
    local = SCHEMA_DIR / url[len(SCHEMA_BASE) :]
    if not local.exists():
        return [f"schema version not vendored (powerbi/schemas/pbir): {url}"]
    schema = json.loads(local.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, registry=_REGISTRY)
    return [f"{e.json_path}: {e.message[:200]}" for e in validator.iter_errors(doc)]


def filter_errors(definition: dict) -> list[str]:
    """Validate a semantic-query filter (e.g. a slicer's saved selection) on its own."""
    global _REGISTRY
    _REGISTRY = _REGISTRY or _registry()
    ref = {"$ref": SCHEMA_BASE + "semanticQuery/1.4.0/schema.json#/definitions/FilterDefinition"}
    validator = Draft7Validator(ref, registry=_REGISTRY)
    return [f"{e.json_path}: {e.message[:200]}" for e in validator.iter_errors(definition)]


@dataclass(frozen=True)
class FieldRef:
    """A model field a visual uses: ``kind`` is Column, Measure or Aggregation(Column)."""

    entity: str
    prop: str
    kind: str


def field_refs(node: Any, aliases: dict[str, str] | None = None) -> Iterator[FieldRef]:
    """Every column / measure reference, by entity or by a query alias.

    Projections name the table (``SourceRef.Entity``); filters and subqueries use aliases
    (``SourceRef.Source``) declared in the query's ``From`` list, which are resolved here.
    """
    aliases = dict(aliases or {})
    if isinstance(node, dict):
        for src in node.get("From", []) if isinstance(node.get("From"), list) else []:
            if isinstance(src, dict) and "Name" in src and "Entity" in src:
                aliases[src["Name"]] = src["Entity"]
        for key, value in node.items():
            if key in ("Column", "Measure") and isinstance(value, dict) and "Property" in value:
                ref = value.get("Expression", {}).get("SourceRef", {})
                entity = ref.get("Entity") or aliases.get(ref.get("Source", ""))
                if entity:
                    yield FieldRef(entity, value["Property"], key)
                    continue
            yield from field_refs(value, aliases)
    elif isinstance(node, list):
        for item in node:
            yield from field_refs(item, aliases)


# Properties that are report state, not formatting, so the theme schema doesn't list them:
# a slicer's saved selection lives in ``general.filter``.
NON_THEME_PROPERTIES = {("slicer", "general", "filter")}


def literal_value(prop: Any) -> Any:
    """A PBIR literal (``{"expr": {"Literal": {"Value": "'Dropdown'"}}}``) as Python, else None."""
    if not isinstance(prop, dict):
        return None
    raw = prop.get("expr", {}).get("Literal", {}).get("Value")
    if not isinstance(raw, str):
        return None
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    if raw[-1:] in ("D", "L", "M") and raw[:-1].lstrip("-").replace(".", "", 1).isdigit():
        number = float(raw[:-1])
        return int(number) if number.is_integer() else number
    return None


def object_errors(visual: dict, index: dict | None = None) -> list[str]:
    """Formatting objects, properties or literal values the visual type doesn't have.

    Checked against Microsoft's report theme schema (``visual_objects.json``): every object
    and property name must exist for the visual type, and a literal must be one of the
    property's allowed values where the schema enumerates them.
    """
    index = index or json.loads(VISUAL_OBJECTS.read_text(encoding="utf-8"))["visuals"]
    vtype = visual.get("visualType", "")
    if vtype not in index:
        return [f"unknown visualType {vtype!r}"]
    known = index[vtype]
    errors = []
    for obj, entries in (visual.get("objects") or {}).items():
        if obj not in known:
            errors.append(f"{vtype}: no formatting object {obj!r}")
            continue
        for entry in entries:
            for prop, value in entry.get("properties", {}).items():
                if (vtype, obj, prop) in NON_THEME_PROPERTIES:
                    continue
                if prop not in known[obj]:
                    errors.append(f"{vtype}.{obj}: no property {prop!r}")
                    continue
                allowed = known[obj][prop]
                literal = literal_value(value)
                if allowed is not None and literal is not None and literal not in allowed:
                    errors.append(f"{vtype}.{obj}.{prop}: {literal!r} not in {allowed}")
    return errors


def visual_files() -> list[Path]:
    """Every visual.json of every page."""
    return sorted(REPORT_DEFINITION.glob("pages/*/visuals/*/visual.json"))


def page_files() -> list[Path]:
    """Every page.json."""
    return sorted(REPORT_DEFINITION.glob("pages/*/page.json"))
