# Report visuals (generated)

Generated from the PBIR files by `make pbi-inventory` (`powerbi/pbir.py`); `tests/test_powerbi_model.py` fails when it is stale. Positions are x, y, width, height on the 1280 × 720 canvas. Intent, decisions and checks: `powerbi/BUILD.md`.

## 1 Executive Overview

Interactions set to none: p1_Year → p1_value_by_month.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p1_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Executive] |  |  | Page title with this page's headline finding. |
| `p1_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p1_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p1_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p1_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p1_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p1_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p1_kpis` | cardVisual | 16, 116, 1036, 84 | Data: [Market Sales Value] as "Sales value", [Market Sales] as "Market sales", [Median Price per Sq M] as "Median AED / sq m", [Index YoY] as "Prices YoY (like for like)", [Off-Plan Share (Value)] as "Off-plan share (value)" |  |  | Five headline numbers for the selected year: sales value, number of market sales, median price per square metre, like-for-like price change, off-plan share of value. |
| `p1_mortgage` | cardVisual | 1060, 116, 204, 84 | Data: [Purchase Mortgage Share] as "Mortgage share (ready)" |  | Mortgage share (ready) / at least – matched loans only | Share of ready purchases matched to a same-day mortgage of the same unit: a lower bound (in 2025 between 28% matched and 48% for all ready-unit mortgages). |
| `p1_value_by_month` | lineChart | 16, 208, 820, 312 | Category: 'Date'[Month Start]; Y: [Market Sales Value] as "Sales value" | 'Date'[Is After Snapshot] in false | Market sales value by month, AED / All years; not filtered by Year | Line chart of monthly market sales value since 2004, with the 2008, 2014, 2020 and 2021 cycle points marked. Shows all years regardless of the Year slicer. |
| `p1_top_areas` | clusteredBarChart | 844, 208, 420, 312 | Category: 'Area'[Area]; Y: [Market Sales Value] as "Sales value" | top 10 'Area'[Area] by [Market Sales Value] | Top 10 areas by sales value | Bar chart of the ten areas with the highest sales value in the selected period. |
| `p1_insight_offplan` | textbox | 16, 528, 410, 152 |  |  |  | Insight: off-plan share of sales by count and by value. |
| `p1_insight_2026` | textbox | 434, 528, 410, 152 |  |  |  | Insight: the 2026 slowdown compared with 2025. |
| `p1_insight_2009` | textbox | 852, 528, 410, 152 |  |  |  | Insight: the 2009 registration backlog. |
| `p1_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 2 Financing & Market Mix

Interactions set to none: p2_Year → p2_ready_financed; p2_Year → p2_share; p2_Year → p2_rate; p2_Year → p2_per100; p2_Year → p2_mix.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p2_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Financing] |  |  | Page title with this page's headline finding. |
| `p2_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p2_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p2_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p2_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p2_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p2_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p2_kpis` | cardVisual | 16, 116, 1036, 84 | Data: [Ready Market Sales] as "Ready sales", [Purchase Mortgages] as "Matched mortgages", [New Mortgages per 100 Sales] as "New mortgages / 100 sales", [Off-Plan Share (Count)] as "Off-plan share (count)" |  |  | Financing headline numbers for the selected year: ready market sales, matched purchase mortgages, new mortgages per 100 market sales, off-plan share of sales. |
| `p2_mortgage` | cardVisual | 1060, 116, 204, 84 | Data: [Purchase Mortgage Share] as "Mortgage share (ready)" |  | Mortgage share (ready) / at least – matched loans only | Share of ready purchases matched to a same-day mortgage of the same unit: a lower bound (in 2025 between 28% matched and 48% for all ready-unit mortgages). |
| `p2_ready_financed` | columnChart | 16, 208, 404, 212 | Category: 'Date'[Month Start]; Y: [Purchase Mortgages] as "Matched mortgage", [Ready Sales Not Bank-Financed] as "Not bank-financed" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Ready sales: mortgage-financed or not / From 2010; not filtered by Year | Monthly ready sales split into those matched to a same-day purchase mortgage and those not bank-financed at registration. |
| `p2_share` | lineChart | 428, 208, 404, 212 | Category: 'Date'[Month Start]; Y: [Purchase Mortgage Share] as "Mortgage share (ready)" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Mortgage share of ready sales (at least) / Matched loans only; not filtered by Year | Line chart of the matched purchase-mortgage share of ready sales by month since 2010. |
| `p2_rate` | lineChart | 840, 208, 424, 212 | Category: 'Date'[Month Start]; Y: [Reference Rate] as "Rate" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | [Reference Rate Label] / Same time range as the mortgage share | Line chart of the reference interest rate by month since 2010, beside the mortgage share on the same time range. |
| `p2_per100` | lineChart | 16, 428, 404, 252 | Category: 'Date'[Year]; Y: [New Mortgages per 100 Sales] as "Per 100 sales" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | New mortgages per 100 market sales / Incl. refinancing; not filtered by Year | New mortgages per 100 market sales by year. |
| `p2_mix` | hundredPercentStackedColumnChart | 428, 428, 404, 252 | Category: 'Date'[Year]; Y: [Market Sales] as "Market sales"; Series: 'Ready Off-Plan'[Ready / Off-Plan] | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Off-plan vs ready share of sales / 2010-2026 (2026 partial); not filtered by Year | Share of market sales that were off-plan or ready, by year, 2010 to 2026. |
| `p2_offplan_areas` | clusteredBarChart | 840, 428, 424, 252 | Category: 'Area'[Area]; Y: [Off-Plan Share (Count)] as "Off-plan share" | top 7 'Area'[Area] by [Market Sales] | Off-plan share, 7 busiest areas | Off-plan share of sales in the seven areas with the most market sales. |
| `p2_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 3 Prices & Index

Interactions set to none: p3_Year → p3_maxdd; p3_Year → p3_vs_dld; p3_Year → p3_mix_shift; p3_Year → p3_drawdown.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p3_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Prices] |  |  | Page title with this page's headline finding. |
| `p3_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p3_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p3_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p3_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p3_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p3_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p3_IndexSegment` | slicer | 1066, 52, 198, 58 | Values: 'Price Index'[Segment] |  |  | Slicer: Index segment |
| `p3_kpis` | cardVisual | 16, 116, 1036, 84 | Data: [Index Value (Latest Complete)] as "Index (Jan 2019 = 100)", [Index YoY] as "Prices YoY", [Drawdown from Peak] as "Below previous peak", [Area-Weighted Price per Sq M (Homes)] as "AED / sq m (homes)" |  |  | Price headline numbers: the selected index segment's level, year-on-year change and distance below its previous peak at the latest complete month, and the area-weighted price per square metre of homes. |
| `p3_maxdd` | cardVisual | 1060, 116, 204, 84 | Data: [Max Drawdown] as "Deepest fall" |  | Deepest fall / Since 2011; all years | The deepest fall of the selected price index from a previous peak, over its whole history. |
| `p3_vs_dld` | lineChart | 16, 208, 404, 236 | Category: 'Date'[Month Start]; Y: [Index Value] as "Hedonic index", [DLD Index Value] as "DLD index (to May 2024)" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Like for like vs DLD's index (2019 = 100) / Ours leads by ~6 months; not filtered by Year | Line chart comparing this project's like-for-like price index with DLD's official index since 2011, both rebased to January 2019. |
| `p3_mix_shift` | lineChart | 428, 208, 404, 236 | Category: 'Date'[Month Start]; Y: [Index Value (Apartments)] as "Like for like", [Raw Median Rebased (Apartments)] as "Raw median" | 'Date'[Year] >= 2015L; 'Date'[Is After Snapshot] in false | Apartments: raw median vs like for like / 2023: +1% raw vs +17% like for like | Apartment price index against the raw median price per square metre, both rebased to January 2019: the gap is the mix shift. |
| `p3_drawdown` | areaChart | 16, 452, 404, 228 | Category: 'Date'[Month Start]; Y: [Index Drawdown] as "Below previous peak" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Fall from the previous peak / 2014-2020: -24% Dubai-wide; not filtered by Year | Drawdown of the selected price index from its running peak since 2011. |
| `p3_price_areas` | clusteredBarChart | 428, 452, 404, 228 | Category: 'Area'[Area]; Y: [Median Price per Sq M] as "Median AED / sq m" | top 6 'Area'[Area] by [Median Price per Sq M]; 'Property Type'[Usage Group] in 'Residential'; [Clean Sales] >= 20L | Highest median AED per sq m, top 6 areas / Residential; areas with 20+ clean sales | Bar chart of the six areas with the highest median price per square metre of residential sales (areas with fewer than 20 clean sales are left out). |
| `p3_bed_zone` | pivotTable | 840, 208, 424, 472 | Rows: 'Area'[Zone]; Columns: 'Bedrooms'[Bedrooms]; Values: [Median Price per Sq M (K)] as "Median AED / sq m" | 'Property Type'[Usage Group] in 'Residential'; 'Bedrooms'[Bedrooms] not in 'Unknown'; [Clean Sales] >= 20L | Median AED per sq m: zone × bedrooms / Residential; AED thousands; blank = under 20 sales | Table of the residential median price per square metre in thousands of AED by zone and bedrooms; blank cells have fewer than 20 sales. |
| `p3_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 4 Rental Yields

Interactions set to none: p4_Year → p4_trend.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p4_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Yields] |  |  | Page title with this page's headline finding. |
| `p4_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p4_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p4_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p4_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p4_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p4_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p4_kpis` | cardVisual | 16, 116, 1248, 84 | Data: [Gross Yield (Latest 4 Quarters)] as "Gross yield (last 4 quarters)", [New Market Rents] as "New rent contracts", [Area-Weighted New Rent per Sq M (Homes)] as "New rent / sq m / year (homes)" |  | Yields and rents / Gross: before service charges, vacancy and fees | Yield headline numbers: gross yield over the last four complete quarters, number of new market rent contracts in the selected year, and the area-weighted annual rent per square metre of new contracts for homes. |
| `p4_by_zone` | clusteredBarChart | 16, 208, 500, 472 | Category: 'Area'[Zone]; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse' | Gross yield by zone, last four quarters / Cells outside 2-15% left out (see yields.md) | Gross rental yield by zone for apartments and villas over the last four complete quarters, out-of-band cells left out. |
| `p4_area_yields` | clusteredBarChart | 524, 208, 360, 236 | Category: 'Area'[Area]; Y: [Gross Yield by Area (Latest 4 Quarters)] as "Gross yield" | top 7 'Area'[Area] by [Gross Yield by Area (Latest 4 Quarters)] | Highest area yields, top 7 | Bar chart of the seven areas with the highest gross yield, where both rents and sales reach 20 per cell. |
| `p4_yield_growth` | scatterChart | 892, 208, 372, 236 | Category: 'Area'[Zone]; X: [Index Growth 3Y (Zone)] as "Price growth, 3 years"; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Size: [Market Sales] as "Market sales" | 'Property Type'[Property Type] in 'Residential · Apartment'; top 8 'Area'[Zone] by [Market Sales] | Income vs growth: apartments / 8 zones with most sales; top right = both | Scatter of the eight zones with the most sales: three-year apartment price growth against gross yield, bubble size is sales. |
| `p4_trend` | lineChart | 524, 452, 360, 228 | Category: 'Date'[Quarter Start]; Y: [Gross Yield by Quarter] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse'; 'Date'[Year] >= 2012L; 'Date'[Is After Snapshot] in false | Yields: 2021 low, partly recovered / From 2012; not filtered by Year | Quarterly gross yield for apartments and villas since 2012. |
| `p4_rent_beds` | clusteredColumnChart | 892, 452, 372, 228 | Category: 'Bedrooms'[Bedrooms]; Y: [New Rent per Sq M] as "AED / sq m / year" | 'Property Type'[Property Type] in 'Residential · Apartment'; 'Bedrooms'[Bedrooms] not in 'Unknown' | New rent per sq m by bedrooms / Apartments, new contracts | Annual rent per square metre of new apartment contracts by number of bedrooms. |
| `p4_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 5 Valuation Model (AVM)

Page filters: 'AVM Score'[Model Set] in 'Test'.

Interactions set to none: p5_Year → p5_actual_vs_avm.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p5_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Valuation] |  |  | Page title with this page's headline finding. |
| `p5_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p5_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p5_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p5_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p5_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p5_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p5_Breakdown` | slicer | 1066, 52, 198, 58 | Values: 'AVM Performance'[Breakdown] | 'AVM Performance'[Breakdown] in 'Property Type', 'Reg Type', 'Price Band' |  | Slicer: Accuracy by |
| `p5_kpis` | cardVisual | 16, 116, 1248, 84 | Data: [AVM Test MdAPE] as "AVM median error", [AVM Test Hit Rate 10%] as "AVM within ±10%", [AVM Test Hit Rate 20%] as "AVM within ±20%", [AVM Test MdAPE (Baseline)] as "Comps median error", [AVM Test Hit Rate 10% (Baseline)] as "Comps within ±10%", [AVM MdAPE Gain vs Baseline] as "Error saved (pp)" |  | AVM accuracy (model card) / Test set 2025 to snapshot; ignores slicers | AVM accuracy on the 2025-26 out-of-time test set against the comparable-sales baseline: median absolute error and the shares valued within 10% and 20%. |
| `p5_by_segment` | clusteredBarChart | 16, 208, 404, 260 | Category: 'AVM Performance'[Segment]; Y: [AVM Segment MdAPE] as "Median error"; Series: 'AVM Performance'[Model Name] | 'AVM Performance'[Split] in 'Test'; 'AVM Performance'[Model] in 'lightgbm', 'comps' | Median error by segment: AVM vs comps | Median absolute percentage error by segment for the AVM and the comparable-sales baseline on the 2025-26 test set. |
| `p5_features` | clusteredBarChart | 428, 208, 404, 260 | Category: 'Feature Importance'[Feature Label]; Y: [Mean Abs SHAP] as "Mean |SHAP|" | 'Feature Importance'[Rank] <= 8L | What drives the valuation (mean |SHAP|) | Top eight features by mean absolute SHAP value, in log points of the predicted price. |
| `p5_actual_vs_avm` | lineChart | 840, 208, 424, 260 | Category: 'Date'[Month Start]; Y: [Median Sale Price (AVM Sample)] as "Median price", [Median AVM Value] as "Median AVM value" |  | Median price vs median AVM value / Out of sample, by month; not filtered by Year | Median sale price and median AVM value of out-of-sample sales by month. |
| `p5_gaps` | tableEx | 16, 476, 1000, 204 | Values: 'Area'[Area], 'Project'[Project], [Valued Sales] as "Valued sales", [Median Gap %] as "Median gap to AVM", [Flagged for Review] as "Flagged", [Flagged Share] as "Flagged share" | top 6 'Project'[Project] by [Flagged for Review] | Where sales sit furthest from the AVM: 6 projects with most flags | Table of the six projects with the most sales flagged for review, with their area and median gap to the AVM. |
| `p5_note` | textbox | 1024, 476, 240, 204 |  |  |  | Note on how to read the review flags. |
| `p5_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 6 Risk & Stress Test

Page filters: 'Forecast'[Target] in 'Price index'.

Interactions set to none: p6_Shock → p6_heatmap; p6_LTV → p6_heatmap.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p6_hdr_title` | cardVisual | 16, 4, 876, 44 | Data: [Title Stress] |  |  | Page title with this page's headline finding. |
| `p6_hdr_asof` | cardVisual | 900, 8, 364, 36 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p6_Year` | slicer | 16, 52, 150, 58 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p6_Area` | slicer | 174, 52, 260, 58 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p6_PropertyType` | slicer | 442, 52, 260, 58 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p6_Bedrooms` | slicer | 710, 52, 160, 58 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p6_ReadyOffPlan` | slicer | 878, 52, 180, 58 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p6_StressSegment` | slicer | 16, 116, 300, 56 | Values: 'Stress Grid'[Segment] | 'Stress Grid'[Segment Level] in 'Dubai', 'Type', 'Zone' |  | Slicer: Stress segment |
| `p6_ForecastSegment` | slicer | 1066, 52, 198, 58 | Values: 'Forecast'[Segment] |  |  | Slicer: Outlook segment |
| `p6_LTV` | slicer | 472, 116, 300, 56 | Values: 'LTV %'[LTV Label] |  |  | Slicer: Loan-to-value |
| `p6_ReplayDepth` | slicer | 780, 116, 240, 56 | Values: 'Replay Depth'[Replay Depth] |  |  | Slicer: 2014-2020 replay depth |
| `p6_Scenario` | slicer | 1028, 116, 236, 56 | Values: 'Forecast Scenario'[Scenario] |  |  | Slicer: Rate scenario (outlook) |
| `p6_Shock` | slicer | 324, 116, 140, 56 | Values: 'Price Shock %'[Price Shock %] |  |  | Slicer: Price shock % |
| `p6_kpis` | cardVisual | 16, 180, 1248, 72 | Data: [Negative Equity Share] as "In negative equity", [Negative Equity AED] as "Shortfall", [Stress Purchases] as "Purchases", [Negative Equity Share (CBUAE Cap)] as "At CBUAE cap", [Negative Equity Share (Registered Loans)] as "Registered loans", [Replay Negative Equity Share] as "2014-20 replay" |  | Stress result / Illustrative, not a regulatory stress test; loans at origination | Stress test results for the selected segment, price shock and loan-to-value: share of recent buyers in negative equity, the shortfall in AED, the number of purchases, the same share at the CBUAE cap and for registered loans, and under a repeat of the 2014 to 2020 fall. |
| `p6_heatmap` | pivotTable | 16, 256, 400, 424 | Rows: 'Price Shock %'[Price Shock %]; Columns: 'LTV %'[LTV Short]; Values: [Negative Equity Share] as "In negative equity" |  | Negative equity: shock × LTV / 85%* = UAE national first-home cap. Illustrative, not a regulatory stress test | Heatmap of the share of recent buyers in negative equity for price falls of 0 to 50% and loan-to-values of 50 to 85%. |
| `p6_areas` | clusteredBarChart | 424, 256, 400, 208 | Category: 'Area'[Area]; Y: [Negative Equity Share by Area] as "In negative equity" | top 5 'Area'[Area] by [Negative Equity Share by Area] | Most exposed areas (illustrative) / Selected shock and LTV | Bar chart of the five areas with the highest negative-equity share at the selected price shock and loan-to-value. |
| `p6_replay` | clusteredBarChart | 832, 256, 432, 208 | Category: 'Stress Replay'[Segment]; Y: [Replay Drawdown] as "2014-2020 fall" | bottom 5 'Stress Replay'[Segment] by [Replay Drawdown]; 'Stress Replay'[Used In Replay] in true | 2014→2020 fall, 5 deepest series / Zone series overstate it. Illustrative, not a regulatory stress test | Bar chart of the five index series with the deepest fall in the 2014 to 2020 downturn. |
| `p6_concentration` | clusteredBarChart | 424, 472, 400, 208 | Category: 'Project'[Master Project]; Y: [Master Project Share (Off-Plan)] as "Share of off-plan sales" | top 6 'Project'[Master Project] by [Off-Plan Market Sales (Lines)]; 'Project'[Master Project] not in 'Unknown' | [Title Concentration] | Top six master projects' shares of off-plan sales in the selected year, a proxy for developer concentration. |
| `p6_outlook` | lineChart | 832, 472, 432, 208 | Category: 'Forecast'[Month]; Y: [Forecast Actual] as "Actual", [Forecast Central] as "Forecast", [Forecast Lower 80] as "80% low", [Forecast Upper 80] as "80% high" | 'Forecast'[Month] >= datetime'2021-01-01T00:00:00' | [Title Outlook] / Dashed = 80% interval; a baseline, not a call | Price index history since 2021 and the 12-month forecast with its 80% interval for the selected rate scenario. |
| `p6_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |
