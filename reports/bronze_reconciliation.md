# Bronze reconciliation: files vs bronze row counts

Generated 2026-10-01 09:00 UTC by `quality/reconcile.py`. Status: **PASS**.

`rows_in_file` = CSV records counted with Python's `csv` parser (not `wc -l`: quoted fields can contain line breaks); `rows_loaded` = rows reported by Postgres `COPY`; `rows_in_bronze` = live `count(*)` per `_source_file`.

| Table | File | rows_in_file | rows_loaded | rows_in_bronze | OK |
|---|---|---:|---:|---:|:-:|
| dld_price_index | residential_sale_index_2026-09-01_18-28-58_0001.csv | 159 | 159 | 159 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0001.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0002.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0003.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0004.csv | 958,083 | 958,083 | 958,083 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0005.csv | 958,083 | 958,083 | 958,083 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0006.csv | 958,083 | 958,083 | 958,083 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0007.csv | 958,083 | 958,083 | 958,083 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0008.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0009.csv | 958,084 | 958,084 | 958,084 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0010.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_rent_contracts | rent_contracts_2026-09-30_00-46-44_0011.csv | 958,085 | 958,085 | 958,085 | ✓ |
| dld_transactions | transactions_2026-09-29_06-34-19_0001.csv | 894,076 | 894,076 | 894,076 | ✓ |
| dld_transactions | transactions_2026-09-29_06-34-19_0002.csv | 894,074 | 894,074 | 894,074 | ✓ |
| rates_brent | DCOILBRENTEU_2026-09-30.csv | 10,265 | 10,265 | 10,265 | ✓ |
| rates_fedfunds | FEDFUNDS_2026-09-30.csv | 866 | 866 | 866 | ✓ |

**Totals per table**

| Table | Files | rows_in_file | rows_loaded | rows_in_bronze |
|---|---:|---:|---:|---:|
| dld_price_index | 1 | 159 | 159 | 159 |
| dld_rent_contracts | 11 | 10,538,926 | 10,538,926 | 10,538,926 |
| dld_transactions | 2 | 1,788,150 | 1,788,150 | 1,788,150 |
| rates_brent | 1 | 10,265 | 10,265 | 10,265 |
| rates_fedfunds | 1 | 866 | 866 | 866 |
