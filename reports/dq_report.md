# Data-quality report: silver

Generated 2026-09-30 13:59 UTC by `quality/dq_report.py` from database `dubai_property`. Regenerate with `make dq` (after `make dbt`). The rules are in docs/04 §2.

## 1. Rows in and out per step

Silver removes rows in one place only: C1 keeps the latest snapshot of each line. Every other rule is a flag. The dbt tests `recon_transactions_partition` and `recon_rents_rows` enforce these counts.

| Step | Rows | Removed | Reason |
|---|---|---|---|
| bronze.dld_transactions | 1,788,150 |  | raw lines as loaded |
| silver.stg_transactions | 1,788,150 | 0 | C1: older snapshot of a transaction_id removed |
| silver.int_transaction_deal_groups | 1,788,150 | 0 | none (adds C16 columns) |
| silver.int_market_sales | 1,435,345 |  | split: Sales + Gifts groups (flags only, nothing removed) |
| silver.int_mortgages | 352,805 |  | split: Mortgages group (flags only, nothing removed) |
| bronze.dld_rent_contracts | 10,538,926 |  | raw lines as loaded |
| silver.int_rent_contracts | 10,538,926 | 0 | C1: older snapshot of a (contract_id, line_number) removed |

## 2. Rows affected per rule

Every column documented with `meta.dq_rule` in the dbt YAML. Flags overlap, so rows don't add up across rules. AED is once per deal (transactions, `actual_worth_once_aed`) or allocated per line (rents, `annual_rent_alloc_aed`), so it never double-counts a portfolio deal or a multi-unit contract.

| Rule | Flag | Rows | % of model | AED bn | Meaning |
|---|---|---|---|---|---|
| C4 | `int_market_sales.is_ppsqm_outlier` | 31,166 | 2.17 | 225.74 | C4. price_per_sqm outside the P0.5-P99.5 band of clean market sales. |
| C4 | `int_market_sales.is_price_below_floor` | 2,431 | 0.17 | 0.06 | C4. actual_worth below AED 50,000 (nominal or partial-share values). |
| C4 | `int_market_sales.is_price_invalid` | 31,762 | 2.21 | 225.76 | C4. Below the floor or outside the band. |
| C5 | `int_market_sales.is_area_invalid` | 4,355 | 0.3 | 27.28 | C5. Units outside 15-3,000 sq m, villas outside 15-10,000 sq m, land/buildings under 1 sq m, or no area. |
| C6 | `int_market_sales.is_ppsqm_mismatch` | 11 | 0.0 | 0.00 | C6. Recomputed price per sq m more than 5% off DLD's meter_sale_price. |
| C11 | `int_rent_contracts.is_amount_inconsistent` | 0 | 0.0 |  | Lines of one contract carry different annual amounts (0 in Phase 1). Makes C11 ambiguous. |
| C11 | `int_rent_contracts.is_multi_unit` | 1,992,040 | 18.9 | 99.39 | C11. The contract has more than one line; its amount is a whole-contract total. |
| C14 | `int_rent_contracts.is_rent_below_floor` | 39,079 | 0.37 | 0.01 | C14. Allocated annual rent under AED 1,000. |
| C14 | `int_rent_contracts.is_rent_outlier` | 231,685 | 2.2 | 43.53 | C14. Below the floor, or outside the P0.5-P99.5 band of rent per sq m (annual rent where there is no usable area) by area x Ejari sub-type. |
| C16 | `int_market_sales.is_repeated_deal_value` | 6,486 | 0.45 | 6.47 | C16. See int_transaction_deal_groups. |
| C16 | `int_market_sales.is_similar_size_batch` | 46,192 | 3.22 | 91.63 | C16. See int_transaction_deal_groups. |
| C16 | `int_mortgages.is_repeated_deal_value` | 10,795 | 3.06 | 56.78 | C16. |
| C16 | `int_mortgages.is_similar_size_batch` | 7,466 | 2.12 | 57.90 | C16. |
| C16 | `int_transaction_deal_groups.is_repeated_deal_value` | 17,281 | 0.97 | 203.61 | C16. Line of an inferred portfolio deal: >= 2 lines with the same group, procedure, date, value and ID-year, registered in one batch (ID span <= 2 x lines), whose unit sizes differ by more than 10%. |
| C16 | `int_transaction_deal_groups.is_similar_size_batch` | 53,658 | 3.0 | 149.54 | C16 (kept visible, not corrected). Same batch pattern but unit sizes within 10%: most likely identical units at identical prices, so every line keeps its value. |
| C17 | `int_market_sales.is_lease_to_own` | 35,613 | 2.48 | 64.58 | C17. Sales leg of a lease-to-own deal; is_market_sale is false (volume only). |
| C17 | `int_mortgages.is_lease_to_own` | 36,932 | 10.47 | 54.17 | C17. Financing leg of a lease-to-own deal. |
| C17 | `stg_transactions.is_lease_to_own` | 72,545 | 4.06 | 119.85 | C17. Either leg of a lease-to-own / lease-development deal. |
| C18 | `int_market_sales.is_date_invalid` | 0 | 0.0 |  | C18. See stg_transactions. |
| C18 | `int_market_sales.is_pre_2004` | 9,598 | 0.67 | 23.71 | C18. Before the analysis window. |
| C18 | `int_mortgages.is_date_invalid` | 4 | 0.0 | 0.01 | C18. Includes the 4 Hijri-dated Mortgage Registration rows. |
| C18 | `int_mortgages.is_pre_2004` | 8,610 | 2.44 | 37.18 | C18. |
| C18 | `int_rent_contracts.is_date_invalid` | 100 | 0.0 | 0.03 | C18. Start date unparseable or more than a year after the extract (up to year 2205). |
| C18 | `int_rent_contracts.is_end_date_implausible` | 401 | 0.0 | 0.13 | C18. End date missing, before the start, or more than 10 years after it (up to year 5013). |
| C18 | `int_rent_contracts.is_pre_2004` | 1 | 0.0 | 0.00 | C18. Starts before 2004. |
| C18 | `stg_transactions.is_date_invalid` | 4 | 0.0 | 0.01 | C18. Unparseable, a Hijri year (4 rows, 1416-1422 AH) or after the extract date. |
| C18 | `stg_transactions.is_pre_2004` | 18,208 | 1.02 | 62.74 | C18. Registered 1900-2003, before the charter's analysis window (flag, don't drop). |
| C20 | `int_rent_contracts.is_non_market_property_type` | 1,996,808 | 18.95 | 77.52 | C20. Virtual Unit, Labor Camps or Room in labor Camp / Labor Camp. Not market rents. |
| C21 | `int_rent_contracts.is_area_placeholder` | 1,551,171 | 14.72 | 86.79 | C21. Blank, 0 or 1 sq m area. No rent per sq m. |

## 3. Populations

Each row is counted once, under the **first** reason that keeps it out (in the order shown), so the rows add up to the model total.

**Clean market sales** (`int_market_sales.is_clean_market_sale`): the population for prices, indices, yields and the AVM.

| Reason | Rows | AED bn |
|---|---|---|
| 0 not a market sale (C3: gift, development, lease-to-own) | 136,067 | 569.57 |
| 2 C18 before 2004 | 8,539 | 21.37 |
| 3 C16 repeated deal value | 5,211 | 4.87 |
| 4 C4 price below AED 50k | 1,521 | 0.03 |
| 5 C4 price per sq m outside band | 14,777 | 166.07 |
| 6 C5 implausible area | 1,470 | 7.47 |
| 8 clean market sale | 1,267,760 | 3390.46 |

**Market rents** (`int_rent_contracts.is_market_rent`): the population for market rent and yields.

| Reason | Lines | Allocated AED bn |
|---|---|---|
| 0 C13 renewal | 5,061,528 | 430.51 |
| 1 C11 multi-unit contract | 1,193,949 | 56.02 |
| 2 C20 virtual unit / labour camp | 633,621 | 27.67 |
| 3 C18 start date invalid | 4 | 0.00 |
| 4 C18 before 2004 | 1 | 0.00 |
| 5 C18 end date implausible | 128 | 0.09 |
| 6 C14 outlier | 48,082 | 19.47 |
| 7 market rent | 3,601,613 | 322.72 |

## 4. Reconciliation with Phase 1

AED counted once per deal / contract, and the C16 / C11 counts, against `seed_phase1_reconciliation` (reports/phase1_findings.md). `phase1` is blank where Phase 1 published no figure. On any other data than the Phase 1 snapshot (e.g. the CI fixtures) the figures are expected to differ; the dbt tests `recon_*_phase1_figures` only check them on that snapshot, and `recon_*_once_vs_*` check the method on any data.

| Dataset | Group | Metric | Phase 1 | Silver | Check |
|---|---|---|---|---|---|
| rents |  | contracts | 8,795,059 | 8,795,059 | match |
| rents |  | multi_line_contracts | 248,173 | 248,173 | match |
| rents |  | multi_line_lines | 1,992,040 | 1,992,040 | match |
| rents |  | naive_total_bn | 4,490 | 4,490 | match |
| rents |  | once_per_contract_bn | 856.5 | 856.5 | match |
| transactions | Gifts | naive_total_bn | 398.9 | 398.9 | match |
| transactions | Gifts | once_per_deal_bn |  | 397.4 |  |
| transactions | Gifts | overstated_bn | 1.5 | 1.5 | match |
| transactions | Gifts | repeated_groups | 199 | 199 | match |
| transactions | Gifts | repeated_lines | 546 | 546 | match |
| transactions | Gifts | similar_size_groups | 1,563 | 1,563 | match |
| transactions | Gifts | similar_size_lines | 3,734 | 3,734 | match |
| transactions | Mortgages | naive_total_bn | 2724.5 | 2724.5 | match |
| transactions | Mortgages | once_per_deal_bn |  | 2593.5 |  |
| transactions | Mortgages | overstated_bn | 130.9 | 130.9 | match |
| transactions | Mortgages | repeated_groups | 2,014 | 2,014 | match |
| transactions | Mortgages | repeated_lines | 10,795 | 10,795 | match |
| transactions | Mortgages | similar_size_groups | 2,943 | 2,943 | match |
| transactions | Mortgages | similar_size_lines | 7,466 | 7,466 | match |
| transactions | Sales | naive_total_bn | 3770.4 | 3770.4 | match |
| transactions | Sales | once_per_deal_bn |  | 3762.4 |  |
| transactions | Sales | overstated_bn | 8.0 | 8.0 | match |
| transactions | Sales | repeated_groups | 2,276 | 2,276 | match |
| transactions | Sales | repeated_lines | 5,940 | 5,940 | match |
| transactions | Sales | similar_size_groups | 17,724 | 17,724 | match |
| transactions | Sales | similar_size_lines | 42,458 | 42,458 | match |

## 5. Mortgage share inputs

Mortgage share (docs/01 §4) = individual new mortgages / (individual new mortgages + market sales), by registration year. Individual new mortgages are Mortgage Registration, Delayed Mortgage and Mortgage Pre-Registration (`is_new_mortgage`). Loans (AED bn) are once per deal, and only for the two procedures whose amount is a verified loan (C10). **Portfolio mortgage registrations** (`is_portfolio_mortgage`: one loan over several units) are outside the ratio and shown separately, counted once per deal (C16). Their value is as recorded, not a verified loan amount.

| Year | Market sales | New mortgages | Mortgage share % | Loans AED bn | Portfolio deals | Portfolio lines | Portfolio value AED bn |
|---|---|---|---|---|---|---|---|
| 2004 | 2,794 | 1,159 | 29.3 | 7.7 | 0 | 0 |  |
| 2005 | 2,487 | 1,249 | 33.4 | 12.9 | 0 | 0 |  |
| 2006 | 2,621 | 1,640 | 38.5 | 36.6 | 0 | 0 |  |
| 2007 | 7,275 | 2,737 | 27.3 | 36.4 | 4 | 9 | 10.71 |
| 2008 | 21,324 | 5,218 | 19.7 | 74.8 | 1 | 1 | 1.93 |
| 2009 | 56,340 | 7,022 | 11.1 | 18.3 | 5 | 5 | 13.61 |
| 2010 | 30,185 | 7,311 | 19.5 | 26.4 | 4 | 4 | 4.61 |
| 2011 | 24,891 | 6,022 | 19.5 | 31.9 | 4 | 6 | 9.55 |
| 2012 | 32,546 | 5,250 | 13.9 | 17.6 | 8 | 8 | 9.93 |
| 2013 | 58,159 | 8,091 | 12.2 | 51.0 | 16 | 16 | 9.33 |
| 2014 | 50,163 | 8,088 | 13.9 | 58.2 | 17 | 17 | 2.44 |
| 2015 | 38,436 | 9,099 | 19.1 | 63.3 | 21 | 21 | 3.00 |
| 2016 | 37,742 | 10,079 | 21.1 | 54.8 | 72 | 74 | 16.25 |
| 2017 | 42,831 | 11,144 | 20.6 | 61.6 | 121 | 121 | 6.21 |
| 2018 | 29,712 | 9,962 | 25.1 | 56.6 | 143 | 162 | 8.13 |
| 2019 | 35,503 | 9,271 | 20.7 | 47.0 | 182 | 182 | 7.72 |
| 2020 | 32,138 | 10,288 | 24.2 | 32.1 | 104 | 105 | 2.99 |
| 2021 | 57,640 | 14,558 | 20.2 | 48.6 | 144 | 145 | 7.04 |
| 2022 | 93,615 | 16,578 | 15.0 | 68.8 | 151 | 151 | 80.83 |
| 2023 | 129,195 | 22,772 | 15.0 | 69.8 | 146 | 153 | 26.87 |
| 2024 | 175,437 | 31,247 | 15.1 | 95.0 | 178 | 181 | 7.42 |
| 2025 | 211,007 | 37,715 | 15.2 | 115.1 | 345 | 345 | 9.69 |
| 2026 | 118,698 | 26,618 | 18.3 | 88.3 | 207 | 208 | 6.68 |
