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
    assert v["avm_model_version"] == config.AVM_MODEL_VERSION
    assert v["stress_model_version"] == config.STRESS_MODEL_VERSION
    assert v["forecast_model_version"] == config.FORECAST_MODEL_VERSION
    assert v["index_base_month"] == config.INDEX_BASE_MONTH.isoformat()


def test_hedonic_settings_are_consistent():
    assert config.HEDONIC_START <= config.INDEX_BASE_MONTH
    assert config.RTD_STEP_MONTHS < config.RTD_WINDOW_MONTHS  # windows must overlap to chain
    assert 0 < config.YIELD_SANITY[0] < config.YIELD_SANITY[1] < 1


def test_avm_settings_are_consistent():
    assert config.AVM_HISTORY_START < config.AVM_TRAIN_START <= config.TRAIN_END
    assert config.TRAIN_END < config.VALID_START <= config.VALID_END < config.TEST_START
    assert 0 < config.AVM_OPTUNA_TRIALS <= 50  # docs/05 §1: at most 50 trials
    assert list(config.AVM_PRICE_BANDS) == sorted(config.AVM_PRICE_BANDS)
    assert 0 < config.LEAKAGE_MDAPE_FLOOR < config.AVM_REVIEW_GAP


def test_stress_and_forecast_settings_are_consistent():
    """Integer what-if keys (docs/06), shocks from 0 down to -50 in 5-point steps."""
    assert config.STRESS_SHOCKS == tuple(range(0, -55, -5))
    assert all(isinstance(x, int) for x in (*config.STRESS_SHOCKS, *config.STRESS_LTV_GRID))
    assert list(config.STRESS_LTV_GRID) == sorted(config.STRESS_LTV_GRID)
    assert max(config.STRESS_LTV_GRID) < 100  # base case: no negative equity at a 0 shock
    assert set(config.STRESS_LTV_LABELS) <= set(config.STRESS_LTV_GRID)
    assert config.STRESS_REPLAY_START <= config.STRESS_REPLAY_PEAK_BY < config.STRESS_REPLAY_END
    assert max(config.FORECAST_HORIZONS) <= config.FORECAST_STEPS
    assert config.FORECAST_RATE_SCENARIOS["rates_flat"] == 0
    assert all(0 < x < 1 for x in config.FORECAST_INTERVALS)
