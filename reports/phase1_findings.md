# Phase 1 findings: ingestion, bronze and profiling

Snapshot: DLD bulk transactions extracted 2026-09-29 (rows to 2026-09-25), Ejari rent contracts extracted 2026-09-30, FRED series downloaded 2026-09-30. Every number below can be regenerated with `make profile`. The query results are in [phase1_evidence.md](phase1_evidence.md), and the column profiles are in `profile_dld_transactions.md`, `profile_dld_rent_contracts.md`, `profile_rates_fedfunds.md` and `profile_rates_brent.md`.

## Summary

| # | Question | Answer | Consequence for Phase 2 |
|---|---|---|---|
| 1 | What procedures exist? | 52 procedure names in 58 group × procedure pairs: Sales 18, Mortgages 36, Gifts 4. There is **no inheritance procedure**. Six lease-to-own / lease-development procedures are registered under both Sales and Mortgages | `seed_procedure_map` must be keyed on **(trans_group, procedure_id)**, not on the name alone |
| 2 | Is mortgage `actual_worth` the loan amount? | **Yes, for completed-property mortgages.** Matched to a same-day sale of the same unit, the median ratio is 0.795 and the yearly medians follow the CBUAE LTV caps. Off-plan pre-registration mortgages are mixed: 43% equal the price | Rule C10: expose `mortgage_amount` for Mortgage Registration / Delayed Mortgage; treat pre-registration mortgages as count-only or flag them |
| 2b | Do portfolio deals repeat one value per line? | Yes. In the bulk file every line has its own `transaction_id`, so these groups have to be inferred. A naive Σ overstates mortgages by **AED 130.9bn (4.8%)**, sales by AED 8.0bn (0.2%) and gifts by AED 1.5bn (0.4%) | New flag `is_repeated_deal_value`; count the value once per group in any AED total |
| 3 | How do multi-property rent contracts repeat amounts? | **100%** of the 248,173 multi-line contracts repeat the same `annual_amount` and `contract_amount` on every line. A naive Σ is **5.24× the true total** (AED 4,490bn vs 856.5bn) | Rule C11 is mandatory before any rent sum. Decision options are in §3 |
| 4 | Date formats? | One format everywhere: ISO `YYYY-MM-DD` (and ISO 8601 UTC for `load_timestamp`). 4 Hijri dates, 18,208 rows before 2004, rent dates as late as year 5013 | Cast with `to_date(…, 'YYYY-MM-DD')`; flag, don't drop: `date_invalid` (Hijri, before 2004) and `end_date_implausible` (rents) |

The load is clean. All 15 files reconcile three ways: parser records = COPY rows = live bronze count ([bronze_reconciliation.md](bronze_reconciliation.md)). Arabic survived intact: 100% of `_ar` values contain Arabic script and **0 rows show mojibake**.

## 0. Ingestion results

| Table | Files | Rows | Size in Postgres | Load time |
|---|---:|---:|---:|---|
| `bronze.dld_transactions` | 2 | 1,788,150 | 1.25 GB | 21.9 s COPY + 8.1 s Python pre-pass |
| `bronze.dld_rent_contracts` | 11 | 10,538,926 | 5.9 GB | 211 s COPY (10.6–13.6 s per file, except one at 91 s) + 38 s pre-pass |
| `bronze.rates_fedfunds` | 1 | 866 (1954-07 → 2026-08) | small | < 1 s |
| `bronze.rates_brent` | 1 | 10,265 (1987-05-20 → 2026-09-22) | small | < 1 s |
| `bronze.rates_eibor` | 0 | none | none | **Skipped**: no CBUAE file in `data/raw/cbuae/` yet |
| `transactions_increment` | 1 | not loaded | none | **Disabled by design** (see docs/04 Decisions) |

- **Record count vs `wc -l`.** Record counts equal physical lines minus the header in every DLD file, so no quoted field in these files contains a line break. The loader still counts with a CSV parser, because a future snapshot might contain one.
- **Encoding.** Every file is valid UTF-8 without a BOM. The BOM-stripping and Windows-1256 fallback paths are exercised by `tests/test_load_bronze.py` rather than by real files.
- **Throughput** is about 80k rows/s per file for COPY on a 16 GB M-series Mac with the default Postgres settings. The one slow rent file (91 s, rent_contracts_…_0011) hit back-to-back checkpoints: the Postgres log shows "checkpoints are occurring too frequently (9 seconds apart)" during that load, because `max_wal_size` is still the 1 GB default. Raising it (e.g. to 4 GB) alongside the docs/03 server settings should remove these stalls.
- **Re-runs** are a no-op: `make bronze` again skips all 15 files by SHA-256 in 9 s.
- **Empty strings, not NULLs.** DLD quotes every field, so missing values arrive in bronze as `''`. Staging must apply `nullif(col, '')` before casting.

## 1. Procedures

The transaction groups are Sales 1,368,630 (76.5%), Mortgages 352,805 (19.7%) and Gifts 66,715 (3.7%). The largest procedures:

| Group | Procedure | Rows |
|---|---|---:|
| Sales | Sell - Pre registration (off-plan) | 628,175 |
| Sales | Sell | 513,971 |
| Mortgages | Mortgage Registration | 244,142 |
| Sales | Delayed Sell | 154,742 |
| Gifts | Grant | 59,018 |
| Sales / Mortgages | Lease to Own Registration | 29,826 / 29,823 |
| Mortgages | Modify Mortgage | 22,547 |
| Mortgages | Delayed Mortgage | 20,486 |

The full list of 58 pairs is in the evidence file, §1. Points that matter for `seed_procedure_map`:

- **Dual-registered procedures.** Six procedure codes (107, 110, 361, 371, 715, 814) appear in both Sales and Mortgages: lease-to-own and lease-development deals. 35,610 of the 35,613 Sales rows have a Mortgages row for the same unit on the same day (same procedure, date, area and size), but **only 1,878 carry the same value**. One deal is recorded twice, as a sale leg and a financing leg with a different amount. So the seed key is (trans_group, procedure_id). The Mortgages leg belongs in financing analysis only. The Sales leg is a financed purchase: flag it `is_lease_to_own` and decide in Phase 2 whether it counts as a market sale.
- **No inheritance procedure exists** in this extract. The Gifts group contains only Grant variants (Grant, Grant Pre-Registration, Grant on Delayed Sell, Grant Development). The seed's `inheritance` category will be empty; keep it for future snapshots.
- **Development / land procedures** (Development Registration, Sell Development, Adding Land By Sell, Portfolio Development Registration) are developer and land transfers. They belong in the seed as `other` or `development`, not `market_sale`.
- `procedure_id` is unique per procedure name, and it matches the second segment of `transaction_id` (`<group>-<procedure>-<year>-<seq>`) on 100% of rows.

## 2. `actual_worth` on mortgage rows is the loan amount

**Method.** A mortgage row and a sale row describe the same unit on the same day if they share date, area, building, project, sq m, rooms and sub-type. The key is kept only when it is unique on both sides. That gives 113,532 matched pairs out of 270,951 mortgage rows. The unmatched rows are mostly refinancings and mortgages on units bought earlier, which have no same-day sale. For each pair, `ratio = mortgage actual_worth / sale actual_worth`.

| Mortgage procedure | Matched sale | Pairs | p25 | Median | p75 | = price | ≤ 0.85 |
|---|---|---:|---:|---:|---:|---:|---:|
| Mortgage Registration | Sell | 102,516 | 0.700 | **0.795** | 0.832 | 0.5% | 89.8% |
| Delayed Mortgage | Delayed Sell | 8,934 | 0.742 | **0.800** | 0.835 | 0.2% | 93.8% |
| Mortgage Pre-Registration | Sell - Pre registration | 1,716 | 0.750 | 0.900 | 1.000 | **42.9%** | 46.5% |

**Why this is conclusive for completed properties.** If `actual_worth` were the property value, the ratio would sit at 1. Instead it sits below 1, and the mass moves with CBUAE's LTV rules:

- In **2014–2019**, 28–34% of pairs sit exactly at **0.75** and the median is 0.75. That matches the 75% cap for expat first homes ≤ AED 5M in the 2013 CBUAE mortgage regulation.
- From **2021**, the median is **0.80**, and in 2025–2026 41–50% of pairs sit exactly at 0.80. That follows the 2020 relaxation for first-time buyers.

The regulatory history is from domain knowledge. The Phase 2 LTV seed must cite the CBUAE source per CLAUDE.md.

**Caveats**

- 3.0% of Mortgage Registration pairs have a ratio above 1. These may be loans that include fees, loans secured on more than the one unit, or false matches.
- Off-plan **Mortgage Pre-Registration** is mixed: 42.9% exactly equal the price. It may record the property value, or 100% developer financing.

**Recommendation for C10.** Expose `mortgage_amount = actual_worth` for Mortgage Registration and Delayed Mortgage. Keep pre-registration mortgages, Modify Mortgage and Mortgage Transfer as counts, with an `amount_is_loan` flag set to false or unknown.

### 2b. Portfolio deals repeat one value on every unit line

The pre-check saw repeated `TRANSACTION_NUMBER`s in the portal export. **In the bulk export `transaction_id` is unique on all 1,788,150 rows**, so a portfolio deal shows up as several lines, each with its own ID, carrying the same deal value. Example: a 2007 Portfolio Mortgage Registration puts AED 6.79bn on each of 6 units across two areas (evidence, §2b).

**Detection rule** (`REPEATED_VALUE_GROUP` in `quality/investigate.py`). Group lines by group, procedure, date, value and ID-year. A group counts as one repeated deal value when all three hold:

- it has at least 2 lines;
- its `transaction_id` sequence numbers are close together (span ≤ 2 × lines, meaning they were registered in one batch);
- its unit sizes differ by more than 10%. Identical units can legitimately sell at identical prices.

Unrelated same-value deals on the same day (AED 750k, 1M, …) fail the sequence test, so they are not counted.

| Group | Repeated-value groups | Lines | Naive Σ overstated by | Share of naive Σ |
|---|---:|---:|---:|---:|
| Mortgages | 2,014 | 10,795 | **AED 130.9bn** | 4.8% |
| Sales | 2,276 | 5,940 | AED 8.0bn | 0.2% |
| Gifts | 199 | 546 | AED 1.5bn | 0.4% |

Within Mortgages, the overstatement comes from Portfolio Mortgage Registration (AED 44.9bn from only 11 groups), Modify Mortgage (43.0bn) and Mortgage Registration (37.4bn). The effect is lumpy by year. Naive vs corrected mortgage value:

| Year | Naive | Corrected |
|---|---:|---:|
| 2011 | AED 117.7bn | 94.0bn (−20%) |
| 2020 | AED 85.8bn | 77.1bn (−10%) |

Any mortgage-value time series must count each group's value once.

**Contiguous groups with similar unit sizes (within 10%)** are left out of the correction and kept visible as a separate count. There are 17,724 of these groups (42,458 lines) in Sales, and they are most likely identical units at identical prices. For price models they're harmless per line. For **AVM training** they are near-duplicates, so the out-of-time split already stops them leaking across sets.

## 3. Multi-property rent contracts repeat the contract amount

The 10,538,926 lines belong to **8,795,059 contracts**. There are 8,546,886 single-line contracts, and 248,173 multi-line contracts holding 1,992,040 lines.

- **Every multi-line contract (100%) repeats the same `annual_amount` and `contract_amount` on every line.** The amount is the contract total, not a per-unit rent. Example: CNT100148436 lists 4 flats (140.75, 141.86, 113.34 and 113.34 sq m), each with AED 184,000.
- The per-line attributes do vary: 117,373 multi-line contracts list different unit sizes. So the lines are real units, but the price is a single figure for the whole contract.
- `line_number` is clean: 1..n with no gaps or duplicates. `no_of_prop` disagrees with the line count on 5,594 multi-line contracts and 35 single-line ones, so **count lines, don't trust `no_of_prop`**.
- **Inflation of a naive Σ `annual_amount`.** The naive total is AED 4,490.0bn against AED 856.5bn counted once per contract, **5.24×**. On multi-line contracts alone it is 3,732.9bn vs 99.4bn (37.5×). Multi-line contracts are 2.8% of contracts, 18.9% of lines and 11.6% of true contract value. Lines per contract reach 788.
- The multi-line share is stable at 2–4% of contracts per year for both New and Renew (evidence, §3), so it doesn't bias trends. It does wreck totals and medians taken over lines.

**Options for C11 (a Phase 2 decision; recommendation first)**

1. **Recommended:** use single-line contracts only for market rent and yields (8.55M contracts, 97.2%). Keep multi-line contracts in `fct_rent_contract` with `annual_amount / lines` allocated per line and flagged `is_multi_unit`. A bulk lease, such as a company leasing a whole floor, is not a like-for-like rent for one unit anyway.
2. Allocate the amount by each line's share of `actual_area`. It's more precise, but 12.6% of lines have a blank area, and 1.55M lines have a blank area or a placeholder (0 or 1 sq m).

Either way, the `agg_rent_month` totals must equal Σ per-contract amounts. docs/04 §4 already plans that singular test.

**Other rent issues to flag in Phase 2**

- `ejari_bus_property_type_en = 'Virtual Unit'` covers 1.23M lines, which look like flexi-desk or virtual offices used for trade licences. There are also 1.22M lines in `Labor Camps` and 1.06M in `Room in labor Camp`. These are not residential market rents: exclude them from yields.
- `tenant_type` is blank on 40.1% of lines.
- `project_number` is blank on 84.5% of rent lines, compared with 26.3% of transactions. Rents join to sales at **area** level, not project level.
- `contract_amount ≠ annual_amount` on 1.2M lines (contracts not running 12 months), so apply C12. 7,227 lines have `annual_amount` < AED 1,000 and 955 are above AED 50M, so apply C14.

## 4. Date formats

| Column | Format | Range | Issues |
|---|---|---|---|
| `dld_transactions.instance_date` | `YYYY-MM-DD` (100%) | 1416-07-02 → 2026-09-25 | 4 Hijri dates; 18,208 rows 1966–2003 |
| `dld_transactions.load_timestamp` | ISO 8601 UTC `YYYY-MM-DDTHH:MM:SS.000Z` | one value per snapshot | DLD's extract time: use it as the snapshot timestamp |
| `dld_rent_contracts.contract_start_date` | `YYYY-MM-DD` (100%) | 2001-02-15 → 2205-07-16 | 18,764 start after the snapshot; 1 before 2004 |
| `dld_rent_contracts.contract_end_date` | `YYYY-MM-DD` (100%) | 2002-02-15 → 5013-05-28 | 11 end after 2040; none end before their start |
| FRED `observation_date` | `YYYY-MM-DD` | FEDFUNDS monthly (1st of month), Brent daily | no missing values in this download |

No `dd-mm-yyyy` values exist, which answers the C1 question in docs/04: every non-Hijri value casts cleanly with `to_date(x, 'YYYY-MM-DD')`.

**The Hijri dates.** 4 Mortgage Registration rows have years 1416–1422. Converted with the tabular Islamic calendar they become 1995-11-24, 1996-06-20, 1999-05-15 and 2002-02-05. The first three match the year in their `transaction_id` exactly. The fourth (ID year 1995, converted 2002) fits the general pattern: the ID year looks like the application year, which usually comes before registration. 67,846 rows (3.8%) have an ID year 1 or more years *before* `instance_date`, and only 45 have it after. **Recommendation:** flag them `date_invalid` rather than convert. They are pre-2004 and fall outside every analysis window.

**Pre-2004 rows.** There are 18,208 rows dated 1966–2003, mostly title transfers registered before the modern system. Out of scope (the charter covers 2004 onwards): flag them `is_pre_2004` and exclude from marts.

## 5. Other quality issues found while profiling

| Issue | Rows | Where it's handled |
|---|---:|---|
| `property_usage` EN/AR swapped for one category: `property_usage_en = 'أخرى'` with `_ar = 'Other'` | 6,322 | Staging: map `'أخرى'` → `Other` |
| `property_usage_ar = 'مليون'` ("million") on the `Other` category, a mistranslation | 48,129 | Harmless: `_ar` is dropped in silver |
| Round per-sq-ft prices show up as sq m values (10.76 = AED 1/sq ft; 538.19 = 50; 10,763.90 = 1,000), mostly buildings, villas and land | 3,043 | Informational: `meter_sale_price` is consistent with `actual_worth / procedure_area`, and only 20 rows in the whole table are more than 5% off (C6) |
| Sales with `actual_worth` < AED 50k | 2,237 | C4 flag |
| `procedure_area` < 1 sq m | 280 | C5 flag |
| `actual_worth` up to AED 13.8bn (portfolio/land); `procedure_area` up to 342M sq m | tail | C4/C5 flags plus §2b |
| Rent `actual_area` blank or placeholder (0 or 1 sq m) | 1.55M lines | C14: no rent per sq m for these lines |
| Transactions have 259 area IDs, rents 216, 266 in either table (**correction, Phase 2a:** 215 and 265 real IDs; the extra value is the blank `area_id` on 3 rent lines) | none | `seed_area` covers all 265 |

## 6. Figures for docs/02 §7

| Item | Actual |
|---|---|
| Transaction rows (raw) | 1,788,150 (2 files: 894,076 + 894,074) |
| Date range | 2004-01-05 → 2026-09-25 in scope; 18,212 earlier rows (incl. 4 Hijri) flagged |
| Sales / Mortgages / Gifts | 1,368,630 / 352,805 / 66,715 (76.5% / 19.7% / 3.7%) |
| Off-plan share of sales, last 12 months (2025-09-26 → 2026-09-25) | 68.2% of sales rows, 47.8% of sales value |
| Rent contract lines (raw) | 10,538,926 (11 files) |
| Rent contracts after de-duplication | 8,795,059 |
| Σ sales value, 2025 | AED 681.2bn across all Sales-group procedures (Sell / Sell pre-reg / Delayed Sell: 665.9bn). Before the market-sale filter; the repeated-value overstatement is only AED 0.5bn |
| Mortgage `actual_worth` | Loan amount (median LTV 0.795) for Mortgage Registration / Delayed Mortgage; mixed for pre-registration |
| Distinct areas | 259 area IDs (transactions), 216 (rents), 266 combined; 215 / 265 excluding the blank `area_id` (Phase 2a correction) |

## 7. Limitations

- The mortgage-to-sale match covers 42% of mortgage rows. Refinancings and mortgages on units bought earlier can't be matched by design, so the loan-amount conclusion is proven on purchase mortgages and assumed for the rest.
- The portfolio rule is a heuristic, and its thresholds (span ≤ 2 × lines, size spread > 10%) are judgement calls. The evidence file shows the excluded "similar size" groups, so a reviewer can see what the rule leaves out.
- EIBOR is not loaded yet. CBUAE doesn't provide a stable CSV endpoint, so a manual download into `data/raw/cbuae/` is needed. Fed Funds is the fallback rate driver.
- `data/sample/` is gitignored per CLAUDE.md, so CI can't use it yet. See the open question in docs/04 Decisions.
