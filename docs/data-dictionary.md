# Data dictionary

Generated 2026-10-01 09:40 UTC by `quality/data_dictionary.py` from the dbt manifest (descriptions, tests) and the database catalogue (columns, types). Regenerate with `make dictionary` (after `make dbt`). Rules C1-C22 are in docs/04 §2; the star schema in docs/04 §3. Bronze is raw text (docs/04 §1) and not listed.

## Silver: seeds, staging views and intermediate tables (typed, cleaned, flagged)

| Object | Type | Description |
|---|---|---|
| [`silver.seed_area`](#silverseed_area) | seed | C8: every DLD area_id seen in transactions or rents (265 IDs; Phase 1's "266" counted the blank area_id on 3 rent lines as a value) -> canonical name and zone. Zones group areas into markets for the min-n roll-up. Every area has a zone; `make unzoned` (reports/unzoned_areas.md) lists any that don't, e.g. a new area in a later snapshot. |
| [`silver.seed_ltv_rules`](#silverseed_ltv_rules) | seed | CBUAE mortgage loan-to-value caps for the Phase 4 stress test (docs/05 §4), one row per rule (borrower x property status x home number x value band) per regulatory period. Current regime: CBUAE Regulations Regarding Mortgage Loans, Art. 3(2), as amended by Board Resolution 31/2/2020 (effective 2020-04-08). Earlier regime: Circular No. 31/2013 (2013-10-28 to 2020-04-07). Every row verified by the owner against the CBUAE rulebook (2026-09-30). The stress test is illustrative and must say which LTVs it assumed. |
| [`silver.seed_phase1_reconciliation`](#silverseed_phase1_reconciliation) | seed | The Phase 1 figures (reports/phase1_findings.md, phase1_evidence.md) that silver must reproduce. The reconciliation tests check them only when bronze holds exactly the Phase 1 snapshot (the `bronze_rows` gate), so they are skipped on the CI fixtures. |
| [`silver.seed_procedure_category`](#silverseed_procedure_category) | seed | The procedure categories used by seed_procedure_map, with the market-sale flag each implies. `inheritance` is kept although no procedure maps to it in the 2026-09 extract (phase1_findings §1), so a future snapshot has a place to land. |
| [`silver.seed_procedure_map`](#silverseed_procedure_map) | seed | C2: every (trans_group, procedure_id) pair in the DLD register (58 in the 2026-09 extract) -> category and flags. Keyed on the pair, not the name, because six lease-to-own codes are registered under both Sales and Mortgages (phase1_findings §1). A procedure missing from this seed fails the stg_transactions not_null test on procedure_category, so a new DLD procedure can't slip through unmapped. |
| [`silver.seed_property_class`](#silverseed_property_class) | seed | Conformed property classes shared by DLD sales and Ejari rents (dim_property_type). property_class_id is the last two digits of property_type_key; 99 = Unknown (no property type in the source). |
| [`silver.seed_property_type_map`](#silverseed_property_type_map) | seed | Source property type (and sub-type) -> conformed property class. DLD rows are keyed on type x sub-type (Unit/Flat -> Apartment); a blank sub-type is a wildcard used when no exact row matches (Villa, Land, Building, other Units). Ejari rows are keyed on the Ejari property type alone, because its sub-type is a layout (2 bed rooms+hall) that becomes bedrooms (C22), not a property class. A label present in the data but missing here fails the int_property_type_lookup tests. |
| [`silver.seed_property_usage_map`](#silverseed_property_usage_map) | seed | Source usage label -> conformed usage group, per source (DLD and Ejari use different labels, e.g. Hospitality vs Tourist origin). usage_group_id is the hundreds digit of property_type_key; 9 = Unknown (blank usage in the source, 15,050 rent lines). Mixed-use, education, health and agricultural labels share "Mixed & other" so no group is too thin to publish (min-n rule). |
| [`silver.seed_rent_subtype_map`](#silverseed_rent_subtype_map) | seed | C22: Ejari residential sub-type label -> bedrooms (Studio = 0). Other sub-types have no bedrooms. |
| [`silver.seed_rooms_map`](#silverseed_rooms_map) | seed | C7: DLD `rooms_en` label -> bedrooms (Studio = 0) and unit-type flags. |
| [`silver.int_data_snapshot`](#silverint_data_snapshot) | table | One row: data_snapshot_date = the latest valid transaction date. Ends the reporting scope, is the report's "Data As Of" date and anchors "last 12 months". Rent contracts starting later are flagged is_start_after_snapshot (C18). |
| [`silver.int_market_sales`](#silverint_market_sales) | table | Ownership transfers: every Sales- and Gifts-group line with the price-quality flags (C3-C6, C16-C19). Nothing is removed. is_market_sale picks arm's-length sales; is_clean_market_sale also drops every flagged row and is the population for prices, indices, yields and the AVM. Gifts, development transfers and the Sales leg of lease-to-own deals stay for volume counts only. |
| [`silver.int_mortgages`](#silverint_mortgages) | table | Financing: every Mortgages-group line (C10, C16-C18), analysed separately from prices. mortgage_amount_aed is set only where actual_worth is a verified loan amount (Mortgage Registration, Delayed Mortgage); every other procedure counts as volume only. |
| [`silver.int_property_type_lookup`](#silverint_property_type_lookup) | table | Every (source, usage, property type, sub-type) combination in the data, resolved to the conformed dim_property_type key (usage group x property class) via seed_property_usage_map and seed_property_type_map. The facts join on the *_join columns (NULL -> '') so the 10.5M-line rent join can hash. |
| [`silver.int_purchase_mortgage_pairs`](#silverint_purchase_mortgage_pairs) | table | Purchase mortgages: a Mortgage Registration (Delayed Mortgage) and a Sell (Delayed Sell) of the same unit on the same day, keyed on date, area, building, project, sq m, rooms, type and sub-type, unique on both sides, inferred portfolio lines (C16) excluded. One row per pair. The numerator of the purchase-mortgage share of ready sales (docs/01 §4) and the source of observed LTVs. A lower bound: loans registered on another day or keyed differently don't match. |
| [`silver.int_rent_contracts`](#silverint_rent_contracts) | table | Ejari contract lines (~10.5M) with the contract-level rent rules: C11 allocation, C12 annualisation, C13 new vs renewal, C14 outliers, C18 dates, C20 non-market types, C21 placeholder areas, C22 bedrooms. Nothing is removed. is_market_rent is the population for market rents and yields: new, single-line, market property type, inside the band, with usable dates. Never exposed to Power BI in detail. |
| [`silver.int_transaction_deal_groups`](#silverint_transaction_deal_groups) | table | C16 at transaction-line grain (all groups). Infers portfolio deals that repeat one deal value on every unit line (the Phase 1 REPEATED_VALUE_GROUP rule) and gives each line a deal_group_id and an AED value counted once per deal. Contiguous same-value batches of similar-size units are flagged separately and not corrected. |
| [`silver.stg_dld_price_index`](#silverstg_dld_price_index) | view | DLD's official Residential Sale Index in long form (month x segment x frequency). Validation only: the hedonic index is compared with it on growth rates (docs/05 §2). index_ratio is 1.000 at the base period (Jan 2012 for the monthly series); typical_price_aed is DLD's AED price level of a typical unit. The DLD file ends in May 2024 although it was loaded in 2026. |
| [`silver.stg_rates`](#silverstg_rates) | view | Monthly rate drivers: Fed Funds (monthly, as a decimal) and Brent (monthly mean of daily prices, USD). EIBOR is added when the CBUAE file is loaded. |
| [`silver.stg_rent_contracts`](#silverstg_rent_contracts) | view | Ejari contract lines, typed and decoded (view over ~10.5M rows). C1 keeps the latest snapshot of each (contract_id, line_number). Contract-level rules live in int_rent_contracts, which is the only model that should select from this view; its tests are there too, so the de-duplication window over 10.5M rows isn't recomputed for each test. |
| [`silver.stg_transactions`](#silverstg_transactions) | view | DLD transaction lines, typed and decoded (view). C1 keeps the latest snapshot of each transaction_id, the only step in silver that removes rows. C2, C7, C8 and C9 attach the procedure, rooms and area seeds; C18 and C19 fix or flag dates and labels. Units: sq m and AED. Arabic columns are dropped. |

<a id="silverseed_area"></a>
### `silver.seed_area`

C8: every DLD area_id seen in transactions or rents (265 IDs; Phase 1's "266" counted the blank area_id on 3 rent lines as a value) -> canonical name and zone. Zones group areas into markets for the min-n roll-up. Every area has a zone; `make unzoned` (reports/unzoned_areas.md) lists any that don't, e.g. a new area in a later snapshot.

| Column | Type | Description | Tests |
|---|---|---|---|
| `area_id` | integer |  | not_null, unique |
| `area_name_en` | text |  | not_null |
| `zone` | text | Market zone for roll-ups. NULL = not assigned yet. |  |
| `latitude` | numeric | Area centroid latitude (WGS84) for the Power BI bubble map. Empty until Phase 5. |  |
| `longitude` | numeric | Area centroid longitude (WGS84). Empty until Phase 5. |  |

<a id="silverseed_ltv_rules"></a>
### `silver.seed_ltv_rules`

CBUAE mortgage loan-to-value caps for the Phase 4 stress test (docs/05 §4), one row per rule (borrower x property status x home number x value band) per regulatory period. Current regime: CBUAE Regulations Regarding Mortgage Loans, Art. 3(2), as amended by Board Resolution 31/2/2020 (effective 2020-04-08). Earlier regime: Circular No. 31/2013 (2013-10-28 to 2020-04-07). Every row verified by the owner against the CBUAE rulebook (2026-09-30). The stress test is illustrative and must say which LTVs it assumed.

| Column | Type | Description | Tests |
|---|---|---|---|
| `rule_id` | integer |  | not_null, unique |
| `borrower` | text |  |  |
| `property_status` | text |  |  |
| `home_number` | text |  |  |
| `value_band` | text |  |  |
| `max_ltv` | numeric | Maximum loan / property value, as a decimal (0.80 = 80%). | expression_is_true, not_null |
| `effective_from` | date | First day the cap applies. Pre-2020 rows use the Circular 31/2013 date (2013-10-28); it came into force one month after Official Gazette publication, a date not verified. |  |
| `effective_to` | date | Last day the cap applies; NULL = still in force. |  |
| `source_citation` | text |  | not_null |
| `source_url` | text | CBUAE rulebook page for the regulation. | not_null |
| `secondary_source_url` | text | Secondary summary used alongside the rulebook (pre-2020 rows). |  |
| `verified` | boolean | The owner has checked this row against the CBUAE regulation (2026-09-30). | expression_is_true, not_null |
| `note` | text |  |  |

<a id="silverseed_phase1_reconciliation"></a>
### `silver.seed_phase1_reconciliation`

The Phase 1 figures (reports/phase1_findings.md, phase1_evidence.md) that silver must reproduce. The reconciliation tests check them only when bronze holds exactly the Phase 1 snapshot (the `bronze_rows` gate), so they are skipped on the CI fixtures.

| Column | Type | Description | Tests |
|---|---|---|---|
| `dataset` | text |  |  |
| `metric` | text |  | not_null |
| `trans_group` | text |  |  |
| `expected_value` | numeric |  |  |
| `note` | text |  |  |

<a id="silverseed_procedure_category"></a>
### `silver.seed_procedure_category`

The procedure categories used by seed_procedure_map, with the market-sale flag each implies. `inheritance` is kept although no procedure maps to it in the 2026-09 extract (phase1_findings §1), so a future snapshot has a place to land.

| Column | Type | Description | Tests |
|---|---|---|---|
| `procedure_category` | text |  | not_null, unique |
| `is_market_sale` | boolean |  | not_null |
| `description` | text |  |  |

<a id="silverseed_procedure_map"></a>
### `silver.seed_procedure_map`

C2: every (trans_group, procedure_id) pair in the DLD register (58 in the 2026-09 extract) -> category and flags. Keyed on the pair, not the name, because six lease-to-own codes are registered under both Sales and Mortgages (phase1_findings §1). A procedure missing from this seed fails the stg_transactions not_null test on procedure_category, so a new DLD procedure can't slip through unmapped.

| Column | Type | Description | Tests |
|---|---|---|---|
| `procedure_key` | integer | Stable integer key for dim_procedure. Append new procedures with the next number; never renumber (Power BI relationships and saved filters use it). | not_null, unique |
| `trans_group` | text |  | accepted_values, not_null |
| `procedure_id` | integer |  | not_null |
| `procedure_name_en` | text |  |  |
| `procedure_category` | text |  | not_null, relationships |
| `is_market_sale` | boolean | Arm's-length sale; feeds prices, indices, yields and the AVM. |  |
| `is_lease_to_own` | boolean | C17. Lease-to-own / lease-development deal, either leg. |  |
| `is_new_mortgage` | boolean | A new individual (single-unit) bank mortgage: Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration. The mortgage-share numerator. Portfolio registrations, modifications, transfers, development and lease finance are excluded. |  |
| `is_portfolio_mortgage` | boolean | A new portfolio mortgage registration (one loan over several units: procedures 43, 101, 60). Reported separately from mortgage share, counted once per deal (C16). |  |
| `amount_is_loan` | boolean | C10. `actual_worth` is the loan amount (Mortgage Registration, Delayed Mortgage). |  |
| `note` | text |  |  |

<a id="silverseed_property_class"></a>
### `silver.seed_property_class`

Conformed property classes shared by DLD sales and Ejari rents (dim_property_type). property_class_id is the last two digits of property_type_key; 99 = Unknown (no property type in the source).

| Column | Type | Description | Tests |
|---|---|---|---|
| `property_class_id` | integer |  | not_null, unique |
| `property_class` | text |  | not_null, unique |
| `description` | text |  |  |

<a id="silverseed_property_type_map"></a>
### `silver.seed_property_type_map`

Source property type (and sub-type) -> conformed property class. DLD rows are keyed on type x sub-type (Unit/Flat -> Apartment); a blank sub-type is a wildcard used when no exact row matches (Villa, Land, Building, other Units). Ejari rows are keyed on the Ejari property type alone, because its sub-type is a layout (2 bed rooms+hall) that becomes bedrooms (C22), not a property class. A label present in the data but missing here fails the int_property_type_lookup tests.

| Column | Type | Description | Tests |
|---|---|---|---|
| `source` | text |  |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_class` | text |  | not_null, relationships |

<a id="silverseed_property_usage_map"></a>
### `silver.seed_property_usage_map`

Source usage label -> conformed usage group, per source (DLD and Ejari use different labels, e.g. Hospitality vs Tourist origin). usage_group_id is the hundreds digit of property_type_key; 9 = Unknown (blank usage in the source, 15,050 rent lines). Mixed-use, education, health and agricultural labels share "Mixed & other" so no group is too thin to publish (min-n rule).

| Column | Type | Description | Tests |
|---|---|---|---|
| `source` | text |  | accepted_values |
| `property_usage` | text |  |  |
| `usage_group_id` | integer |  | not_null |
| `usage_group` | text |  |  |

<a id="silverseed_rent_subtype_map"></a>
### `silver.seed_rent_subtype_map`

C22: Ejari residential sub-type label -> bedrooms (Studio = 0). Other sub-types have no bedrooms.

| Column | Type | Description | Tests |
|---|---|---|---|
| `ejari_property_sub_type_en` | text |  | not_null, unique |
| `bedrooms` | smallint |  |  |
| `room_class` | text |  |  |

<a id="silverseed_rooms_map"></a>
### `silver.seed_rooms_map`

C7: DLD `rooms_en` label -> bedrooms (Studio = 0) and unit-type flags.

| Column | Type | Description | Tests |
|---|---|---|---|
| `rooms_en` | text |  | not_null, unique |
| `bedrooms` | smallint |  | between |
| `room_class` | text |  |  |
| `is_penthouse` | boolean |  |  |
| `is_commercial_unit` | boolean |  |  |

<a id="silverint_data_snapshot"></a>
### `silver.int_data_snapshot`

One row: data_snapshot_date = the latest valid transaction date. Ends the reporting scope, is the report's "Data As Of" date and anchors "last 12 months". Rent contracts starting later are flagged is_start_after_snapshot (C18).

| Column | Type | Description | Tests |
|---|---|---|---|
| `data_snapshot_date` | date |  | not_null |

<a id="silverint_market_sales"></a>
### `silver.int_market_sales`

Ownership transfers: every Sales- and Gifts-group line with the price-quality flags (C3-C6, C16-C19). Nothing is removed. is_market_sale picks arm's-length sales; is_clean_market_sale also drops every flagged row and is the population for prices, indices, yields and the AVM. Gifts, development transfers and the Sales leg of lease-to-own deals stay for volume counts only.

| Column | Type | Description | Tests |
|---|---|---|---|
| `transaction_id` | text | DLD transaction id `<group>-<procedure>-<year>-<seq>`. Primary key after C1. (from `stg_transactions`) | not_null, unique |
| `trans_group` | text |  | accepted_values |
| `procedure_id` | integer |  |  |
| `procedure_name` | text |  |  |
| `procedure_category` | text | C2. From seed_procedure_map; NULL would mean a procedure the seed doesn't know. (from `stg_transactions`) | accepted_values |
| `is_market_sale` | boolean | C3. Arm's-length sale per seed_procedure_map. | not_null |
| `is_lease_to_own` | boolean | C17. Sales leg of a lease-to-own deal; is_market_sale is false (volume only). |  |
| `txn_date` | date | Registration date. NULL when is_date_invalid. (from `stg_transactions`) |  |
| `instance_date_raw` | text | The date as published, kept so invalid dates stay traceable. (from `stg_transactions`) |  |
| `is_date_invalid` | boolean | C18. See stg_transactions. |  |
| `is_pre_2004` | boolean | C18. Before the analysis window. |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. (from `stg_transactions`) |  |
| `reg_type` | text |  |  |
| `is_offplan` | boolean | Off-plan vs ready, a first-class dimension (CLAUDE.md). (from `stg_transactions`) |  |
| `area_id` | integer | C8. DLD area; joins seed_area. (from `stg_transactions`) |  |
| `area_name` | text | Canonical name from seed_area. (from `stg_transactions`) |  |
| `zone` | text | Market zone from seed_area (NULL where not assigned yet). (from `stg_transactions`) |  |
| `building_name` | text |  |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `has_project` | boolean | C9. The line names a DLD project (26% don't). Names stay NULL here; gold labels them Unknown. (from `stg_transactions`) |  |
| `nearest_landmark` | text |  |  |
| `nearest_metro` | text |  |  |
| `nearest_mall` | text |  |  |
| `rooms_en` | text |  |  |
| `bedrooms` | smallint | C7. From seed_rooms_map; Studio = 0; NULL for offices, shops, penthouses, land. (from `stg_transactions`) |  |
| `room_class` | text |  |  |
| `is_penthouse` | boolean |  |  |
| `is_commercial_unit` | boolean |  |  |
| `has_parking` | boolean |  |  |
| `area_sqm` | numeric | procedure_area in sq m, as published. (from `stg_transactions`) |  |
| `actual_worth_aed` | numeric | AED value as published. Sales: price. Mortgage Registration / Delayed Mortgage: loan amount (C10). Repeated on every line of a portfolio deal: see C16. (from `stg_transactions`) |  |
| `price_per_sqm_aed` | numeric | C6. actual_worth_aed / area_sqm, recomputed (AED per sq m). |  |
| `meter_sale_price_aed` | numeric |  |  |
| `is_price_below_floor` | boolean | C4. actual_worth below AED 50,000 (nominal or partial-share values). |  |
| `ppsqm_band_level` | text | Which band applied: area_x_type (area x property type, n >= 20) or type (Dubai-wide fallback for thin segments). |  |
| `ppsqm_band_low` | double precision |  |  |
| `ppsqm_band_high` | double precision |  |  |
| `is_ppsqm_outlier` | boolean | C4. price_per_sqm outside the P0.5-P99.5 band of clean market sales. |  |
| `is_price_invalid` | boolean | C4. Below the floor or outside the band. |  |
| `is_area_invalid` | boolean | C5. Units outside 15-3,000 sq m, villas outside 15-10,000 sq m, land/buildings under 1 sq m, or no area. |  |
| `is_ppsqm_mismatch` | boolean | C6. Recomputed price per sq m more than 5% off DLD's meter_sale_price. |  |
| `is_repeated_deal_value` | boolean | C16. See int_transaction_deal_groups. |  |
| `deal_group_id` | text | The lead line's transaction_id for a repeated-value deal; the line's own transaction_id otherwise. count(distinct deal_group_id) counts deals. (from `int_transaction_deal_groups`) |  |
| `deal_group_lines` | bigint | Lines in the deal (1 unless is_repeated_deal_value). (from `int_transaction_deal_groups`) |  |
| `is_deal_group_lead` | boolean | The deal's first line by DLD running number; carries the deal value once. (from `int_transaction_deal_groups`) |  |
| `actual_worth_once_aed` | numeric | AED counted once per deal (C16). Sum this, not actual_worth_aed. |  |
| `is_similar_size_batch` | boolean | C16. See int_transaction_deal_groups. |  |
| `batch_group_id` | text | Lead transaction_id of a similar-size batch (NULL otherwise). (from `int_transaction_deal_groups`) |  |
| `batch_group_lines` | bigint |  |  |
| `is_clean_market_sale` | boolean | The price population: is_market_sale, dated 2004+, and none of C4, C5, C6, C16 (repeated value) or C18. | not_null |
| `snapshot_date` | date |  |  |
| `source_file` | text |  |  |

<a id="silverint_mortgages"></a>
### `silver.int_mortgages`

Financing: every Mortgages-group line (C10, C16-C18), analysed separately from prices. mortgage_amount_aed is set only where actual_worth is a verified loan amount (Mortgage Registration, Delayed Mortgage); every other procedure counts as volume only.

| Column | Type | Description | Tests |
|---|---|---|---|
| `transaction_id` | text | DLD transaction id `<group>-<procedure>-<year>-<seq>`. Primary key after C1. (from `stg_transactions`) | not_null, unique |
| `trans_group` | text |  | accepted_values |
| `procedure_id` | integer |  |  |
| `procedure_name` | text |  |  |
| `procedure_category` | text | C2. From seed_procedure_map; NULL would mean a procedure the seed doesn't know. (from `stg_transactions`) | accepted_values |
| `is_new_mortgage` | boolean | New individual (non-portfolio) mortgage: Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration. Includes refinancing and loans on units bought earlier, so it is a secondary indicator (new mortgages per 100 market sales, docs/01 §4); the headline is the purchase-mortgage share (int_purchase_mortgage_pairs). | not_null |
| `is_portfolio_mortgage` | boolean | New portfolio mortgage registration (one loan over several units). Not in either mortgage indicator; count per deal with count(distinct deal_group_id). | not_null |
| `is_lease_to_own` | boolean | C17. Financing leg of a lease-to-own deal. |  |
| `amount_is_loan` | boolean | C10. True for Mortgage Registration and Delayed Mortgage only. | not_null |
| `txn_date` | date | Registration date. NULL when is_date_invalid. (from `stg_transactions`) |  |
| `instance_date_raw` | text | The date as published, kept so invalid dates stay traceable. (from `stg_transactions`) |  |
| `is_date_invalid` | boolean | C18. Includes the 4 Hijri-dated Mortgage Registration rows. |  |
| `is_pre_2004` | boolean | C18. |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. (from `stg_transactions`) |  |
| `reg_type` | text |  |  |
| `is_offplan` | boolean | Off-plan vs ready, a first-class dimension (CLAUDE.md). (from `stg_transactions`) |  |
| `area_id` | integer | C8. DLD area; joins seed_area. (from `stg_transactions`) |  |
| `area_name` | text | Canonical name from seed_area. (from `stg_transactions`) |  |
| `zone` | text | Market zone from seed_area (NULL where not assigned yet). (from `stg_transactions`) |  |
| `building_name` | text |  |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `has_project` | boolean | C9. The line names a DLD project (26% don't). Names stay NULL here; gold labels them Unknown. (from `stg_transactions`) |  |
| `rooms_en` | text |  |  |
| `bedrooms` | smallint | C7. From seed_rooms_map; Studio = 0; NULL for offices, shops, penthouses, land. (from `stg_transactions`) |  |
| `room_class` | text |  |  |
| `area_sqm` | numeric | procedure_area in sq m, as published. (from `stg_transactions`) |  |
| `actual_worth_aed` | numeric | AED value as published. Sales: price. Mortgage Registration / Delayed Mortgage: loan amount (C10). Repeated on every line of a portfolio deal: see C16. (from `stg_transactions`) |  |
| `mortgage_amount_aed` | numeric | C10. The loan amount (AED), as recorded on the line; NULL where amount_is_loan is false. |  |
| `mortgage_amount_once_aed` | numeric | C10 + C16. Loan amount counted once per portfolio deal. Sum this for loan totals. |  |
| `portfolio_mortgage_value_once_aed` | numeric | Recorded value of a portfolio mortgage, once per deal (C16); NULL for other procedures. Not a verified loan amount (C10). |  |
| `is_repeated_deal_value` | boolean | C16. |  |
| `deal_group_id` | text | The lead line's transaction_id for a repeated-value deal; the line's own transaction_id otherwise. count(distinct deal_group_id) counts deals. (from `int_transaction_deal_groups`) |  |
| `deal_group_lines` | bigint | Lines in the deal (1 unless is_repeated_deal_value). (from `int_transaction_deal_groups`) |  |
| `is_deal_group_lead` | boolean | The deal's first line by DLD running number; carries the deal value once. (from `int_transaction_deal_groups`) |  |
| `actual_worth_once_aed` | numeric | actual_worth_aed on the lead line, 0 on the other lines of a repeated-value deal. Sum this column for AED totals. (from `int_transaction_deal_groups`) |  |
| `is_similar_size_batch` | boolean | C16. |  |
| `batch_group_id` | text | Lead transaction_id of a similar-size batch (NULL otherwise). (from `int_transaction_deal_groups`) |  |
| `batch_group_lines` | bigint |  |  |
| `snapshot_date` | date |  |  |
| `source_file` | text |  |  |

<a id="silverint_property_type_lookup"></a>
### `silver.int_property_type_lookup`

Every (source, usage, property type, sub-type) combination in the data, resolved to the conformed dim_property_type key (usage group x property class) via seed_property_usage_map and seed_property_type_map. The facts join on the *_join columns (NULL -> '') so the 10.5M-line rent join can hash.

| Column | Type | Description | Tests |
|---|---|---|---|
| `source` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage_join` | text |  |  |
| `property_type_join` | text |  |  |
| `property_sub_type_join` | text |  |  |
| `usage_group_id` | integer |  |  |
| `property_class_id` | integer | Conformed property class (seed_property_class) from the Ejari property type; sets the C21 area cap. (from `int_rent_contracts`) |  |
| `property_type_key` | integer | usage_group_id * 100 + property_class_id. | not_null, relationships |
| `is_usage_mapped` | boolean | False when the source usage label exists but is missing from seed_property_usage_map. | accepted_values |
| `is_type_mapped` | boolean | False when the source property type exists but is missing from seed_property_type_map. | accepted_values |

<a id="silverint_purchase_mortgage_pairs"></a>
### `silver.int_purchase_mortgage_pairs`

Purchase mortgages: a Mortgage Registration (Delayed Mortgage) and a Sell (Delayed Sell) of the same unit on the same day, keyed on date, area, building, project, sq m, rooms, type and sub-type, unique on both sides, inferred portfolio lines (C16) excluded. One row per pair. The numerator of the purchase-mortgage share of ready sales (docs/01 §4) and the source of observed LTVs. A lower bound: loans registered on another day or keyed differently don't match.

| Column | Type | Description | Tests |
|---|---|---|---|
| `mortgage_transaction_id` | text |  | not_null, relationships, unique |
| `sale_transaction_id` | text |  | not_null, relationships, unique |
| `txn_date` | date | Registration date. NULL when is_date_invalid. (from `stg_transactions`) | not_null |
| `mortgage_procedure` | text |  |  |
| `sale_procedure` | text |  |  |
| `loan_aed` | numeric |  |  |
| `sale_price_aed` | numeric |  |  |
| `purchase_ltv` | numeric | Loan ÷ same-day sale price of the same unit (observed loan-to-value). |  |

<a id="silverint_rent_contracts"></a>
### `silver.int_rent_contracts`

Ejari contract lines (~10.5M) with the contract-level rent rules: C11 allocation, C12 annualisation, C13 new vs renewal, C14 outliers, C18 dates, C20 non-market types, C21 placeholder areas, C22 bedrooms. Nothing is removed. is_market_rent is the population for market rents and yields: new, single-line, market property type, inside the band, with usable dates. Never exposed to Power BI in detail.

| Column | Type | Description | Tests |
|---|---|---|---|
| `contract_id` | text | Ejari contract number. (from `stg_rent_contracts`) | not_null |
| `line_number` | integer | 1..n within a contract (clean in Phase 1). (from `stg_rent_contracts`) | not_null |
| `line_count` | bigint | C11. Lines in the contract, counted (not no_of_prop). | not_null |
| `is_multi_unit` | boolean | C11. The contract has more than one line; its amount is a whole-contract total. |  |
| `no_of_prop_source` | integer | Published property count. Unreliable (disagrees with the line count on 5,629 contracts). (from `stg_rent_contracts`) |  |
| `contract_reg_type` | text | C13. New or Renew. Market rent uses New (renewals lag the market). | accepted_values |
| `is_new` | boolean | C13. |  |
| `start_date` | date |  |  |
| `end_date` | date |  |  |
| `start_date_raw` | text |  |  |
| `end_date_raw` | text |  |  |
| `contract_days` | integer |  |  |
| `is_date_invalid` | boolean | C18. Start date unparseable or more than a year after the extract (up to year 2205). |  |
| `is_pre_2004` | boolean | C18. Starts before 2004. |  |
| `is_start_after_snapshot` | boolean | C18. A valid start date after the data snapshot date (the latest transaction date, int_data_snapshot): registered ahead of time. Not a market rent; outside the report scope. | not_null |
| `is_end_date_implausible` | boolean | C18. End date missing, before the start, or more than 10 years after it (up to year 5013). |  |
| `contract_amount_aed` | numeric |  |  |
| `annual_amount_aed` | numeric | As published; the contract total repeated on every line. Never sum it. |  |
| `is_amount_inconsistent` | boolean | Lines of one contract carry different annual amounts (0 in Phase 1). Makes C11 ambiguous. |  |
| `annual_rent_contract_aed` | numeric | C12. Contract annual rent (annual_amount, else contract_amount x 365 / days). |  |
| `annual_rent_alloc_aed` | numeric | C11. annual_rent_contract_aed / line_count. Sums to exactly one contract amount per contract, so it is the only rent column safe to SUM. | not_null |
| `bus_property_type` | text |  |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. (from `stg_transactions`) |  |
| `is_free_hold` | boolean |  |  |
| `is_non_market_property_type` | boolean | C20. Virtual Unit, Labor Camps or Room in labor Camp / Labor Camp. Not market rents. |  |
| `bedrooms` | smallint | C22. Studio = 0. | between |
| `room_class` | text |  |  |
| `property_class_id` | integer | Conformed property class (seed_property_class) from the Ejari property type; sets the C21 area cap. | not_null |
| `area_id` | integer | C8. DLD area; joins seed_area. (from `stg_transactions`) |  |
| `area_name` | text | Canonical name from seed_area. (from `stg_transactions`) |  |
| `zone` | text | Market zone for roll-ups. NULL = not assigned yet. (from `seed_area`) |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `nearest_landmark` | text |  |  |
| `nearest_metro` | text |  |  |
| `nearest_mall` | text |  |  |
| `actual_area_sqm` | numeric | Per-line area as published; blank / 0 / 1 are placeholders (C21). (from `stg_rent_contracts`) |  |
| `area_sqm` | numeric | C21. actual_area when above 1 sq m and up to 10,000 sq m; NULL for blank / 0 / 1 placeholders and implausible areas. |  |
| `is_area_placeholder` | boolean | C21. Blank, 0 or 1 sq m area. No rent per sq m. |  |
| `is_area_implausible` | boolean | C21. Area above the cap for its property class (apartment 1,000 sq m, villa / townhouse 3,000, office / retail 5,000, other 10,000): a community, plot or building area, not the unit's. Rent kept; no area, no rent per sq m. | not_null |
| `rent_per_sqm_aed` | numeric | Annual rent per sq m, single-line contracts with a real area only. |  |
| `is_rent_below_floor` | boolean | C14. Allocated annual rent under AED 1,000. |  |
| `rent_band_level` | text | area_x_subtype (n >= 20) or subtype (Dubai-wide fallback). |  |
| `rent_per_sqm_band_low` | double precision |  |  |
| `rent_per_sqm_band_high` | double precision |  |  |
| `annual_rent_band_low` | double precision |  |  |
| `annual_rent_band_high` | double precision |  |  |
| `is_rent_outlier` | boolean | C14. Below the floor, or outside the P0.5-P99.5 band of rent per sq m (annual rent where there is no usable area) by area x Ejari sub-type. |  |
| `tenant_type` | text |  |  |
| `is_market_rent` | boolean | The market-rent population (see model description); starts on or before the data snapshot date. | not_null |
| `snapshot_date` | date |  |  |
| `source_file` | text |  |  |

<a id="silverint_transaction_deal_groups"></a>
### `silver.int_transaction_deal_groups`

C16 at transaction-line grain (all groups). Infers portfolio deals that repeat one deal value on every unit line (the Phase 1 REPEATED_VALUE_GROUP rule) and gives each line a deal_group_id and an AED value counted once per deal. Contiguous same-value batches of similar-size units are flagged separately and not corrected.

| Column | Type | Description | Tests |
|---|---|---|---|
| `transaction_id` | text | DLD transaction id `<group>-<procedure>-<year>-<seq>`. Primary key after C1. (from `stg_transactions`) | not_null, unique |
| `trans_group` | text |  |  |
| `actual_worth_aed` | numeric | AED value as published. Sales: price. Mortgage Registration / Delayed Mortgage: loan amount (C10). Repeated on every line of a portfolio deal: see C16. (from `stg_transactions`) |  |
| `is_repeated_deal_value` | boolean | C16. Line of an inferred portfolio deal: >= 2 lines with the same group, procedure, date, value and ID-year, registered in one batch (ID span <= 2 x lines), whose unit sizes differ by more than 10%. | not_null |
| `deal_group_id` | text | The lead line's transaction_id for a repeated-value deal; the line's own transaction_id otherwise. count(distinct deal_group_id) counts deals. | not_null |
| `deal_group_lines` | bigint | Lines in the deal (1 unless is_repeated_deal_value). |  |
| `is_deal_group_lead` | boolean | The deal's first line by DLD running number; carries the deal value once. |  |
| `actual_worth_once_aed` | numeric | actual_worth_aed on the lead line, 0 on the other lines of a repeated-value deal. Sum this column for AED totals. |  |
| `is_similar_size_batch` | boolean | C16 (kept visible, not corrected). Same batch pattern but unit sizes within 10%: most likely identical units at identical prices, so every line keeps its value. | not_null |
| `batch_group_id` | text | Lead transaction_id of a similar-size batch (NULL otherwise). |  |
| `batch_group_lines` | bigint |  |  |

<a id="silverstg_dld_price_index"></a>
### `silver.stg_dld_price_index`

DLD's official Residential Sale Index in long form (month x segment x frequency). Validation only: the hedonic index is compared with it on growth rates (docs/05 §2). index_ratio is 1.000 at the base period (Jan 2012 for the monthly series); typical_price_aed is DLD's AED price level of a typical unit. The DLD file ends in May 2024 although it was loaded in 2026.

| Column | Type | Description | Tests |
|---|---|---|---|
| `month_start` | date | First day of the month; quarterly values on the quarter's last month, yearly on December. | not_null |
| `segment` | text | all, flat or villa (DLD's labels). | accepted_values, not_null |
| `frequency` | text |  | accepted_values, not_null |
| `index_ratio` | numeric | DLD index as a ratio to the base period (not x100). | between |
| `index_2012_100` | numeric | index_ratio x 100 (base 2012 = 100), for charts. |  |
| `typical_price_aed` | numeric | DLD's "price index", an AED price level of a typical unit (not used for validation). |  |
| `load_timestamp` | timestamp without time zone |  |  |
| `snapshot_date` | date |  |  |

<a id="silverstg_rates"></a>
### `silver.stg_rates`

Monthly rate drivers: Fed Funds (monthly, as a decimal) and Brent (monthly mean of daily prices, USD). EIBOR is added when the CBUAE file is loaded.

| Column | Type | Description | Tests |
|---|---|---|---|
| `month` | date |  | not_null, unique |
| `fed_funds_rate` | numeric | Effective federal funds rate as a decimal (0.0525 = 5.25%). | between |
| `brent_usd` | numeric | Mean Brent price over the month's trading days, USD per barrel. |  |
| `brent_trading_days` | bigint |  |  |

<a id="silverstg_rent_contracts"></a>
### `silver.stg_rent_contracts`

Ejari contract lines, typed and decoded (view over ~10.5M rows). C1 keeps the latest snapshot of each (contract_id, line_number). Contract-level rules live in int_rent_contracts, which is the only model that should select from this view; its tests are there too, so the de-duplication window over 10.5M rows isn't recomputed for each test.

| Column | Type | Description | Tests |
|---|---|---|---|
| `contract_id` | text | Ejari contract number. |  |
| `line_number` | integer | 1..n within a contract (clean in Phase 1). |  |
| `no_of_prop_source` | integer | Published property count. Unreliable (disagrees with the line count on 5,629 contracts). |  |
| `contract_reg_type` | text |  |  |
| `is_new` | boolean |  |  |
| `start_date_raw` | text |  |  |
| `end_date_raw` | text |  |  |
| `start_date` | date |  |  |
| `end_date` | date |  |  |
| `contract_amount_aed` | numeric |  |  |
| `annual_amount_aed` | numeric | Annualised contract value. The WHOLE contract's amount, repeated on every line. |  |
| `bus_property_type` | text |  |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text |  |  |
| `is_residential` | boolean |  |  |
| `is_free_hold` | boolean |  |  |
| `area_id` | integer |  |  |
| `area_name` | text |  |  |
| `area_name_source` | text |  |  |
| `zone` | text | Market zone for roll-ups. NULL = not assigned yet. (from `seed_area`) |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `nearest_landmark` | text |  |  |
| `nearest_metro` | text |  |  |
| `nearest_mall` | text |  |  |
| `actual_area_sqm` | numeric | Per-line area as published; blank / 0 / 1 are placeholders (C21). |  |
| `bedrooms` | smallint | C22. From seed_rent_subtype_map; Studio = 0. |  |
| `room_class` | text |  |  |
| `tenant_type` | text |  |  |
| `dld_extracted_at` | timestamp with time zone |  |  |
| `snapshot_date` | date |  |  |
| `source_file` | text |  |  |
| `row_hash` | text |  |  |

<a id="silverstg_transactions"></a>
### `silver.stg_transactions`

DLD transaction lines, typed and decoded (view). C1 keeps the latest snapshot of each transaction_id, the only step in silver that removes rows. C2, C7, C8 and C9 attach the procedure, rooms and area seeds; C18 and C19 fix or flag dates and labels. Units: sq m and AED. Arabic columns are dropped.

| Column | Type | Description | Tests |
|---|---|---|---|
| `transaction_id` | text | DLD transaction id `<group>-<procedure>-<year>-<seq>`. Primary key after C1. | not_null, unique |
| `id_year` | text | Year segment of transaction_id (application year; can precede txn_date). |  |
| `id_seq` | integer | DLD running number within id_year. C16 uses it to spot batch registrations. |  |
| `trans_group_id` | smallint |  |  |
| `trans_group` | text |  | accepted_values, not_null |
| `procedure_id` | integer |  | not_null |
| `procedure_name` | text |  |  |
| `procedure_category` | text | C2. From seed_procedure_map; NULL would mean a procedure the seed doesn't know. | not_null, relationships |
| `is_market_sale` | boolean | C2/C3. Arm's-length sale (seed). Gifts, grants, development and lease-to-own are false. |  |
| `is_lease_to_own` | boolean | C17. Either leg of a lease-to-own / lease-development deal. |  |
| `is_new_mortgage` | boolean | New individual (non-portfolio) bank mortgage; the mortgage-share numerator. |  |
| `is_portfolio_mortgage` | boolean | New portfolio mortgage registration (one loan over several units); reported separately. |  |
| `amount_is_loan` | boolean | C10. actual_worth is the loan amount. |  |
| `txn_date` | date | Registration date. NULL when is_date_invalid. |  |
| `instance_date_raw` | text | The date as published, kept so invalid dates stay traceable. |  |
| `is_date_invalid` | boolean | C18. Unparseable, a Hijri year (4 rows, 1416-1422 AH) or after the extract date. |  |
| `is_pre_2004` | boolean | C18. Registered 1900-2003, before the charter's analysis window (flag, don't drop). |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. |  |
| `reg_type_id` | smallint |  |  |
| `reg_type` | text |  | accepted_values |
| `is_offplan` | boolean | Off-plan vs ready, a first-class dimension (CLAUDE.md). | not_null |
| `area_id` | integer | C8. DLD area; joins seed_area. | not_null, relationships |
| `area_name` | text | Canonical name from seed_area. |  |
| `area_name_source` | text | Name as published in this snapshot (name drift is tested against the seed). |  |
| `zone` | text | Market zone from seed_area (NULL where not assigned yet). |  |
| `building_name` | text |  |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `has_project` | boolean | C9. The line names a DLD project (26% don't). Names stay NULL here; gold labels them Unknown. |  |
| `nearest_landmark` | text |  |  |
| `nearest_metro` | text |  |  |
| `nearest_mall` | text |  |  |
| `rooms_en` | text |  |  |
| `bedrooms` | smallint | C7. From seed_rooms_map; Studio = 0; NULL for offices, shops, penthouses, land. | between |
| `room_class` | text |  |  |
| `is_penthouse` | boolean |  |  |
| `is_commercial_unit` | boolean |  |  |
| `has_parking` | boolean |  |  |
| `area_sqm` | numeric | procedure_area in sq m, as published. |  |
| `actual_worth_aed` | numeric | AED value as published. Sales: price. Mortgage Registration / Delayed Mortgage: loan amount (C10). Repeated on every line of a portfolio deal: see C16. |  |
| `meter_sale_price_aed` | numeric |  |  |
| `rent_value_aed` | numeric |  |  |
| `meter_rent_price_aed` | numeric |  |  |
| `no_of_parties_role_1` | integer |  |  |
| `no_of_parties_role_2` | integer |  |  |
| `no_of_parties_role_3` | integer |  |  |
| `dld_extracted_at` | timestamp with time zone |  |  |
| `snapshot_date` | date |  |  |
| `source_file` | text |  |  |
| `row_hash` | text |  |  |

## Gold: star schema (dimensions, facts, aggregates)

| Object | Type | Description |
|---|---|---|
| [`gold.agg_area_month`](#goldagg_area_month) | table | Sales and financing by month x area x property type x bedrooms x off-plan, reporting scope only. Additive counts and AED (reconciled to fct_transaction); medians per cell with their n (min-n applied in rpt.area_month). |
| [`gold.agg_rent_month`](#goldagg_rent_month) | table | Rents by month x area x property type x bedrooms x new/renewal, reporting scope only. The only rent table Power BI imports. Additive counts and AED (reconciled to fct_rent_contract); medians per cell with their n (min-n applied in rpt.rent_month). |
| [`gold.dim_area`](#golddim_area) | table | One row per DLD area (seed_area, 265 IDs, all zoned) plus Unknown (-1). area_key is the DLD area_id. Latitude / longitude are NULL until the Phase 5 centroids are added to seed_area. |
| [`gold.dim_date`](#golddim_date) | table | Day-grain calendar, dim_date_start to dim_date_end (beyond the data for Phase 4 forecasts). The Power BI date table. is_after_snapshot marks days after the data snapshot date. |
| [`gold.dim_procedure`](#golddim_procedure) | table | One row per DLD (trans_group, procedure_id) from seed_procedure_map (C2), with its category. |
| [`gold.dim_project`](#golddim_project) | table | One row per DLD project in the transaction register, plus Unknown (-1) for lines with no project (C9). Developer, status and completion date wait for the DLD projects file (deferred for v1). master_project is the most frequent one where a project appears under several (master_project_count > 1). |
| [`gold.dim_property_type`](#golddim_property_type) | table | Conformed property type (usage group x property class), shared by sales, rents and both aggregates so one slicer filters them all. Every seed combination is listed. property_type_key = usage_group_id * 100 + property_class_id; 999 = Unknown x Unknown. |
| [`gold.fct_rates_monthly`](#goldfct_rates_monthly) | table | Monthly rate drivers from 2004: Fed Funds and Brent (FRED); EIBOR columns NULL until a CBUAE file is loaded. Rates are decimals (0.0525 = 5.25%). |
| [`gold.fct_rent_contract`](#goldfct_rent_contract) | table | Every Ejari contract line (10.5M) with dimension keys and the silver rent flags. Stays in Postgres; Power BI reads agg_rent_month. **Sum `annual_rent_alloc_aed` only** (C11). |
| [`gold.fct_transaction`](#goldfct_transaction) | table | Every DLD transaction line (Sales, Gifts, Mortgages; 1.79M) with dimension keys and the silver quality flags. Nothing is filtered. **Sum `aed_counted_once`**, never `actual_worth_aed`, for AED totals (C16 portfolio deals repeat their value per line). |

<a id="goldagg_area_month"></a>
### `gold.agg_area_month`

Sales and financing by month x area x property type x bedrooms x off-plan, reporting scope only. Additive counts and AED (reconciled to fct_transaction); medians per cell with their n (min-n applied in rpt.area_month).

| Column | Type | Description | Tests |
|---|---|---|---|
| `month` | date |  | not_null, relationships |
| `area_key` | integer | DLD area_id (-1 = Unknown). (from `fct_transaction`) | relationships |
| `property_type_key` | integer | usage_group_id * 100 + property_class_id. (from `int_property_type_lookup`) | relationships |
| `bedrooms` | smallint | C7. From seed_rooms_map; Studio = 0; NULL for offices, shops, penthouses, land. (from `stg_transactions`) |  |
| `is_offplan` | boolean | Off-plan vs ready, a first-class dimension (CLAUDE.md). (from `stg_transactions`) |  |
| `transaction_lines` | bigint |  |  |
| `aed_counted_once` | numeric | AED counted once per deal (C16): the deal value on the lead line, 0 on repeats. The only transaction AED column that is safe to SUM. (from `fct_transaction`) |  |
| `market_sales` | bigint |  |  |
| `market_sales_value_aed` | numeric | Σ aed_counted_once over market sales. |  |
| `clean_sales` | bigint | n behind the medians (clean market sales). |  |
| `clean_sales_aw_n` | bigint | Clean market sales with an area within the class cap (the area-weighted population). |  |
| `clean_sales_value_aed` | numeric | Σ AED over clean market sales with an area within the class cap. ÷ clean_sales_area_sqm = area-weighted AED per sq m; meaningful within a property class (the grain has property_type_key), not across land, buildings and units. |  |
| `clean_sales_area_sqm` | numeric | Σ area (sq m) over the same sales. |  |
| `sum_price_per_sqm_aed` | numeric |  |  |
| `median_price_per_sqm_aed` | numeric |  |  |
| `median_price_aed` | numeric |  |  |
| `purchase_mortgages` | bigint | Ready market sales matched to a same-day purchase mortgage (has_purchase_mortgage), counted on the sale line. ÷ ready market sales (market_sales where not is_offplan) = purchase-mortgage share (docs/01 §4). |  |
| `new_mortgages` | bigint | Individual new mortgages (is_new_mortgage), including refinancing. Secondary indicator: new mortgages per 100 market sales. |  |
| `new_mortgage_loans_aed` | numeric | Σ verified loan amounts (C10), once per deal. |  |
| `portfolio_mortgage_deals` | bigint | Portfolio mortgage deals, counted on the lead line so the column adds up. |  |
| `portfolio_mortgage_lines` | bigint |  |  |
| `portfolio_mortgage_value_aed` | numeric |  |  |

<a id="goldagg_rent_month"></a>
### `gold.agg_rent_month`

Rents by month x area x property type x bedrooms x new/renewal, reporting scope only. The only rent table Power BI imports. Additive counts and AED (reconciled to fct_rent_contract); medians per cell with their n (min-n applied in rpt.rent_month).

| Column | Type | Description | Tests |
|---|---|---|---|
| `month` | date |  | not_null, relationships |
| `area_key` | integer | DLD area_id (-1 = Unknown). (from `fct_rent_contract`) | relationships |
| `property_type_key` | integer | usage_group_id * 100 + property_class_id. (from `int_property_type_lookup`) | relationships |
| `bedrooms` | smallint | C22, from the Ejari sub-type (Studio = 0). Up to 15: Ejari has 11- and 15-bedroom labels (225 lines), unlike DLD's 0-10. (from `fct_rent_contract`) |  |
| `is_new` | boolean | C13. (from `int_rent_contracts`) |  |
| `rent_lines` | bigint |  |  |
| `contracts` | bigint | Contracts counted on line 1, so the column adds up across cells. |  |
| `annual_rent_alloc_aed` | numeric | Σ allocated annual rent (C11), each contract once. |  |
| `comparable_contracts` | bigint | n behind median_annual_rent_aed. |  |
| `market_rent_contracts` | bigint |  |  |
| `sum_annual_rent_aed` | numeric |  |  |
| `median_annual_rent_aed` | numeric |  |  |
| `rent_per_sqm_n` | bigint | n behind median_rent_per_sqm_aed (comparable lines with a real area). |  |
| `sum_rent_per_sqm_aed` | numeric |  |  |
| `median_rent_per_sqm_aed` | numeric |  |  |
| `comparable_area_sqm` | numeric | Σ area (sq m) over comparable lines with a real area. |  |
| `comparable_rent_with_area_aed` | numeric | Σ annual rent over the same lines; ÷ comparable_area_sqm = area-weighted rent per sq m. |  |

<a id="golddim_area"></a>
### `gold.dim_area`

One row per DLD area (seed_area, 265 IDs, all zoned) plus Unknown (-1). area_key is the DLD area_id. Latitude / longitude are NULL until the Phase 5 centroids are added to seed_area.

| Column | Type | Description | Tests |
|---|---|---|---|
| `area_key` | integer |  | not_null, unique |
| `area_id` | integer |  |  |
| `area_name` | text |  | not_null |
| `zone` | text | Market zone used for the min-n roll-up. | not_null |
| `latitude` | numeric | Area centroid latitude (WGS84) for the Power BI bubble map. Empty until Phase 5. (from `seed_area`) |  |
| `longitude` | numeric | Area centroid longitude (WGS84). Empty until Phase 5. (from `seed_area`) |  |

<a id="golddim_date"></a>
### `gold.dim_date`

Day-grain calendar, dim_date_start to dim_date_end (beyond the data for Phase 4 forecasts). The Power BI date table. is_after_snapshot marks days after the data snapshot date.

| Column | Type | Description | Tests |
|---|---|---|---|
| `date` | date |  | not_null, unique |
| `year` | smallint |  |  |
| `quarter` | smallint |  |  |
| `month_num` | smallint |  |  |
| `month_name` | text |  |  |
| `month_short` | text |  |  |
| `month_start` | date | First day of the month; the aggregates' `month` joins to `date` on this day. |  |
| `quarter_start` | date |  |  |
| `year_month` | text |  |  |
| `year_quarter` | text |  |  |
| `day_of_week` | smallint | ISO day of week, 1 = Monday. |  |
| `day_name` | text |  |  |
| `is_month_start` | boolean |  |  |
| `is_after_snapshot` | boolean | The day is after the data snapshot date (latest transaction date). | not_null |

<a id="golddim_procedure"></a>
### `gold.dim_procedure`

One row per DLD (trans_group, procedure_id) from seed_procedure_map (C2), with its category.

| Column | Type | Description | Tests |
|---|---|---|---|
| `procedure_key` | integer | Stable integer key for dim_procedure. Append new procedures with the next number; never renumber (Power BI relationships and saved filters use it). (from `seed_procedure_map`) | not_null, unique |
| `trans_group` | text |  |  |
| `procedure_id` | integer |  |  |
| `procedure_name` | text |  |  |
| `procedure_category` | text |  | not_null |
| `procedure_category_description` | text |  |  |
| `is_market_sale` | boolean | Arm's-length sale; feeds prices, indices, yields and the AVM. (from `seed_procedure_map`) |  |
| `is_lease_to_own` | boolean | C17. Lease-to-own / lease-development deal, either leg. (from `seed_procedure_map`) |  |
| `is_new_mortgage` | boolean | A new individual (single-unit) bank mortgage: Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration. The mortgage-share numerator. Portfolio registrations, modifications, transfers, development and lease finance are excluded. (from `seed_procedure_map`) |  |
| `is_portfolio_mortgage` | boolean | A new portfolio mortgage registration (one loan over several units: procedures 43, 101, 60). Reported separately from mortgage share, counted once per deal (C16). (from `seed_procedure_map`) |  |
| `amount_is_loan` | boolean | C10. `actual_worth` is the loan amount (Mortgage Registration, Delayed Mortgage). (from `seed_procedure_map`) |  |

<a id="golddim_project"></a>
### `gold.dim_project`

One row per DLD project in the transaction register, plus Unknown (-1) for lines with no project (C9). Developer, status and completion date wait for the DLD projects file (deferred for v1). master_project is the most frequent one where a project appears under several (master_project_count > 1).

| Column | Type | Description | Tests |
|---|---|---|---|
| `project_key` | integer | DLD project_number (-1 = Unknown). | not_null, unique |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `master_project` | text |  |  |
| `master_project_count` | bigint | Distinct master projects the project's lines were registered under. |  |
| `transaction_lines` | bigint |  |  |
| `first_txn_date` | date |  |  |
| `last_txn_date` | date |  |  |

<a id="golddim_property_type"></a>
### `gold.dim_property_type`

Conformed property type (usage group x property class), shared by sales, rents and both aggregates so one slicer filters them all. Every seed combination is listed. property_type_key = usage_group_id * 100 + property_class_id; 999 = Unknown x Unknown.

| Column | Type | Description | Tests |
|---|---|---|---|
| `property_type_key` | integer |  | not_null, unique |
| `usage_group_id` | integer |  |  |
| `usage_group` | text |  | not_null |
| `property_class_id` | integer |  |  |
| `property_class` | text |  | not_null |
| `property_type_label` | text |  |  |
| `property_class_description` | text |  |  |

<a id="goldfct_rates_monthly"></a>
### `gold.fct_rates_monthly`

Monthly rate drivers from 2004: Fed Funds and Brent (FRED); EIBOR columns NULL until a CBUAE file is loaded. Rates are decimals (0.0525 = 5.25%).

| Column | Type | Description | Tests |
|---|---|---|---|
| `month` | date |  | not_null, relationships, unique |
| `fed_funds_rate` | numeric | Effective federal funds rate as a decimal (0.0525 = 5.25%). (from `stg_rates`) | between |
| `eibor_1m` | numeric |  |  |
| `eibor_3m` | numeric |  |  |
| `eibor_6m` | numeric |  |  |
| `eibor_12m` | numeric |  |  |
| `brent_usd` | numeric | Mean Brent price over the month's trading days, USD per barrel. (from `stg_rates`) |  |
| `brent_trading_days` | bigint |  |  |

<a id="goldfct_rent_contract"></a>
### `gold.fct_rent_contract`

Every Ejari contract line (10.5M) with dimension keys and the silver rent flags. Stays in Postgres; Power BI reads agg_rent_month. **Sum `annual_rent_alloc_aed` only** (C11).

| Column | Type | Description | Tests |
|---|---|---|---|
| `contract_id` | text | Ejari contract number. (from `stg_rent_contracts`) |  |
| `line_number` | integer | 1..n within a contract (clean in Phase 1). (from `stg_rent_contracts`) |  |
| `start_date` | date |  | relationships |
| `end_date` | date |  |  |
| `area_key` | integer | DLD area_id (-1 = Unknown). | not_null, relationships |
| `property_type_key` | integer | usage_group_id * 100 + property_class_id. (from `int_property_type_lookup`) | not_null, relationships |
| `property_class_id` | integer | Conformed property class (seed_property_class) from the Ejari property type; sets the C21 area cap. (from `int_rent_contracts`) |  |
| `contract_reg_type` | text | C13. New or Renew. Market rent uses New (renewals lag the market). (from `int_rent_contracts`) |  |
| `is_new` | boolean | C13. (from `int_rent_contracts`) |  |
| `line_count` | bigint | C11. Lines in the contract, counted (not no_of_prop). (from `int_rent_contracts`) |  |
| `is_multi_unit` | boolean | C11. The contract has more than one line; its amount is a whole-contract total. (from `int_rent_contracts`) |  |
| `contract_days` | integer |  |  |
| `bus_property_type` | text |  |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. (from `stg_transactions`) |  |
| `is_free_hold` | boolean |  |  |
| `bedrooms` | smallint | C22, from the Ejari sub-type (Studio = 0). Up to 15: Ejari has 11- and 15-bedroom labels (225 lines), unlike DLD's 0-10. | between |
| `room_class` | text |  |  |
| `project_number` | integer |  |  |
| `project_name` | text |  |  |
| `tenant_type` | text |  |  |
| `area_sqm` | numeric | C21. actual_area when above 1 sq m and up to 10,000 sq m; NULL for blank / 0 / 1 placeholders and implausible areas. (from `int_rent_contracts`) |  |
| `contract_amount_aed` | numeric |  |  |
| `annual_rent_contract_aed` | numeric | C12. Contract annual rent (annual_amount, else contract_amount x 365 / days). (from `int_rent_contracts`) |  |
| `annual_rent_alloc_aed` | numeric | Contract annual rent / line count (C11). The only rent column to SUM. Full precision, not rounded to fils, so the shares add back to the contract amount exactly. |  |
| `rent_per_sqm_aed` | numeric | Annual rent per sq m, single-line contracts with a real area only (C11, C21). |  |
| `is_date_invalid` | boolean | C18. Start date unparseable or more than a year after the extract (up to year 2205). (from `int_rent_contracts`) |  |
| `is_pre_2004` | boolean | C18. Starts before 2004. (from `int_rent_contracts`) |  |
| `is_start_after_snapshot` | boolean | C18. Starts after the data snapshot date (registered ahead); outside the report scope. |  |
| `is_end_date_implausible` | boolean | C18. End date missing, before the start, or more than 10 years after it (up to year 5013). (from `int_rent_contracts`) |  |
| `is_amount_inconsistent` | boolean | Lines of one contract carry different annual amounts (0 in Phase 1). Makes C11 ambiguous. (from `int_rent_contracts`) |  |
| `is_non_market_property_type` | boolean | C20. Virtual Unit, Labor Camps or Room in labor Camp / Labor Camp. Not market rents. (from `int_rent_contracts`) |  |
| `is_area_placeholder` | boolean | C21. Blank, 0 or 1 sq m area. No rent per sq m. (from `int_rent_contracts`) |  |
| `is_area_implausible` | boolean | C21. Area above the cap for its property class (apartment 1,000 sq m, villa / townhouse 3,000, office / retail 5,000, other 10,000): a community, plot or building area, not the unit's. Rent kept; no area, no rent per sq m. (from `int_rent_contracts`) |  |
| `is_rent_below_floor` | boolean | C14. Allocated annual rent under AED 1,000. (from `int_rent_contracts`) |  |
| `is_rent_outlier` | boolean | C14. Below the floor, or outside the P0.5-P99.5 band of rent per sq m (annual rent where there is no usable area) by area x Ejari sub-type. (from `int_rent_contracts`) |  |
| `is_rent_comparable` | boolean | Like-for-like unit rent, new or renewed: single line, market property type (C20), inside the C14 band, usable dates (C18). | not_null |
| `is_market_rent` | boolean | Comparable and a new contract (C13). The default market-rent population. | not_null |
| `is_in_report_scope` | boolean | Valid start date from 2004 to the data snapshot date. | not_null |

<a id="goldfct_transaction"></a>
### `gold.fct_transaction`

Every DLD transaction line (Sales, Gifts, Mortgages; 1.79M) with dimension keys and the silver quality flags. Nothing is filtered. **Sum `aed_counted_once`**, never `actual_worth_aed`, for AED totals (C16 portfolio deals repeat their value per line).

| Column | Type | Description | Tests |
|---|---|---|---|
| `transaction_id` | text | DLD transaction id `<group>-<procedure>-<year>-<seq>`. Primary key after C1. (from `stg_transactions`) | not_null, unique |
| `txn_date` | date | Registration date (C18). NULL on the 4 Hijri-dated rows. | relationships |
| `area_key` | integer | DLD area_id (-1 = Unknown). | not_null, relationships |
| `property_type_key` | integer | usage_group_id * 100 + property_class_id. (from `int_property_type_lookup`) | not_null, relationships |
| `procedure_key` | integer | Stable integer key for dim_procedure. Append new procedures with the next number; never renumber (Power BI relationships and saved filters use it). (from `seed_procedure_map`) | not_null, relationships |
| `project_key` | integer | DLD project_number (-1 = no project, C9). | not_null, relationships |
| `trans_group` | text |  | accepted_values |
| `procedure_name` | text |  |  |
| `procedure_category` | text | C2. From seed_procedure_map; NULL would mean a procedure the seed doesn't know. (from `stg_transactions`) | accepted_values, not_null |
| `is_market_sale` | boolean | Arm's-length sale (C3). The market-sales KPI population (docs/01 §4). | not_null |
| `is_clean_market_sale` | boolean | The price population (medians, AED per sq m, index, AVM). | not_null |
| `has_quality_flag` | boolean | A market sale excluded from price statistics by C4-C6, C16 or C18. |  |
| `is_new_mortgage` | boolean | New individual (non-portfolio) mortgage: Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration. Includes refinancing and loans on units bought earlier, so it is a secondary indicator (new mortgages per 100 market sales, docs/01 §4); the headline is the purchase-mortgage share (int_purchase_mortgage_pairs). (from `int_mortgages`) |  |
| `is_portfolio_mortgage` | boolean | New portfolio mortgage registration (one loan over several units). Not in either mortgage indicator; count per deal with count(distinct deal_group_id). (from `int_mortgages`) |  |
| `amount_is_loan` | boolean | C10. True for Mortgage Registration and Delayed Mortgage only. (from `int_mortgages`) |  |
| `is_lease_to_own` | boolean | C17. Sales leg of a lease-to-own deal; is_market_sale is false (volume only). (from `int_market_sales`) |  |
| `reg_type` | text |  |  |
| `is_offplan` | boolean | Off-plan vs ready, a first-class dimension (CLAUDE.md). (from `stg_transactions`) |  |
| `property_type` | text |  |  |
| `property_sub_type` | text |  |  |
| `property_usage` | text | C19. Residential / Commercial / Other / ...; the swapped Arabic label is fixed to 'Other'. (from `stg_transactions`) |  |
| `is_residential` | boolean | C15 helper. property_usage = 'Residential'. (from `stg_transactions`) |  |
| `building_name` | text |  |  |
| `has_project` | boolean | C9. The line names a DLD project (26% don't). Names stay NULL here; gold labels them Unknown. (from `stg_transactions`) |  |
| `nearest_metro` | text |  |  |
| `rooms_en` | text |  |  |
| `bedrooms` | smallint | C7. From seed_rooms_map; Studio = 0; NULL for offices, shops, penthouses, land. (from `stg_transactions`) | between |
| `room_class` | text |  |  |
| `is_penthouse` | boolean |  |  |
| `is_commercial_unit` | boolean |  |  |
| `has_parking` | boolean |  |  |
| `area_sqm` | numeric | procedure_area in sq m, as published. (from `stg_transactions`) |  |
| `actual_worth_aed` | numeric | Value as registered (AED). Repeats a portfolio deal's total on each unit line. |  |
| `aed_counted_once` | numeric | AED counted once per deal (C16): the deal value on the lead line, 0 on repeats. The only transaction AED column that is safe to SUM. | not_null |
| `price_per_sqm_aed` | numeric | actual_worth_aed / area_sqm (C6), transfers only. AED per sq m. |  |
| `mortgage_amount_aed` | numeric | C10. The loan amount (AED), as recorded on the line; NULL where amount_is_loan is false. (from `int_mortgages`) |  |
| `mortgage_amount_once_aed` | numeric | Verified loan amount (C10), once per deal. NULL where the amount isn't a loan. |  |
| `portfolio_mortgage_value_once_aed` | numeric | Portfolio mortgage registration value, once per deal (not a verified loan). |  |
| `deal_group_id` | text | The lead line's transaction_id for a repeated-value deal; the line's own transaction_id otherwise. count(distinct deal_group_id) counts deals. (from `int_transaction_deal_groups`) |  |
| `deal_group_lines` | bigint | Lines in the deal (1 unless is_repeated_deal_value). (from `int_transaction_deal_groups`) |  |
| `is_deal_group_lead` | boolean | The deal's first line by DLD running number; carries the deal value once. (from `int_transaction_deal_groups`) |  |
| `batch_group_id` | text | Lead transaction_id of a similar-size batch (NULL otherwise). (from `int_transaction_deal_groups`) |  |
| `is_date_invalid` | boolean | C18. See stg_transactions. (from `int_market_sales`) |  |
| `is_pre_2004` | boolean | C18. Before the analysis window. (from `int_market_sales`) |  |
| `is_price_below_floor` | boolean | C4. actual_worth below AED 50,000 (nominal or partial-share values). (from `int_market_sales`) |  |
| `is_ppsqm_outlier` | boolean | C4. price_per_sqm outside the P0.5-P99.5 band of clean market sales. (from `int_market_sales`) |  |
| `is_price_invalid` | boolean | C4. Below the floor or outside the band. (from `int_market_sales`) |  |
| `is_area_invalid` | boolean | C5. Units outside 15-3,000 sq m, villas outside 15-10,000 sq m, land/buildings under 1 sq m, or no area. (from `int_market_sales`) |  |
| `is_ppsqm_mismatch` | boolean | C6. Recomputed price per sq m more than 5% off DLD's meter_sale_price. (from `int_market_sales`) |  |
| `is_repeated_deal_value` | boolean | C16. See int_transaction_deal_groups. (from `int_market_sales`) |  |
| `is_similar_size_batch` | boolean | C16. See int_transaction_deal_groups. (from `int_market_sales`) |  |
| `is_purchase_mortgage` | boolean | Mortgage Registration / Delayed Mortgage matched to a same-day ready sale of the same unit (int_purchase_mortgage_pairs): the loan that funded that purchase. | not_null |
| `has_purchase_mortgage` | boolean | Ready market sale matched to a same-day purchase mortgage of the same unit (int_purchase_mortgage_pairs). The numerator of the purchase-mortgage share of ready sales (docs/01 §4); a lower bound on mortgaged purchases. | not_null |
| `purchase_ltv` | numeric | Observed loan-to-value on a purchase mortgage line (loan ÷ matched sale price). |  |
| `property_class_id` | integer | Conformed property class (property_type_key % 100); sets the area cap. |  |
| `is_area_above_class_cap` | boolean | Area above the cap for the property class (apartment 1,000 sq m, villa 3,000, office / retail 5,000, other 10,000). Kept out of the area-weighted sums only; does not change is_clean_market_sale. | not_null |
| `is_in_report_scope` | boolean | Dated from 2004 to the data snapshot date. False for 1900-2003 rows and the 4 Hijri-dated rows. | not_null |

## rpt: reporting views, the only objects Power BI reads

| Object | Type | Description |
|---|---|---|
| [`rpt.area_month`](#rptarea_month) | view | rpt.area_month. Monthly sales and financing aggregate. |
| [`rpt.dim_area`](#rptdim_area) | view | rpt.dim_area. Areas with zone and centroid. |
| [`rpt.dim_date`](#rptdim_date) | view | rpt.dim_date. Calendar; mark as the date table on "Date". |
| [`rpt.dim_procedure`](#rptdim_procedure) | view | rpt.dim_procedure. DLD procedures and categories. |
| [`rpt.dim_project`](#rptdim_project) | view | rpt.dim_project. DLD projects (no developer yet). |
| [`rpt.dim_property_type`](#rptdim_property_type) | view | rpt.dim_property_type. Conformed usage group x property class. |
| [`rpt.price_index`](#rptprice_index) | view | rpt.price_index. Hedonic price index per segment (Dubai, apartments, villas, zones passing min-n) and period, Jan 2019 = 100, with YoY, volatility and drawdown. |
| [`rpt.rates_monthly`](#rptrates_monthly) | view | rpt.rates_monthly. Fed Funds, Brent and (later) EIBOR by month. |
| [`rpt.rent_month`](#rptrent_month) | view | rpt.rent_month. Monthly rent aggregate; the only rent table in Power BI. |
| [`rpt.report_info`](#rptreport_info) | view | rpt.report_info. One row with the data-as-of date, min-n and attribution. |
| [`rpt.transactions`](#rpttransactions) | view | rpt.transactions. Transaction lines in the reporting scope, without text ids or the individual quality flags. Sum "AED Counted Once" for values. |
| [`rpt.yield_quarter`](#rptyield_quarter) | view | rpt.yield_quarter. Gross yields by area / zone x property type x bedrooms x quarter, with both sample sizes; published cells only. |

<a id="rptarea_month"></a>
### `rpt.area_month`

dbt model `rpt_area_month`.

rpt.area_month. Monthly sales and financing aggregate.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Month` | date |  |  |
| `Area Key` | integer |  |  |
| `Property Type Key` | integer |  |  |
| `Bedrooms` | smallint |  |  |
| `Is Off-Plan` | boolean |  |  |
| `Market Sales` | bigint |  |  |
| `Market Sales Value AED` | bigint |  |  |
| `Clean Sales` | bigint |  |  |
| `Clean Sales AW N` | bigint |  |  |
| `Clean Sales Value AED` | bigint |  |  |
| `Clean Sales Area Sq M` | numeric |  |  |
| `Median Price per Sq M AED` | bigint |  |  |
| `Median Price AED` | bigint |  |  |
| `Purchase Mortgages` | bigint |  |  |
| `New Mortgages` | bigint |  |  |
| `New Mortgage Loans AED` | bigint |  |  |
| `Portfolio Mortgage Deals` | bigint |  |  |
| `Portfolio Mortgage Lines` | bigint |  |  |
| `Portfolio Mortgage Value AED` | bigint |  |  |

<a id="rptdim_area"></a>
### `rpt.dim_area`

dbt model `rpt_dim_area`.

rpt.dim_area. Areas with zone and centroid.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Area Key` | integer |  |  |
| `Area` | text |  |  |
| `Zone` | text |  |  |
| `Latitude` | numeric |  |  |
| `Longitude` | numeric |  |  |

<a id="rptdim_date"></a>
### `rpt.dim_date`

dbt model `rpt_dim_date`.

rpt.dim_date. Calendar; mark as the date table on "Date".

| Column | Type | Description | Tests |
|---|---|---|---|
| `Date` | date |  |  |
| `Year` | smallint |  |  |
| `Quarter` | smallint |  |  |
| `Month Number` | smallint |  |  |
| `Month` | text |  |  |
| `Month Short` | text |  |  |
| `Month Start` | date |  |  |
| `Quarter Start` | date |  |  |
| `Year Month` | text |  |  |
| `Year Quarter` | text |  |  |
| `Day of Week` | smallint |  |  |
| `Day Name` | text |  |  |
| `Is Month Start` | boolean |  |  |
| `Is After Snapshot` | boolean |  |  |

<a id="rptdim_procedure"></a>
### `rpt.dim_procedure`

dbt model `rpt_dim_procedure`.

rpt.dim_procedure. DLD procedures and categories.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Procedure Key` | integer |  |  |
| `Transaction Group` | text |  |  |
| `Procedure` | text |  |  |
| `Procedure Category` | text |  |  |
| `Procedure Category Description` | text |  |  |
| `Is Market Sale` | boolean |  |  |
| `Is New Mortgage` | boolean |  |  |
| `Is Portfolio Mortgage` | boolean |  |  |
| `Is Lease to Own` | boolean |  |  |
| `Amount Is Loan` | boolean |  |  |

<a id="rptdim_project"></a>
### `rpt.dim_project`

dbt model `rpt_dim_project`.

rpt.dim_project. DLD projects (no developer yet).

| Column | Type | Description | Tests |
|---|---|---|---|
| `Project Key` | integer |  |  |
| `Project` | text |  |  |
| `Master Project` | text |  |  |
| `First Transaction Date` | date |  |  |
| `Last Transaction Date` | date |  |  |
| `Transaction Lines` | bigint |  |  |

<a id="rptdim_property_type"></a>
### `rpt.dim_property_type`

dbt model `rpt_dim_property_type`.

rpt.dim_property_type. Conformed usage group x property class.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Property Type Key` | integer |  |  |
| `Usage Group` | text |  |  |
| `Usage Group Order` | integer |  |  |
| `Property Class` | text |  |  |
| `Property Class Order` | integer |  |  |
| `Property Type` | text |  |  |
| `Property Class Description` | text |  |  |

<a id="rptprice_index"></a>
### `rpt.price_index`

dbt model `rpt_price_index`.

rpt.price_index. Hedonic price index per segment (Dubai, apartments, villas, zones passing min-n) and period, Jan 2019 = 100, with YoY, volatility and drawdown.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Segment Key` | text |  |  |
| `Segment` | text |  |  |
| `Segment Level` | text |  |  |
| `Property Type Key` | integer |  |  |
| `Zone` | text |  |  |
| `Frequency` | text |  |  |
| `Period Start` | date |  |  |
| `Sales` | integer |  |  |
| `Index Value` | numeric |  |  |
| `Index 3M Average` | numeric |  |  |
| `Change on Previous Period` | numeric |  |  |
| `YoY Change` | numeric |  |  |
| `Volatility 12M` | numeric |  |  |
| `Running Peak` | numeric |  |  |
| `Drawdown` | numeric |  |  |
| `Drawdown Episode` | integer |  |  |
| `Is Partial Period` | boolean |  |  |
| `Model Version` | text |  |  |

<a id="rptrates_monthly"></a>
### `rpt.rates_monthly`

dbt model `rpt_rates_monthly`.

rpt.rates_monthly. Fed Funds, Brent and (later) EIBOR by month.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Month` | date |  |  |
| `Fed Funds Rate` | numeric |  |  |
| `EIBOR 1M` | numeric |  |  |
| `EIBOR 3M` | numeric |  |  |
| `EIBOR 6M` | numeric |  |  |
| `EIBOR 12M` | numeric |  |  |
| `Brent USD` | numeric |  |  |

<a id="rptrent_month"></a>
### `rpt.rent_month`

dbt model `rpt_rent_month`.

rpt.rent_month. Monthly rent aggregate; the only rent table in Power BI.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Month` | date |  |  |
| `Area Key` | integer |  |  |
| `Property Type Key` | integer |  |  |
| `Bedrooms` | smallint |  |  |
| `Is New Contract` | boolean |  |  |
| `Rent Lines` | bigint |  |  |
| `Contracts` | bigint |  |  |
| `Annual Rent AED` | bigint |  |  |
| `Comparable Contracts` | bigint |  |  |
| `Market Rent Contracts` | bigint |  |  |
| `Comparable Annual Rent AED` | bigint |  |  |
| `Median Annual Rent AED` | bigint |  |  |
| `Rent per Sq M N` | bigint |  |  |
| `Median Rent per Sq M AED` | bigint |  |  |
| `Comparable Area Sq M` | numeric |  |  |
| `Comparable Rent with Area AED` | bigint |  |  |

<a id="rptreport_info"></a>
### `rpt.report_info`

dbt model `rpt_report_info`.

rpt.report_info. One row with the data-as-of date, min-n and attribution.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Data As Of` | date |  |  |
| `Min N` | integer |  |  |
| `Source` | text |  |  |

<a id="rpttransactions"></a>
### `rpt.transactions`

dbt model `rpt_transactions`.

rpt.transactions. Transaction lines in the reporting scope, without text ids or the individual quality flags. Sum "AED Counted Once" for values.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Date` | date |  |  |
| `Area Key` | integer |  |  |
| `Property Type Key` | integer |  |  |
| `Procedure Key` | integer |  |  |
| `Project Key` | integer |  |  |
| `Transaction Group` | text |  |  |
| `Procedure Category` | text |  |  |
| `Is Market Sale` | boolean |  |  |
| `Is Clean Market Sale` | boolean |  |  |
| `Has Quality Flag` | boolean |  |  |
| `Is New Mortgage` | boolean |  |  |
| `Is Portfolio Mortgage` | boolean |  |  |
| `Has Purchase Mortgage` | boolean |  |  |
| `Is Purchase Mortgage` | boolean |  |  |
| `Is Deal Lead` | boolean |  |  |
| `Is Lease to Own` | boolean |  |  |
| `Is Off-Plan` | boolean |  |  |
| `Registration Type` | text |  |  |
| `DLD Property Usage` | text |  |  |
| `DLD Property Type` | text |  |  |
| `DLD Property Sub-Type` | text |  |  |
| `Rooms` | text |  |  |
| `Bedrooms` | smallint |  |  |
| `Has Parking` | boolean |  |  |
| `Area Above Class Cap` | boolean |  |  |
| `Area Sq M` | numeric |  |  |
| `Price AED` | bigint |  |  |
| `AED Counted Once` | bigint |  |  |
| `Price per Sq M AED` | bigint |  |  |
| `Loan Amount AED` | bigint |  |  |
| `Portfolio Mortgage Value AED` | bigint |  |  |
| `Purchase LTV` | numeric |  |  |

<a id="rptyield_quarter"></a>
### `rpt.yield_quarter`

dbt model `rpt_yield_quarter`.

rpt.yield_quarter. Gross yields by area / zone x property type x bedrooms x quarter, with both sample sizes; published cells only.

| Column | Type | Description | Tests |
|---|---|---|---|
| `Quarter Start` | date |  |  |
| `Geo Level` | text |  |  |
| `Zone` | text |  |  |
| `Area Key` | integer |  |  |
| `Property Type Key` | integer |  |  |
| `Bedrooms` | integer |  |  |
| `Rent Contracts` | integer |  |  |
| `Sales` | integer |  |  |
| `Median Annual Rent AED` | bigint |  |  |
| `Median Price AED` | bigint |  |  |
| `Gross Yield` | numeric |  |  |
| `Is Outside Sanity Band` | boolean |  |  |
| `Areas Rolled Up` | integer |  |  |
| `Is Partial Period` | boolean |  |  |
