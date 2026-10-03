"""Build the small committed CI fixtures in ``tests/fixtures/`` (``make fixtures``).

CI has no DLD data (``data/`` is gitignored and multi-GB), but it must run ``dbt build``
end to end. So a tiny extract of the real bronze tables is committed: about 2k lines per
table. DLD open data is CC BY 4.0, which allows this with attribution
(``tests/fixtures/README.md``).

Unlike ``make sample`` (a 2% statistical sample for development), the fixtures are chosen
to *exercise every rule*, so a small file still tests the tricky cases:

* **Stratified by year:** a fixed number of deals / contracts per year, ordered by
  ``md5(key)`` so every run picks the same ones.
* **Edge cases on purpose:** the Hijri-dated rows, pre-2004 rows, every
  (group, procedure) pair, repeated-value portfolio groups and similar-size batches
  (C16), lease-to-own Sales + Mortgages legs (C17), the swapped ``property_usage`` label
  (C19), sub-AED 50k prices and sub-1 sq m areas (C4, C5); for rents, multi-line
  contracts (C11), virtual units and labour camps (C20), placeholder areas (C21), extreme
  amounts (C14), implausible and future dates (C18), and a blank ``area_id``.
* **Whole groups:** transactions are sampled by the C16 candidate-group key (group,
  procedure, date, value, ID-year), so a portfolio deal is either complete or absent;
  rents by ``contract_id``, so multi-line contracts keep every line.
* **One dense segment per table** (Marsa Dubai, 2024) with more than ``min_n`` rows, so
  the area-level outlier band is built, not only the Dubai-wide fallback.

The files keep the DLD shape (every field quoted, same header), so CI loads them with the
normal loader: ``make bronze BRONZE_ROOT=tests/fixtures``.

The DLD Residential Sale Index fixture is the exception: it is **synthetic** (decision,
2026-10-01). The file comes from data.dubai, whose licence for it hasn't been confirmed as
CC BY 4.0, so no DLD value is committed. ``write_price_index_fixture`` generates 36 months
with the real header and blank pattern, which is all the dbt staging model needs.

Usage::

    uv run python -m dubai_property.ingest.fixtures
"""

from __future__ import annotations

import csv
import logging
import math
import sys
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql

from dubai_property import config, db
from dubai_property.ingest.load_bronze import METADATA_COLUMNS, SCHEMA, table_columns

log = logging.getLogger(__name__)

FIXTURES_ROOT = config.PROJECT_ROOT / "tests" / "fixtures"
RAW_PREFIX = "raw/%"  # only rows loaded from data/raw are eligible
PER_YEAR_TXN_GROUPS = 75  # candidate groups per year, 2004-2026
PER_YEAR_RENT_CONTRACTS = 90  # single-line contracts per start year
BRENT_FROM = date(2018, 1, 1)  # Brent is daily; ~2k rows from here on

# Synthetic DLD index fixture: the real 20-column header, 2018-01 to 2020-12.
PRICE_INDEX_SEGMENTS = ("all", "flat", "villa")
PRICE_INDEX_FREQS = ("monthly", "quarterly", "yearly")


def _segment_columns(segment: str) -> list[str]:
    return [f"{segment}_{f}_{k}" for f in PRICE_INDEX_FREQS for k in ("index", "price_index")]


# The DLD column order: all_*, the date, flat_*, villa_*, then the load stamp.
PRICE_INDEX_HEADER = [
    *_segment_columns("all"),
    "first_date_of_month",
    *_segment_columns("flat"),
    *_segment_columns("villa"),
    "load_timestamp",
]
PRICE_INDEX_FIXTURE_NAME = "residential_sale_index_fixture_2026-10-01.csv"

# Candidate groups (the C16 key) with the attributes the selection needs. Temp table.
TXN_GROUPS_SQL = """
create temp table fx_txn_groups as
select md5(concat_ws('|', trans_group_en, procedure_id, instance_date, actual_worth,
                     split_part(transaction_id, '-', 3))) as gkey,
       trans_group_en as grp, procedure_id, instance_date, left(instance_date, 4) as yr,
       count(*) as lines,
       max(split_part(transaction_id, '-', 4)::int)
         - min(split_part(transaction_id, '-', 4)::int) + 1 as id_span,
       max(procedure_area::numeric) / nullif(min(procedure_area::numeric), 0) as area_ratio,
       bool_or(property_usage_en = 'أخرى') as usage_swapped,
       bool_or(actual_worth::numeric < 50000) as low_price,
       bool_or(procedure_area::numeric < 1) as tiny_area,
       min(area_id) as area_id, min(property_type_en) as property_type
from bronze.dld_transactions
where _source_file like %(raw)s
group by trans_group_en, procedure_id, instance_date, actual_worth,
         split_part(transaction_id, '-', 3)
"""

# Each branch picks group keys for one reason; the union is the fixture.
TXN_PICK_SQL = """
create temp table fx_txn_keys as
with g as (select *, row_number() over (order by gkey) as h from fx_txn_groups),
lto_sales as (  -- lease-to-own Sales legs (single line) ...
    select t.procedure_id, t.instance_date, t.area_id, t.procedure_area
    from bronze.dld_transactions t
    where t._source_file like %(raw)s and t.trans_group_en = 'Sales'
      and t.procedure_id in ('107', '110', '361', '371', '715', '814')
    order by md5(t.transaction_id) limit 8
),
picks as (
    select gkey from g where instance_date < '1900'                                -- Hijri
    union select gkey from (select gkey from g where instance_date between '1900' and '2003-12-31'
                            order by h limit 6) x                                  -- pre-2004
    union select gkey from (select distinct on (grp, procedure_id) gkey from g
                            order by grp, procedure_id, h) x                    -- each procedure
    union select gkey from (select gkey, row_number() over (partition by grp order by h) rn
                            from g where lines between 2 and 6 and id_span <= 2 * lines
                              and area_ratio > 1.10) x where rn <= 4               -- C16 repeated
    union select gkey from (select gkey, row_number() over (partition by grp order by h) rn
                            from g where lines between 2 and 4 and id_span <= 2 * lines
                              and area_ratio <= 1.10) x where rn <= 3              -- C16 similar
    union select gkey from (select gkey from g where usage_swapped order by h limit 4) x
    union select gkey from (select gkey from g where low_price and grp = 'Sales'
                            order by h limit 5) x                                  -- C4 floor
    union select gkey from (select gkey from g where tiny_area order by h limit 3) x  -- C5
    union select gkey from (select gkey from g where grp = 'Sales' and procedure_id = '11'
                              and area_id = '330' and property_type = 'Unit' and yr = '2024'
                              and lines = 1 order by h limit 30) x                 -- dense band
    union select gkey from (select gkey, row_number() over (partition by yr order by h) rn
                            from g where yr between '2004' and '2026' and lines <= 3) x
                       where rn <= %(per_year)s                                    -- by year
    union select md5(concat_ws('|', t.trans_group_en, t.procedure_id, t.instance_date,
                               t.actual_worth, split_part(t.transaction_id, '-', 3)))
          from bronze.dld_transactions t join lto_sales l
            on (t.procedure_id, t.instance_date, t.area_id, t.procedure_area)
             = (l.procedure_id, l.instance_date, l.area_id, l.procedure_area)
          where t._source_file like %(raw)s                                        -- C17 both legs
)
select distinct gkey from picks
"""

TXN_ROWS_WHERE = """
where _source_file like %(raw)s
  and md5(concat_ws('|', trans_group_en, procedure_id, instance_date, actual_worth,
                    split_part(transaction_id, '-', 3))) in (select gkey from fx_txn_keys)
order by instance_date, transaction_id
"""

RENT_CONTRACTS_SQL = """
create temp table fx_rent_contracts as
select contract_id, count(*) as lines, min(left(contract_start_date, 4)) as yr,
       min(contract_start_date) as start_date, max(contract_end_date) as end_date,
       min(area_id) as area_id, min(ejari_property_sub_type_en) as sub_type,
       min(contract_reg_type_en) as reg_type,
       bool_or(ejari_bus_property_type_en = 'Virtual Unit') as virtual_unit,
       bool_or(ejari_property_type_en = 'Labor Camps') as labour_camp,
       bool_or(ejari_property_sub_type_en = 'Room in labor Camp') as labour_room,
       bool_or(nullif(actual_area, '') is null or actual_area::numeric <= 1) as area_placeholder,
       min(annual_amount::numeric) as annual_amount,
       bool_or(contract_amount <> annual_amount) as amounts_differ,
       bool_or(no_of_prop::int <> 1) as no_of_prop_ne_1,
       bool_or(area_id = '') as blank_area,
       md5(contract_id) as h
from bronze.dld_rent_contracts
where _source_file like %(raw)s
group by contract_id
"""

RENT_PICK_SQL = """
create temp table fx_rent_keys as
with c as (select * from fx_rent_contracts),
picks as (
    select contract_id from (select contract_id from c where lines between 2 and 8
                             order by h limit 25) x                                -- C11
    union select contract_id from (select contract_id from c where lines between 2 and 8
                                     and no_of_prop_ne_1 is false order by h limit 3) x
    union select contract_id from (select contract_id from c where lines = 1 and no_of_prop_ne_1
                                   order by h limit 2) x          -- no_of_prop disagrees
    union select contract_id from (select contract_id from c where virtual_unit and lines = 1
                                   order by h limit 10) x                          -- C20
    union select contract_id from (select contract_id from c where labour_camp and lines = 1
                                   order by h limit 10) x
    union select contract_id from (select contract_id from c where labour_room and lines = 1
                                   order by h limit 10) x
    union select contract_id from (select contract_id from c where area_placeholder and lines = 1
                                   order by h limit 10) x                          -- C21
    union select contract_id from (select contract_id from c where annual_amount < 1000
                                   and lines = 1 order by h limit 5) x             -- C14 floor
    union select contract_id from (select contract_id from c where annual_amount > 50000000
                                   and lines = 1 order by h limit 3) x             -- C14 extreme
    union select contract_id from (select contract_id from c
                                   where end_date::date - start_date::date > 3653
                                   order by h limit 3) x                           -- C18 end
    union select contract_id from (select contract_id from c
                                   where start_date > '2027-10-01' order by h limit 3) x
    union select contract_id from (select contract_id from c where start_date < '2004'
                                   order by h limit 1) x
    union select contract_id from (select contract_id from c where amounts_differ and lines = 1
                                   order by h limit 3) x                           -- C12
    union select contract_id from c where blank_area                               -- area_id ''
    union select contract_id from (select contract_id from c where lines = 1 and area_id = '330'
                                     and sub_type = '1bed room+Hall' and reg_type = 'New'
                                     and yr = '2024' and not area_placeholder
                                   order by h limit 30) x                          -- dense band
    union select contract_id from (select contract_id, row_number() over (partition by yr
                                   order by h) rn from c where lines = 1
                                   and yr between '2004' and '2026') x
                             where rn <= %(per_year)s                              -- by year
)
select distinct contract_id from picks
"""

RENT_ROWS_WHERE = """
where _source_file like %(raw)s and contract_id in (select contract_id from fx_rent_keys)
order by contract_start_date, contract_id, line_number::int
"""


def _bind(conn: psycopg.Connection, query: str | sql.Composable, params: dict[str, object]) -> str:
    """Render a query with its parameters bound client-side.

    CREATE TABLE AS and COPY can't take server-side bind parameters, and every value here
    is a constant from this module, so client-side binding is safe.
    """
    with psycopg.ClientCursor(conn) as cur:
        return cur.mogrify(query, params)


def _copy_out(
    conn: psycopg.Connection, table: str, where: str, params: dict[str, object], path: Path
) -> int:
    """COPY the selected bronze rows (source columns only, every field quoted) to ``path``."""
    columns = [c for c in table_columns(conn, table) or [] if c not in METADATA_COLUMNS]
    if not columns:
        raise RuntimeError(f"{SCHEMA}.{table} is not loaded: run `make bronze` on data/raw first")
    query = sql.SQL("select {cols} from {t} ").format(
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        t=sql.Identifier(SCHEMA, table),
    ) + sql.SQL(where)
    copy_sql = (
        f"copy ({_bind(conn, query, params)}) to stdout (format csv, header true, force_quote *)"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    for old in path.parent.glob("*.csv"):
        old.unlink()  # one fixture file per dataset
    with conn.cursor() as cur, cur.copy(copy_sql) as copy, path.open("wb") as fh:
        for chunk in copy:
            fh.write(chunk)
    with path.open(newline="") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def _snapshot(conn: psycopg.Connection, table: str) -> date:
    (snap,) = conn.execute(
        sql.SQL("select max(_snapshot_date) from {} where _source_file like %s").format(
            sql.Identifier(SCHEMA, table)
        ),
        [RAW_PREFIX],
    ).fetchone()
    return snap


def build_transactions(conn: psycopg.Connection, root: Path) -> tuple[Path, int]:
    """Write the transactions fixture. Returns (path, rows)."""
    params = {"raw": RAW_PREFIX, "per_year": PER_YEAR_TXN_GROUPS}
    conn.execute(_bind(conn, TXN_GROUPS_SQL, params))
    conn.execute(_bind(conn, TXN_PICK_SQL, params))
    snap = _snapshot(conn, "dld_transactions")
    path = root / "dld" / "transactions" / f"transactions_fixture_{snap}.csv"
    return path, _copy_out(conn, "dld_transactions", TXN_ROWS_WHERE, params, path)


def build_rents(conn: psycopg.Connection, root: Path) -> tuple[Path, int]:
    """Write the rent-contracts fixture. Returns (path, rows)."""
    params = {"raw": RAW_PREFIX, "per_year": PER_YEAR_RENT_CONTRACTS}
    conn.execute(_bind(conn, RENT_CONTRACTS_SQL, params))
    conn.execute(_bind(conn, RENT_PICK_SQL, params))
    snap = _snapshot(conn, "dld_rent_contracts")
    path = root / "dld" / "rents" / f"rents_fixture_{snap}.csv"
    return path, _copy_out(conn, "dld_rent_contracts", RENT_ROWS_WHERE, params, path)


def copy_rates(raw_root: Path, root: Path) -> list[tuple[Path, int]]:
    """Copy the FRED files: Fed Funds whole (monthly, small), Brent from BRENT_FROM on."""
    out = []
    for name, since in (("fedfunds", None), ("brent", BRENT_FROM)):
        d = config.DATASETS_BY_NAME[name]
        src_dir = raw_root / d.subdir
        files = sorted(src_dir.glob("*.csv")) if src_dir.is_dir() else []
        if not files:
            log.warning("%s: no file in %s, skipped", name, src_dir)
            continue
        src = files[-1]  # latest snapshot
        dst = root / d.subdir / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        for old in dst.parent.glob("*.csv"):
            old.unlink()
        with src.open(newline="") as fin, dst.open("w", newline="") as fout:
            reader, writer = csv.reader(fin), csv.writer(fout, lineterminator="\n")
            writer.writerow(next(reader))
            rows = [r for r in reader if since is None or r[0] >= since.isoformat()]
            writer.writerows(rows)
        out.append((dst, len(rows)))
    return out


def write_price_index_fixture(root: Path) -> tuple[Path, int]:
    """Write the synthetic DLD index fixture (36 months, no real DLD values).

    Same header and blank pattern as the DLD file: monthly values on every row, quarterly
    values on the quarter's last month, yearly values on December; every present value is
    quoted and every blank is an unquoted empty field. The values are a smooth made-up path
    (ratio near 1.1-1.3), deterministic so the file never changes between rebuilds.
    """
    d = config.DATASETS_BY_NAME["price_index"]
    folder = root / d.subdir
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.csv"):
        old.unlink()
    path = folder / PRICE_INDEX_FIXTURE_NAME
    base_price = {"all": 1_000_000, "flat": 950_000, "villa": 1_700_000}
    lines = [",".join(f'"{h}"' for h in PRICE_INDEX_HEADER)]
    for i in range(36):
        year, month = 2018 + i // 12, i % 12 + 1
        row: dict[str, str] = {
            "first_date_of_month": f"{year}-{month:02d}-01",
            "load_timestamp": "2026-10-01 00:00:00.000",
        }
        for k, seg in enumerate(PRICE_INDEX_SEGMENTS):
            ratio = 1.2 + 0.05 * math.sin((i + 4 * k) / 6) - 0.002 * i
            for freq in PRICE_INDEX_FREQS:
                has = freq == "monthly" or (freq == "quarterly" and month % 3 == 0) or month == 12
                row[f"{seg}_{freq}_index"] = f"{ratio:.3f}" if has else ""
                price = f"{ratio * base_price[seg]:.3f}" if has else ""
                row[f"{seg}_{freq}_price_index"] = price
        lines.append(",".join(f'"{row[h]}"' if row[h] else "" for h in PRICE_INDEX_HEADER))
    path.write_text("\n".join(lines) + "\n")
    return path, 36


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.perf_counter()
    with db.connect() as conn:
        conn.execute("set work_mem = '1GB'")
        for build in (build_transactions, build_rents):
            path, rows = build(conn, FIXTURES_ROOT)
            log.info(
                "%s: %d rows (%.0f kB)",
                path.relative_to(config.PROJECT_ROOT),
                rows,
                path.stat().st_size / 1e3,
            )
        conn.rollback()  # temp tables only
    for path, rows in copy_rates(config.DATA_RAW, FIXTURES_ROOT):
        log.info("%s: %d rows", path.relative_to(config.PROJECT_ROOT), rows)
    path, rows = write_price_index_fixture(FIXTURES_ROOT)
    log.info("%s: %d rows (synthetic)", path.relative_to(config.PROJECT_ROOT), rows)
    log.info("fixtures written in %.0fs", time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
