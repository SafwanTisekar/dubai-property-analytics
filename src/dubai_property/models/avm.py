"""Automated valuation model (docs/05 §1): baselines, hedonic OLS, LightGBM; ml.avm_*.

What it does (``make train``), in order:

1. Loads clean residential market sales from 2010 (2010 = history for the trailing
   features; fitting starts in 2011, like the index) on the hedonic index's basis
   (villas: bedroom-known only; areas within the class cap). Rows out are logged by reason.
2. Builds the as-of features (``features.build``): real-time index vintages, trailing
   comparable medians, the reference price. No feature of a month-M sale uses a sale
   dated M or later (``tests/test_avm_features.py``).
3. Scores four models out of time (``models.split``: train <= 2023, validation 2024,
   test 2025+):

   * ``comps``: median AED per sq m of the cell (area x type x bedrooms x off-plan) over
     the previous 6 months, needing ``AVM_COMPS_MIN_N`` sales (docs/05 §1 baseline);
   * ``comps_indexed``: the cell's sales of the last 12 months, each moved to the
     valuation date by the real-time index (the stronger baseline);
   * ``hedonic_ols``: the rolling time-dummy regression of the index, re-fitted every
     month on the 36 months before it, priced at the latest month's effect;
   * ``lightgbm``: gradient boosting on the log ratio to the as-of reference price, early
     stopping on validation, Optuna (<= 50 trials) tuned on validation only, then re-fitted
     on train + validation with the tuned number of trees for the test period.

4. Picks the champion on **validation** MdAPE (never test), evaluates every model on test
   by segment and month (``models.avm_eval``), and **stops before writing anything** if a
   result is too good to be true (``avm_eval.leakage_alarm``).
5. SHAP importance, dependence data and the rule-based worked examples
   (``models.avm_explain``).
6. Writes ``ml.avm_score``, ``ml.avm_performance`` and ``ml.feature_importance`` with COPY,
   plus diagnostics and artifacts for ``make model-reports``.

Usage::

    uv run python -m dubai_property.models.avm              # part of make train
    uv run python -m dubai_property.models.avm --trials 5   # quick run (fewer Optuna trials)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

import connectorx as cx
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import polars as pl

from dubai_property import config, db
from dubai_property.features import build
from dubai_property.models import avm_eval, avm_explain, split
from dubai_property.models import hedonic_index as h

log = logging.getLogger(__name__)

MODELS = ("comps", "comps_indexed", "hedonic_ols", "lightgbm")
ARTIFACTS_NAME = "avm"

# One row per clean residential sale since 2010, on the hedonic index's population basis.
POPULATION_SQL = """
select t.transaction_id,
       t.txn_date,
       date_trunc('month', t.txn_date)::date as month,
       t.area_key,
       a.area_name,
       a.zone,
       t.property_type_key,
       coalesce(t.property_sub_type, 'Unknown') as property_sub_type,
       coalesce(least(t.bedrooms, {cap}), -1) as bedrooms,
       ln(t.area_sqm::float8) as ln_area,
       t.area_sqm::float8 as area_sqm,
       t.is_offplan,
       t.has_parking,
       t.is_penthouse,
       t.actual_worth_aed::float8 as price_aed,
       ln(t.price_per_sqm_aed::float8) as ln_ppsqm,
       t.project_key,
       t.building_name,
       t.nearest_metro,
       coalesce(p.master_project, 'Unknown') as master_project
from gold.fct_transaction as t
join gold.dim_area as a on a.area_key = t.area_key
left join gold.dim_project as p on p.project_key = t.project_key
where t.is_clean_market_sale
  and t.is_in_report_scope
  and t.property_type_key in ({apt}, {villa})
  and t.txn_date >= date '{start}'
  and not t.is_area_above_class_cap
  and (t.property_type_key = {apt} or t.bedrooms is not null)
"""

# Rows in and out of the population, with the reason (CLAUDE.md: log every filter).
EXCLUSIONS_SQL = """
select property_type_key,
       count(*) as clean_sales,
       count(*) filter (where is_area_above_class_cap) as above_class_cap,
       count(*) filter (where not is_area_above_class_cap and property_type_key = {villa}
                        and bedrooms is null) as villa_no_bedrooms
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope
  and property_type_key in ({apt}, {villa}) and txn_date >= date '{start}'
group by 1
order by 1
"""

RATES_SQL = "select month, fed_funds_rate::float8 as fed_funds_rate from gold.fct_rates_monthly"

SCORE_DDL = f"""
create table if not exists {config.SCHEMA_ML}.avm_score (
    model_version       text           not null,
    scored_at           timestamptz    not null,
    model               text           not null,
    transaction_id      text           not null,
    txn_date            date           not null,
    area_key            integer        not null,
    property_type_key   integer        not null,
    bedrooms            smallint,
    is_offplan          boolean        not null,
    area_sqm            numeric(12, 2) not null,
    model_set           text           not null,
    actual_price_aed    numeric(18, 2) not null,
    predicted_value_aed numeric(18, 2) not null,
    predicted_ppsqm_aed numeric(18, 2) not null,
    abs_pct_error       numeric(12, 6) not null,
    gap_pct             numeric(12, 6) not null,
    is_review           boolean,
    comps_value_aed     numeric(18, 2),
    primary key (model_version, transaction_id)
)
"""
SCORE_COLUMNS = [
    "model_version", "scored_at", "model", "transaction_id", "txn_date", "area_key",
    "property_type_key", "bedrooms", "is_offplan", "area_sqm", "model_set",
    "actual_price_aed", "predicted_value_aed", "predicted_ppsqm_aed", "abs_pct_error",
    "gap_pct", "is_review", "comps_value_aed",
]  # fmt: skip

PERF_DDL = f"""
create table if not exists {config.SCHEMA_ML}.avm_performance (
    model_version text           not null,
    fitted_at     timestamptz    not null,
    model         text           not null,
    is_champion   boolean        not null,
    split         text           not null,
    breakdown     text           not null,
    segment       text           not null,
    n_total       integer,
    n_scored      integer        not null,
    coverage      numeric(8, 6),
    mdape         numeric(10, 6) not null,
    hit10         numeric(8, 6)  not null,
    hit20         numeric(8, 6)  not null,
    mape          numeric(12, 6) not null,
    r2_log_price  numeric(10, 6),
    primary key (model_version, model, split, breakdown, segment)
)
"""

IMPORTANCE_DDL = f"""
create table if not exists {config.SCHEMA_ML}.feature_importance (
    model_version text           not null,
    fitted_at     timestamptz    not null,
    feature       text           not null,
    feature_group text           not null,
    mean_abs_shap numeric(12, 8) not null,
    gain          numeric(20, 4) not null,
    rank          integer        not null,
    primary key (model_version, feature)
)
"""


def artifacts() -> Path:
    """``artifacts/avm`` (a scratch folder when ``PG_DB`` isn't the main database)."""
    path = db.artifacts_dir() / ARTIFACTS_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- Data ----------------------------------------------------------------------------
def _fmt(sql: str) -> str:
    return sql.format(
        cap=h.BEDROOMS_CAP, apt=h.APARTMENT, villa=h.VILLA, start=config.AVM_HISTORY_START
    )


def load_population() -> pl.DataFrame:
    """Model-sized frame (~0.9M rows x 20 columns) via connectorx; filtered in SQL."""
    df = cx.read_sql(db.connectorx_uri(), _fmt(POPULATION_SQL), return_type="polars")
    return df.with_columns(pl.col("month").cast(pl.Date), pl.col("txn_date").cast(pl.Date))


def load_rates() -> pl.DataFrame:
    """Monthly Fed Funds (the EIBOR proxy until a CBUAE file is loaded, docs/01 §8)."""
    df = cx.read_sql(db.connectorx_uri(), RATES_SQL, return_type="polars")
    return df.with_columns(pl.col("month").cast(pl.Date))


def load_exclusions(conn) -> list[dict]:
    """Clean sales per type and the rows left out, with the reason."""
    cur = conn.execute(_fmt(EXCLUSIONS_SQL))
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


# --- LightGBM ------------------------------------------------------------------------
def categories_of(train: pl.DataFrame) -> dict[str, list[str]]:
    """Category levels seen in training; anything else is treated as missing."""
    cats = train.select(build.CATEGORICALS).with_columns(
        pl.all().cast(pl.Utf8).fill_null("missing")
    )
    return {c: sorted(cats[c].unique().to_list()) for c in build.CATEGORICALS}


def to_lgb(df: pl.DataFrame, categories: dict[str, list[str]]) -> pd.DataFrame:
    """Model-ready pandas frame: numerics as float, categoricals with the training levels."""
    p = (
        df.select(build.FEATURES)
        .with_columns(pl.col(build.CATEGORICALS).cast(pl.Utf8).fill_null("missing"))
        .to_pandas()
    )
    for c in build.CATEGORICALS:
        known = set(categories[c])
        p[c] = pd.Categorical(p[c].where(p[c].isin(known)), categories=categories[c])
    for c in build.NUMERICS:
        p[c] = p[c].astype("float64")
    return p


BASE_PARAMS = {
    "objective": "huber",  # robust to the odd mispriced sale, unlike squared error
    "learning_rate": 0.05,
    "bagging_freq": 1,
    "max_cat_to_onehot": 8,
    "verbose": -1,
    "seed": config.AVM_SEED,
    "deterministic": True,
    "force_row_wise": True,
}
DEFAULT_PARAMS = {
    "alpha": 0.15,
    "num_leaves": 127,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "lambda_l2": 1.0,
    "cat_smooth": 10.0,
}
MAX_ROUNDS = 5000
EARLY_STOP = 100


def fit_lgb(
    params: dict, train: tuple, valid: tuple | None = None, rounds: int | None = None
) -> lgb.Booster:
    """Fit on ``train`` = (X, y); early stopping on ``valid`` if given, else ``rounds``."""
    dtrain = lgb.Dataset(*train, categorical_feature=build.CATEGORICALS, free_raw_data=False)
    if valid is None:
        return lgb.train({**BASE_PARAMS, **params}, dtrain, num_boost_round=rounds)
    dvalid = lgb.Dataset(*valid, reference=dtrain)
    return lgb.train(
        {**BASE_PARAMS, **params, "metric": "l1"},
        dtrain,
        num_boost_round=MAX_ROUNDS,
        valid_sets=[dvalid],
        callbacks=[lgb.early_stopping(EARLY_STOP, verbose=False)],
    )


def price_mdape(ref_ln: np.ndarray, rel_pred: np.ndarray, area: np.ndarray, price: np.ndarray):
    """MdAPE of the AED price implied by a predicted log ratio to the reference."""
    pred = np.exp(ref_ln + rel_pred) * area
    return float(np.median(np.abs(pred - price) / price))


def tune(train: tuple, valid: tuple, valid_frame: pl.DataFrame, trials: int) -> dict:
    """Optuna TPE search, scored on validation MdAPE only (test never seen)."""
    ref = valid_frame["ref_ln"].to_numpy()
    area = valid_frame["area_sqm"].to_numpy()
    price = valid_frame["price_aed"].to_numpy()

    def objective(trial: optuna.Trial) -> float:
        params = {
            "alpha": trial.suggest_float("alpha", 0.05, 0.5, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 511, log=True),
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 20, 500, log=True),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-3, 10.0, log=True),
            "cat_smooth": trial.suggest_float("cat_smooth", 1.0, 50.0, log=True),
        }
        t = time.perf_counter()
        booster = fit_lgb(params, train, valid)
        trial.set_user_attr("best_iteration", booster.best_iteration)
        rel = booster.predict(valid[0], num_iteration=booster.best_iteration)
        value = price_mdape(ref, rel, area, price)
        log.info(
            "optuna trial %d/%d: validation MdAPE %.4f, %d trees, %.0fs",
            trial.number + 1,
            trials,
            value,
            booster.best_iteration,
            time.perf_counter() - t,
        )
        return value

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction="minimize", sampler=optuna.samplers.TPESampler(seed=config.AVM_SEED)
    )
    study.enqueue_trial(DEFAULT_PARAMS)  # the hand-set starting point is trial 0
    study.optimize(objective, n_trials=trials)
    log.info(
        "optuna: %d trials, best validation MdAPE %.4f (trial %d)",
        len(study.trials),
        study.best_value,
        study.best_trial.number,
    )
    return {
        "params": study.best_params,
        "best_value": study.best_value,
        "trials": [
            {"number": t.number, "value": t.value, "params": t.params, **t.user_attrs}
            for t in study.trials
        ],
    }


def feature_signature() -> str:
    """Hash of the feature list and the tuning setup: saved params are reused only if equal."""
    text = json.dumps([build.FEATURES, BASE_PARAMS, config.AVM_TRAIN_START.isoformat()])
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def get_params(
    train: tuple, valid: tuple, valid_frame: pl.DataFrame, trials: int | None
) -> tuple[dict, dict]:
    """Tuned params: reuse the saved study if the features are unchanged, else tune.

    ``trials`` None: reuse ``best_params.json`` when its signature matches, otherwise
    run ``AVM_OPTUNA_TRIALS`` trials. An explicit number always re-tunes (0: defaults).
    """
    path = artifacts() / "best_params.json"
    sig = feature_signature()
    if trials is None and path.exists():
        saved = json.loads(path.read_text())
        if saved.get("signature") == sig:
            log.info("optuna: reusing %s (%d trials)", path.name, len(saved["trials"]))
            return saved["params"], saved
    n = config.AVM_OPTUNA_TRIALS if trials is None else trials
    if n <= 0:
        return dict(DEFAULT_PARAMS), {"params": DEFAULT_PARAMS, "trials": [], "signature": sig}
    study = {**tune(train, valid, valid_frame, n), "signature": sig, "tuned_at": datetime.now()}
    path.write_text(json.dumps(study, default=str, indent=1))
    return study["params"], study


# --- Orchestration -------------------------------------------------------------------
def to_value(ln_ppsqm: pl.Expr) -> pl.Expr:
    """AED value from a predicted log AED per sq m."""
    return ln_ppsqm.exp() * pl.col("area_sqm")


def run(trials: int | None = None) -> dict:
    """Fit, evaluate, explain and write the AVM outputs; see the module docstring."""
    t0 = time.perf_counter()
    timings: dict[str, float] = {}
    with db.connect() as conn:
        snapshot = h.load_snapshot(conn)
        exclusions = load_exclusions(conn)
    for e in exclusions:
        log.info(
            "type %s: %d clean sales since %s; out: %d above the class area cap, %d villas "
            "without bedrooms",
            e["property_type_key"],
            e["clean_sales"],
            config.AVM_HISTORY_START,
            e["above_class_cap"],
            e["villa_no_bedrooms"],
        )
    population = load_population()
    rates = load_rates()
    log.info("population: %d sales since %s", population.height, config.AVM_HISTORY_START)
    end_month = date(snapshot.year, snapshot.month, 1)

    t = time.perf_counter()
    vintages, pricing = build.compute_vintages(population, end_month)
    timings["vintages_s"] = time.perf_counter() - t
    t = time.perf_counter()
    feats = split.assign_split(build.build_features(population, rates, vintages, pricing))
    timings["features_s"] = time.perf_counter() - t
    counts = dict(feats.group_by("split").len().iter_rows())
    log.info("split: %s", counts)

    # Sales with no reference price (the first month of the history) can't be modelled.
    modelled = feats.filter(pl.col("split") != "history")
    no_ref = modelled.filter(pl.col("ref_ln").is_null()).height
    modelled = modelled.filter(pl.col("ref_ln").is_not_null())
    log.info("modelled: %d sales (%d without a reference price left out)", modelled.height, no_ref)
    tr = modelled.filter(pl.col("split") == "train")
    va = modelled.filter(pl.col("split") == "validation")
    te = modelled.filter(pl.col("split") == "test")
    trva = modelled.filter(pl.col("split").is_in(["train", "validation"]))
    empty = [
        name for name, df in (("train", tr), ("validation", va), ("test", te)) if df.is_empty()
    ]
    if empty:
        raise SystemExit(f"AVM: no modelled sales in {', '.join(empty)}: check the population")

    cats = categories_of(tr)
    X = {name: to_lgb(df, cats) for name, df in (("tr", tr), ("va", va), ("te", te))}
    y_tr, y_va = tr["target_rel"].to_numpy(), va["target_rel"].to_numpy()

    t = time.perf_counter()
    params, study = get_params((X["tr"], y_tr), (X["va"], y_va), va, trials)
    timings["tuning_s"] = time.perf_counter() - t

    # Train-only model: early stopping on validation; it values the validation year.
    t = time.perf_counter()
    model_tr = fit_lgb(params, (X["tr"], y_tr), (X["va"], y_va))
    best_iter = model_tr.best_iteration
    rel_va = model_tr.predict(X["va"], num_iteration=best_iter)
    # Median calibration: a median (not mean) estimate is what MdAPE and hit rates score.
    calibration = float(np.median(y_va - rel_va))
    # Final model: train + validation, the tuned number of trees; it values test (and,
    # in sample, the training years).
    cats_final = categories_of(trva)
    X_trva = to_lgb(trva, cats_final)
    model = fit_lgb(params, (X_trva, trva["target_rel"].to_numpy()), rounds=best_iter)
    X_te_final = to_lgb(te, cats_final)
    timings["lightgbm_s"] = time.perf_counter() - t
    log.info(
        "lightgbm: %d trees (early stopping on 2024), calibration %+.4f log points",
        best_iter,
        calibration,
    )
    model.save_model(str(artifacts() / "lightgbm.txt"))

    lgb_ln = pl.concat(
        [
            tr.select(
                "transaction_id",
                (pl.col("ref_ln") + model.predict(to_lgb(tr, cats_final)) + calibration).alias(
                    "lightgbm_ln"
                ),
            ),
            va.select(
                "transaction_id", (pl.col("ref_ln") + rel_va + calibration).alias("lightgbm_ln")
            ),
            te.select(
                "transaction_id",
                (pl.col("ref_ln") + model.predict(X_te_final) + calibration).alias("lightgbm_ln"),
            ),
        ]
    )
    scored = modelled.join(lgb_ln, on="transaction_id", how="left").with_columns(
        pred_comps=to_value(pl.col("base_comps_ln")),
        pred_comps_indexed=to_value(pl.col("base_comps_idx_ln")),
        pred_hedonic_ols=to_value(pl.col("base_ols_ln")),
        pred_lightgbm=to_value(pl.col("lightgbm_ln")),
    )

    perf = avm_eval.evaluate(scored, MODELS)
    val_common = perf.filter(
        (pl.col("split") == "validation") & (pl.col("breakdown") == "overall_common")
    ).sort("mdape")
    champion = val_common["model"][0] if val_common.height else "lightgbm"
    log.info("champion on validation (common subset MdAPE): %s", champion)
    for r in perf.filter(
        (pl.col("split") == "test") & (pl.col("breakdown").is_in(["overall", "overall_common"]))
    ).iter_rows(named=True):
        log.info(
            "test %-15s %-14s n=%7d coverage=%s MdAPE=%.2f%% hit10=%.1f%% hit20=%.1f%%",
            r["breakdown"],
            r["model"],
            r["n_scored"],
            f"{r['coverage']:.1%}" if r["coverage"] is not None else "-",
            100 * r["mdape"],
            100 * r["hit10"],
            100 * r["hit20"],
        )

    alarm = avm_eval.leakage_alarm(perf)
    diagnostics = {
        "model_version": config.AVM_MODEL_VERSION,
        "fitted_at": datetime.now().astimezone(),
        "snapshot": snapshot,
        "exclusions": exclusions,
        "population_rows": population.height,
        "split_rows": counts,
        "modelled_rows": modelled.height,
        "no_reference_rows": no_ref,
        "vintage_rows": vintages.height,
        "params": params,
        "tuning": {k: v for k, v in study.items() if k != "trials"},
        "n_trials": len(study.get("trials", [])),
        "best_iteration": best_iter,
        "calibration": calibration,
        "champion": champion,
        "leakage_alarm": alarm,
        "ref_source_test": dict(te.group_by("ref_source").len().iter_rows()),
        "idx_source_test": dict(te.group_by("idx_source").len().iter_rows()),
    }
    diag_path = artifacts() / "diagnostics.json"
    if alarm:
        diag_path.write_text(json.dumps(diagnostics, default=str, indent=1))
        for reason in alarm:
            log.error("LEAKAGE ALARM: %s", reason)
        raise SystemExit(
            "AVM results too good to be true (CLAUDE.md): nothing written to ml.*. "
            f"Investigate before going further; diagnostics in {diag_path}"
        )

    # Ablation: fit from 2010 (the docs/05 split) with the same params, test only.
    t = time.perf_counter()
    diagnostics["ablation_2010"] = ablation_2010(feats, params)
    timings["ablation_s"] = time.perf_counter() - t

    t = time.perf_counter()
    diagnostics.update(explain(model, te, X_te_final, scored, cats_final, calibration))
    timings["shap_s"] = time.perf_counter() - t

    fitted_at = diagnostics["fitted_at"]
    score = score_frame(scored, champion, fitted_at)
    importance = diagnostics.pop("_importance")
    with db.connect() as conn:
        written = write_outputs(conn, score, perf, champion, importance, fitted_at)
        conn.commit()
    diagnostics["rows_written"] = written
    timings["total_s"] = time.perf_counter() - t0
    diagnostics["timings"] = timings
    diag_path.write_text(json.dumps(diagnostics, default=str, indent=1))
    log.info("avm: %s written in %.0fs", written, timings["total_s"])
    return diagnostics


def ablation_2010(feats: pl.DataFrame, params: dict) -> dict:
    """Test accuracy if fitting started in 2010 (docs/05 §1) instead of 2011."""
    from_2010 = (
        feats.drop("split")
        .pipe(split.assign_split, train_start=config.AVM_HISTORY_START)
        .filter(pl.col("ref_ln").is_not_null())
    )
    out = {}
    for name, frame in (
        ("2011_start", feats.filter(pl.col("ref_ln").is_not_null())),
        ("2010_start", from_2010),
    ):
        tr = frame.filter(pl.col("split") == "train")
        va = frame.filter(pl.col("split") == "validation")
        te = frame.filter(pl.col("split") == "test")
        cats = categories_of(tr)
        booster = fit_lgb(
            params,
            (to_lgb(tr, cats), tr["target_rel"].to_numpy()),
            (to_lgb(va, cats), va["target_rel"].to_numpy()),
        )
        pred = (
            np.exp(te["ref_ln"].to_numpy() + booster.predict(to_lgb(te, cats)))
            * te["area_sqm"].to_numpy()
        )
        out[name] = {
            "train_rows": tr.height,
            "trees": booster.best_iteration,
            **avm_eval.metrics(te["price_aed"].to_numpy(), pred),
        }
        log.info(
            "ablation %s: %d training sales, test MdAPE %.2f%% (train-only model, uncalibrated)",
            name,
            tr.height,
            100 * out[name]["mdape"],
        )
    return out


def feature_group(feature: str) -> str:
    """Feature family for the importance chart."""
    if feature.startswith(("cell_", "at_", "zt_", "comps_")):
        return "comparable sales"
    if feature.startswith(("proj_", "bldg_")):
        return "project / building history"
    if feature.startswith(("idx_", "fed_")) or feature == "ref_source":
        return "market state"
    if feature in ("area_key", "zone", "nearest_metro", "master_project"):
        return "location"
    return "property"


def explain(
    model: lgb.Booster,
    te: pl.DataFrame,
    X_te: pd.DataFrame,
    scored: pl.DataFrame,
    cats: dict,
    calibration: float,
) -> dict:
    """SHAP on a seeded test sample, dependence data, and the worked examples."""
    n = min(config.AVM_SHAP_SAMPLE, te.height)
    rng = np.random.default_rng(config.AVM_SEED)
    idx = np.sort(rng.choice(te.height, size=n, replace=False)) if n else np.array([], int)
    shap, bias = avm_explain.shap_values(model, X_te.iloc[idx])
    imp = avm_explain.importance(model, shap, build.FEATURES).with_columns(
        pl.col("feature").map_elements(feature_group, return_dtype=pl.Utf8).alias("feature_group")
    )
    sample = te.with_row_index("_i").filter(pl.col("_i").is_in(idx.tolist())).select(
        "transaction_id", "area_key", "area_name", "property_type_key", "bedrooms",
        "is_offplan", "area_sqm", "ln_area",
    )  # fmt: skip
    shap_df = pl.DataFrame(shap, schema=[f"shap_{f}" for f in build.FEATURES])
    sample.hstack(shap_df).write_parquet(artifacts() / "shap_sample.parquet")

    test_scored = scored.filter(
        (pl.col("split") == "test") & pl.col("pred_lightgbm").is_not_null()
    ).with_columns(
        pl.col("pred_lightgbm").alias("pred_value"),
        ((pl.col("pred_lightgbm") - pl.col("price_aed")).abs() / pl.col("price_aed")).alias("ape"),
        (pl.col("price_aed") / pl.col("pred_lightgbm") - 1).alias("gap_pct"),
    )
    examples = []
    for ex in avm_explain.pick_examples(test_scored, avm_eval.top_areas(scored)):
        row = ex["row"]
        X_row = to_lgb(te.filter(pl.col("transaction_id") == row["transaction_id"]), cats)
        contrib = avm_explain.contributions(model, X_row, build.FEATURES)
        item = {
            "key": ex["key"],
            "title": ex["title"],
            "kind": ex["kind"],
            "transaction_id": row["transaction_id"],
            "date": row["txn_date"],
            "area": row["area_name"],
            "zone": row["zone"],
            "property_type": "apartment" if row["property_type_key"] == h.APARTMENT else "villa",
            "bedrooms": row["bedrooms"],
            "is_offplan": row["is_offplan"],
            "area_sqm": round(row["area_sqm"], 1),
            "price_aed": round(row["price_aed"]),
            "avm_value_aed": round(row["pred_value"]),
            "ape": row["ape"],
            "gap_pct": row["gap_pct"],
            "reference_source": row["ref_source"],
            "reference_ppsqm_aed": round(float(np.exp(row["ref_ln"])), 0),
            "comps_6m_n": row["cell_n_6m"],
            "bldg_rel_24m": row["bldg_rel_24m"],
            "bldg_n_24m": row["bldg_n_24m"],
            "calibration": calibration,
            "shap": contrib,
        }
        if ex["kind"] == "miss":
            item["reasons"] = avm_explain.miss_reasons(item)
        examples.append(item)
    log.info("worked examples: %s", [e["key"] for e in examples])
    return {
        "shap_sample_rows": n,
        "shap_expected_value": bias,
        "importance": imp.to_dicts(),
        "examples": examples,
        "selection_rule": avm_explain.SELECTION_RULE,
        "_importance": imp,
    }


def score_frame(scored: pl.DataFrame, champion: str, fitted_at: datetime) -> pl.DataFrame:
    """``ml.avm_score`` rows: the champion's value for every sale it can value.

    ``is_review`` (|gap| > 25%) is set only out of sample (validation, test) and left
    NULL for training rows: the model has fitted those sales, so their gaps understate
    how far the price is from what the model would have said beforehand.
    """
    pred = pl.col(f"pred_{champion}")
    gap = pl.col("price_aed") / pred - 1
    return (
        scored.filter(pred.is_not_null())
        .select(
            pl.lit(config.AVM_MODEL_VERSION).alias("model_version"),
            pl.lit(fitted_at.isoformat()).alias("scored_at"),
            pl.lit(champion).alias("model"),
            "transaction_id",
            "txn_date",
            "area_key",
            "property_type_key",
            pl.when(pl.col("bedrooms") >= 0).then(pl.col("bedrooms")).alias("bedrooms"),
            "is_offplan",
            pl.col("area_sqm").round(2),
            pl.col("split").alias("model_set"),
            pl.col("price_aed").round(2).alias("actual_price_aed"),
            pred.round(2).alias("predicted_value_aed"),
            (pred / pl.col("area_sqm")).round(2).alias("predicted_ppsqm_aed"),
            ((pred - pl.col("price_aed")).abs() / pl.col("price_aed")).alias("abs_pct_error"),
            gap.alias("gap_pct"),
            pl.when(pl.col("split") == "train")
            .then(None)
            .otherwise(gap.abs() > config.AVM_REVIEW_GAP)
            .alias("is_review"),
            pl.col("pred_comps").round(2).alias("comps_value_aed"),
        )
        .select(SCORE_COLUMNS)
    )


def write_outputs(
    conn,
    score: pl.DataFrame,
    perf: pl.DataFrame,
    champion: str,
    importance: pl.DataFrame,
    fitted_at: datetime,
) -> dict[str, int]:
    """Replace this model version's rows in the three ml tables (caller commits)."""
    version = config.AVM_MODEL_VERSION
    perf_out = perf.with_columns(
        pl.lit(version).alias("model_version"),
        pl.lit(fitted_at.isoformat()).alias("fitted_at"),
        (pl.col("model") == champion).alias("is_champion"),
    )
    imp_out = importance.with_columns(
        pl.lit(version).alias("model_version"), pl.lit(fitted_at.isoformat()).alias("fitted_at")
    ).select(
        "model_version", "fitted_at", "feature", "feature_group", "mean_abs_shap", "gain", "rank"
    )
    written = {}
    for table, ddl, frame in (
        ("avm_score", SCORE_DDL, score),
        ("avm_performance", PERF_DDL, perf_out),
        ("feature_importance", IMPORTANCE_DDL, imp_out),
    ):
        conn.execute(ddl)
        conn.execute(f"delete from {config.SCHEMA_ML}.{table} where model_version = %s", [version])
        written[table] = db.copy_frame(conn, frame, config.SCHEMA_ML, table)
        conn.execute(f"analyze {config.SCHEMA_ML}.{table}")
        log.info("%s.%s: %d rows written", config.SCHEMA_ML, table, written[table])
    return written


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make train``)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--trials",
        type=int,
        default=None,
        help="Optuna trials (default: reuse the saved study if the features are unchanged, "
        f"else {config.AVM_OPTUNA_TRIALS}; 0 = hand-set defaults)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.trials)
    return 0


if __name__ == "__main__":
    sys.exit(main())
