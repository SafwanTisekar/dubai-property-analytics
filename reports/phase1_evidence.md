# Phase 1 evidence: bronze investigations

Generated 2026-09-30 11:54 UTC by `quality/investigate.py`. Raw query results; interpretation is in [phase1_findings.md](phase1_findings.md).

## 1. Procedures (`procedure_name_en`)

All distinct procedure / transaction-group pairs. `procedure_id` is unique per name, but six lease-to-own and lease-development procedures appear under **both** Sales and Mortgages.

**Procedures by transaction group**

| trans_group_en | procedure_id | procedure_name_en | rows | first_year | last_year |
|---|---|---|---|---|---|
| Gifts | 9 | Grant | 59,018 | 1999 | 2026 |
| Gifts | 120 | Grant Pre-Registration | 3,936 | 2008 | 2026 |
| Gifts | 219 | Grant on Delayed Sell | 2,401 | 2010 | 2026 |
| Gifts | 59 | Grant Development | 1,360 | 2010 | 2026 |
| Mortgages | 13 | Mortgage Registration | 244,142 | 1416 | 2026 |
| Mortgages | 110 | Lease to Own Registration | 29,823 | 2007 | 2026 |
| Mortgages | 14 | Modify Mortgage | 22,547 | 1998 | 2026 |
| Mortgages | 190 | Delayed Mortgage | 20,486 | 2009 | 2026 |
| Mortgages | 810 | Lease Finance Registration | 8,256 | 2012 | 2026 |
| Mortgages | 39 | Development Mortgage | 6,786 | 2008 | 2026 |
| Mortgages | 105 | Mortgage Pre-Registration | 6,323 | 2004 | 2026 |
| Mortgages | 107 | Lease to Own Registration Pre-Registration | 3,557 | 2009 | 2026 |
| Mortgages | 44 | Mortgage Transfer | 3,305 | 2010 | 2026 |
| Mortgages | 43 | Portfolio Mortgage Registration | 1,818 | 2007 | 2026 |
| Mortgages | 361 | Delayed Lease to Own Registration | 1,089 | 2009 | 2021 |
| Mortgages | 37 | Lease to Own Transfer | 869 | 2007 | 2025 |
| Mortgages | 56 | Modify Development Mortgage | 824 | 2008 | 2026 |
| Mortgages | 49 | Portfolio Mortgage Modification | 619 | 2008 | 2026 |
| Mortgages | 371 | Lease Development Registration | 471 | 2009 | 2024 |
| Mortgages | 32 | Lease to Own Modify | 432 | 2010 | 2026 |
| Mortgages | 811 | Lease Finance Modification | 389 | 2013 | 2026 |
| Mortgages | 715 | Delayed Sell Lease to Own Registration | 361 | 2014 | 2026 |
| Mortgages | 814 | Lease to Own on Development Registration | 310 | 2012 | 2026 |
| Mortgages | 191 | Modify Delayed Mortgage | 104 | 2010 | 2026 |
| Mortgages | 101 | Portfolio Mortgage Registration Pre-Registration | 78 | 2017 | 2026 |
| Mortgages | 151 | Portfolio Mortgage Development Registration | 54 | 2016 | 2026 |
| Mortgages | 113 | Mortgage Transfer Pre-Registration | 42 | 2021 | 2021 |
| Mortgages | 108 | Modify Mortgage Pre-Registration | 28 | 2015 | 2026 |
| Mortgages | 135 | Portfolio Mortgage Modification Pre-Registration | 20 | 2017 | 2026 |
| Mortgages | 60 | Delayed Portfolio Mortgage | 18 | 2019 | 2026 |
| Mortgages | 861 | Development Mortgage Pre-Registration | 12 | 2016 | 2024 |
| Mortgages | 815 | Lease to Own on Development Modification | 10 | 2016 | 2026 |
| Mortgages | 57 | Transfer Development Mortgage | 9 | 2014 | 2022 |
| Mortgages | 152 | Portfolio Mortgage Development Modification | 9 | 2016 | 2026 |
| Mortgages | 103 | Lease to Own Transfer Pre-Registration | 5 | 2025 | 2025 |
| Mortgages | 111 | Portfolio Mortgage Transfer | 4 | 2021 | 2022 |
| Mortgages | 372 | Lease Development Modify | 2 | 2017 | 2020 |
| Mortgages | 362 | Delayed Lease to Own Modify | 1 | 2015 | 2015 |
| Mortgages | 716 | Delayed Sell Lease To Own Modification | 1 | 2024 | 2024 |
| Mortgages | 363 | Delayed Lease to Own Transfer | 1 | 2010 | 2010 |
| Sales | 102 | Sell - Pre registration | 628,175 | 2003 | 2026 |
| Sales | 11 | Sell | 513,971 | 1975 | 2026 |
| Sales | 41 | Delayed Sell | 154,742 | 2006 | 2026 |
| Sales | 110 | Lease to Own Registration | 29,826 | 2006 | 2026 |
| Sales | 45 | Sell Development | 12,927 | 2008 | 2026 |
| Sales | 133 | Development Registration | 12,832 | 2000 | 2026 |
| Sales | 851 | Development Registration Pre-Registration | 5,721 | 2010 | 2026 |
| Sales | 107 | Lease to Own Registration Pre-Registration | 3,556 | 2009 | 2026 |
| Sales | 460 | Sale On Payment Plan | 2,390 | 2018 | 2026 |
| Sales | 95 | Delayed Development | 1,343 | 2012 | 2026 |
| Sales | 361 | Delayed Lease to Own Registration | 1,089 | 2009 | 2021 |
| Sales | 371 | Lease Development Registration | 471 | 2009 | 2024 |
| Sales | 4 | Adding Land By Sell | 471 | 2000 | 2026 |
| Sales | 715 | Delayed Sell Lease to Own Registration | 361 | 2014 | 2026 |
| Sales | 814 | Lease to Own on Development Registration | 310 | 2012 | 2026 |
| Sales | 852 | Sell Development - Pre Registration | 275 | 2015 | 2026 |
| Sales | 93 | Delayed Sell Development | 164 | 2016 | 2026 |
| Sales | 150 | Portfolio Development Registration | 6 | 2015 | 2025 |

**Transaction groups**

| trans_group_en | rows | pct | procedures |
|---|---|---|---|
| Sales | 1,368,630 | 76.5 | 18 |
| Mortgages | 352,805 | 19.7 | 36 |
| Gifts | 66,715 | 3.7 | 4 |

**Procedures registered under both Sales and Mortgages: are they the same deal? (match on date + area + size; value equal or not)**

| sales_rows | mortgage_rows | sales_rows_with_same_unit_day_mortgage | of_which_same_value |
|---|---|---|---|
| 35,613 | 35,611 | 35,610 | 1,878 |

## 2. Is `actual_worth` on mortgage rows the loan amount?

Mortgage rows matched to a sale of the same unit on the same day (key: date, area, building, project, sq m, rooms, sub-type; unique on both sides). `ratio` = mortgage `actual_worth` / sale `actual_worth`.

**Ratio distribution by procedure pair**

| mortgage_procedure | sale_procedure | pairs | p10 | p25 | median | p75 | p90 | pct_equal | pct_le_0_85 | pct_above_1 |
|---|---|---|---|---|---|---|---|---|---|---|
| Mortgage Registration | Sell | 102,516 | 0.599 | 0.700 | 0.795 | 0.832 | 0.851 | 0.5 | 89.8 | 3 |
| Delayed Mortgage | Delayed Sell | 8,934 | 0.600 | 0.742 | 0.800 | 0.835 | 0.850 | 0.2 | 93.8 | 0.7 |
| Mortgage Pre-Registration | Sell - Pre registration | 1,716 | 0.600 | 0.750 | 0.900 | 1 | 1 | 42.9 | 46.5 | 4.1 |
| Mortgage Registration | Delayed Sell | 323 | 0.436 | 0.603 | 0.800 | 0.911 | 1.227 | 0.9 | 65.6 | 20.1 |
| Delayed Mortgage | Sell | 34 | 0.293 | 0.376 | 0.585 | 0.757 | 0.872 | 0 | 88.2 | 5.9 |
| Mortgage Registration | Sell - Pre registration | 8 | 0.495 | 0.533 | 0.700 | 0.847 | 1.140 | 0 | 75 | 12.5 |
| Delayed Mortgage | Sell - Pre registration | 1 | 0.363 | 0.363 | 0.363 | 0.363 | 0.363 | 0 | 100 | 0 |

**Mortgage Registration vs Sell/Delayed Sell: mass at the LTV caps, by year (2010+)**

| yr | pairs | median | pct_at_0_75 | pct_at_0_80 | pct_equal |
|---|---|---|---|---|---|
| 2010 | 1,840 | 0.800 | 6.3 | 8.5 | 0.7 |
| 2011 | 1,606 | 0.790 | 7.4 | 14.3 | 1.2 |
| 2012 | 1,959 | 0.778 | 8.5 | 19.7 | 0.9 |
| 2013 | 2,803 | 0.800 | 9.7 | 17.1 | 0.7 |
| 2014 | 2,291 | 0.750 | 28.2 | 5.5 | 0.5 |
| 2015 | 1,966 | 0.750 | 33.1 | 1.1 | 0.5 |
| 2016 | 2,373 | 0.750 | 34 | 5.9 | 0.4 |
| 2017 | 3,060 | 0.750 | 31.3 | 16.7 | 0.5 |
| 2018 | 2,633 | 0.750 | 30.8 | 18.5 | 0.7 |
| 2019 | 2,688 | 0.750 | 31.1 | 23.5 | 0.8 |
| 2020 | 3,495 | 0.788 | 15.2 | 20.8 | 0.7 |
| 2021 | 6,600 | 0.800 | 5.2 | 22.8 | 0.4 |
| 2022 | 8,656 | 0.800 | 3 | 16.7 | 0.5 |
| 2023 | 12,147 | 0.800 | 2.7 | 13.2 | 0.2 |
| 2024 | 18,070 | 0.810 | 2 | 10.7 | 0.2 |
| 2025 | 21,758 | 0.800 | 2.1 | 41.1 | 0.3 |
| 2026 | 12,662 | 0.800 | 2.4 | 50.3 | 0.2 |

**Match coverage**

| mortgage_rows | with_unique_unit_day_key | matched_to_a_sale |
|---|---|---|
| 270,951 | 253,796 | 113,532 |

## 2b. Portfolio deals: one deal value repeated on every unit line

Inferred repeated-value groups: `lines > 1 and id_span <= 2 * lines and area_ratio > 1.10` (see module docstring). `overstated` = worth × (lines − 1), i.e. what a naive `sum(actual_worth)` double-counts. Groups where sizes are within 10% are shown separately: they may be identical units at identical prices.

**By transaction group (AED bn)**

| grp | groups | lines | overstated_bn | naive_total_bn | pct_of_naive_total | similar_size_groups | similar_size_lines |
|---|---|---|---|---|---|---|---|
| Gifts | 199 | 546 | 1.5 | 398.9 | 0.4 | 1,563 | 3,734 |
| Mortgages | 2,014 | 10,795 | 130.9 | 2724.5 | 4.8 | 2,943 | 7,466 |
| Sales | 2,276 | 5,940 | 8 | 3770.4 | 0.2 | 17,724 | 42,458 |

**Mortgages by procedure (AED bn)**

| procedure | groups | lines | max_lines | overstated_bn |
|---|---|---|---|---|
| Portfolio Mortgage Registration | 11 | 52 | 20 | 44.89 |
| Modify Mortgage | 252 | 770 | 24 | 42.96 |
| Mortgage Registration | 1,538 | 8,867 | 169 | 37.43 |
| Mortgage Transfer | 7 | 96 | 76 | 3.72 |
| Delayed Mortgage | 43 | 106 | 10 | 0.44 |
| Lease to Own Registration | 48 | 135 | 8 | 0.43 |
| Portfolio Mortgage Modification | 1 | 3 | 3 | 0.36 |
| Development Mortgage | 41 | 279 | 27 | 0.34 |
| Mortgage Pre-Registration | 10 | 68 | 28 | 0.14 |
| Lease Finance Registration | 35 | 240 | 60 | 0.10 |
| Modify Development Mortgage | 14 | 138 | 29 | 0.05 |
| Modify Delayed Mortgage | 2 | 6 | 3 | 0.03 |
| Lease to Own Transfer | 3 | 9 | 4 | 0.01 |
| Lease to Own Registration Pre-Registration | 4 | 12 | 5 | 0.01 |
| Lease Finance Modification | 1 | 3 | 3 | 0.01 |
| Lease to Own on Development Registration | 1 | 2 | 2 | 0 |
| Lease Development Registration | 1 | 2 | 2 | 0 |
| Delayed Lease to Own Registration | 1 | 5 | 5 | 0 |
| Mortgage Transfer Pre-Registration | 1 | 2 | 2 | 0 |

**Mortgage value by year, naive vs corrected (AED bn, 2010+)**

| yr | naive_bn | corrected_bn |
|---|---|---|
| 2010 | 70 | 68.9 |
| 2011 | 117.7 | 94 |
| 2012 | 109.8 | 109.2 |
| 2013 | 110.2 | 107.4 |
| 2014 | 106.3 | 105.8 |
| 2015 | 125.2 | 116.5 |
| 2016 | 136.4 | 134.8 |
| 2017 | 128 | 127.4 |
| 2018 | 118.3 | 116.8 |
| 2019 | 119.3 | 115.2 |
| 2020 | 85.8 | 77.1 |
| 2021 | 141.4 | 141.1 |
| 2022 | 226.1 | 225.8 |
| 2023 | 193.3 | 192.4 |
| 2024 | 186 | 185.6 |
| 2025 | 179 | 178.4 |
| 2026 | 148.9 | 148.6 |

**Example: one Portfolio Mortgage Registration**

| instance_date | procedure_name_en | area_name_en | procedure_area | actual_worth | meter_sale_price | transaction_id |
|---|---|---|---|---|---|---|
| 2007-08-23 | Portfolio Mortgage Registration | Jabal Ali | 2168.16 | 6789500000.00 | 3131457.09 | 2-43-2007-4 |
| 2007-08-23 | Portfolio Mortgage Registration | Jabal Ali | 1463.73 | 6789500000.00 | 4638492.07 | 2-43-2007-5 |
| 2007-08-23 | Portfolio Mortgage Registration | Al Warsan First | 1643.56 | 6789500000.00 | 4130971.79 | 2-43-2007-6 |
| 2007-08-23 | Portfolio Mortgage Registration | Al Warsan First | 822.37 | 6789500000.00 | 8256016.15 | 2-43-2007-10 |
| 2007-08-23 | Portfolio Mortgage Registration | Al Warsan First | 1540.34 | 6789500000.00 | 4407793.08 | 2-43-2007-11 |
| 2007-08-23 | Portfolio Mortgage Registration | Jabal Ali | 1265.28 | 6789500000.00 | 5366005.94 | 2-43-2007-12 |

## 3. Multi-property rent contracts

One row per `contract_id` in a temp table. A contract is multi-line when it has more than one line.

**Single vs multi-line contracts**

| kind | contracts | lines | dup_line_numbers | line_number_gaps | no_of_prop_ne_lines | same_annual_amount_every_line | same_contract_amount_every_line | unit_area_varies |
|---|---|---|---|---|---|---|---|---|
| single-line | 8,546,886 | 8,546,886 | 0 | 0 | 35 | 8,546,886 | 8,546,886 | 0 |
| multi-line | 248,173 | 1,992,040 | 0 | 0 | 5,594 | 248,173 | 248,173 | 117,373 |

**Inflation of a naive sum of `annual_amount` (AED bn)**

| naive_line_sum_bn | once_per_contract_bn | inflation_x | multi_naive_bn | multi_once_bn | multi_share_of_value_pct |
|---|---|---|---|---|---|
| 4,490 | 856.5 | 5.24 | 3732.9 | 99.4 | 11.6 |

**Contracts by number of lines**

| lines_bucket | contracts | lines | pct_same_amount |
|---|---|---|---|
| 1 | 8,546,886 | 8,546,886 | 100 |
| 2-5 | 189,784 | 500,384 | 100 |
| 6-20 | 40,999 | 412,045 | 100 |
| 21-100 | 14,807 | 620,279 | 100 |
| 100+ | 2,583 | 459,332 | 100 |

**Multi-line share by contract start year and New/Renew (2015+)**

| start_year | reg_type | contracts | pct_multi_line_contracts | lines_in_multi |
|---|---|---|---|---|
| 2015 | New | 189,333 | 3.92 | 78,790 |
| 2015 | Renew | 231,828 | 2.52 | 32,649 |
| 2016 | New | 176,436 | 3.74 | 68,308 |
| 2016 | Renew | 264,073 | 2.98 | 56,182 |
| 2017 | New | 213,668 | 3.70 | 76,177 |
| 2017 | Renew | 257,501 | 3.04 | 59,914 |
| 2018 | New | 241,290 | 3.52 | 90,159 |
| 2018 | Renew | 260,391 | 3.19 | 61,091 |
| 2019 | New | 250,247 | 3.35 | 84,271 |
| 2019 | Renew | 274,093 | 3.10 | 65,905 |
| 2020 | New | 263,043 | 3.02 | 79,052 |
| 2020 | Renew | 277,150 | 2.91 | 55,700 |
| 2021 | New | 360,637 | 2.68 | 80,094 |
| 2021 | Renew | 292,129 | 2.96 | 54,711 |
| 2022 | New | 384,050 | 2.80 | 93,450 |
| 2022 | Renew | 377,753 | 2.78 | 61,311 |
| 2023 | New | 390,323 | 2.97 | 110,261 |
| 2023 | Renew | 450,331 | 2.67 | 71,598 |
| 2024 | New | 467,472 | 2.76 | 131,041 |
| 2024 | Renew | 495,124 | 2.72 | 80,768 |
| 2025 | New | 514,146 | 2.61 | 142,934 |
| 2025 | Renew | 512,505 | 2.70 | 92,412 |
| 2026 | New | 366,924 | 1.94 | 69,946 |
| 2026 | Renew | 372,448 | 2.85 | 74,402 |

**Example: a 4-unit contract**

| contract_id | line_number | no_of_prop | annual_amount | contract_amount | actual_area | ejari_property_sub_type_en | contract_start_date |
|---|---|---|---|---|---|---|---|
| CNT100148436 | 1 | 4 | 184000.00 | 184000.00 | 140.75 | 2 bed rooms+hall | 2011-11-01 |
| CNT100148436 | 2 | 4 | 184000.00 | 184000.00 | 141.86 | 2 bed rooms+hall | 2011-11-01 |
| CNT100148436 | 3 | 4 | 184000.00 | 184000.00 | 113.34 | 2 bed rooms+hall | 2011-11-01 |
| CNT100148436 | 4 | 4 | 184000.00 | 184000.00 | 113.34 | 2 bed rooms+hall | 2011-11-01 |

## 4. Date formats

Each value's shape with digits replaced by 9 and letters by a.

**Shapes of every date column**

| col | shape | count | min | max |
|---|---|---|---|---|
| rates_fedfunds.observation_date | 9999-99-99 | 866 | 1954-07-01 | 2026-08-01 |
| rates_brent.observation_date | 9999-99-99 | 10,265 | 1987-05-20 | 2026-09-22 |
| dld_transactions.instance_date | 9999-99-99 | 1,788,150 | 1416-07-02 | 2026-09-25 |
| dld_transactions.load_timestamp | 9999-99-99a99:99:99.999a | 1,788,150 | 2026-09-29T06:31:10.000Z | 2026-09-29T06:31:10.000Z |
| dld_rent_contracts.contract_start_date | 9999-99-99 | 10,538,926 | 2001-02-15 | 2205-07-16 |
| dld_rent_contracts.contract_end_date | 9999-99-99 | 10,538,926 | 2002-02-15 | 5013-05-28 |

**`instance_date` by era**

| era | count | min | max |
|---|---|---|---|
| 1 before 1900 (Hijri) | 4 | 1416-07-02 | 1422-11-23 |
| 2 1900-2003 | 18,208 | 1966-01-18 | 2003-12-31 |
| 3 2004 to snapshot | 1,769,938 | 2004-01-05 | 2026-09-25 |

**The Hijri-dated rows (year in `transaction_id` for comparison)**

| instance_date | transaction_id | id_year | procedure_name_en | actual_worth |
|---|---|---|---|---|
| 1416-07-02 | 2-13-1995-128 | 1995 | Mortgage Registration | 500000.00 |
| 1417-02-04 | 2-13-1996-190 | 1996 | Mortgage Registration | 2290000.00 |
| 1420-01-30 | 2-13-1999-631 | 1999 | Mortgage Registration | 500000.00 |
| 1422-11-23 | 2-13-1995-137 | 1995 | Mortgage Registration | 2000000.00 |

**`transaction_id` year minus `instance_date` year**

| id_year_minus_date_year | count |
|---|---|
| 0 | 1,720,255 |
| -1 | 27,840 |
| -2 | 19,162 |
| -3 | 12,369 |
| -4 | 5,413 |
| -5 | 1,780 |
| -6 | 473 |
| -8 | 210 |
| -7 | 184 |
| -11 | 91 |

**Rent contract dates**

| start_pre_2004 | start_after_snapshot | end_before_start | end_after_2040 | max_end |
|---|---|---|---|---|
| 1 | 18,764 | 0 | 11 | 5013-05-28 |

**FRED missing values (empty value field)**

| series | blank | rows |
|---|---|---|
| fedfunds | 0 | 866 |
| brent | 0 | 10,265 |

## 5. Encoding: Arabic columns

Share of rows whose `_ar` columns contain Arabic script (U+0600–U+06FF), and rows with typical mojibake (`Ø`, `Ù`) or the replacement character U+FFFD.

**Arabic integrity**

| tbl | rows | area_ar_arabic | procedure_ar_arabic | mojibake_rows |
|---|---|---|---|---|
| dld_transactions | 1,788,150 | 1,788,150 | 1,788,150 | 0 |
| dld_rent_contracts | 10,538,926 | 10,538,923 | 10,538,926 | 0 |

**`property_usage`: EN/AR labels swapped for one category**

| property_usage_en | property_usage_ar | rows |
|---|---|---|
| Residential | سكني | 1,489,074 |
| Commercial | تجاري | 189,123 |
| Other | مليون | 48,129 |
| Hospitality | ضيافة | 44,486 |
| أخرى | Other | 6,322 |
| Industrial | صناعي | 4,968 |
| Multi-Use | متعدد الاستخدامات | 4,127 |
| Agricultural | زراعي | 1,150 |
| Storage | تخزين | 710 |
| Residential / Commercial | سكني / تجاري | 61 |

## 6. docs/02 §7 figures

Sales = `trans_group_en = 'Sales'` (all sale procedures, before the Phase 2 market-sale filter). Snapshot runs to 2026-09-25, so "last 12 months" is 2025-09-26 → 2026-09-25 and the last full year is 2025.

**Transactions: rows and valid date range (2004+)**

| rows | first_2004plus | last | pre_2004_rows | distinct_area_ids |
|---|---|---|---|---|
| 1,788,150 | 2004-01-05 | 2026-09-25 | 18,212 | 259 |

**Off-plan share of sales, last 12 months**

| sales_rows | offplan_rows | offplan_pct_rows | offplan_pct_value |
|---|---|---|---|
| 182,872 | 124,673 | 68.2 | 47.8 |

**Sales value, full year 2025 (AED bn)**

| sales_rows | naive_sum_bn | sell_procedures_bn | repeated_value_overstatement_bn |
|---|---|---|---|
| 214,529 | 681.2 | 665.9 | 0.5 |

**Rent lines, contracts and areas**

| lines | contracts | distinct_area_ids | area_ids_either_table |
|---|---|---|---|
| 10,538,926 | 8,795,059 | 216 | 266 |
