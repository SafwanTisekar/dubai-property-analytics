# CI fixtures

Small extracts of the real bronze inputs, committed so CI can run `dbt build` end to end
(`make bronze BRONZE_ROOT=tests/fixtures && make dbt`). Rebuild them from full bronze with
`make fixtures` (`src/dubai_property/ingest/fixtures.py` explains the selection).

| File | Lines | Selection |
|---|---:|---|
| `dld/transactions/transactions_fixture_2026-09-29.csv` | ~2,000 | 75 C16 candidate groups per year 2004–2026, plus every edge case the rules handle (Hijri and pre-2004 dates, every procedure, portfolio groups, lease-to-own legs, swapped labels, sub-AED 50k prices, tiny areas) and one dense segment for the outlier band |
| `dld/rents/rents_fixture_2026-09-30.csv` | ~1,750 | 90 single-line contracts per start year 2004–2026, plus multi-line contracts, virtual units, labour camps, placeholder areas, extreme amounts, implausible dates and a blank area_id |
| `fred/fedfunds/FEDFUNDS_2026-09-30.csv` | 866 | Whole series |
| `fred/dcoilbrenteu/DCOILBRENTEU_2026-09-30.csv` | ~2,300 | 2018 onwards |

They are small by design, so the figures they produce mean nothing. The Phase 1
reconciliation tests skip themselves on this data; the method-level reconciliation
tests still run.

## Attribution

- Transactions and rent contracts: **Dubai Land Department**, open data via Dubai Pulse,
  licensed under **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). Rows are
  unmodified extracts of the bulk exports of 2026-09-29 (transactions) and 2026-09-30
  (rents); only a subset of rows is included.
- Fed Funds (FEDFUNDS) and Brent (DCOILBRENTEU): Federal Reserve Bank of St. Louis, FRED.
