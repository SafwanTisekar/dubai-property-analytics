# Report visuals (generated)

Generated from the PBIR files by `make pbi-inventory` (`powerbi/pbir.py`); `tests/test_powerbi_model.py` fails when it is stale. Positions are x, y, width, height on the 1280 × 720 canvas. Intent, decisions and checks: `powerbi/BUILD.md`.

## Introduction

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p0Intro_frame_panel` | textbox | 182, 12, 1086, 696 |  |  |  | Content panel (decorative). |
| `p0Intro_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p0Intro_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p0Intro_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p0Intro_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: INTRODUCTION TO THE REPORT. |
| `p0Intro_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p0Intro_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset all filters on this page. |
| `p0Intro_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p0Intro_what` | textbox | 198, 60, 520, 116 |  |  |  | What this report is. |
| `p0Intro_why` | textbox | 198, 186, 520, 140 |  |  |  | Why it matters. |
| `p0Intro_data` | cardVisual | 198, 336, 520, 132 | Data: [Guide Data Line] |  | Where the data comes from | Where the data comes from: the number of sales and rent contracts and the snapshot date. |
| `p0Intro_questions` | textbox | 198, 478, 520, 198 |  |  |  | The questions the report answers. |
| `p0Intro_use` | textbox | 728, 60, 530, 214 |  |  |  | How to use the report. |
| `p0Intro_pages` | textbox | 728, 284, 530, 250 |  |  |  | One line per page of the report. |
| `p0Intro_good` | textbox | 728, 544, 530, 132 |  |  |  | Good to know. |
| `p0Intro_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## Key terms

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p0Terms_frame_panel` | textbox | 182, 12, 1086, 696 |  |  |  | Content panel (decorative). |
| `p0Terms_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p0Terms_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p0Terms_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p0Terms_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: KEY TERMS & METHODS. |
| `p0Terms_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p0Terms_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset all filters on this page. |
| `p0Terms_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p0Terms_h_terms` | textbox | 198, 60, 1060, 22 |  |  |  | Section heading: Property terms. |
| `p0Terms_term1` | textbox | 198, 84, 346, 124 |  |  |  | Term: Off-plan and ready. Off-plan means buying a home before it is built, usually paying the developer in stages. Ready means it is finished and you can move in. Example: a flat bought in 2025 for handover in 2028 is off-plan. |
| `p0Terms_term2` | textbox | 554, 84, 346, 124 |  |  |  | Term: AED per sq m. The price divided by the floor area. It lets you compare homes of different sizes. Example: a 70 sq m flat sold for AED 1,400,000 costs AED 20,000 per sq m. |
| `p0Terms_term3` | textbox | 910, 84, 346, 124 |  |  |  | Term: Mortgage. A bank loan to buy a home. The home is the bank's security: if the loan is not repaid, the bank can sell it. Example: a buyer pays AED 300,000 and borrows AED 1,200,000 for a AED 1,500,000 home. |
| `p0Terms_term4` | textbox | 198, 216, 346, 124 |  |  |  | Term: Loan-to-value (LTV). The loan as a share of the home's value. The higher it is, the smaller the buyer's cushion. Example: AED 1,200,000 borrowed on a AED 1,500,000 home is an LTV of 80%. |
| `p0Terms_term5` | textbox | 554, 216, 346, 124 |  |  |  | Term: Gross rental yield. A year's rent as a share of the price, before costs such as service charges and empty months. Example: AED 90,000 a year of rent on a AED 1,500,000 flat is a 6% gross yield. |
| `p0Terms_term6` | textbox | 910, 216, 346, 124 |  |  |  | Term: Negative equity. When a home is worth less than the loan on it. Selling it would not repay the bank in full. Example: bought for AED 1,500,000 with a AED 1,200,000 loan, now worth AED 1,100,000: AED 100,000 short. |
| `p0Terms_h_models` | textbox | 198, 348, 1060, 22 |  |  |  | Section heading: How the four models work. |
| `p0Terms_model1` | textbox | 198, 372, 257, 120 |  |  |  | Model: Price index: a fixed shopping basket. Instead of averaging whatever sold this month, it compares similar homes over time. Prices don't look higher just because more expensive homes happened to sell. |
| `p0Terms_model1_live` | cardVisual | 198, 498, 257, 112 | Data: [Guide Index Line] |  | From the data | Live example for Price index: a fixed shopping basket, from the data. |
| `p0Terms_model2` | textbox | 465, 372, 257, 120 |  |  |  | Model: AVM: an automated valuer. It learned how size, location, bedrooms and recent nearby prices relate to price, then estimates what a home is worth. |
| `p0Terms_model2_live` | cardVisual | 465, 498, 257, 112 | Data: [Guide AVM Line] |  | From the data | Live example for AVM: an automated valuer, from the data. |
| `p0Terms_model3` | textbox | 732, 372, 257, 120 |  |  |  | Model: Stress test: a what-if calculator. It applies a price fall of X% to every recent purchase and counts who would owe more than the home is worth. It is illustrative, not a regulatory test. |
| `p0Terms_model3_live` | cardVisual | 732, 498, 257, 112 | Data: [Guide Stress Line] |  | From the data | Live example for Stress test: a what-if calculator, from the data. |
| `p0Terms_model4` | textbox | 999, 372, 257, 120 |  |  |  | Model: Forecast: a baseline with a range. It extends past patterns over the next 12 months. It is not a promise, and the range matters as much as the central line. |
| `p0Terms_model4_live` | cardVisual | 999, 498, 257, 112 | Data: [Guide Forecast Line] |  | From the data | Live example for Forecast: a baseline with a range, from the data. |
| `p0Terms_limits` | textbox | 198, 618, 1060, 58 |  |  |  | What this can't tell you. |
| `p0Terms_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 1 Executive

Interactions set to none: p1_Year → p1_value_by_month.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p1_frame_panel` | textbox | 182, 12, 1086, 696 |  |  |  | Content panel (decorative). |
| `p1_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p1_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p1_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p1_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: EXECUTIVE OVERVIEW DASHBOARD. |
| `p1_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p1_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset all filters on this page. |
| `p1_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p1_Year` | slicer | 198, 60, 150, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p1_Area` | slicer | 358, 60, 250, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p1_PropertyType` | slicer | 618, 60, 250, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p1_Bedrooms` | slicer | 878, 60, 170, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p1_ReadyOffPlan` | slicer | 1058, 60, 196, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p1_h_activity` | textbox | 198, 124, 600, 22 |  |  |  | Section heading: Market activity. |
| `p1_t1_kpi` | cardVisual | 198, 148, 168, 74 | Data: [Market Sales Value] as "Sales value" |  |  | KPI: Sales value for the selected filters, with a split underneath. |
| `p1_t1_strip` | cardVisual | 198, 222, 168, 26 | Data: [Sales Value Split] |  |  | Split of Sales value. |
| `p1_t2_kpi` | cardVisual | 376, 148, 168, 74 | Data: [Market Sales] as "Market sales" |  |  | KPI: Market sales for the selected filters, with a split underneath. |
| `p1_t2_strip` | cardVisual | 376, 222, 168, 26 | Data: [Market Sales Split] |  |  | Split of Market sales. |
| `p1_t3_kpi` | cardVisual | 554, 148, 168, 74 | Data: [Median Price per Sq M] as "Median AED / sq m" |  |  | KPI: Median AED / sq m for the selected filters, with a split underneath. |
| `p1_t3_strip` | cardVisual | 554, 222, 168, 26 | Data: [Median Price Split] |  |  | Split of Median AED / sq m. |
| `p1_t4_kpi` | cardVisual | 732, 148, 168, 74 | Data: [Index YoY] as "Prices YoY (like for like)" |  |  | KPI: Prices YoY (like for like) for the selected filters, with a split underneath. |
| `p1_t4_strip` | cardVisual | 732, 222, 168, 26 | Data: [Index YoY Split] |  |  | Split of Prices YoY (like for like). |
| `p1_t5_kpi` | cardVisual | 910, 148, 168, 74 | Data: [Off-Plan Share (Value)] as "Off-plan share (value)" |  |  | KPI: Off-plan share (value) for the selected filters, with a split underneath. |
| `p1_t5_strip` | cardVisual | 910, 222, 168, 26 | Data: [Off-Plan Share Split] |  |  | Split of Off-plan share (value). |
| `p1_t6_kpi` | cardVisual | 1088, 148, 168, 74 | Data: [Purchase Mortgage Share] as "Mortgage share (ready, at least)" |  |  | KPI: Mortgage share (ready, at least) for the selected filters, with a split underneath. |
| `p1_t6_strip` | cardVisual | 1088, 222, 168, 26 | Data: [Mortgage Share Split] |  |  | Split of Mortgage share (ready, at least). |
| `p1_h_cycles` | textbox | 198, 258, 620, 22 |  |  |  | Section heading: Market cycles. |
| `p1_h_where` | textbox | 828, 258, 430, 22 |  |  |  | Section heading: Where value concentrates. |
| `p1_value_by_month` | lineChart | 198, 282, 620, 252 | Category: 'Date'[Month Start]; Y: [Market Sales Value] as "Sales value" | 'Date'[Is After Snapshot] in false | Market sales value by month, AED / All years; not filtered by Year | Line chart of monthly market sales value since 2004, with the 2008, 2014, 2020 and 2021 cycle points marked. Shows all years regardless of the Year slicer. |
| `p1_top_areas` | clusteredBarChart | 828, 282, 430, 252 | Category: 'Area'[Area]; Y: [Market Sales Value] as "Sales value" | top 7 'Area'[Area] by [Market Sales Value] | Top 7 areas by sales value | Bar chart of the seven areas with the highest sales value in the selected period. |
| `p1_h_stands` | textbox | 198, 542, 600, 22 |  |  |  | Section heading: What stands out. |
| `p1_insight_offplan` | cardVisual | 198, 566, 346, 110 | Data: [Insight Off-Plan] |  | Off-plan: most sales, not most value | Insight: off-plan share of sales by number and by value in the last complete year. |
| `p1_insight_ytd` | cardVisual | 554, 566, 346, 110 | Data: [Insight Year to Date] |  | This year so far | Insight: this year's market sales so far against the same months last year. |
| `p1_insight_2009` | textbox | 910, 566, 346, 110 |  |  |  | Insight: the 2009 registration backlog. |
| `p1_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 2 Financing

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
| `p2_kpis` | cardVisual | 16, 116, 1036, 100 | Data: [Ready Market Sales] as "Ready sales", [Purchase Mortgages] as "Matched mortgages", [New Mortgages per 100 Sales] as "New mortgages / 100 sales", [Off-Plan Share (Count)] as "Off-plan share (count)" |  |  | Financing headline numbers for the selected year: ready market sales, matched purchase mortgages, new mortgages per 100 market sales, off-plan share of sales. |
| `p2_mortgage` | cardVisual | 1060, 116, 204, 100 | Data: [Purchase Mortgage Share] as "Mortgage share (ready, at least)" |  |  | Share of ready purchases matched to a same-day mortgage of the same unit: a lower bound, matched loans only (in 2025 between 28% matched and 48% for all ready-unit mortgages). |
| `p2_ready_financed` | columnChart | 16, 224, 404, 220 | Category: 'Date'[Month Start]; Y: [Purchase Mortgages] as "Matched mortgage", [Ready Sales Not Bank-Financed] as "Not bank-financed" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Ready sales: mortgage-financed or not / From 2010; not filtered by Year | Monthly ready sales split into those matched to a same-day purchase mortgage and those not bank-financed at registration. |
| `p2_share` | lineChart | 428, 224, 404, 220 | Category: 'Date'[Month Start]; Y: [Purchase Mortgage Share] as "Mortgage share (ready)" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Mortgage share of ready sales (at least) / Matched loans only; not filtered by Year | Line chart of the matched purchase-mortgage share of ready sales by month since 2010. |
| `p2_rate` | lineChart | 840, 224, 424, 220 | Category: 'Date'[Month Start]; Y: [Reference Rate] as "Rate" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | [Reference Rate Label] / Same time range as the mortgage share | Line chart of the reference interest rate by month since 2010, beside the mortgage share on the same time range. |
| `p2_per100` | lineChart | 16, 452, 404, 228 | Category: 'Date'[Year]; Y: [New Mortgages per 100 Sales] as "Per 100 sales" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | New mortgages per 100 market sales / Incl. refinancing; not filtered by Year | New mortgages per 100 market sales by year. |
| `p2_mix` | hundredPercentStackedColumnChart | 428, 452, 404, 228 | Category: 'Date'[Year]; Y: [Market Sales] as "Market sales"; Series: 'Ready Off-Plan'[Ready / Off-Plan] | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Off-plan vs ready share of sales / 2010-2026 (2026 partial); not filtered by Year | Share of market sales that were off-plan or ready, by year, 2010 to 2026. |
| `p2_offplan_areas` | clusteredBarChart | 840, 452, 424, 228 | Category: 'Area'[Area]; Y: [Off-Plan Share (Count)] as "Off-plan share" | top 6 'Area'[Area] by [Market Sales] | Off-plan share, 6 busiest areas | Off-plan share of sales in the six areas with the most market sales. |
| `p2_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 3 Prices

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
| `p3_kpis` | cardVisual | 16, 116, 1036, 100 | Data: [Index Value (Latest Complete)] as "Index (Jan 2019 = 100)", [Index YoY] as "Prices YoY", [Drawdown from Peak] as "Below previous peak", [Area-Weighted Price per Sq M (Homes)] as "AED / sq m (homes)" |  |  | Price headline numbers: the selected index segment's level, year-on-year change and distance below its previous peak at the latest complete month, and the area-weighted price per square metre of homes. |
| `p3_maxdd` | cardVisual | 1060, 116, 204, 100 | Data: [Max Drawdown] as "Deepest fall since 2011" |  |  | The deepest fall of the selected price index from a previous peak since 2011, over its whole history (not filtered by Year). |
| `p3_vs_dld` | lineChart | 16, 224, 380, 228 | Category: 'Date'[Month Start]; Y: [Index Value] as "Hedonic index", [DLD Index Value] as "DLD index (to May 2024)" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Like for like vs DLD's index (2019 = 100) / Ours leads by ~6 months; not filtered by Year | Line chart comparing this project's like-for-like price index with DLD's official index since 2011, both rebased to January 2019. |
| `p3_mix_shift` | lineChart | 404, 224, 380, 228 | Category: 'Date'[Month Start]; Y: [Index Value (Apartments)] as "Like for like", [Raw Median Rebased (Apartments)] as "Raw median" | 'Date'[Year] >= 2015L; 'Date'[Is After Snapshot] in false | Apartments: raw median vs like for like | Apartment price index against the raw median price per square metre, both rebased to January 2019: the gap is the mix shift. |
| `p3_drawdown` | areaChart | 16, 460, 380, 220 | Category: 'Date'[Month Start]; Y: [Index Drawdown] as "Below previous peak" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Fall from the previous peak / 2014-2020: -24% Dubai-wide; not filtered by Year | Drawdown of the selected price index from its running peak since 2011. |
| `p3_price_areas` | clusteredBarChart | 404, 460, 380, 220 | Category: 'Area'[Area]; Y: [Median Price per Sq M] as "Median AED / sq m" | top 6 'Area'[Area] by [Median Price per Sq M]; 'Property Type'[Usage Group] in 'Residential'; [Clean Sales] >= 20L | Top 6 areas, median AED / sq m (residential) | Bar chart of the six areas with the highest median price per square metre of residential sales (areas with fewer than 20 clean sales are left out). |
| `p3_bed_zone` | pivotTable | 792, 224, 472, 456 | Rows: 'Area'[Zone]; Columns: 'Bedrooms'[Bedrooms]; Values: [Median Price per Sq M (K)] as "Median AED / sq m" | 'Property Type'[Usage Group] in 'Residential'; 'Bedrooms'[Bedrooms] in 'Studio', '1 BR', '2 BR', '3 BR', '4 BR'; [Clean Sales] >= 20L | Median AED / sq m (K), zone × Studio–4 BR, residential | Table of the residential median price per square metre in thousands of AED by zone, studios to four bedrooms; blank cells have fewer than 20 sales. |
| `p3_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 4 Yields

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
| `p4_kpis` | cardVisual | 16, 116, 1248, 84 | Data: [Gross Yield (Latest 4 Quarters)] as "Gross yield, last 4 quarters (before costs)", [New Market Rents] as "New rent contracts", [Area-Weighted New Rent per Sq M (Homes)] as "New rent / sq m / year (homes)" |  |  | Yield headline numbers: gross yield over the last four complete quarters (before service charges, vacancy and fees), number of new market rent contracts in the selected year, and the area-weighted annual rent per square metre of new contracts for homes. |
| `p4_by_zone` | clusteredBarChart | 16, 208, 500, 472 | Category: 'Area'[Zone]; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse' | Gross yield by zone, last four quarters / Cells outside 2-15% left out (see yields.md) | Gross rental yield by zone for apartments and villas over the last four complete quarters, out-of-band cells left out. |
| `p4_area_yields` | clusteredBarChart | 524, 208, 360, 236 | Category: 'Area'[Area]; Y: [Gross Yield by Area (Latest 4 Quarters)] as "Gross yield" | top 6 'Area'[Area] by [Gross Yield by Area (Latest 4 Quarters)] | Highest area yields, top 6 | Bar chart of the six areas with the highest gross yield, where both rents and sales reach 20 per cell. |
| `p4_yield_growth` | scatterChart | 892, 208, 372, 236 | Category: 'Area'[Zone]; X: [Index Growth 3Y (Zone)] as "Price growth, 3 years"; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Size: [Market Sales] as "Market sales" | 'Property Type'[Property Type] in 'Residential · Apartment'; top 8 'Area'[Zone] by [Market Sales] | Income vs growth: apartments / 8 zones with most sales; top right = both | Scatter of the eight zones with the most sales: three-year apartment price growth against gross yield, bubble size is sales. |
| `p4_trend` | lineChart | 524, 452, 360, 228 | Category: 'Date'[Quarter Start]; Y: [Gross Yield by Quarter] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse'; 'Date'[Year] >= 2012L; 'Date'[Is After Snapshot] in false | Yields: 2021 low, partly recovered / From 2012; not filtered by Year | Quarterly gross yield for apartments and villas since 2012. |
| `p4_rent_beds` | clusteredColumnChart | 892, 452, 372, 228 | Category: 'Bedrooms'[Bedrooms]; Y: [New Rent per Sq M] as "AED / sq m / year" | 'Property Type'[Property Type] in 'Residential · Apartment'; 'Bedrooms'[Bedrooms] not in 'Unknown' | New rent per sq m by bedrooms / Apartments, new contracts | Annual rent per square metre of new apartment contracts by number of bedrooms. |
| `p4_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 5 Valuation

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
| `p5_Breakdown` | slicer | 1066, 52, 198, 58 | Values: 'AVM Performance'[Breakdown] | 'AVM Performance'[Breakdown] in 'Property Type (same sales)', 'Reg Type (same sales)' |  | Slicer: Accuracy by |
| `p5_kpis` | cardVisual | 16, 116, 1248, 84 | Data: [AVM Test MdAPE] as "AVM median error (test)", [AVM Test Hit Rate 10%] as "AVM within ±10%", [AVM Test Hit Rate 20%] as "AVM within ±20%", [AVM Test MdAPE (Baseline)] as "Comps median error", [AVM Test Hit Rate 10% (Baseline)] as "Comps within ±10%", [AVM MdAPE Gain vs Baseline] as "Error saved (pp)" |  |  | AVM accuracy on the 2025-26 out-of-time test set against the comparable-sales baseline (the model card's numbers; not filtered by slicers): median absolute error and the shares valued within 10% and 20%. |
| `p5_by_segment` | clusteredBarChart | 16, 208, 404, 232 | Category: 'AVM Performance'[Segment]; Y: [AVM Segment MdAPE] as "Median error"; Series: 'AVM Performance'[Model Name] | 'AVM Performance'[Split] in 'Test'; 'AVM Performance'[Model] in 'lightgbm', 'comps' | Median error by segment: AVM vs comps / Same sales for both models (model card) | Median absolute percentage error by segment for the AVM and the comparable-sales baseline on the 2025-26 test sales both can value (the model card's head-to-head). |
| `p5_features` | clusteredBarChart | 428, 208, 404, 232 | Category: 'Feature Importance'[Feature Label]; Y: [Mean Abs SHAP] as "Mean |SHAP|" | 'Feature Importance'[Rank] <= 6L | Top 6 drivers of the valuation (mean |SHAP|) | Top six features by mean absolute SHAP value, in log points of the predicted price. |
| `p5_actual_vs_avm` | lineChart | 840, 208, 424, 232 | Category: 'Date'[Month Start]; Y: [Median Sale Price (AVM Sample)] as "Median price", [Median AVM Value] as "Median AVM value" |  | Median price vs median AVM value / Out of sample, by month; not filtered by Year | Median sale price and median AVM value of out-of-sample sales by month. |
| `p5_gaps` | tableEx | 16, 448, 1000, 232 | Values: 'Area'[Area], 'Project'[Project], [Valued Sales] as "Valued sales", [Median Gap %] as "Median gap to AVM", [Flagged for Review] as "Flagged", [Flagged Share] as "Flagged share" | top 4 'Project'[Project] by [Flagged for Review]; 'Project'[Project] not in 'Unknown' | Where sales sit furthest from the AVM: 4 projects with most flags | Table of the four projects with the most sales flagged for review, with their area and median gap to the AVM. |
| `p5_note` | textbox | 1024, 448, 240, 232 |  |  |  | Note on how to read the review flags. |
| `p5_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 6 Risk

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
| `p6_kpis` | cardVisual | 16, 180, 1248, 80 | Data: [Negative Equity Share] as "Negative equity (illustrative)", [Negative Equity AED] as "Shortfall", [Stress Purchases] as "Purchases", [Negative Equity Share (CBUAE Cap)] as "At CBUAE cap", [Negative Equity Share (Registered Loans)] as "Registered loans", [Replay Negative Equity Share] as "2014-20 replay" |  |  | Stress test results (illustrative, not a regulatory stress test; loans held at origination) for the selected segment, price shock and loan-to-value: share of recent buyers in negative equity, the shortfall in AED, the number of purchases, the same share at the CBUAE cap and for registered loans, and under a repeat of the 2014 to 2020 fall. |
| `p6_heatmap` | pivotTable | 16, 268, 400, 412 | Rows: 'Price Shock %'[Price Shock %]; Columns: 'LTV %'[LTV Short]; Values: [Negative Equity Share] as "In negative equity" |  | Negative equity: shock × LTV (85%* = UAE national cap) | Heatmap of the share of recent buyers in negative equity (illustrative) for price falls of 0 to 50% and loan-to-values of 50 to 85%; 85% is the UAE national first-home cap, the worst case. |
| `p6_areas` | clusteredBarChart | 424, 268, 400, 196 | Category: 'Area'[Area]; Y: [Negative Equity Share by Area] as "In negative equity" | top 5 'Area'[Area] by [Negative Equity Share by Area] | Most exposed areas, top 5 (illustrative) | Bar chart of the five areas with the highest negative-equity share at the selected price shock and loan-to-value. |
| `p6_replay` | clusteredBarChart | 832, 268, 432, 196 | Category: 'Stress Replay'[Segment]; Y: [Replay Drawdown] as "2014-2020 fall" | bottom 5 'Stress Replay'[Segment] by [Replay Drawdown]; 'Stress Replay'[Used In Replay] in true | 2014→2020 fall, 5 deepest series (illustrative) | Bar chart of the five index series with the deepest fall in the 2014 to 2020 downturn; zone series are noisier and overstate it. |
| `p6_concentration` | clusteredBarChart | 424, 472, 400, 208 | Category: 'Project'[Master Project]; Y: [Master Project Share (Off-Plan)] as "Share of off-plan sales" | top 5 'Project'[Master Project] by [Off-Plan Market Sales (Lines)]; 'Project'[Master Project] not in 'Unknown' | [Title Concentration] | Top five master projects' shares of off-plan sales in the selected year, a proxy for developer concentration. |
| `p6_outlook` | lineChart | 832, 472, 432, 208 | Category: 'Forecast'[Month]; Y: [Forecast Actual] as "Actual", [Forecast Central] as "Forecast", [Forecast Lower 80] as "80% low", [Forecast Upper 80] as "80% high" | 'Forecast'[Month] >= datetime'2021-01-01T00:00:00' | [Title Outlook] / Dashed = 80% interval; a baseline, not a call | Price index history since 2021 and the 12-month forecast with its 80% interval for the selected rate scenario. |
| `p6_ftr_source` | cardVisual | 16, 684, 1248, 32 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## KPI guide

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p7_frame_panel` | textbox | 182, 12, 1086, 696 |  |  |  | Content panel (decorative). |
| `p7_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p7_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p7_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p7_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: KPI GUIDE. |
| `p7_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p7_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset all filters on this page. |
| `p7_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p7Guide_placeholder` | textbox | 198, 60, 1060, 60 |  |  |  | Placeholder for the KPI guide. |
| `p7_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |
