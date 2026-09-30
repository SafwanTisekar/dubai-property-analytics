# 02 – Data Sources

All row counts below are **approximate and come from third-party profiles**. **Phase 1 must verify them** and record the actual figures in §7.

## 1. Where the DLD data lives

| Route | What you get | Use for |
|---|---|---|
| **DLD Open Data**: [dubailand.gov.ae/en/open-data/real-estate-data](https://dubailand.gov.ae/en/open-data/real-estate-data/) | CSV download with From/To date filters for 9 datasets: Transactions, Rents, Projects, Valuations, Land, Buildings, Units, Brokers, Developers | Recent data and incremental top-ups |
| **Dubai Pulse / Dubai Data**: [dubaipulse.gov.ae](https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open) | Full-history bulk CSVs (`dld_transactions-open`, `dld_rent_contracts-open`, units, buildings, projects, lookups) plus an API that needs registered OAuth credentials | **Primary historical load** |
| **Kaggle mirrors**, e.g. [Dubai Real Estate Transactions](https://www.kaggle.com/datasets/alexefimik/dubai-real-estate-transactions-dataset) | Snapshot copies (e.g. ~1.51M transactions, 46 columns, 2003 → mid-2025) | Fallback if the official downloads are slow or blocked. Record the snapshot date |

**Licence:** DLD open data is published under **CC BY 4.0**. Attribute "Dubai Land Department" on the website and in the report footer.

**Access plan:** do a one-off bulk historical load, then incremental monthly top-ups from the DLD date-filtered download. If the DLD page limits the date range per download, script the download in monthly windows. If downloads need manual clicks, save them to `data/raw/dld/<dataset>/` with the date range in the filename, and the pipeline takes over from there.

## 2. Core dataset: Transactions (sales, mortgages, gifts)

| | |
|---|---|
| Grain | One row per registered transaction procedure (a multi-unit deal can span several rows) |
| Size | ~1.5–1.8M rows × ~46 columns, 2004 → present, updated daily/weekly |
| Language | Bilingual: `*_en` and `*_ar` columns. Keep `_en` and drop `_ar` in silver |

**Key columns (verify names in Phase 1)**

| Column | Meaning | Notes |
|---|---|---|
| `transaction_id` | Transaction number | Candidate key, but test uniqueness. May repeat across procedure lines |
| `instance_date` | Registration date | Drives all time analysis |
| `trans_group_en` | **Sales / Mortgages / Gifts** | Top-level split, and the core of the financing analysis |
| `procedure_name_en` | e.g. Sell, Sell - Pre registration (off-plan), Mortgage Registration, Modify Mortgage, Delayed Sell, Lease to Own | Map to a clean `procedure_category` via a seed |
| `reg_type_en` | **Off-Plan** vs **Existing (ready)** | Key risk dimension |
| `property_type_en` / `property_sub_type_en` | Unit/Land/Building; Flat, Villa, Office, Hotel Apartment… | |
| `property_usage_en` | Residential / Commercial / … | |
| `area_id`, `area_name_en` | DLD area/community | Main geographic key |
| `project_number`, `project_name_en`, `master_project_en`, `building_name_en` | Project hierarchy | 11–18% missing |
| `rooms_en` | Studio, 1 B/R, 2 B/R, … Penthouse | Normalise to integer `bedrooms` + flags |
| `has_parking` | 0/1 | |
| `procedure_area` | Area in **sq m** | Heavy tails, tiny values exist |
| `actual_worth` | Transaction value, AED | For sales this is the price. **For mortgage rows, confirm whether it's the loan amount** (Phase 1 must verify this and document it) |
| `meter_sale_price` | AED per sq m | Recompute and compare with `actual_worth / procedure_area` |
| `rent_value`, `meter_rent_price` | Only for lease-to-own | ~97% missing |
| `nearest_landmark_en`, `nearest_metro_en`, `nearest_mall_en` | Proximity features | ~26% missing |
| `no_of_parties_role_1/2/3` | Buyer/seller/other counts | |

**Known quality issues:** values as low as AED 1, areas below 0.01 sq m, AED 600M+ bulk and land deals, skewed distributions, missing project/building names, and gifts and inheritance mixed in with market sales.

## 3. Rent contracts (Ejari)

| | |
|---|---|
| Grain | One row per contract **line**. Multi-property contracts repeat with `line_number` and `no_of_prop` |
| Size | **~4.4 GB across 11 CSV files (~400 MB each)** from the DLD portal export, so likely 10M+ contract lines. Exact count verified in Phase 1 |

**Key columns (verify):** `contract_id`, `contract_reg_type_en` (New/Renew), `contract_start_date`, `contract_end_date`, `contract_amount`, `annual_amount`, `no_of_prop`, `line_number`, `ejari_property_type_en`, `ejari_property_sub_type_en`, `property_usage_en`, `area_id`, `area_name_en`, `project_number`, `project_name_en`, `actual_area`, `tenant_type_en`, `is_free_hold`, `nearest_*`.

**Critical trap:** on multi-property contracts the contract amount may repeat on every line. De-duplicate or allocate per line before summing, or rent totals will be inflated.

## 4. Reference and supporting DLD tables

| Table | Use |
|---|---|
| Projects | Developer, project status, start/completion dates, % complete. Used for off-plan pipeline and property age |
| Buildings | Floors, units, completion year, per building |
| Units | Unit-level attributes (size, rooms, floor) |
| Land | Land parcels, zoning/usage |
| Valuations | Official valuation records. A useful comparison for the AVM |
| Developers / Brokers | Developer names and registration details, for concentration analysis |
| Lookups (areas, transaction groups, procedures) | Code → name mappings |
| **DLD Residential Price Index** (published separately) | External benchmark to validate the hedonic index built in this project |

## 5. Rates and economy data

| Series | Source | Frequency | Use |
|---|---|---|---|
| **EIBOR** (1M/3M/12M) | [CBUAE](https://www.centralbank.ae/en/open-data-landing/) | Daily → monthly average | Mortgage cost driver |
| **Fed Funds rate** (`FEDFUNDS`) | FRED | Monthly | The AED is pegged to the USD, so UAE rates track the Fed. This series is clean and long-history |
| Brent crude (`DCOILBRENTEU`) | FRED | Daily → monthly | Regional liquidity and sentiment proxy |
| UAE banking indicators: credit to the real-estate sector, mortgage lending | CBUAE statistical bulletins / [Bayanat](https://bayanat.ae/) | Monthly/quarterly | Context for the financing story |
| Dubai population | Dubai Statistics Center | Annual | Demand context |

## 6. Hand-built seeds (dbt)

- `seed_procedure_map.csv`: procedure → category (market_sale, offplan_sale, mortgage, gift, inheritance, other) + `is_market_sale` flag
- `seed_rooms_map.csv`: `rooms_en` → bedrooms (Studio = 0) + flags (penthouse, office, shop)
- `seed_area.csv`: `area_id` → cleaned name, zone/cluster (e.g. Downtown/Business Bay, Marina/JBR, JVC/JVT, Palm, Emirates Hills/Meadows, Deira/Bur Dubai, Dubai South), lat/long centroid
- `seed_ltv_rules.csv`: CBUAE mortgage LTV caps used in the stress test, e.g. expat first home ≤ AED 5M; off-plan cap. **Verify the current rules from CBUAE regulations before use** and cite the source

## 7. Verified profile (fill in during Phase 1)

| Item | Expected | Actual | Notes |
|---|---|---|---|
| Transactions rows (raw) | ~1.5–1.8M (DLD portal: 2 files × ~500 MB + 2026 file) | | |
| Date range | 2004 → 2026 | | |
| Sales / Mortgages / Gifts split | | | |
| Off-plan share of sales (last 12 months) | | | |
| Rent contract lines (raw) | 10M+ (4.4 GB, 11 files) | ~10.5M lines / 11 files | Bulk snapshot 2026-09-30, identical 41-column header in all 11 files. 10,538,937 physical lines including 11 headers. Parsed record count to be confirmed in Phase 1 (quoted fields may contain newlines) |
| Rent contracts after multi-line de-duplication | | | |
| Σ sales value, last full year (AED) | | | |
| `actual_worth` meaning on mortgage rows | loan amount? | | |
| Distinct areas | ~200+ | | |
