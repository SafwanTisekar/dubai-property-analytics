"""Gross rental yields by area x property type x bedrooms x quarter (docs/05 §3).

``gross_yield = median annual rent / median sale price`` for the same cell:

* **Rent side:** new market rents (``is_market_rent``): new contracts only (renewals lag
  the market), **single-line contracts only** (rule C11, option 1: a multi-unit contract
  repeats its amount on every line, so its per-unit rent is an allocation, not a price),
  no outliers, non-market property types or bad dates. Rent = the contract's annual rent.
* **Sale side:** clean market sales of **ready** units (``is_clean_market_sale`` and not
  off-plan). An off-plan price buys a unit that can't be let yet, often on a payment plan,
  so it isn't the price a landlord pays for this rent. Price = AED per unit, so the villa
  plot-vs-built-up area question (Phase 3) doesn't arise.
* **Min-n:** a cell is published only with ≥ 20 observations on **both** sides. Thin area
  cells roll up to the zone (medians recomputed from the rows, not averaged); zone cells
  under min-n aren't published either. Sample sizes are kept on every row.
* **Sanity:** yields outside 2-15% are logged as a warning (a bedroom label or price that
  doesn't match the rent's unit), not dropped; the published value is kept.

Gross yield excludes service charges, vacancy, maintenance and fees, so net yields are
lower (reports/yields.md).

Everything heavy runs in Postgres: ``fct_rent_contract`` never leaves the database; only
the cell medians (tens of thousands of rows) are read.

Usage::

    uv run python -m dubai_property.models.yields      # part of make train
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Sequence
from datetime import date, datetime

import polars as pl

from dubai_property import config, db
from dubai_property.models.hedonic_index import add_months, quarter_start

log = logging.getLogger(__name__)

ML_TABLE = "agg_yield_quarter"

# Medians for both sides at two grains in one pass: area cells and zone cells (grouping
# sets, so the zone medians come from the rows). grouping(area_key) = 1 on zone rows.
CELLS_SQL = """
with rent as (
    select date_trunc('quarter', r.start_date)::date as quarter_start, a.zone, r.area_key,
           r.property_type_key, r.bedrooms, r.annual_rent_contract_aed::float8 as value
    from gold.fct_rent_contract as r
    join gold.dim_area as a on a.area_key = r.area_key
    where r.is_market_rent and r.is_in_report_scope and r.area_key >= 0
      and r.property_type_key in ({keys}) and r.bedrooms is not null
      and r.start_date >= date '{start}'
),
sale as (
    select date_trunc('quarter', t.txn_date)::date as quarter_start, a.zone, t.area_key,
           t.property_type_key, t.bedrooms, t.actual_worth_aed::float8 as value
    from gold.fct_transaction as t
    join gold.dim_area as a on a.area_key = t.area_key
    where t.is_clean_market_sale and t.is_in_report_scope and not t.is_offplan
      and t.area_key >= 0 and t.property_type_key in ({keys}) and t.bedrooms is not null
      and t.txn_date >= date '{start}'
),
{side_cells}
select coalesce(r.geo_level, s.geo_level) as geo_level,
       coalesce(r.quarter_start, s.quarter_start) as quarter_start,
       coalesce(r.zone, s.zone) as zone,
       coalesce(r.area_key, s.area_key) as area_key,
       coalesce(r.property_type_key, s.property_type_key) as property_type_key,
       coalesce(r.bedrooms, s.bedrooms) as bedrooms,
       coalesce(r.n, 0) as n_rent,
       coalesce(s.n, 0) as n_sale,
       r.median_value as median_annual_rent_aed,
       s.median_value as median_price_aed
from rent_cells as r
full join sale_cells as s
    on s.geo_level = r.geo_level and s.quarter_start = r.quarter_start and s.zone = r.zone
   and s.area_key is not distinct from r.area_key
   and s.property_type_key = r.property_type_key and s.bedrooms = r.bedrooms
"""

SIDE_CELLS = """{side}_cells as (
    select case when grouping(area_key) = 1 then 'zone' else 'area' end as geo_level,
           quarter_start, zone, area_key, property_type_key, bedrooms, count(*) as n,
           percentile_cont(0.5) within group (order by value) as median_value
    from {side}
    group by grouping sets (
        (quarter_start, zone, area_key, property_type_key, bedrooms),
        (quarter_start, zone, property_type_key, bedrooms)
    )
)"""

DDL = f"""
create table if not exists {config.SCHEMA_ML}.{ML_TABLE} (
    model_version          text           not null,
    fitted_at              timestamptz    not null,
    quarter_start          date           not null,
    geo_level              text           not null,
    zone                   text           not null,
    area_key               integer,
    property_type_key      integer        not null,
    bedrooms               integer        not null,
    n_rent                 integer        not null,
    n_sale                 integer        not null,
    median_annual_rent_aed numeric(18, 2) not null,
    median_price_aed       numeric(18, 2) not null,
    gross_yield            numeric(8, 6)  not null,
    is_outside_sanity      boolean        not null,
    areas_rolled_up        integer,
    is_partial_period      boolean        not null
)
"""

COLUMNS = [
    "model_version", "fitted_at", "quarter_start", "geo_level", "zone", "area_key",
    "property_type_key", "bedrooms", "n_rent", "n_sale", "median_annual_rent_aed",
    "median_price_aed", "gross_yield", "is_outside_sanity", "areas_rolled_up",
    "is_partial_period",
]  # fmt: skip

CELL_KEYS = ["quarter_start", "zone", "property_type_key", "bedrooms"]


def cells_sql(
    keys: Sequence[int] = config.RESIDENTIAL_HOMES_KEYS, start: date = config.YIELD_START
) -> str:
    """The cell query for the given property type keys and start date."""
    side_cells = ",\n".join(SIDE_CELLS.format(side=side) for side in ("rent", "sale"))
    return CELLS_SQL.format(
        keys=", ".join(str(int(k)) for k in keys), start=start.isoformat(), side_cells=side_cells
    )


def publish(
    cells: pl.DataFrame,
    min_n: int = config.MIN_N,
    sanity: tuple[float, float] = config.YIELD_SANITY,
) -> pl.DataFrame:
    """Apply the min-n rule on both sides and compute the yields.

    Args:
        cells: One row per (geo_level, quarter, zone, area_key, type, bedrooms) with
            ``n_rent``, ``n_sale`` and both medians (area rows and zone rows).
        min_n: Observations needed on each side.
        sanity: Plausible gross-yield band; outside it is flagged, not dropped.

    Returns:
        Published rows only: area cells passing min-n on both sides, and zone cells
        passing it. ``areas_rolled_up`` on a zone row = area cells in that zone cell that
        had data but failed min-n (so they are only represented at zone level).
    """
    passes = (pl.col("n_rent") >= min_n) & (pl.col("n_sale") >= min_n)
    failed_areas = (
        cells.filter((pl.col("geo_level") == "area") & ~passes)
        .group_by(CELL_KEYS)
        .agg(pl.len().cast(pl.Int32).alias("areas_rolled_up"))
    )
    out = (
        cells.filter(passes & (pl.col("median_price_aed") > 0))
        .join(failed_areas, on=CELL_KEYS, how="left")
        .with_columns(
            areas_rolled_up=pl.when(pl.col("geo_level") == "zone")
            .then(pl.col("areas_rolled_up").fill_null(0))
            .otherwise(None),
            gross_yield=pl.col("median_annual_rent_aed") / pl.col("median_price_aed"),
        )
        .with_columns(is_outside_sanity=~pl.col("gross_yield").is_between(*sanity))
    )
    return out.sort("geo_level", "quarter_start", "zone", "area_key", "property_type_key")


def warn_outside_sanity(published: pl.DataFrame, examples: int = 5) -> int:
    """Log the published yields outside the sanity band; return how many there are."""
    bad = published.filter(pl.col("is_outside_sanity"))
    if bad.height:
        lo, hi = config.YIELD_SANITY
        log.warning(
            "%d of %d published yields outside %.0f-%.0f%% (kept, flagged is_outside_sanity)",
            bad.height,
            published.height,
            100 * lo,
            100 * hi,
        )
        cols = ["geo_level", "quarter_start", "zone", "area_key", "property_type_key", "bedrooms"]
        for row in bad.sort("n_sale", descending=True).head(examples).iter_rows(named=True):
            log.warning(
                "  e.g. %s yield %.1f%% (rent n=%d, sale n=%d)",
                {c: row[c] for c in cols},
                100 * row["gross_yield"],
                row["n_rent"],
                row["n_sale"],
            )
    return bad.height


def load_cells(conn) -> pl.DataFrame:
    """Cell medians from Postgres (both grains, both sides)."""
    cur = conn.execute(cells_sql())
    cols = [c.name for c in cur.description]
    schema = {
        "geo_level": pl.Utf8,
        "quarter_start": pl.Date,
        "zone": pl.Utf8,
        "area_key": pl.Int32,
        "property_type_key": pl.Int32,
        "bedrooms": pl.Int32,
        "n_rent": pl.Int64,
        "n_sale": pl.Int64,
        "median_annual_rent_aed": pl.Float64,
        "median_price_aed": pl.Float64,
    }
    assert cols == list(schema), cols
    return pl.DataFrame(cur.fetchall(), schema=schema, orient="row")


def write_yields(conn, frame: pl.DataFrame) -> int:
    """Replace this model version's rows in ``ml.agg_yield_quarter`` (caller commits)."""
    conn.execute(DDL)
    conn.execute(
        f"delete from {config.SCHEMA_ML}.{ML_TABLE} where model_version = %s",
        [config.YIELD_MODEL_VERSION],
    )
    n = db.copy_frame(conn, frame, config.SCHEMA_ML, ML_TABLE)
    conn.execute(f"analyze {config.SCHEMA_ML}.{ML_TABLE}")
    return n


def run() -> pl.DataFrame:
    """Compute, check and write the published yields; return them."""
    t0 = time.perf_counter()
    with db.connect() as conn:
        conn.execute("set work_mem = '512MB'")
        cells = load_cells(conn)
        (snapshot,) = conn.execute(
            "select data_snapshot_date from silver.int_data_snapshot"
        ).fetchone()
    log.info("%d cells read in %.0fs", cells.height, time.perf_counter() - t0)
    for level in ("area", "zone"):
        c = cells.filter(pl.col("geo_level") == level)
        log.info(
            "%s cells: %d (rent rows %d, sale rows %d)",
            level,
            c.height,
            c["n_rent"].sum(),
            c["n_sale"].sum(),
        )
    published = publish(cells)
    for level in ("area", "zone"):
        log.info(
            "published %s cells: %d of %d",
            level,
            published.filter(pl.col("geo_level") == level).height,
            cells.filter(pl.col("geo_level") == level).height,
        )
    warn_outside_sanity(published)

    # The snapshot's quarter is partial unless the snapshot is its last day.
    q = quarter_start(snapshot)
    partial_quarter = q if snapshot < date.fromordinal(add_months(q, 3).toordinal() - 1) else None
    out = published.with_columns(
        model_version=pl.lit(config.YIELD_MODEL_VERSION),
        fitted_at=pl.lit(datetime.now().astimezone().isoformat()),
        is_partial_period=pl.col("quarter_start") == pl.lit(partial_quarter, dtype=pl.Date),
    ).select(COLUMNS)
    with db.connect() as conn:
        written = write_yields(conn, out)
        conn.commit()
    log.info(
        "%s.%s: %d rows written in %.0fs",
        config.SCHEMA_ML,
        ML_TABLE,
        written,
        time.perf_counter() - t0,
    )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point (``make train``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
