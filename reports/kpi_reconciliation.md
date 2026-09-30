# KPI reconciliation

Generated 2026-09-30 15:07 UTC by `quality/kpi_reconciliation.py` from database `dubai_property`. Regenerate with `make kpi` (after `make dbt`); `tests/test_kpi_reconciliation.py` fails if any check below fails.

These are the numbers the Power BI cards must match (docs/06 §3). Every KPI in docs/01 §4 that exists before the models is computed from silver (canonical, below) and again from the rpt views Power BI imports, at three grains (all time, year, month). **Data snapshot: 2026-09-25** (the latest transaction date; `rpt.report_info` "Data As Of"). Scope: 2004-01-01 to the snapshot; rent contracts starting after it are excluded. **All checks pass.**

Definitions (docs/01 §4): **market sales** = `is_market_sale` lines, AED counted once per deal (C16); **median AED per sq m** = all clean market sales (`is_clean_market_sale`); **area-weighted AED per sq m** = Σ AED / Σ sq m over clean sales of residential apartments and villas / townhouses whose area is within the class cap (1,000 / 3,000 sq m), because across property classes it would mix land, buildings and units; **mortgage share** = individual new mortgages / (new mortgages + market sales); portfolio mortgages are outside the share, counted once per deal; **off-plan share** = off-plan market sales / market sales; **new market rents** = `is_market_rent` (new, single-line, comparable, started by the snapshot); area-weighted rent = Σ annual rent / Σ sq m over new market rents of residential apartments and villas with a plausible area (C21 class caps).

## 1. All time

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | New mortgages | Mortgage share % | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 1,290,739 | 3,568.9 | 13,993 | 14,375 | 263,118 | 16.9 | 48.7 | 35.0 | 1,873 | 245.0 | 3,593,480 | 618 |

## 2. By year

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | New mortgages | Mortgage share % | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2004 | 2,794 | 11.7 | 2,153 | 1,609 | 1,159 | 29.3 | 0.4 | 0.2 | 0 | 0.0 | 0 |  |
| 2005 | 2,487 | 15.6 | 3,162 | 2,463 | 1,249 | 33.4 | 0.1 | 0.0 | 0 | 0.0 | 5 | 2,050 |
| 2006 | 2,621 | 18.6 | 3,229 | 3,318 | 1,640 | 38.5 | 0.3 | 0.2 | 0 | 0.0 | 4 | 286 |
| 2007 | 7,275 | 49.6 | 4,897 | 4,216 | 2,737 | 27.3 | 0.0 | 0.0 | 4 | 10.7 | 10 | 288 |
| 2008 | 21,324 | 103.3 | 6,275 | 6,817 | 5,218 | 19.7 | 0.1 | 0.0 | 1 | 1.9 | 7 | 252 |
| 2009 | 56,340 | 88.3 | 9,191 | 9,311 | 7,022 | 11.1 | 53.1 | 44.7 | 5 | 13.6 | 31 | 688 |
| 2010 | 30,185 | 57.2 | 9,443 | 9,329 | 7,311 | 19.5 | 33.7 | 29.5 | 4 | 4.6 | 10,680 | 559 |
| 2011 | 24,891 | 51.3 | 8,628 | 8,788 | 6,022 | 19.5 | 10.5 | 6.2 | 4 | 9.5 | 45,813 | 516 |
| 2012 | 32,546 | 67.1 | 9,129 | 8,487 | 5,250 | 13.9 | 11.7 | 9.6 | 8 | 9.9 | 106,874 | 480 |
| 2013 | 58,159 | 135.8 | 10,012 | 10,101 | 8,091 | 12.2 | 20.1 | 16.5 | 16 | 9.3 | 189,143 | 511 |
| 2014 | 50,163 | 128.9 | 11,158 | 11,557 | 8,088 | 13.9 | 27.2 | 18.1 | 17 | 2.4 | 201,738 | 591 |
| 2015 | 38,436 | 109.5 | 10,761 | 11,298 | 9,099 | 19.1 | 35.0 | 20.3 | 21 | 3.0 | 168,138 | 635 |
| 2016 | 37,742 | 92.4 | 10,459 | 11,709 | 10,079 | 21.1 | 41.5 | 26.8 | 72 | 16.3 | 158,291 | 637 |
| 2017 | 42,831 | 101.2 | 11,122 | 11,182 | 11,144 | 20.6 | 51.0 | 30.4 | 121 | 6.2 | 192,484 | 606 |
| 2018 | 29,712 | 66.1 | 11,556 | 11,154 | 9,962 | 25.1 | 50.0 | 29.6 | 143 | 8.1 | 219,730 | 564 |
| 2019 | 35,503 | 71.5 | 10,553 | 11,182 | 9,271 | 20.7 | 56.6 | 41.7 | 182 | 7.7 | 226,813 | 523 |
| 2020 | 32,138 | 65.5 | 9,994 | 10,160 | 10,288 | 24.2 | 45.5 | 31.1 | 104 | 3.0 | 237,223 | 461 |
| 2021 | 57,640 | 141.7 | 10,810 | 12,494 | 14,558 | 20.2 | 40.6 | 31.0 | 144 | 7.0 | 310,158 | 484 |
| 2022 | 93,615 | 255.8 | 13,089 | 15,670 | 16,578 | 15.0 | 45.2 | 35.8 | 151 | 80.8 | 317,588 | 563 |
| 2023 | 129,195 | 398.9 | 14,855 | 17,587 | 22,772 | 15.0 | 52.2 | 39.2 | 146 | 26.9 | 343,193 | 670 |
| 2024 | 175,437 | 506.0 | 16,521 | 18,225 | 31,247 | 15.1 | 61.1 | 44.3 | 178 | 7.4 | 335,891 | 783 |
| 2025 | 211,007 | 668.3 | 17,828 | 20,387 | 37,715 | 15.2 | 63.4 | 43.6 | 345 | 9.7 | 307,680 | 852 |
| 2026 | 118,698 | 364.8 | 18,573 | 20,798 | 26,618 | 18.3 | 68.7 | 49.5 | 207 | 6.7 | 221,986 | 857 |

## 3. Last 12 months

The 12 months to the snapshot (2026-09-25); mortgage share is defined by month (docs/01 §4). The snapshot month is partial.

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | New mortgages | Mortgage share % | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10 | 19,387 | 56.8 | 18,230 | 20,823 | 3,519 | 15.4 | 66.8 | 47.9 | 29 | 0.7 | 31,594 | 918 |
| 2025-11 | 18,433 | 62.7 | 18,974 | 21,422 | 3,244 | 15.0 | 68.6 | 44.9 | 16 | 0.5 | 27,785 | 892 |
| 2025-12 | 18,890 | 62.7 | 19,502 | 21,164 | 3,084 | 14.0 | 71.0 | 48.8 | 22 | 0.2 | 24,493 | 879 |
| 2026-01 | 16,593 | 68.8 | 19,446 | 21,220 | 3,210 | 16.2 | 65.3 | 40.6 | 38 | 0.5 | 27,958 | 888 |
| 2026-02 | 16,713 | 60.2 | 18,893 | 21,560 | 3,201 | 16.1 | 63.1 | 45.5 | 24 | 0.4 | 25,442 | 902 |
| 2026-03 | 13,589 | 43.3 | 18,588 | 21,422 | 2,667 | 16.4 | 70.6 | 54.7 | 20 | 0.7 | 19,352 | 854 |
| 2026-04 | 13,599 | 47.3 | 19,855 | 22,626 | 2,987 | 18.0 | 73.5 | 58.2 | 19 | 0.4 | 21,511 | 815 |
| 2026-05 | 9,872 | 27.7 | 18,033 | 20,722 | 2,147 | 17.9 | 72.1 | 56.6 | 13 | 0.3 | 20,618 | 822 |
| 2026-06 | 13,381 | 31.0 | 18,219 | 19,391 | 2,690 | 16.7 | 72.5 | 54.4 | 25 | 0.9 | 23,745 | 825 |
| 2026-07 | 13,499 | 33.2 | 18,328 | 19,819 | 3,588 | 21.0 | 69.4 | 47.4 | 32 | 0.6 | 26,578 | 826 |
| 2026-08 | 11,847 | 28.1 | 18,333 | 19,474 | 3,144 | 21.0 | 68.1 | 49.8 | 18 | 2.0 | 28,731 | 863 |
| 2026-09 | 9,605 | 25.2 | 18,174 | 19,378 | 2,984 | 23.7 | 66.1 | 47.3 | 18 | 0.9 | 28,051 | 890 |

## 4. Checks: silver vs rpt

Counts exact; AED within 0.5 AED per row summed and areas within 0.01 sq m per row (rpt rounds each row); medians within 1 AED. `rpt.area_month` has no median (cell medians can't be combined), and `rpt.rent_month` carries the rent metrics.

| rpt view | Values checked | Mismatches |
|---|---|---|
| rpt.transactions | 4,158 | 0 |
| rpt.area_month | 3,564 | 0 |
| rpt.rent_month | 786 | 0 |

## 5. Sanity check: residential apartments, area-weighted vs median AED per sq m

Must be within ±40% of each other in every year from 2010. A wider gap would mean plot- or building-sized areas are still leaking into the area-weighted sums (or a unit mix shift worth explaining).

| Year | Median AED / sq m | Area-weighted AED / sq m | Area-weighted / median % | Check |
|---|---|---|---|---|
| 2004 | 8,582 | 10,865 | 126.6 |  |
| 2005 | 9,409 | 11,259 | 119.7 |  |
| 2006 | 10,482 | 10,755 | 102.6 |  |
| 2007 | 5,796 | 6,785 | 117.1 |  |
| 2008 | 6,675 | 9,487 | 142.1 |  |
| 2009 | 9,018 | 10,530 | 116.8 |  |
| 2010 | 9,710 | 11,697 | 120.5 | pass |
| 2011 | 9,145 | 11,131 | 121.7 | pass |
| 2012 | 9,846 | 11,302 | 114.8 | pass |
| 2013 | 11,125 | 13,115 | 117.9 | pass |
| 2014 | 12,932 | 15,078 | 116.6 | pass |
| 2015 | 11,907 | 14,056 | 118.0 | pass |
| 2016 | 11,805 | 14,187 | 120.2 | pass |
| 2017 | 12,471 | 13,903 | 111.5 | pass |
| 2018 | 12,585 | 13,912 | 110.5 | pass |
| 2019 | 12,978 | 14,468 | 111.5 | pass |
| 2020 | 11,314 | 13,291 | 117.5 | pass |
| 2021 | 12,475 | 15,679 | 125.7 | pass |
| 2022 | 16,238 | 19,296 | 118.8 | pass |
| 2023 | 16,433 | 20,551 | 125.1 | pass |
| 2024 | 17,631 | 20,249 | 114.8 | pass |
| 2025 | 18,657 | 21,989 | 117.9 | pass |
| 2026 | 18,568 | 21,982 | 118.4 | pass |

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
