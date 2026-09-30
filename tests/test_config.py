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
