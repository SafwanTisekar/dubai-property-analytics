"""List the areas in ``seed_area`` that have no zone yet → ``reports/unzoned_areas.md``.

A worksheet for the owner: for every area with a blank zone, its market-sale volume since
2020 and its top master projects and projects, so the zone can be chosen from what is
actually built there. The allowed zones are the ones already used in ``seed_area``.
Copy the chosen zones into ``dbt/seeds/seed_area.csv`` and run ``make dbt``; a re-run of
this module (``make unzoned``) then lists only what is still blank.

Needs silver (``make dbt``). All work is SQL; only the small result comes back.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dubai_property import db
from dubai_property.quality.dq_report import md_table

log = logging.getLogger(__name__)

REPORT_NAME = "unzoned_areas.md"


def report_path() -> Path:
    """``reports/unzoned_areas.md``; a scratch folder when PG_DB isn't the main DB."""
    return db.reports_dir() / REPORT_NAME


SALES_SINCE = "2020-01-01"
TOP_N = 3

# Names are ranked by transaction lines over all years and groups: many unzoned areas have
# few or no recent market sales, and older registrations still show what the area is.
UNZONED_SQL = f"""
with unzoned as (
    select area_id, area_name_en from silver.seed_area where zone is null
),
sales as (
    select area_id, count(*) as market_sales_since_2020
    from silver.int_market_sales
    where is_market_sale and txn_date >= date '{SALES_SINCE}'
    group by 1
),
ranked as (
    select area_id, kind, name, lines,
           row_number() over (partition by area_id, kind order by lines desc, name) as rn
    from (
        select area_id, 'master' as kind, master_project as name, count(*) as lines
        from silver.stg_transactions where master_project is not null group by 1, 2, 3
        union all
        select area_id, 'project', project_name, count(*)
        from silver.stg_transactions where project_name is not null group by 1, 2, 3
    ) n
    where area_id in (select area_id from unzoned)
),
names as (
    select area_id,
           string_agg(name || ' (' || lines || ')', '; ' order by rn)
               filter (where kind = 'master') as top_master_projects,
           string_agg(name || ' (' || lines || ')', '; ' order by rn)
               filter (where kind = 'project') as top_projects
    from ranked where rn <= {TOP_N}
    group by 1
)
select u.area_id::text, u.area_name_en, coalesce(s.market_sales_since_2020, 0),
       n.top_master_projects, n.top_projects, '' as zone
from unzoned u
left join sales s using (area_id)
left join names n using (area_id)
order by coalesce(s.market_sales_since_2020, 0) desc, u.area_id
"""

ZONES_SQL = "select distinct zone from silver.seed_area where zone is not null order by 1"


def run(path: Path | None = None) -> Path:
    """Query silver and write the worksheet."""
    path = path or report_path()
    with db.connect() as conn:
        rows = conn.execute(UNZONED_SQL).fetchall()
        zones = [z for (z,) in conn.execute(ZONES_SQL).fetchall()]
        conn.rollback()
    lines = [
        "# Areas without a zone",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/unzoned_areas.py` "
        "(`make unzoned`). One row per `seed_area` entry with a blank zone, sorted by market "
        f"sales since {SALES_SINCE[:4]} (`int_market_sales.is_market_sale`). Top {TOP_N} master "
        "projects and projects are ranked by transaction lines over all years (line counts in "
        "brackets). Fill in the `zone` column from the list below, then copy the zones into "
        "`dbt/seeds/seed_area.csv` and run `make dbt`.",
        "",
        f"**{len(rows)} areas.** Zones already used in `seed_area`:",
        "",
        *[f"- {z}" for z in zones],
        "",
        *md_table(
            [
                "area_id",
                "DLD name",
                f"Market sales since {SALES_SINCE[:4]}",
                "Top master projects",
                "Top projects",
                "zone",
            ],
            rows,
        ),
        "",
    ]
    path.write_text("\n".join(lines))
    log.info("%d unzoned areas written to %s", len(rows), path)
    return path


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
