import yaml

from dubai_property import config


def test_out_of_time_split_is_ordered_and_disjoint():
    assert config.TRAIN_START < config.TRAIN_END < config.VALID_START
    assert config.VALID_START <= config.VALID_END < config.TEST_START


def test_business_thresholds_match_claude_md():
    assert config.MIN_N == 20
    assert config.SQM_TO_SQFT == 10.7639
    assert config.INDEX_BASE_MONTH.isoformat() == "2019-01-01"


def test_schemas_cover_all_medallion_layers():
    assert config.SCHEMAS == ("bronze", "silver", "gold", "ml", "rpt")


def test_model_artifacts_live_outside_the_package():
    package_dir = config.PROJECT_ROOT / "src" / "dubai_property"
    assert package_dir not in config.ARTIFACTS_MODELS.parents


def test_report_scope_matches_dbt_vars():
    """kpi_reconciliation filters silver on the same dates dim_date is built from."""
    project = yaml.safe_load((config.DBT_DIR / "dbt_project.yml").read_text())
    assert project["vars"]["dim_date_start"] == config.REPORT_SCOPE_START.isoformat()
    assert project["vars"]["min_n"] == config.MIN_N


def test_area_caps_match_dbt_vars():
    """The KPI's silver SQL applies the same class caps as the dbt macro class_area_cap."""
    v = yaml.safe_load((config.DBT_DIR / "dbt_project.yml").read_text())["vars"]
    assert config.AREA_CAP_SQM == {
        1: v["area_cap_apartment_sqm"],
        2: v["area_cap_villa_sqm"],
        4: v["area_cap_office_retail_sqm"],
        5: v["area_cap_office_retail_sqm"],
    }
    assert config.AREA_CAP_OTHER_SQM == v["area_cap_other_sqm"]


def test_model_versions_and_index_base_match_dbt_vars():
    """rpt shows the model version the Python models write (docs/05 §2-3)."""
    v = yaml.safe_load((config.DBT_DIR / "dbt_project.yml").read_text())["vars"]
    assert v["hedonic_model_version"] == config.HEDONIC_MODEL_VERSION
    assert v["yield_model_version"] == config.YIELD_MODEL_VERSION
    assert v["index_base_month"] == config.INDEX_BASE_MONTH.isoformat()


def test_hedonic_settings_are_consistent():
    assert config.HEDONIC_START <= config.INDEX_BASE_MONTH
    assert config.RTD_STEP_MONTHS < config.RTD_WINDOW_MONTHS  # windows must overlap to chain
    assert 0 < config.YIELD_SANITY[0] < config.YIELD_SANITY[1] < 1
