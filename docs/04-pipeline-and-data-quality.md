# 04 – Pipeline, Cleaning & Data Quality

## 1. Ingestion (raw files → PostgreSQL bronze)

| Step | Script | Detail |
|---|---|---|
| Database setup | `make db` → `sql/00_create_database.sql`, `sql/01_schemas_grants.sql` | UTF-8 database `dubai_property`; roles `dpa_owner` (pipeline) and `pbi_reader` (read-only on `rpt`); schemas `bronze`, `silver`, `gold`, `ml`, `rpt` |
| Bulk + incremental DLD files | `ingest/load_bronze.py` | For each CSV in `data/raw/dld/<dataset>/`: record SHA-256, size and snapshot date in `data/raw/manifest.json` (skip files already loaded); create the bronze table from the CSV header with **every column as `text`**; stream the file with psycopg `COPY … FROM STDIN (FORMAT csv, HEADER true)`; add metadata columns; `ANALYZE` |
| DLD increments | `ingest/download_dld_increment.py` | Downloads date-windowed CSVs from DLD Open Data (monthly windows) into `data/raw/dld/<dataset>/`. Where automation isn't possible, you drop files there manually |
| Rates / macro | `ingest/download_rates.py` | FRED (`FEDFUNDS`, `DCOILBRENTEU`) via the CSV endpoint; EIBOR from a CBUAE download in `data/raw/cbuae/`; loaded to `bronze.rates_*` the same way |

**Bronze rules (load only, no transformation)**
- Tables: `bronze.dld_transactions`, `bronze.dld_rent_contracts`, `bronze.dld_projects`, … Column names are snake_cased from the header; values untouched (`text`).
- Encoding: the database is UTF-8. Detect and strip a UTF-8 BOM; if a file isn't UTF-8, convert it on the fly and log that.
- Metadata: `_source_file`, `_source` (bulk / increment / kaggle), `_snapshot_date`, `_ingested_at`, `_row_hash` (md5 of the raw line).
- Append-only: re-loading the same file is a no-op (manifest check). New snapshots are appended, and de-duplication happens in silver (C1).
- Log to `reports/ingest_log.csv`: file, rows_in_file, rows_loaded, seconds.

## 2. Cleaning rules (dbt → silver)

| # | Field | Issue | Rule | Model |
|---|---|---|---|---|
| C1 | Transaction key | Duplicates across snapshots | Cast types here (dates: check `dd-mm-yyyy` vs ISO; AED and area to numeric). De-duplicate on `transaction_id` + procedure + `_row_hash` keeping the latest `_snapshot_date` (`row_number()` window); test uniqueness on the chosen key | `stg_transactions` |
| C2 | `procedure_name_en` | ~40+ procedure types | Map via `seed_procedure_map` → `procedure_category`, `is_market_sale` | `stg_transactions` |
| C3 | Gifts, inheritance, grants | Not arm's-length prices | Exclude from all price, index, yield and AVM models (keep them for volume stats) | `int_market_sales` |
| C4 | `actual_worth` | AED 1–1,000 values; AED 600M+ bulk deals | Flag `price_invalid` if < AED 50k (unit) or price/sq m outside the area-level P0.5–P99.5 band; flag `bulk_deal` if a transaction spans multiple units | `int_market_sales` |
| C5 | `procedure_area` | < 0.01 sq m; implausible sizes | Units: valid 15–3,000 sq m; villas up to 10,000; land treated separately; otherwise flag | `int_market_sales` |
| C6 | `price_per_sqm` | Provided vs computed disagree | Recompute `actual_worth / procedure_area`; flag if > 5% off the provided `meter_sale_price` | `int_market_sales` |
| C7 | `rooms_en` | Mixed labels | Map via `seed_rooms_map` → `bedrooms` (Studio = 0), `is_penthouse`, `is_commercial_unit` | `stg_transactions` |
| C8 | Area names | Spelling variants, renamed communities | Standardise via `area_id` + `seed_area`; name drift tested | `stg_transactions` |
| C9 | Project/building missing | 11–18% null | Keep as "Unknown"; flag `has_project` | `stg_transactions` |
| C10 | Mortgage rows | `actual_worth` meaning | Per the Phase 1 finding: if it's the loan amount, expose `mortgage_amount`; otherwise treat as count-only | `int_mortgages` |
| C11 | Rent: multi-unit contracts | Amount repeated per line | Where `no_of_prop > 1`, allocate `annual_amount / no_of_prop`, or keep single-property contracts only for yield (decide, document, test) | `int_rent_contracts` |
| C12 | Rent: annualisation | Contracts shorter or longer than 12 months | Use `annual_amount`; if missing, `contract_amount × 365 / contract_days` | `int_rent_contracts` |
| C13 | Rent: renewals vs new | Renewals lag the market | Keep `contract_reg_type`; market rent analysis defaults to **new** contracts | `int_rent_contracts` |
| C14 | Rent outliers | AED 0 or extreme per sq m | Same P0.5–P99.5 banding by area × sub-type | `int_rent_contracts` |
| C15 | Commercial vs residential | Mixed | `property_usage` filter. The core analysis is **residential**; commercial is a secondary view | marts |

Every flag is kept as a column (never silently deleted), and `reports/dq_report.md` shows rows affected per rule.

## 3. Gold star schema

```mermaid
erDiagram
    fct_transaction }o--|| dim_date : txn_date
    fct_transaction }o--|| dim_area : area_key
    fct_transaction }o--|| dim_property_type : property_type_key
    fct_transaction }o--|| dim_project : project_key
    fct_transaction }o--|| dim_procedure : procedure_key
    fct_rent_contract }o--|| dim_date : start_date
    fct_rent_contract }o--|| dim_area : area_key
    fct_rent_contract }o--|| dim_property_type : property_type_key
    agg_area_month }o--|| dim_date : month
    agg_area_month }o--|| dim_area : area_key
    fct_price_index }o--|| dim_date : month
    fct_rates_monthly }o--|| dim_date : month
    dim_project }o--|| dim_developer : developer_key
```

| Table | Grain | ~Rows | Key columns |
|---|---|---|---|
| `fct_transaction` (indexed: txn_date, area_key, is_market_sale) | Transaction line | ~1.5–1.8M | ids, keys, trans_group, procedure_category, is_market_sale, is_offplan, bedrooms, area_sqm, price_aed, price_per_sqm, mortgage_amount, quality flags, **avm_value, avm_gap_pct**, model_set |
| `fct_rent_contract` | Contract line (de-duplicated) | 10M+ | keys, is_new, annual_rent_aed, rent_per_sqm, area_sqm, bedrooms, tenant_type. Indexed on start_date, area_key; **not exposed to Power BI in detail** |
| `agg_rent_month` | Area × month × sub-type × bedrooms × new/renewal × usage | ~300–600K | contracts, median_annual_rent, median_rent_per_sqm, total_annual_rent. The rent table Power BI uses |
| `agg_area_month` | Area × month × sub-type × bedrooms × offplan flag | ~200–400K | sales_count, sales_value, median_ppsqm, mortgage_count, new_rent_count, median_rent_per_sqm |
| `agg_yield_quarter` | Area × quarter × sub-type × bedrooms | ~50K | median_price, median_annual_rent, gross_yield, sample sizes (min-n rule) |
| `fct_price_index` | Month × segment (Dubai, zone, top areas, apartment/villa) | ~20K | index_value, yoy, drawdown_from_peak, volatility_12m |
| `fct_rates_monthly` | Month | ~270 | eibor_3m, fed_funds, brent |
| `ml_avm_performance` | Model × segment × metric | small | MdAPE, hit rate ±10/±20, R² |
| `ml_feature_importance` | Model × feature | ~40 | mean_abs_shap, rank |
| `ml_stress_grid` | Area × shock % × LTV % | ~50K | purchases, negative-equity count/share, AED at risk |
| `ml_forecast` | Segment × month (history + 12 months ahead) | ~5K | actual, forecast, lower, upper, scenario |
| `dim_date` | **Day** | ~9K | Day grain for Power BI time intelligence |
| `rpt.*` views | One per table Power BI needs | — | Friendly names, only needed columns, `_ar` and raw flags excluded. The **only** objects Power BI reads |
| `dim_area` | Area | ~200+ | name, zone, lat/long |
| `dim_property_type` | Type × sub-type × usage | small | |
| `dim_project` / `dim_developer` | Project / developer | ~few K | status, completion date, developer |
| `dim_procedure` | Procedure | ~50 | group, category, is_market_sale |

## 4. Data-quality tests

| Level | Test |
|---|---|
| Keys | `unique`/`not_null` on PKs; `relationships` from facts to dims |
| Domains | `accepted_values` for trans_group, reg_type, procedure_category, bedrooms 0–10 |
| Ranges (`dbt_expectations`) | price_per_sqm between the per-area bands for clean sales; area_sqm in valid ranges; dates 2004 → today |
| Reconciliation | Row counts and Σ AED: bronze → silver → gold, with every exclusion accounted for |
| Volume anomalies | Monthly sales per area within ±5σ of the rolling mean (warn, not fail) |
| Rent de-duplication | Σ annual rent after allocation ≤ raw Σ; singular test on multi-line contracts |
| Yield sanity | Gross yields between 2% and 15% for segments with n ≥ 20 (warn) |
| Model outputs | avm_value > 0; stress shares ∈ [0, 1] |
| Leakage (pytest) | AVM features use only data available at transaction time (docs/05) |

## 5. Orchestration

The `Makefile` runs the steps in order: `db (once) → download → bronze → dbt build (pre-ML) → train → score → dbt build --select tag:post_ml (incl. rpt views) → test`. Incremental runs use `make update`, which pulls the latest month and rebuilds.
