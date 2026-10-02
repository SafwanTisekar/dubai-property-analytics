# KPI reconciliation

Generated 2026-10-02 16:46 UTC by `quality/kpi_reconciliation.py` from database `dubai_property`. Regenerate with `make kpi` (after `make dbt`); `tests/test_kpi_reconciliation.py` fails if any check below fails.

These are the numbers the Power BI cards must match (docs/06 §3). Every KPI in docs/01 §4 that exists before the models is computed from silver (canonical, below) and again from the rpt views Power BI imports, at three grains (all time, year, month). **Data snapshot: 2026-09-25** (the latest transaction date; `rpt.report_info` "Data As Of"). Scope: 2004-01-01 to the snapshot; rent contracts starting after it are excluded. **All checks pass.**

Definitions (docs/01 §4): **market sales** = `is_market_sale` lines, AED counted once per deal (C16); **median AED per sq m** = all clean market sales (`is_clean_market_sale`); **area-weighted AED per sq m** = Σ AED / Σ sq m over clean sales of residential apartments and villas / townhouses whose area is within the class cap (1,000 / 3,000 sq m), because across property classes it would mix land, buildings and units; **purchase-mortgage share of ready sales** = ready market sales matched to a same-day purchase mortgage of the same unit (`has_purchase_mortgage`, a lower bound) / ready market sales; **new mortgages per 100 market sales** = individual new mortgages (incl. refinancing) x 100 / market sales, a secondary indicator; portfolio mortgages are outside both, counted once per deal; **off-plan share** = off-plan market sales / market sales; **new market rents** = `is_market_rent` (new, single-line, comparable, started by the snapshot); area-weighted rent = Σ annual rent / Σ sq m over new market rents of residential apartments and villas with a plausible area (C21 class caps).

## 1. All time

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 1,290,739 | 3,568.9 | 13,993 | 14,375 | 662,565 | 109,947 | 16.6 | 263,118 | 20.4 | 48.7 | 35.0 | 1,873 | 245.0 | 3,593,480 | 618 |

## 2. By year

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2004 | 2,794 | 11.7 | 2,153 | 1,609 | 2,782 | 139 | 5.0 | 1,159 | 41.5 | 0.4 | 0.2 | 0 | 0.0 | 0 |  |
| 2005 | 2,487 | 15.6 | 3,162 | 2,463 | 2,484 | 156 | 6.3 | 1,249 | 50.2 | 0.1 | 0.0 | 0 | 0.0 | 5 | 2,050 |
| 2006 | 2,621 | 18.6 | 3,229 | 3,318 | 2,614 | 291 | 11.1 | 1,640 | 62.6 | 0.3 | 0.2 | 0 | 0.0 | 4 | 286 |
| 2007 | 7,275 | 49.6 | 4,897 | 4,216 | 7,273 | 812 | 11.2 | 2,737 | 37.6 | 0.0 | 0.0 | 4 | 10.7 | 10 | 288 |
| 2008 | 21,324 | 103.3 | 6,275 | 6,817 | 21,311 | 1,751 | 8.2 | 5,218 | 24.5 | 0.1 | 0.0 | 1 | 1.9 | 7 | 252 |
| 2009 | 56,340 | 88.3 | 9,191 | 9,311 | 26,442 | 1,583 | 6.0 | 7,022 | 12.5 | 53.1 | 44.7 | 5 | 13.6 | 31 | 688 |
| 2010 | 30,185 | 57.2 | 9,443 | 9,329 | 20,005 | 1,779 | 8.9 | 7,311 | 24.2 | 33.7 | 29.5 | 4 | 4.6 | 10,680 | 559 |
| 2011 | 24,891 | 51.3 | 8,628 | 8,788 | 22,271 | 1,551 | 7.0 | 6,022 | 24.2 | 10.5 | 6.2 | 4 | 9.5 | 45,813 | 516 |
| 2012 | 32,546 | 67.1 | 9,129 | 8,487 | 28,745 | 1,877 | 6.5 | 5,250 | 16.1 | 11.7 | 9.6 | 8 | 9.9 | 106,874 | 480 |
| 2013 | 58,159 | 135.8 | 10,012 | 10,101 | 46,497 | 2,735 | 5.9 | 8,091 | 13.9 | 20.1 | 16.5 | 16 | 9.3 | 189,143 | 511 |
| 2014 | 50,163 | 128.9 | 11,158 | 11,557 | 36,516 | 2,240 | 6.1 | 8,088 | 16.1 | 27.2 | 18.1 | 17 | 2.4 | 201,738 | 591 |
| 2015 | 38,436 | 109.5 | 10,761 | 11,298 | 24,989 | 1,910 | 7.6 | 9,099 | 23.7 | 35.0 | 20.3 | 21 | 3.0 | 168,138 | 635 |
| 2016 | 37,742 | 92.4 | 10,459 | 11,709 | 22,086 | 2,330 | 10.5 | 10,079 | 26.7 | 41.5 | 26.8 | 72 | 16.3 | 158,291 | 637 |
| 2017 | 42,831 | 101.2 | 11,122 | 11,182 | 21,004 | 3,014 | 14.3 | 11,144 | 26.0 | 51.0 | 30.4 | 121 | 6.2 | 192,484 | 606 |
| 2018 | 29,712 | 66.1 | 11,556 | 11,154 | 14,853 | 2,591 | 17.4 | 9,962 | 33.5 | 50.0 | 29.6 | 143 | 8.1 | 219,730 | 564 |
| 2019 | 35,503 | 71.5 | 10,553 | 11,182 | 15,393 | 2,654 | 17.2 | 9,271 | 26.1 | 56.6 | 41.7 | 182 | 7.7 | 226,813 | 523 |
| 2020 | 32,138 | 65.5 | 9,994 | 10,160 | 17,521 | 3,439 | 19.6 | 10,288 | 32.0 | 45.5 | 31.1 | 104 | 3.0 | 237,223 | 461 |
| 2021 | 57,640 | 141.7 | 10,810 | 12,494 | 34,247 | 6,495 | 19.0 | 14,558 | 25.3 | 40.6 | 31.0 | 144 | 7.0 | 310,158 | 484 |
| 2022 | 93,615 | 255.8 | 13,089 | 15,670 | 51,280 | 8,550 | 16.7 | 16,578 | 17.7 | 45.2 | 35.8 | 151 | 80.8 | 317,588 | 563 |
| 2023 | 129,195 | 398.9 | 14,855 | 17,587 | 61,811 | 12,040 | 19.5 | 22,772 | 17.6 | 52.2 | 39.2 | 146 | 26.9 | 343,193 | 670 |
| 2024 | 175,437 | 506.0 | 16,521 | 18,225 | 68,172 | 17,947 | 26.3 | 31,247 | 17.8 | 61.1 | 44.3 | 178 | 7.4 | 335,891 | 783 |
| 2025 | 211,007 | 668.3 | 17,828 | 20,387 | 77,154 | 21,537 | 27.9 | 37,715 | 17.9 | 63.4 | 43.6 | 345 | 9.7 | 307,680 | 852 |
| 2026 | 118,698 | 364.8 | 18,573 | 20,798 | 37,115 | 12,526 | 33.7 | 26,618 | 22.4 | 68.7 | 49.5 | 207 | 6.7 | 221,986 | 857 |

## 3. Last 12 months

The 12 months to the snapshot (2026-09-25). The snapshot month is partial.

| Period | Market sales | Market sales AED bn | Median AED / sq m (all clean sales) | Area-weighted AED / sq m (res. apartments + villas) | Ready market sales | Purchase mortgages (matched) | Purchase-mortgage share of ready sales % | New mortgages | New mortgages per 100 market sales | Off-plan share % (count) | Off-plan share % (value) | Portfolio mortgage deals | Portfolio value AED bn | New market rents | Area-weighted new rent AED / sq m (res. apartments + villas) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10 | 19,387 | 56.8 | 18,230 | 20,823 | 6,437 | 2,005 | 31.1 | 3,519 | 18.2 | 66.8 | 47.9 | 29 | 0.7 | 31,594 | 918 |
| 2025-11 | 18,433 | 62.7 | 18,974 | 21,422 | 5,786 | 1,845 | 31.9 | 3,244 | 17.6 | 68.6 | 44.9 | 16 | 0.5 | 27,785 | 892 |
| 2025-12 | 18,890 | 62.7 | 19,502 | 21,164 | 5,486 | 1,731 | 31.6 | 3,084 | 16.3 | 71.0 | 48.8 | 22 | 0.2 | 24,493 | 879 |
| 2026-01 | 16,593 | 68.8 | 19,446 | 21,220 | 5,751 | 1,682 | 29.2 | 3,210 | 19.3 | 65.3 | 40.6 | 38 | 0.5 | 27,958 | 888 |
| 2026-02 | 16,713 | 60.2 | 18,893 | 21,560 | 6,160 | 1,734 | 28.1 | 3,201 | 19.2 | 63.1 | 45.5 | 24 | 0.4 | 25,442 | 902 |
| 2026-03 | 13,589 | 43.3 | 18,588 | 21,422 | 3,999 | 1,433 | 35.8 | 2,667 | 19.6 | 70.6 | 54.7 | 20 | 0.7 | 19,352 | 854 |
| 2026-04 | 13,599 | 47.3 | 19,855 | 22,626 | 3,606 | 1,367 | 37.9 | 2,987 | 22.0 | 73.5 | 58.2 | 19 | 0.4 | 21,511 | 815 |
| 2026-05 | 9,872 | 27.7 | 18,033 | 20,722 | 2,755 | 906 | 32.9 | 2,147 | 21.7 | 72.1 | 56.6 | 13 | 0.3 | 20,618 | 822 |
| 2026-06 | 13,381 | 31.0 | 18,219 | 19,391 | 3,685 | 1,168 | 31.7 | 2,690 | 20.1 | 72.5 | 54.4 | 25 | 0.9 | 23,745 | 825 |
| 2026-07 | 13,499 | 33.2 | 18,328 | 19,819 | 4,131 | 1,519 | 36.8 | 3,588 | 26.6 | 69.4 | 47.4 | 32 | 0.6 | 26,578 | 826 |
| 2026-08 | 11,847 | 28.1 | 18,333 | 19,474 | 3,776 | 1,440 | 38.1 | 3,144 | 26.5 | 68.1 | 49.8 | 18 | 2.0 | 28,731 | 863 |
| 2026-09 | 9,605 | 25.2 | 18,174 | 19,378 | 3,252 | 1,277 | 39.3 | 2,984 | 31.1 | 66.1 | 47.3 | 18 | 0.9 | 28,051 | 890 |

## 4. Checks: silver vs rpt

Counts exact; AED within 0.5 AED per row summed and areas within 0.01 sq m per row (rpt rounds each row); medians within 1 AED. `rpt.area_month` has no median (cell medians can't be combined), and `rpt.rent_month` carries the rent metrics.

| rpt view | Values checked | Mismatches |
|---|---|---|
| rpt.transactions | 4,752 | 0 |
| rpt.area_month | 4,158 | 0 |
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

## 6. Model KPIs

Computed by the Phase 4 models, not from silver, so they aren't reconciled above; §7 lists the card values from the rpt views.

| KPI | Source |
|---|---|
| Price index, YoY growth, max drawdown | rpt.price_index (Phase 4a): §7 cards |
| Gross rental yield | rpt.yield_quarter (Phase 4a, min-n both sides): §7 cards |
| AVM accuracy (MdAPE, ±10% / ±20%) | rpt.avm_performance / avm_score (4b): §7 cards |
| Negative-equity share | rpt.stress_grid (Phase 4c): §7 cards |
| 12-month outlook | rpt.forecast (Phase 4c): §7 cards |
| Developer concentration (HHI) | Deferred (needs the DLD projects file); master-project proxy in §7 |

## 7. Power BI card checklist

Set the filters, read the card, tick it. Every other slicer is cleared unless listed. The report opens on **Year = 2025** (the latest complete year; the snapshot year is partial). Values are as the measures' format strings display them; a last-digit difference is rounding, anything more is a bug. AED amounts are formatted "AED "#,0 in the model, so bn values assume the card's display units = Billions with 1 decimal (Auto would switch to Trillions on all-time totals). Measure definitions: `powerbi/DubaiProperty.SemanticModel/definition/tables/_Measures.tmdl`.

| Page | Card (measure) | Filters to set | Expected | Source |
|---|---|---|---|---|
| 1 Executive | Market Sales Value | Year = 2025 | AED 668.3bn | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Market Sales | Year = 2025 | 211,007 | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Median Price per Sq M | Year = 2025 | AED 17,828 | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Purchase Mortgage Share | Year = 2025 | 27.9% | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Off-Plan Share (Value) | Year = 2025 | 43.6% | kpi_reconciliation §1–2 (silver = rpt) |
| 2 Financing | Ready Market Sales | Year = 2025 | 77,154 | kpi_reconciliation §1–2 (silver = rpt) |
| 2 Financing | Purchase Mortgages | Year = 2025 | 21,537 | kpi_reconciliation §1–2 (silver = rpt) |
| 2 Financing | New Mortgages per 100 Sales | Year = 2025 | 17.9 | kpi_reconciliation §1–2 (silver = rpt) |
| 2 Financing | Off-Plan Share (Count) | Year = 2025 | 63.4% | kpi_reconciliation §1–2 (silver = rpt) |
| 2 Financing | Portfolio Mortgage Deals | Year = 2025 | 345 | kpi_reconciliation §1–2 (silver = rpt) |
| 3 Prices | Area-Weighted Price per Sq M (Homes) | Year = 2025 | AED 20,387 | kpi_reconciliation §1–2 (silver = rpt) |
| 4 Yields | New Market Rents | Year = 2025 | 307,680 | kpi_reconciliation §1–2 (silver = rpt) |
| 4 Yields | Area-Weighted New Rent per Sq M (Homes) | Year = 2025 | AED 852 | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Market Sales Value | no Year selected | AED 3,568.9bn | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Market Sales | no Year selected | 1,290,739 | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Median Price per Sq M | no Year selected | AED 13,993 | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Purchase Mortgage Share | no Year selected | 16.6% | kpi_reconciliation §1–2 (silver = rpt) |
| 1 Executive | Off-Plan Share (Value) | no Year selected | 35.0% | kpi_reconciliation §1–2 (silver = rpt) |

Model cards. Defaults: shock -20%, LTV 80%, Ready, scenario Rates flat, AVM page filtered to the test period. Min-n is 20: a blank card means the segment is below it.

| Page | Card (measure) | Filters to set | Expected | Source |
|---|---|---|---|---|
| 1 Executive | Index YoY | Year = 2025; index segment = Dubai (all residential) (Dec 2025) | +15.0% | rpt.price_index (latest complete month) |
| 1 Executive | Index YoY | no Year selected; index segment = Dubai (all residential) (Aug 2026) | +1.0% | rpt.price_index (latest complete month) |
| 3 Prices | Max Drawdown Split | strip under Below previous peak; index segment = Dubai (all residential) | Deepest since 2011 -23.6% | rpt.price_index (latest complete month) |
| 3 Prices | Index YoY | no Year selected; index segment = Apartments (Aug 2026) | -0.2% | rpt.price_index (latest complete month) |
| 3 Prices | Index Value (Latest Complete) | no Year selected; index segment = Apartments (Aug 2026) | 176.3 | rpt.price_index (latest complete month) |
| 3 Prices | Drawdown from Peak | no Year selected; index segment = Apartments (Aug 2026) | -5.0% | rpt.price_index (latest complete month) |
| 3 Prices | Max Drawdown Split | strip under Below previous peak; index segment = Apartments | Deepest since 2011 -25.4% | rpt.price_index (latest complete month) |
| 3 Prices | Index YoY | no Year selected; index segment = Villas / Townhouses (Aug 2026) | +4.9% | rpt.price_index (latest complete month) |
| 3 Prices | Index Value (Latest Complete) | no Year selected; index segment = Villas / Townhouses (Aug 2026) | 220.8 | rpt.price_index (latest complete month) |
| 3 Prices | Drawdown from Peak | no Year selected; index segment = Villas / Townhouses (Aug 2026) | -9.3% | rpt.price_index (latest complete month) |
| 3 Prices | Max Drawdown Split | strip under Below previous peak; index segment = Villas / Townhouses | Deepest since 2011 -30.4% | rpt.price_index (latest complete month) |
| 4 Yields | Gross Yield (Latest 4 Quarters) | Property Type = Residential · Apartment; 2025-07 to 2026-04 quarter starts | 7.1% | rpt.yield_quarter, zone cells, sales-weighted (yields.md) |
| 4 Yields | Gross Yield (Latest 4 Quarters) | Property Type = Residential · Villa / Townhouse; 2025-07 to 2026-04 quarter starts | 5.2% | rpt.yield_quarter, zone cells, sales-weighted (yields.md) |
| 5 Valuation | AVM Test MdAPE | none | 6.83% | rpt.avm_performance, LightGBM, Test / Overall |
| 5 Valuation | AVM Test Hit Rate 10% | none | 65.0% | rpt.avm_performance, LightGBM, Test / Overall |
| 5 Valuation | AVM Test Hit Rate 20% | none | 88.2% | rpt.avm_performance, LightGBM, Test / Overall |
| 5 Valuation | AVM Test MdAPE (Baseline) | none | 9.90% | rpt.avm_performance, Comparable sales (baseline), Test / Overall |
| 5 Valuation | AVM Test Hit Rate 10% (Baseline) | none | 50.3% | rpt.avm_performance, Comparable sales (baseline), Test / Overall |
| 5 Valuation | AVM Test Hit Rate 20% (Baseline) | none | 76.1% | rpt.avm_performance, Comparable sales (baseline), Test / Overall |
| 5 Valuation | Valued Sales | Model Set = Test (page filter); other slicers clear | 275,702 | rpt.avm_score, Model Set = Test |
| 5 Valuation | AVM MdAPE (Interactive) | Model Set = Test (page filter); other slicers clear | 6.83% | rpt.avm_score, Model Set = Test |
| 5 Valuation | Flagged Share | Model Set = Test (page filter); other slicers clear | 6.8% | rpt.avm_score, Model Set = Test |
| 6 Risk | Negative Equity Share | Stress segment = Dubai (all residential); Ready; Shock -10; LTV 80 | 0.0% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Dubai (all residential); Ready; Shock -20; LTV 80 | 22.1% | rpt.stress_grid |
| 6 Risk | Negative Equity AED | Stress segment = Dubai (all residential); Ready; Shock -20; LTV 80 | AED 1.9bn | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Dubai (all residential); Ready; Shock -30; LTV 80 | 71.9% | rpt.stress_grid |
| 6 Risk | Replay Negative Equity Share | Stress segment = Dubai (all residential); Ready; LTV 80; tile (Dubai-wide) | 41.9% | rpt.stress_grid |
| 6 Risk | Replay Split | Stress segment = Dubai (all residential); Ready; LTV 80; strip: own series (upper) | Own series (upper) 78% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Apartments; Ready; Shock -10; LTV 80 | 0.0% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Apartments; Ready; Shock -20; LTV 80 | 22.4% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Apartments; Ready; Shock -30; LTV 80 | 73.2% | rpt.stress_grid |
| 6 Risk | Replay Negative Equity Share | Stress segment = Apartments; Ready; LTV 80; tile (Dubai-wide) | 43.1% | rpt.stress_grid |
| 6 Risk | Replay Split | Stress segment = Apartments; Ready; LTV 80; strip: own series (upper) | Own series (upper) 80% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Villas / Townhouses; Ready; Shock -10; LTV 80 | 0.0% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Villas / Townhouses; Ready; Shock -20; LTV 80 | 19.7% | rpt.stress_grid |
| 6 Risk | Negative Equity Share | Stress segment = Villas / Townhouses; Ready; Shock -30; LTV 80 | 63.7% | rpt.stress_grid |
| 6 Risk | Replay Negative Equity Share | Stress segment = Villas / Townhouses; Ready; LTV 80; tile (Dubai-wide) | 34.1% | rpt.stress_grid |
| 6 Risk | Replay Split | Stress segment = Villas / Townhouses; Ready; LTV 80; strip: own series (upper) | Own series (upper) 64% | rpt.stress_grid |
| 6 Risk | Negative Equity Share (CBUAE Cap) | Stress segment = Dubai (all residential); Ready; Shock -20 | 20.7% (20.69%) | rpt.stress_grid |
| 6 Risk | Negative Equity Share (Registered Loans) | Stress segment = Dubai (all residential); Ready; Shock -20 | 20.7% (20.73%) | rpt.stress_grid |
| 6 Risk | Negative Equity Share (CBUAE Cap) | Stress segment = Apartments; Ready; Shock -20 | 21.7% (21.70%) | rpt.stress_grid |
| 6 Risk | Negative Equity Share (Registered Loans) | Stress segment = Apartments; Ready; Shock -20 | 22.8% (22.80%) | rpt.stress_grid |
| 6 Risk | Forecast 12M Change | Forecast segment = Dubai (all residential) (default); Scenario = Rates flat (default) | +4.6% | rpt.forecast |
| 6 Risk | Forecast Split | strip under Price outlook; Forecast segment = Dubai (all residential) (default); Scenario = Rates flat (default) | 80%: -5.1% to +15.4% | rpt.forecast (forecast.md) |
| 6 Risk | Top 10 Master Project Share (Off-Plan) | Year = 2025 | 52.8% | rpt.transactions + rpt.dim_project (proxy, not developer HHI) |
| 6 Risk | Master Project HHI (Off-Plan) | Year = 2025 | 399 | rpt.transactions + rpt.dim_project (proxy, not developer HHI) |
