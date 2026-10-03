"""AVM features: the no-look-ahead proof (docs/01 §7, docs/05 §1) and the as-of mechanics.

The leakage test is behavioural, not a code review: build every feature on a synthetic
market, then rewrite history from month M on (reprice every sale dated M or later,
including the ones being valued, drop later sales, add new ones in M and after) and
rebuild everything, index vintages included. Every feature and every baseline of a sale
dated in M must come out the same. A power check perturbs M-1 instead and requires the
features to move, so the test can't pass by computing nothing.
"""

from datetime import date

import numpy as np
import polars as pl
import pytest

from dubai_property import config
from dubai_property.features import asof_index, asof_market, build
from dubai_property.models import hedonic_index as h

START, END = date(2017, 1, 1), date(2020, 6, 1)
ZONES = {1: "North", 2: "North", 3: "South", 4: "South"}
CHECKED = build.FEATURES + list(build.BASELINES.values()) + ["ref_ln", "ref_source"]


def synthetic_population(
    start: date = START, end: date = END, seed: int = 3, prefix: str = "t"
) -> pl.DataFrame:
    """Apartments and villas in four areas, two zones, a rising market, mixed features."""
    rng = np.random.default_rng(seed)
    rows = []
    for t, m in enumerate(h.period_grid(start, end, "month")):
        for type_key, n in ((101, 90), (102, 45)):
            area = rng.integers(1, 5, n)
            beds = rng.integers(0, 4, n) if type_key == 101 else rng.integers(2, 6, n)
            offplan = rng.random(n) < 0.4
            ln_area = np.log(45 + 40 * beds + rng.normal(0, 6, n).clip(-15, 15))
            y = (
                9.0
                + 0.01 * t
                + 0.12 * area
                - 0.2 * ln_area
                + 0.15 * offplan
                + (0.1 if type_key == 102 else 0)
                + rng.normal(0, 0.05, n)
            )
            for i in range(n):
                area_sqm = float(np.exp(ln_area[i]))
                rows.append(
                    {
                        "transaction_id": f"{prefix}-{type_key}-{t}-{i}",
                        "txn_date": date(m.year, m.month, 1 + int(rng.integers(0, 27))),
                        "month": m,
                        "area_key": int(area[i]),
                        "zone": ZONES[int(area[i])],
                        "property_type_key": type_key,
                        "property_sub_type": "Flat" if type_key == 101 else "Villa",
                        "bedrooms": int(beds[i]),
                        "ln_area": float(ln_area[i]),
                        "area_sqm": area_sqm,
                        "is_offplan": bool(offplan[i]),
                        "has_parking": bool(rng.random() < 0.7),
                        "is_penthouse": False,
                        "ln_ppsqm": float(y[i]),
                        "price_aed": float(np.exp(y[i]) * area_sqm),
                        "project_key": int(rng.integers(-1, 6)),
                        "building_name": f"B{int(area[i])}{int(rng.integers(0, 4))}"
                        if type_key == 101
                        else None,
                        "nearest_metro": None if rng.random() < 0.3 else f"M{int(area[i])}",
                        "master_project": f"MP{int(area[i])}",
                    }
                )
    return pl.DataFrame(rows)


def rates_for(population: pl.DataFrame) -> pl.DataFrame:
    months = h.period_grid(START, END, "month")
    return pl.DataFrame({"month": months, "fed_funds_rate": np.linspace(0.01, 0.05, len(months))})


def features(population: pl.DataFrame) -> pl.DataFrame:
    return build.compute_all(population, rates_for(population), END)


def rewrite_from(pop: pl.DataFrame, cut: date, seed: int = 11) -> pl.DataFrame:
    """History from ``cut`` on rewritten; the sales dated in ``cut`` keep their ids."""
    rng = np.random.default_rng(seed)
    before = pop.filter(pl.col("month") < cut)
    in_cut = pop.filter(pl.col("month") == cut)
    in_cut = in_cut.with_columns(pl.col("ln_ppsqm") + pl.Series(rng.normal(0, 0.5, in_cut.height)))
    later = (
        pop.filter(pl.col("month") > cut)
        .sample(fraction=0.6, seed=seed)
        .with_columns(pl.col("ln_ppsqm") + 0.7)
    )
    extra = synthetic_population(cut, END, seed=seed + 1, prefix="x").with_columns(
        pl.col("ln_ppsqm") * 1.3
    )
    out = pl.concat([later, extra, in_cut, before])  # a different row order too
    return out.with_columns((pl.col("ln_ppsqm").exp() * pl.col("area_sqm")).alias("price_aed"))


def assert_same_features(a: pl.DataFrame, b: pl.DataFrame, ids: list[str]) -> None:
    a = a.filter(pl.col("transaction_id").is_in(ids)).sort("transaction_id")
    b = b.filter(pl.col("transaction_id").is_in(ids)).sort("transaction_id")
    assert a.height == b.height == len(ids)
    for col in CHECKED:
        x, y = a[col], b[col]
        assert (x.is_null() == y.is_null()).all(), col
        if x.dtype.is_numeric():
            xv = x.drop_nulls().to_numpy().astype(float)
            yv = y.drop_nulls().to_numpy().astype(float)
            np.testing.assert_allclose(xv, yv, rtol=0, atol=1e-9, err_msg=col)
        else:
            assert x.to_list() == y.to_list(), col


@pytest.fixture(scope="module")
def population() -> pl.DataFrame:
    return synthetic_population()


@pytest.fixture(scope="module")
def base(population) -> pl.DataFrame:
    return features(population)


@pytest.mark.parametrize("cut", [date(2018, 3, 1), date(2020, 2, 1)])
def test_no_look_ahead_features_ignore_everything_from_their_month_on(population, base, cut):
    ids = population.filter(pl.col("month") == cut)["transaction_id"].to_list()
    rewritten = features(rewrite_from(population, cut))
    assert_same_features(base, rewritten, ids)
    # The test has teeth: the market features of these sales are populated.
    checked = base.filter(pl.col("transaction_id").is_in(ids))
    for col in ("cell_rel_12m", "comps_idx_rel", "idx_chg_3m", "base_comps_ln", "base_ols_ln"):
        assert checked[col].is_not_null().mean() > 0.5, col


def test_power_check_features_do_move_when_the_previous_month_changes(population, base):
    cut = date(2020, 2, 1)
    prev = h.add_months(cut, -1)
    ids = population.filter(pl.col("month") == cut)["transaction_id"].to_list()
    bumped = population.with_columns(
        pl.when(pl.col("month") == prev)
        .then(pl.col("ln_ppsqm") + 0.3)
        .otherwise(pl.col("ln_ppsqm"))
        .alias("ln_ppsqm")
    )
    moved = features(bumped)
    a = base.filter(pl.col("transaction_id").is_in(ids)).sort("transaction_id")
    b = moved.filter(pl.col("transaction_id").is_in(ids)).sort("transaction_id")
    for col in ("base_comps_ln", "base_comps_idx_ln", "base_ols_ln", "idx_chg_3m"):
        diff = (a[col] - b[col]).abs().drop_nulls()
        assert diff.max() > 0.01, col


def test_no_feature_uses_the_sale_own_price(population, base):
    """A sale's own price feeds only its target, never its features."""
    cut = date(2019, 6, 1)
    one = population.filter(pl.col("month") == cut)["transaction_id"][0]
    changed = population.with_columns(
        pl.when(pl.col("transaction_id") == one)
        .then(pl.col("ln_ppsqm") + 5)
        .otherwise(pl.col("ln_ppsqm"))
        .alias("ln_ppsqm")
    )
    assert_same_features(base, features(changed), [one])


def test_trailing_stats_match_a_brute_force_median(population):
    sales = population.with_columns(asof_market.month_index())
    stats = asof_market.trailing_stats(sales, ["area_key"], (3, 12), "a")
    target = sales["mi"].max()
    for area in (1, 4):
        prior = sales.filter(
            (pl.col("area_key") == area) & pl.col("mi").is_between(target - 3, target - 1)
        )["ln_ppsqm"]
        row = stats.filter((pl.col("area_key") == area) & (pl.col("mi") == target))
        assert row["a_n_3m"][0] == prior.len()
        assert row["a_med_3m"][0] == pytest.approx(prior.median())


def test_vintage_equals_the_rolling_index_fitted_on_earlier_data_only(population):
    """Vintage V is exactly the published method run on the sales before V."""
    seg = h.Segment("apartment", "type", 101, None)
    v = date(2020, 3, 1)
    vint, _ = asof_index.realtime_index(seg, population, [v])
    effects, _ = h.rolling_window_index(
        seg, seg.select(population.filter(pl.col("month") < v)), h.add_months(v, -1)
    )
    periods = vint["period"].to_list()
    ours = np.diff(vint["log_index"].to_numpy())
    ref = np.diff([effects[p] for p in periods])
    np.testing.assert_allclose(ours, ref, atol=1e-9)
    assert max(periods) == h.add_months(v, -1)
    assert len(periods) == asof_index.KEEP_PERIODS


def test_reference_falls_back_through_the_comparable_levels(base):
    assert set(base["ref_source"].unique()) <= {
        "comps_indexed",
        "cell_12m",
        "area_12m",
        "zone_12m",
        "type_3m",
        "none",
    }
    later = base.filter(pl.col("month") >= date(2018, 1, 1))
    assert (later["ref_source"] == "none").sum() == 0
    np.testing.assert_allclose(
        later["target_rel"].to_numpy(), (later["ln_ppsqm"] - later["ref_ln"]).to_numpy()
    )


def test_first_month_has_no_market_features(base):
    first = base.filter(pl.col("month") == START)
    assert first["cell_rel_12m"].is_null().all()
    assert first["base_comps_ln"].is_null().all()
    assert (first["cell_n_12m"] == 0).all()


def test_config_comps_rules():
    assert config.AVM_COMPS_MIN_N >= 3
    assert config.AVM_COMPS_MONTHS == 6  # docs/05 §1 baseline
