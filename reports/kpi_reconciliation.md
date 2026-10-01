# KPI reconciliation

Generated 2026-10-01 09:43 UTC by `quality/kpi_reconciliation.py` from database `dubai_property_ci`. Regenerate with `make kpi` (after `make dbt`); `tests/test_kpi_reconciliation.py` fails if any check below fails.

These are the numbers the Power BI cards must match (docs/06 §3). Every KPI in docs/01 §4 that exists before the models is computed from silver (canonical, below) and again from the rpt views Power BI imports, at three grains (all time, year, month). **Data snapshot: 2026-09-25** (the latest transaction date; `rpt.report_info` "Data As Of"). Scope: 2004-01-01 to the snapshot; rent contracts starting after it are excluded. **All checks pass.**

Definitions (docs/01 §4): **market sales** = `is_market_sale` lines, AED counted once per deal (C16); **median AED per sq m** = all clean market sales (`is_clean_market_sale`); **area-weighted AED per sq m** = Σ AED / Σ sq m over clean sales of residential apartments and villas / townhouses whose area is within the class cap (1,000 / 3,000 sq m), because across property classes it would mix land, buildings and units; **purchase-mortgage share of ready sales** = ready market sales matched to a same-day purchase mortgage of the same unit (`has_purchase_mortgage`, a lower bound) / ready market sales; **new mortgages per 100 market sales** = individual new mortgages (incl. refinancing) x 100 / market sales, a secondary indicator; portfolio mortgages are outside both, counted once per deal; **off-plan share** = off-plan market sales / market sales; **new market rents** = `is_market_rent` (new, single-line, comparable, started by the snapshot); area-weighted rent = Σ annual rent / Σ sq m over new market rents of residential apartments and villas with a plausible area (C21 class caps).

## 1. All time

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 1,321 | 4.2 | 11,126 | 9,087 | 841 | 1 | 0.1 | 314 | 23.8 | 36.3 | 19.6 | 3 | 0.0 | 875 | 602 |

## 2. By year

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2004 | 55 | 0.3 | 2,271 | 1,417 | 55 | 0 | 0.0 | 19 | 34.5 | 0.0 | 0.0 | 0 | 0.0 | 0 |  |
| 2005 | 46 | 0.3 | 3,456 | 2,447 | 46 | 0 | 0.0 | 16 | 34.8 | 0.0 | 0.0 | 0 | 0.0 | 5 | 2,050 |
| 2006 | 47 | 0.2 | 2,707 | 3,407 | 47 | 0 | 0.0 | 27 | 57.4 | 0.0 | 0.0 | 0 | 0.0 | 5 | 286 |
| 2007 | 32 | 0.3 | 4,434 | 6,251 | 32 | 0 | 0.0 | 17 | 53.1 | 0.0 | 0.0 | 0 | 0.0 | 11 | 250 |
| 2008 | 52 | 0.3 | 8,987 | 7,348 | 52 | 0 | 0.0 | 16 | 30.8 | 0.0 | 0.0 | 0 | 0.0 | 7 | 252 |
| 2009 | 56 | 0.1 | 9,360 | 8,830 | 23 | 0 | 0.0 | 7 | 12.5 | 58.9 | 53.5 | 0 | 0.0 | 33 | 688 |
| 2010 | 60 | 0.1 | 9,265 | 10,474 | 36 | 0 | 0.0 | 9 | 15.0 | 40.0 | 43.2 | 0 | 0.0 | 88 | 525 |
| 2011 | 55 | 0.1 | 9,629 | 11,460 | 50 | 0 | 0.0 | 6 | 10.9 | 9.1 | 5.8 | 0 | 0.0 | 80 | 533 |
| 2012 | 66 | 0.1 | 9,884 | 10,867 | 58 | 0 | 0.0 | 8 | 12.1 | 12.1 | 9.4 | 0 | 0.0 | 73 | 540 |
| 2013 | 61 | 0.2 | 10,764 | 9,922 | 50 | 0 | 0.0 | 12 | 19.7 | 18.0 | 8.6 | 0 | 0.0 | 59 | 608 |
| 2014 | 51 | 0.1 | 12,089 | 9,765 | 36 | 0 | 0.0 | 17 | 33.3 | 29.4 | 16.4 | 0 | 0.0 | 44 | 565 |
| 2015 | 57 | 0.1 | 10,462 | 11,990 | 35 | 0 | 0.0 | 13 | 22.8 | 38.6 | 35.0 | 0 | 0.0 | 29 | 535 |
| 2016 | 51 | 0.1 | 9,257 | 10,575 | 34 | 0 | 0.0 | 17 | 33.3 | 33.3 | 29.1 | 0 | 0.0 | 34 | 631 |
| 2017 | 58 | 0.1 | 10,213 | 9,407 | 21 | 0 | 0.0 | 13 | 22.4 | 63.8 | 53.0 | 1 | 0.0 | 39 | 682 |
| 2018 | 55 | 0.1 | 12,844 | 9,674 | 26 | 0 | 0.0 | 10 | 18.2 | 52.7 | 31.1 | 0 | 0.0 | 43 | 586 |
| 2019 | 57 | 0.3 | 14,995 | 13,523 | 21 | 0 | 0.0 | 14 | 24.6 | 63.2 | 23.3 | 1 | 0.0 | 42 | 614 |
| 2020 | 46 | 0.1 | 10,469 | 12,449 | 24 | 0 | 0.0 | 22 | 47.8 | 47.8 | 40.4 | 0 | 0.0 | 38 | 465 |
| 2021 | 62 | 0.2 | 12,409 | 13,899 | 28 | 0 | 0.0 | 13 | 21.0 | 54.8 | 25.2 | 0 | 0.0 | 51 | 381 |
| 2022 | 69 | 0.2 | 16,436 | 17,186 | 33 | 0 | 0.0 | 6 | 8.7 | 52.2 | 33.6 | 0 | 0.0 | 41 | 482 |
| 2023 | 65 | 0.2 | 15,115 | 20,499 | 34 | 1 | 2.9 | 11 | 16.9 | 47.7 | 46.7 | 0 | 0.0 | 34 | 728 |
| 2024 | 94 | 0.2 | 17,703 | 19,737 | 53 | 0 | 0.0 | 12 | 12.8 | 43.6 | 27.8 | 1 | 0.0 | 56 | 1,046 |
| 2025 | 65 | 0.2 | 15,500 | 18,869 | 32 | 0 | 0.0 | 13 | 20.0 | 50.8 | 31.2 | 0 | 0.0 | 35 | 727 |
| 2026 | 61 | 0.3 | 18,980 | 21,577 | 15 | 0 | 0.0 | 16 | 26.2 | 75.4 | 38.7 | 0 | 0.0 | 28 | 877 |

## 3. Last 12 months

The 12 months to the snapshot (2026-09-25). The snapshot month is partial.

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10 | 7 | 0.0 | 17,438 | 19,299 | 3 | 0 | 0.0 | 0 | 0.0 | 57.1 | 69.6 | 0 | 0.0 | 4 | 971 |
| 2025-11 | 5 | 0.0 | 13,043 | 11,511 | 3 | 0 | 0.0 | 3 | 60.0 | 40.0 | 24.7 | 0 | 0.0 | 1 | 298 |
| 2025-12 | 3 | 0.0 | 13,033 | 13,669 | 0 | 0 |  | 2 | 66.7 | 100.0 | 100.0 | 0 | 0.0 | 1 | 1,047 |
| 2026-01 | 6 | 0.1 | 18,263 | 20,188 | 3 | 0 | 0.0 | 1 | 16.7 | 50.0 | 6.8 | 0 | 0.0 | 2 | 1,178 |
| 2026-02 | 14 | 0.1 | 18,918 | 20,070 | 4 | 0 | 0.0 | 2 | 14.3 | 71.4 | 37.6 | 0 | 0.0 | 4 | 2,081 |
| 2026-03 | 6 | 0.0 | 18,089 | 17,863 | 0 | 0 |  | 0 | 0.0 | 100.0 | 100.0 | 0 | 0.0 | 1 |  |
| 2026-04 | 8 | 0.0 | 31,067 | 25,622 | 2 | 0 | 0.0 | 1 | 12.5 | 75.0 | 87.5 | 0 | 0.0 | 3 | 867 |
| 2026-05 | 5 | 0.0 | 19,239 | 28,813 | 1 | 0 | 0.0 | 0 | 0.0 | 80.0 | 63.3 | 0 | 0.0 | 2 | 506 |
| 2026-06 | 7 | 0.0 | 17,626 | 19,297 | 0 | 0 |  | 1 | 14.3 | 100.0 | 100.0 | 0 | 0.0 | 1 | 734 |
| 2026-07 | 6 | 0.0 | 17,121 | 13,311 | 3 | 0 | 0.0 | 6 | 100.0 | 50.0 | 83.2 | 0 | 0.0 | 2 | 651 |
| 2026-08 | 4 | 0.0 | 21,056 | 25,088 | 0 | 0 |  | 0 | 0.0 | 100.0 | 100.0 | 0 | 0.0 | 10 | 833 |
| 2026-09 | 5 | 0.0 | 27,537 | 27,819 | 2 | 0 | 0.0 | 5 | 100.0 | 60.0 | 52.2 | 0 | 0.0 | 3 | 913 |

## 4. Checks: silver vs rpt

Counts exact; AED within 0.5 AED per row summed and areas within 0.01 sq m per row (rpt rounds each row); medians within 1 AED. `rpt.area_month` has no median (cell medians can't be combined), and `rpt.rent_month` carries the rent metrics.

| rpt view | Values checked | Mismatches |
|---|---|---|
| rpt.transactions | 4,736 | 0 |
| rpt.area_month | 4,144 | 0 |
| rpt.rent_month | 774 | 0 |

## 5. Sanity check: residential apartments, area-weighted vs median AED per sq m

Must be within ±40% of each other in every year from 2010. A wider gap would mean plot- or building-sized areas are still leaking into the area-weighted sums (or a unit mix shift worth explaining).

**Not applicable here**: fewer than 100,000 transaction lines in scope (fixture or sample data), so yearly apartment figures are noise.

| Year | Median AED / sq m | Area-weighted AED / sq m | Area-weighted / median % | Check |
|---|---|---|---|---|
| 2004 |  |  |  |  |
| 2005 |  |  |  |  |
| 2006 |  |  |  |  |
| 2007 | 5,008 | 5,041 | 100.7 |  |
| 2008 | 10,405 | 11,929 | 114.6 |  |
| 2009 | 9,360 | 9,471 | 101.2 |  |
| 2010 | 10,270 | 11,330 | 110.3 |  |
| 2011 | 9,918 | 13,405 | 135.2 |  |
| 2012 | 11,244 | 11,580 | 103.0 |  |
| 2013 | 10,857 | 11,805 | 108.7 |  |
| 2014 | 14,522 | 13,908 | 95.8 |  |
| 2015 | 12,740 | 14,071 | 110.4 |  |
| 2016 | 11,575 | 13,319 | 115.1 |  |
| 2017 | 10,271 | 11,916 | 116.0 |  |
| 2018 | 14,218 | 14,709 | 103.5 |  |
| 2019 | 17,453 | 19,423 | 111.3 |  |
| 2020 | 14,971 | 15,838 | 105.8 |  |
| 2021 | 16,393 | 16,644 | 101.5 |  |
| 2022 | 18,299 | 18,456 | 100.9 |  |
| 2023 | 15,979 | 25,071 | 156.9 |  |
| 2024 | 18,676 | 20,783 | 111.3 |  |
| 2025 | 15,933 | 20,533 | 128.9 |  |
| 2026 | 18,908 | 22,480 | 118.9 |  |

## 6. KPIs pending the models

| KPI | Source |
|---|---|
| Price index | Phase 4a: hedonic time-dummy index, Jan 2019 = 100 (docs/05 §2) |
| YoY price growth | Phase 4a: from the index |
| Gross rental yield | Phase 4a: agg_yield_quarter with the min-n rule (docs/05 §3) |
| AVM accuracy (MdAPE, ±10% / ±20%) | Phase 4b (docs/05 §1) |
| Max drawdown | Phase 4a: from the index |
| Negative-equity share | Phase 4c: stress grid (docs/05 §4) |
| Developer concentration (HHI) | Stretch: needs the DLD projects file (deferred) |
