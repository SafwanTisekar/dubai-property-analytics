# 02. Data sources

Where each dataset comes from, what its key fields mean, its known quality issues and the figures verified on load (§7).

## 1. Where the DLD data lives

| Route | What it provides | Used for |
|---|---|---|
| **Dubai Pulse / Dubai Data**: [dubaipulse.gov.ae](https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open) | Full-history bulk CSVs (`dld_transactions-open`, `dld_rent_contracts-open`, units, buildings, projects, lookups) | **The historical load** (snapshots of 2026-09-29 / 2026-09-30) |
| **DLD Open Data**: [dubailand.gov.ae](https://dubailand.gov.ae/en/open-data/real-estate-data/) | Date-filtered CSV downloads for nine datasets | Future incremental top-ups (deferred, docs/04 Decisions) |
| Kaggle mirrors | Snapshot copies | Not used; fallback only |

**Licence:** DLD open data is published under **CC BY 4.0**, credited as "Dubai Land Department" in the report footer and on the website.

**Access:** bulk files are downloaded by hand into `data/raw/dld/<dataset>/` with the snapshot date in the file name; the pipeline takes over from there. Refreshing means dropping in a newer bulk snapshot.

## 2. Transactions (sales, mortgages, gifts)

| | |
|---|---|
| Grain | One row per registered transaction procedure (a multi-unit deal spans several rows) |
| Size | 1,788,150 rows × 47 columns, 2004 → 2026-09-25 (§7) |
| Language | Bilingual `*_en` / `*_ar` columns; `_ar` dropped in silver |

| Column | Meaning | Notes |
|---|---|---|
| `transaction_id` | Transaction number | Unique on every row of the bulk file |
| `instance_date` | Registration date | Drives all time analysis |
| `trans_group_en` | Sales / Mortgages / Gifts | Top-level split, core of the financing analysis |
| `procedure_name_en` | e.g. Sell, Sell - Pre registration, Mortgage Registration, Delayed Sell, Lease to Own | Mapped to `procedure_category` by `seed_procedure_map` |
| `reg_type_en` | Off-Plan vs Existing (ready) | First-class risk dimension |
| `property_type_en` / `property_sub_type_en` | Unit / Land / Building; Flat, Villa, Office … | Conformed with Ejari types in `dim_property_type` |
| `area_id`, `area_name_en` | DLD area | Main geographic key |
| `project_number`, `project_name_en`, `master_project_en`, `building_name_en` | Project hierarchy | 11–26% missing |
| `rooms_en` | Studio, 1 B/R … Penthouse | Normalised to `bedrooms` + flags |
| `procedure_area` | Area in **sq m** | Heavy tails, tiny values |
| `actual_worth` | Value, AED | Sale price on sales; **loan amount** on completed-property mortgages (§7) |
| `meter_sale_price` | AED per sq m | Compared with `actual_worth / procedure_area` (C6) |
| `nearest_landmark_en`, `nearest_metro_en`, `nearest_mall_en` | Proximity | ~26% missing |

**Known issues:** values as low as AED 1, areas under 0.01 sq m, AED 600M+ bulk and land deals, missing project and building names, Hijri and pre-2004 dates, and portfolio deals that repeat one value on every unit line. Cleaning rules: docs/04 §2.

## 3. Rent contracts (Ejari)

| | |
|---|---|
| Grain | One row per contract **line**; multi-property contracts repeat with `line_number` and `no_of_prop` |
| Size | 10,538,926 lines in 11 CSV files (~4.4 GB) |

Key columns: `contract_id`, `contract_reg_type_en` (New / Renew), `contract_start_date`, `contract_end_date`, `contract_amount`, `annual_amount`, `no_of_prop`, `line_number`, `ejari_property_type_en`, `ejari_property_sub_type_en`, `property_usage_en`, `area_id`, `project_number`, `actual_area`, `tenant_type_en`, `is_free_hold`.

**The trap:** every multi-line contract repeats the full contract amount on each line, so a naive sum overstates rent 5.24×. Rule C11 allocates it before any sum (docs/04 §2).

## 4. Reference and supporting DLD tables

| Table | Use | Status |
|---|---|---|
| Projects, Developers | Developer names, completion dates (property age, off-plan pipeline, Q9) | Not loaded in v1 |
| Buildings, Units, Land, Valuations, Brokers | Unit and building attributes, official valuations | Not loaded in v1 |
| **DLD Residential Sale Index** (data.dubai, issued by DLD) | External benchmark for the hedonic index | Loaded 2026-10-01: `bronze.dld_price_index` (159 rows) → `silver.stg_dld_price_index` (long form). Monthly 2011-03 → **2024-05** (the 2026-09-01 stamp is the load time); all / flat / villa × monthly / quarterly / yearly × `_index` (ratio, Jan 2012 = 1.000) and `_price_index` (AED level). CI uses a synthetic 36-row fixture because the file's licence is not confirmed as CC BY 4.0 |

## 5. Rates and economy data

| Series | Source | Frequency | Use |
|---|---|---|---|
| **Fed Funds** (`FEDFUNDS`) | FRED | Monthly | The rate driver: the AED is pegged to the USD, so UAE rates track the Fed |
| **EIBOR** 1M/3M/6M/12M | [CBUAE](https://www.centralbank.ae/en/open-data-landing/) | Daily → monthly | Mortgage cost driver; manual download, not loaded yet (Fed Funds stands in) |
| Brent crude (`DCOILBRENTEU`) | FRED | Daily → monthly | Regional liquidity proxy |

## 6. Hand-built seeds (dbt)

- `seed_procedure_map.csv`: (trans group, procedure) → category, `is_market_sale` and the mortgage flags (docs/04 C2).
- `seed_rooms_map.csv`, `seed_rent_subtype_map.csv`: room and Ejari sub-type labels → bedrooms (Studio = 0) and flags.
- `seed_area.csv`: all 265 `area_id`s → canonical name, zone, and an OpenStreetMap centroid. Centroids come from **Nominatim** (`make centroids`, `ingest/geocode_areas.py`): only the public area name is sent, with a descriptive User-Agent at ≤ 1 request/s; responses are cached in `data/raw/osm/`; a match must be an area feature in Dubai named like the query. `centroid_source` records how each was found. Licence ODbL, credited as "Area locations © OpenStreetMap contributors (ODbL)". Result: `reports/area_centroids.md`.
- `seed_ltv_rules.csv`: CBUAE mortgage LTV caps for the stress test, 14 dated rows with `effective_from` / `effective_to`, `source_citation` and `source_url`. Verified by hand on 2026-09-30 against the CBUAE rulebook: Regulations Regarding Mortgage Loans, Art. 3(2), as amended by Board Resolution 31/2/2020 (effective 2020-04-08), and the earlier regime of Circular No. 31/2013 (2013-10-28 to 2020-04-07).
- Property-type, zone-label and AVM feature-label seeds: see `dbt/seeds/_seeds.yml`.

## 7. Verified profile (Phase 1, 2026-09-30)

Sources: `reports/phase1_findings.md` (interpretation), `reports/phase1_evidence.md` (queries; `make profile`), `reports/bronze_reconciliation.md` (file vs bronze counts).

| Item | Expected | Actual | Notes |
|---|---|---|---|
| Transactions rows (raw) | ~1.5–1.8M (DLD portal: 2 files × ~500 MB + 2026 file) | **1,788,150** | Dubai Pulse bulk snapshot 2026-09-29, 2 files (894,076 + 894,074), 47 columns, UTF-8, no BOM. Parser count = COPY count = bronze count. `transaction_id` is unique on every row |
| Date range | 2004 → 2026 | **2004-01-05 → 2026-09-25** | Plus 18,212 earlier rows: 18,208 dated 1966–2003 and 4 Hijri dates (1416–1422 AH = 1995–2002). All `YYYY-MM-DD`; flag, don't drop |
| Sales / Mortgages / Gifts split | | **1,368,630 / 352,805 / 66,715** (76.5% / 19.7% / 3.7%) | 58 group × procedure pairs, 52 procedure names. No inheritance procedure. Six lease-to-own codes appear in both Sales and Mortgages (one deal, two legs), so key the seed on (group, procedure_id) |
| Off-plan share of sales (last 12 months) | | **68.2% of rows, 47.8% of value** | Sales group, 2025-09-26 → 2026-09-25, `reg_type_en = 'Off-Plan Properties'`, before the market-sale filter |
| Rent contract lines (raw) | 10M+ (4.4 GB, 11 files) | **10,538,926** | Bulk snapshot 2026-09-30, identical 41-column header in all 11 files. 10,538,937 physical lines = records + 11 headers, so no quoted line breaks |
| Rent contracts after multi-line de-duplication | | **8,795,059** | 8,546,886 single-line + 248,173 multi-line (1,992,040 lines). Every multi-line contract repeats the full amount on each line: a naive Σ `annual_amount` is 5.24× the true total |
| Σ sales value, last full year (AED) | | **AED 681.2bn (2025)** | 214,529 Sales-group rows, before the market-sale filter; Sell / Sell pre-reg / Delayed Sell = 665.9bn |
| `actual_worth` meaning on mortgage rows | loan amount? | **Loan amount** (completed-property mortgages) | Matched to a same-day sale of the same unit: median ratio 0.795 (102,516 pairs); 0.75 in 2014–19 and 0.80 from 2021, following the CBUAE LTV caps. Off-plan pre-registration is mixed (43% = price). Portfolio deals repeat one value on each unit line: +AED 130.9bn (4.8%) on a naive mortgage Σ |
| Distinct areas | ~200+ | **259** (transactions), **215** (rents), **265** combined | `area_id`. Phase 1 first reported 216 / 266 because `count(distinct)` counted the blank `area_id` on 3 rent lines as a value. `seed_area` covers all 265 (Phase 2a) |
