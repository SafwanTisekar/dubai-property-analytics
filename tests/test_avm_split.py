"""Out-of-time split: ordered, disjoint, complete, deterministic (never random)."""

import inspect
from datetime import date

import polars as pl

from dubai_property import config
from dubai_property.models import split


def months(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        out.append(d)
        d = date(d.year + d.month // 12, d.month % 12 + 1, 1)
    return out


def test_every_month_lands_in_exactly_one_ordered_set():
    df = split.assign_split(pl.DataFrame({"month": months(date(2009, 1, 1), date(2026, 9, 1))}))
    assert df["split"].null_count() == 0
    first = df.group_by("split").agg(
        pl.col("month").min().alias("lo"), pl.col("month").max().alias("hi")
    )
    spans = {r["split"]: (r["lo"], r["hi"]) for r in first.to_dicts()}
    assert spans["train"] == (config.AVM_TRAIN_START, date(2023, 12, 1))
    assert spans["validation"] == (date(2024, 1, 1), date(2024, 12, 1))
    assert spans["test"][0] == config.TEST_START
    order = ["history", "train", "validation", "test"]
    for a, b in zip(order, order[1:], strict=False):
        assert spans[a][1] < spans[b][0]


def test_split_is_deterministic_and_has_no_random_path():
    df = pl.DataFrame({"month": months(date(2010, 1, 1), date(2026, 1, 1))})
    assert split.assign_split(df).equals(split.assign_split(df.reverse()).reverse())
    source = inspect.getsource(split).lower()
    for word in ("random", "shuffle", "sample(", "train_test_split"):
        assert word not in source.replace("never random", "").replace("a random split", "")


def test_training_starts_with_the_index():
    assert config.AVM_TRAIN_START == config.HEDONIC_START
    assert config.AVM_HISTORY_START < config.AVM_TRAIN_START
