# Profile: `bronze.rates_fedfunds`

Generated 2026-09-30 11:22 UTC by `quality/profile.py` (SQL-based, exact counts over the full table).

- Rows: **866**
- Columns: 7 (2 source + metadata)
- Table size on disk: 136 kB
- Profiling time: 0 s

Blank = `NULL` or `''` (DLD quotes every field, so missing values are empty strings in bronze). Min/max are numeric when ≥95% of non-blank values are numeric, otherwise text order. Values are truncated to 40 characters; ⏎ marks a line break.

| Column | Blank % | Distinct | Min | Max | Numeric % | Top values (count) |
|---|---:|---:|---|---|---:|---|
| `observation_date` | 0.0 | 866 | 1954-07-01 | 2026-08-01 | 0.0 | 1954-07-01 (1)<br>1954-08-01 (1)<br>1954-09-01 (1)<br>1954-10-01 (1)<br>1954-11-01 (1) |
| `fedfunds` | 0.0 | 509 | 0.05 | 19.1 | 100.0 | 0.09 (20)<br>0.08 (16)<br>5.33 (14)<br>0.16 (11)<br>5.25 (10) |
| `_source_file` | 0.0 | 1 | raw/fred/fedfunds/FEDFUNDS_2026-09-30.c… | raw/fred/fedfunds/FEDFUNDS_2026-09-30.c… | 0.0 | raw/fred/fedfunds/FEDFUNDS_2026-09-30.c… (866) |
| `_source` | 0.0 | 1 | fred | fred | 0.0 | fred (866) |
| `_snapshot_date` | 0.0 | 1 | 2026-09-30 | 2026-09-30 | 0.0 | 2026-09-30 (866) |
| `_ingested_at` | 0.0 | 1 | 2026-09-30 15:20:55.612327+04 | 2026-09-30 15:20:55.612327+04 | 0.0 | 2026-09-30 15:20:55.612327+04 (866) |
| `_row_hash` | 0.0 | 866 | 005c57a94f76c9d8fcc21dc77b371809 | ff6d73a7e4d6335a494edf7be9b29c1f | 0.0 | 005c57a94f76c9d8fcc21dc77b371809 (1)<br>0064e19ae233d429eb0d3ca4c887d90e (1)<br>0074a6c6e29654132e9550aef6846303 (1)<br>00db17cf2a0be796a7ec4bd67e7835a7 (1)<br>01b1e220cc342ef69acf7e0655203420 (1) |
