"""data_dictionary: descriptions from the dbt manifest, columns from the catalogue."""

from dubai_property.quality import data_dictionary as dd


def manifest():
    def node(name, schema, columns, parents=(), kind="model", materialized="table"):
        return {
            "resource_type": kind,
            "package_name": "dubai_property",
            "name": name,
            "schema": schema,
            "alias": name,
            "description": f"{name}\n  docs",
            "config": {"materialized": materialized},
            "columns": {c: {"name": c, "description": d} for c, d in columns.items()},
            "depends_on": {"nodes": list(parents)},
        }

    return {
        "nodes": {
            "model.p.int_x": node("int_x", "silver", {"price": "Price in AED.", "id": "Key."}),
            "model.p.fct_x": node("fct_x", "gold", {"id": "Fact key."}, parents=["model.p.int_x"]),
            "test.p.unique_id": {
                "resource_type": "test",
                "column_name": "id",
                "attached_node": "model.p.fct_x",
                "test_metadata": {"name": "unique"},
            },
        }
    }


def test_relations_are_ordered_by_layer_with_tests_attached():
    rels = dd.relations_from_manifest(manifest())
    assert [(r.schema, r.name) for r in rels] == [("silver", "int_x"), ("gold", "fct_x")]
    assert rels[1].tests["id"] == ["unique"]
    assert rels[1].description == "fct_x docs"


def test_undocumented_columns_inherit_from_upstream():
    fct = dd.relations_from_manifest(manifest())[1]
    assert fct.inherited["price"] == "Price in AED. (from `int_x`)"
    assert "id" not in fct.inherited  # own description wins


def test_render_lists_built_columns_with_types():
    rels = dd.relations_from_manifest(manifest())
    cat = {("gold", "fct_x"): [("id", "text"), ("price", "numeric"), ("extra", "integer")]}
    out = dd.render(rels, cat)
    assert "| `id` | text | Fact key. | unique |" in out
    assert "| `price` | numeric | Price in AED. (from `int_x`) |  |" in out
    assert "| `extra` | integer |  |  |" in out
    assert "_Not built in this database._" in out  # int_x missing from the catalogue
