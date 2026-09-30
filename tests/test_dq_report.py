"""dq_report: flags are discovered from the dbt manifest, so none can be missed."""

from dubai_property.quality import dq_report


def manifest():
    def model(name, columns, amount=None, package="dubai_property"):
        return {
            "resource_type": "model",
            "package_name": package,
            "name": name,
            "relation_name": f'"db"."silver"."{name}"',
            "config": {"meta": {"dq_amount_column": amount} if amount else {}},
            "columns": columns,
        }

    return {
        "nodes": {
            "model.a": model(
                "int_rents",
                {
                    "is_multi_unit": {
                        "name": "is_multi_unit",
                        "meta": {"dq_rule": "C11"},
                        "description": "multi\n  unit",
                    },
                    "contract_id": {"name": "contract_id", "meta": {}},
                },
                amount="annual_rent_alloc_aed",
            ),
            "model.b": model(
                "int_sales",
                {
                    "is_price_invalid": {
                        "name": "is_price_invalid",
                        "config": {"meta": {"dq_rule": "C4"}},
                    }
                },
            ),
            "model.pkg": model(
                "other", {"x": {"name": "x", "meta": {"dq_rule": "C1"}}}, package="dbt_utils"
            ),
            "test.t": {"resource_type": "test", "package_name": "dubai_property"},
        }
    }


def test_flags_are_read_from_column_meta_in_rule_order():
    flags = dq_report.flags_from_manifest(manifest())
    # C4 sorts before C11 (numeric order), other packages and non-flag columns are ignored,
    # and meta is found both at column level and under config (dbt 1.10+).
    assert [(f.rule, f.model, f.column) for f in flags] == [
        ("C4", "int_sales", "is_price_invalid"),
        ("C11", "int_rents", "is_multi_unit"),
    ]
    assert flags[1].amount_column == "annual_rent_alloc_aed"
    assert flags[1].description == "multi unit"
    assert flags[0].amount_column is None


def test_rule_sort_key_is_numeric():
    assert sorted(["C16", "C4", "C11"], key=dq_report.rule_sort_key) == ["C4", "C11", "C16"]


def test_md_table_formats_thousands_and_escapes_pipes():
    out = dq_report.md_table(["a", "b"], [(1234567, "x|y"), (None, 5)])
    assert out[2] == "| 1,234,567 | x\\|y |"
    assert out[3] == "|  | 5 |"
