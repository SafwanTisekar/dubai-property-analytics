"""AVM evaluation, explanation and outputs.

Pure tests (CI without data): metric definitions, price bands by predicted value, the
leakage alarm, coverage and the common subset, the worked-example selection rule, the
review flag. DB tests check ml.avm_* once `make train` has run (skipped before).
"""

from datetime import date, datetime

import numpy as np
import polars as pl
import psycopg
import pytest

from dubai_property import config, db
from dubai_property.models import avm, avm_eval, avm_explain


def test_metrics_follow_the_definitions():
    actual = np.array([100.0, 100.0, 100.0, 100.0])
    pred = np.array([105.0, 90.0, 115.0, 70.0])  # APE 5%, 10%, 15%, 30%
    m = avm_eval.metrics(actual, pred)
    assert m["mdape"] == pytest.approx(0.125)
    assert m["hit10"] == 0.5  # within ±10% inclusive
    assert m["hit20"] == 0.75
    assert m["mape"] == pytest.approx(0.15)


def test_price_bands_use_the_column_given_and_leave_unscored_sales_out():
    df = pl.DataFrame({"p": [500_000.0, 1_500_000.0, 3e6, 9e6, None]})
    bands = df.select(avm_eval.band_expr("p").alias("b"))["b"].to_list()
    assert bands == ["< AED 1M", "AED 1M-2M", "AED 2M-5M", ">= AED 5M", None]


def scored_frame() -> pl.DataFrame:
    rng = np.random.default_rng(0)
    n = 400
    price = rng.uniform(4e5, 6e6, n)
    return pl.DataFrame(
        {
            "transaction_id": [f"t{i}" for i in range(n)],
            "split": ["test"] * n,
            "month": [date(2025, 1 + i % 6, 1) for i in range(n)],
            "price_aed": price,
            "is_offplan": rng.random(n) < 0.5,
            "property_type_key": np.where(rng.random(n) < 0.8, 101, 102),
            "area_key": rng.integers(1, 4, n),
            "area_name": ["A"] * n,
            "pred_good": price * rng.normal(1, 0.05, n),
            # Values only the cheaper half, perfectly: coverage must expose that.
            "pred_partial": np.where(price < 3e6, price, np.nan),
        }
    ).with_columns(pl.col("pred_partial").fill_nan(None))


def test_evaluate_reports_coverage_and_the_common_subset():
    perf = avm_eval.evaluate(scored_frame(), ["good", "partial"], splits=["test"])
    overall = {r["model"]: r for r in perf.filter(pl.col("breakdown") == "overall").to_dicts()}
    assert overall["good"]["coverage"] == 1.0
    assert 0.3 < overall["partial"]["coverage"] < 0.7
    common = perf.filter(pl.col("breakdown") == "overall_common")
    assert common["n_scored"].n_unique() == 1  # both models on the same sales
    # Predicted-value bands have no coverage (every member is scored by definition).
    assert perf.filter(pl.col("breakdown") == "price_band")["coverage"].is_null().all()


def test_evaluate_applies_min_n_to_segments():
    perf = avm_eval.evaluate(scored_frame().head(30), ["good"], splits=["test"], min_n=20)
    assert (perf["n_scored"] >= 20).all()
    assert perf.filter(pl.col("breakdown") == "month").is_empty()  # 5 sales a month


def test_leakage_alarm_fires_only_on_implausible_results_with_enough_sales():
    def perf(mdape, hit10, n):
        return pl.DataFrame(
            [{"model": "m", "split": "test", "breakdown": "overall", "segment": "all",
              "n_scored": n, "mdape": mdape, "hit10": hit10}]
        )  # fmt: skip

    assert avm_eval.leakage_alarm(perf(0.07, 0.62, 300_000)) == []
    assert len(avm_eval.leakage_alarm(perf(0.02, 0.95, 300_000))) == 2
    assert avm_eval.leakage_alarm(perf(0.02, 0.95, 50)) == []  # fixtures: not applicable


def test_review_flag_is_out_of_sample_only():
    rows = pl.DataFrame(
        {
            "transaction_id": ["a", "b", "c"],
            "txn_date": [date(2020, 1, 5), date(2024, 1, 5), date(2025, 1, 5)],
            "area_key": [1, 1, 1],
            "property_type_key": [101, 101, 101],
            "bedrooms": [1, -1, 2],
            "is_offplan": [False, False, True],
            "area_sqm": [80.0, 80.0, 80.0],
            "split": ["train", "validation", "test"],
            "price_aed": [2e6, 2e6, 1e6],
            "pred_lightgbm": [1e6, 1e6, 1e6],
            "pred_comps": [1e6, None, 1e6],
        }
    )
    out = avm.score_frame(rows, "lightgbm", datetime(2026, 10, 1))
    flags = dict(zip(out["model_set"], out["is_review"], strict=True))
    assert flags["train"] is None  # in-sample: +100% gap, still not flagged
    assert flags["validation"] is True
    assert flags["test"] is False
    assert out["bedrooms"].to_list() == [1, None, 2]  # -1 (unknown) -> NULL
    assert out["gap_pct"][0] == pytest.approx(1.0)  # (price - AVM) / AVM


def test_worked_examples_follow_the_published_rule():
    rows = []
    for i, (area, beds, offplan, ape) in enumerate(
        [(330, 2, False, 0.02), (330, 2, False, 0.05), (330, 2, False, 0.08), (330, 2, False, 0.3),
         (441, 1, True, 0.01), (441, 3, True, 0.01), (500, 2, False, 0.4), (500, 2, False, 0.6),
         (500, 2, False, 0.5)]
    ):  # fmt: skip
        rows.append(
            {"transaction_id": f"t{i}", "area_key": area, "area_name": f"A{area}",
             "zone": "Z", "property_type_key": 101, "bedrooms": beds, "is_offplan": offplan,
             "pred_value": 1e6 * (1 + i), "ape": ape}
        )  # fmt: skip
    picked = avm_explain.pick_examples(pl.DataFrame(rows), top_areas=[330, 441, 500])
    by_key = {e["key"]: e["row"]["transaction_id"] for e in picked}
    assert by_key["marina_2bed_ready"] == "t1"  # the median value of t0..t2 (APE < 10%)
    assert by_key["jvc_offplan_small"] == "t4"  # t5 is a 3-bed
    # Misses > 25% in top areas: t3 (0.3), t6 (0.4), t8 (0.5), t7 (0.6) -> median APE = t8.
    assert by_key["large_miss"] == "t8"
    assert "median APE" in avm_explain.SELECTION_RULE


def test_tuning_summary_reports_the_spread_and_the_best_trial():
    from dubai_property.models import report_avm

    trials = [
        {"number": 0, "value": 0.0715},
        {"number": 1, "value": 0.0733},
        {"number": 2, "value": 0.0704},
        {"number": 3, "value": None},  # a failed trial doesn't count
    ]
    ts = report_avm.tuning_summary(trials)
    assert ts == {"n": 3, "min": 0.0704, "max": 0.0733, "best_trial": 3}
    sentence = report_avm.tuning_sentence(ts)
    assert "7.0% and 7.3%" in sentence and "likely" in sentence
    # Defaults run (--trials 0): no study, no sentence.
    assert report_avm.tuning_summary([]) is None
    assert report_avm.tuning_sentence(None) == ""


def test_card_wording_follows_the_numbers():
    from dubai_property.models import report_avm

    base = {"mdape": 0.099}
    assert "did not beat" in report_avm.comps_comparison(base, {"mdape": 0.101})
    assert "did not beat" in report_avm.comps_comparison(base, {"mdape": 0.099})
    assert "helps" in report_avm.comps_comparison(base, {"mdape": 0.095})

    def perf(lg_common: float) -> pl.DataFrame:
        rows = [
            ("property_type_common", "lightgbm", 1000, lg_common),
            ("property_type_common", "comps", 1000, 0.085),
            ("property_type", "lightgbm", 1100, 0.087),
        ]
        return pl.DataFrame(
            [
                {"split": "test", "breakdown": b, "model": m, "segment": "villa",
                 "n_scored": n, "mdape": md, "hit20": 0.85}
                for b, m, n, md in rows
            ]
        )  # fmt: skip

    tie = report_avm.villa_comparison(perf(0.0852))
    assert "tie" in tie and "100 villas" in tie
    behind = report_avm.villa_comparison(perf(0.0866))  # the re-tuned model: 8.66% vs 8.51%
    assert "comparables are slightly better than LightGBM" in behind and "a tie" not in behind
    assert "comparables are better" in report_avm.villa_comparison(perf(0.095))
    assert "slightly ahead" in report_avm.villa_comparison(perf(0.0840))
    assert "also beats" in report_avm.villa_comparison(perf(0.070))
    assert report_avm.villa_comparison(perf(0.07).filter(pl.col("model") != "comps")) is None


def test_miss_reasons_state_what_the_numbers_show():
    # Sale at AED 15,000/sq m vs a 10,000 reference; AVM at 20,000. The building trades at
    # 14,500 (ln 1.45 above the reference) and the project median drove the value up.
    ex = {
        "gap_pct": -0.25,
        "price_aed": 1_500_000,
        "avm_value_aed": 2_000_000,
        "area_sqm": 100.0,
        "reference_ppsqm_aed": 10_000.0,
        "comps_6m_n": 50,
        "shap": {"top": [{"feature": "proj_rel_12m", "value": 0.5, "shap": 0.35},
                         {"feature": "bldg_rel_24m", "value": float(np.log(1.45)), "shap": 0.02}]},
    }  # fmt: skip
    reasons = avm_explain.miss_reasons(ex)
    assert "+50%" in reasons[0] and "+100%" in reasons[0]  # sale and AVM vs the reference
    assert "+3% from its building" in reasons[1] and "in line with its building" in reasons[1]
    assert "Project median, 12m" in reasons[2] and "+65% vs the reference price" in reasons[2]
    assert "project median pools" in reasons[3]
    assert not any("Thin comparables" in r for r in reasons)

    # A price far from its building's median is unit-specific; thin comps are reported.
    ex.update(bldg_rel_24m=float(np.log(2.0)), bldg_n_24m=1664, comps_6m_n=3)
    reasons = avm_explain.miss_reasons(ex)
    assert any("Thin comparables: 3 sales" in r for r in reasons)
    assert any("1,664 sales" in r and "specific to the unit" in r for r in reasons)
    assert "register doesn't record" in reasons[-1]


def test_features_and_categoricals_are_disjoint_and_complete():
    from dubai_property.features import build

    assert not set(build.CATEGORICALS) & set(build.NUMERICS)
    assert build.FEATURES == build.CATEGORICALS + build.NUMERICS
    # No raw target, price or time-trend leaks into the model inputs.
    for banned in ("ln_ppsqm", "price_aed", "target_rel", "ref_ln", "month", "mi", "txn_date"):
        assert banned not in build.FEATURES


# --- Written tables (skipped until make train has run) -------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = db.connect(connect_timeout=3)
    except (RuntimeError, psycopg.OperationalError) as exc:
        pytest.skip(f"database not reachable: {exc}")
    with c:
        (exists,) = c.execute("select to_regclass('ml.avm_score') is not null").fetchone()
        if not exists:
            pytest.skip("ml.avm_score not built yet (run make train)")
        yield c


def test_review_flag_is_null_on_training_rows(conn):
    (bad,) = conn.execute(
        "select count(*) from ml.avm_score where model_version = %s and "
        "((model_set = 'train') <> (is_review is null))",
        [config.AVM_MODEL_VERSION],
    ).fetchone()
    assert bad == 0


def test_performance_has_every_model_and_one_champion(conn):
    rows = conn.execute(
        "select model, bool_or(is_champion) from ml.avm_performance where model_version = %s"
        " and split = 'test' and breakdown = 'overall' group by 1",
        [config.AVM_MODEL_VERSION],
    ).fetchall()
    assert {m for m, _ in rows} <= set(avm.MODELS)
    assert sum(1 for _, champ in rows if champ) <= 1
    (n_bad,) = conn.execute(
        "select count(*) from ml.avm_performance where model_version = %s and"
        " (n_scored < %s or coverage > 1)",
        [config.AVM_MODEL_VERSION, config.MIN_N],
    ).fetchone()
    assert n_bad == 0


def test_scores_are_dated_from_the_training_start(conn):
    (first,) = conn.execute(
        "select min(txn_date) from ml.avm_score where model_version = %s",
        [config.AVM_MODEL_VERSION],
    ).fetchone()
    assert first >= config.AVM_TRAIN_START
