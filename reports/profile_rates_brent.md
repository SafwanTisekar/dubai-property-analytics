# Profile: `bronze.rates_brent`

Generated 2026-09-30 11:25 UTC by `quality/profile.py` (SQL-based, exact counts over the full table).

- Rows: **10,265**
- Columns: 7 (2 source + metadata)
- Table size on disk: 1704 kB
- Profiling time: 0 s

Blank = `NULL` or `''` (DLD quotes every field, so missing values are empty strings in bronze). Min/max are numeric when ≥95% of non-blank values are numeric, otherwise text order. Values are truncated to 40 characters; ⏎ marks a line break.

| Column | Blank % | Distinct | Min | Max | Numeric % | Top values (count) |
|---|---:|---:|---|---|---:|---|
| `observation_date` | 0.0 | 10,265 | 1987-05-20 | 2026-09-22 | 0.0 | 1987-05-20 (1)<br>1987-05-21 (1)<br>1987-05-22 (1)<br>1987-05-25 (1)<br>1987-05-26 (1) |
| `dcoilbrenteu` | 11.4 | 5,367 | 9.1 | 143.9 | 100.0 | NULL (1,173)<br>18.48 (24)<br>18.15 (21)<br>18.63 (17)<br>17.85 (16) |
| `_source_file` | 0.0 | 1 | raw/fred/dcoilbrenteu/DCOILBRENTEU_2026… | raw/fred/dcoilbrenteu/DCOILBRENTEU_2026… | 0.0 | raw/fred/dcoilbrenteu/DCOILBRENTEU_2026… (10,265) |
| `_source` | 0.0 | 1 | fred | fred | 0.0 | fred (10,265) |
| `_snapshot_date` | 0.0 | 1 | 2026-09-30 | 2026-09-30 | 0.0 | 2026-09-30 (10,265) |
| `_ingested_at` | 0.0 | 1 | 2026-09-30 15:20:55.666557+04 | 2026-09-30 15:20:55.666557+04 | 0.0 | 2026-09-30 15:20:55.666557+04 (10,265) |
| `_row_hash` | 0.0 | 10,265 | 000621b1abda9d32609703ba5aeafc0c | fffaa74b6bdb5b64b41593d0eba60e09 | 0.0 | 000621b1abda9d32609703ba5aeafc0c (1)<br>001058529c8a836f3b30b16ecadb1ac7 (1)<br>00173a1dc639143a27fa808d5d6d08e9 (1)<br>00254fb24b2616e5414ceb6716da2661 (1)<br>0026a0230f1b6ab7bbddc423b1679727 (1) |
