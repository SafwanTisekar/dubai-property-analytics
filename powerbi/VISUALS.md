# Report visuals (generated)

Generated from the PBIR files by `make pbi-inventory` (`powerbi/pbir.py`); `tests/test_powerbi_model.py` fails when it is stale. Positions are x, y, width, height on the 1280 × 720 canvas. Intent, decisions and checks: `powerbi/BUILD.md`.

## Introduction

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p0Intro_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p0Intro_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p0Intro_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p0Intro_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p0Intro_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: INTRODUCTION TO THE REPORT. |
| `p0Intro_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p0Intro_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p0Intro_what` | textbox | 198, 60, 520, 116 |  |  |  | What this report is. |
| `p0Intro_why` | textbox | 198, 186, 520, 140 |  |  |  | Why it matters. |
| `p0Intro_data_text` | tableEx | 198, 336, 520, 132 | Values: [Guide Data Line] as "Where the data comes from" |  |  | Where the data comes from: the number of sales and rent contracts and the snapshot date. |
| `p0Intro_questions` | textbox | 198, 478, 520, 198 |  |  |  | The questions the report answers. |
| `p0Intro_use` | textbox | 728, 60, 530, 214 |  |  |  | How to use the report. |
| `p0Intro_pages` | textbox | 728, 284, 530, 250 |  |  |  | One line per page of the report. |
| `p0Intro_good` | textbox | 728, 544, 530, 132 |  |  |  | Good to know. |
| `p0Intro_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## Key terms

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p0Terms_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p0Terms_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p0Terms_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p0Terms_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p0Terms_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: KEY TERMS & METHODS. |
| `p0Terms_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p0Terms_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p0Terms_h_terms` | textbox | 198, 60, 1060, 22 |  |  |  | Section heading: Property terms. |
| `p0Terms_term1` | textbox | 198, 84, 346, 112 |  |  |  | Term: Off-plan and ready. Off-plan: bought before it is built, paid to the developer in stages. Ready: finished, you can move in. Example: bought in 2025, handover in 2028: off-plan. |
| `p0Terms_term2` | textbox | 554, 84, 346, 112 |  |  |  | Term: AED per sq m. The price divided by the floor area, so homes of different sizes can be compared. Example: AED 1,400,000 for 70 sq m is AED 20,000 per sq m. |
| `p0Terms_term3` | textbox | 910, 84, 346, 112 |  |  |  | Term: Mortgage. A bank loan to buy a home. If it isn't repaid, the bank can sell the home. Example: pay AED 300,000, borrow AED 1,200,000. |
| `p0Terms_term4` | textbox | 198, 204, 346, 112 |  |  |  | Term: Loan-to-value (LTV). The loan as a share of the home's value. Higher means a thinner cushion. Example: AED 1,200,000 on a AED 1,500,000 home is 80%. |
| `p0Terms_term5` | textbox | 554, 204, 346, 112 |  |  |  | Term: Gross rental yield. A year's rent as a share of the price, before service charges and empty months. Example: AED 90,000 rent on AED 1,500,000 is 6%. |
| `p0Terms_term6` | textbox | 910, 204, 346, 112 |  |  |  | Term: Negative equity. The home is worth less than the loan, so selling it would not repay the bank. Example: AED 1,200,000 loan, home now worth 1,100,000. |
| `p0Terms_h_models` | textbox | 198, 326, 1060, 22 |  |  |  | Section heading: How the four models work. |
| `p0Terms_model1` | textbox | 198, 350, 257, 106 |  |  |  | Model: Price index: a shopping basket. Compares similar homes over time, so prices don't look higher just because pricier homes sold. |
| `p0Terms_model1_live_text` | tableEx | 198, 462, 257, 124 | Values: [Guide Index Line] as "From the data" |  |  | Live example for Price index: a shopping basket, from the data. |
| `p0Terms_model2` | textbox | 465, 350, 257, 106 |  |  |  | Model: AVM: an automated valuer. Learns how size, location, bedrooms and nearby prices relate to price, then estimates a home's value. |
| `p0Terms_model2_live_text` | tableEx | 465, 462, 257, 124 | Values: [Guide AVM Line] as "From the data" |  |  | Live example for AVM: an automated valuer, from the data. |
| `p0Terms_model3` | textbox | 732, 350, 257, 106 |  |  |  | Model: Stress test: a what-if calculator. Applies a price fall to every recent purchase and counts who would owe more than the home is worth. |
| `p0Terms_model3_live_text` | tableEx | 732, 462, 257, 124 | Values: [Guide Stress Line] as "From the data" |  |  | Live example for Stress test: a what-if calculator, from the data. |
| `p0Terms_model4` | textbox | 999, 350, 257, 106 |  |  |  | Model: Forecast: a baseline with a range. Extends past patterns 12 months ahead. Not a promise: the range matters as much as the line. |
| `p0Terms_model4_live_text` | tableEx | 999, 462, 257, 124 | Values: [Guide Forecast Line] as "From the data" |  |  | Live example for Forecast: a baseline with a range, from the data. |
| `p0Terms_limits` | textbox | 198, 592, 1060, 84 |  |  |  | What this can't tell you. |
| `p0Terms_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 1 Executive

Interactions set to none: p1_Year → p1_value_by_month.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p1_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p1_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p1_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p1_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p1_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: EXECUTIVE OVERVIEW DASHBOARD. |
| `p1_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p1_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p1_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p1_Year` | slicer | 198, 60, 150, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p1_Area` | slicer | 358, 60, 250, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p1_PropertyType` | slicer | 618, 60, 250, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p1_Bedrooms` | slicer | 878, 60, 170, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p1_ReadyOffPlan` | slicer | 1058, 60, 196, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p1_h_activity` | textbox | 198, 124, 600, 22 |  |  |  | Section heading: Market activity. |
| `p1_t1_kpi` | cardVisual | 198, 148, 168, 74 | Data: [Market Sales Value] as "Sales value (AED bn)" |  |  | KPI: Sales value (AED bn) for the selected filters, with a split underneath. |
| `p1_t1_strip` | cardVisual | 198, 222, 168, 26 | Data: [Sales Value Split] |  |  | Split of Sales value (AED bn). |
| `p1_t2_kpi` | cardVisual | 376, 148, 168, 74 | Data: [Market Sales] as "Market sales" |  |  | KPI: Market sales for the selected filters, with a split underneath. |
| `p1_t2_strip` | cardVisual | 376, 222, 168, 26 | Data: [Market Sales Split] |  |  | Split of Market sales. |
| `p1_t3_kpi` | cardVisual | 554, 148, 168, 74 | Data: [Median Price per Sq M] as "Median AED / sq m" |  |  | KPI: Median AED / sq m for the selected filters, with a split underneath. |
| `p1_t3_strip` | cardVisual | 554, 222, 168, 26 | Data: [Median Price Split] |  |  | Split of Median AED / sq m. |
| `p1_t4_kpi` | cardVisual | 732, 148, 168, 74 | Data: [Index YoY] as "Prices YoY (like for like)" |  |  | KPI: Prices YoY (like for like) for the selected filters, with a split underneath. |
| `p1_t4_strip` | cardVisual | 732, 222, 168, 26 | Data: [Index YoY Split] |  |  | Split of Prices YoY (like for like). |
| `p1_t5_kpi` | cardVisual | 910, 148, 168, 74 | Data: [Off-Plan Share (Value)] as "Off-plan share (value)" |  |  | KPI: Off-plan share (value) for the selected filters, with a split underneath. |
| `p1_t5_strip` | cardVisual | 910, 222, 168, 26 | Data: [Off-Plan Share Split] |  |  | Split of Off-plan share (value). |
| `p1_t6_kpi` | cardVisual | 1088, 148, 168, 74 | Data: [Purchase Mortgage Share] as "Mortgage share (ready)" |  |  | KPI: Mortgage share (ready) for the selected filters, with a split underneath. |
| `p1_t6_strip` | cardVisual | 1088, 222, 168, 26 | Data: [Mortgage Share Split] |  |  | Split of Mortgage share (ready). |
| `p1_h_cycles` | textbox | 198, 258, 620, 22 |  |  |  | Section heading: Market cycles. |
| `p1_h_where` | textbox | 828, 258, 430, 22 |  |  |  | Section heading: Where value concentrates. |
| `p1_value_by_month` | lineChart | 198, 282, 620, 252 | Category: 'Date'[Month Start]; Y: [Market Sales Value] as "Sales value" | 'Date'[Is After Snapshot] in false | Market sales value by month, AED / All years; not filtered by Year | Line chart of monthly market sales value since 2004, with the 2008, 2014, 2020 and 2021 cycle points marked. Shows all years regardless of the Year slicer. |
| `p1_top_areas` | clusteredBarChart | 828, 282, 430, 252 | Category: 'Area'[Area]; Y: [Market Sales Value] as "Sales value" | top 7 'Area'[Area] by [Market Sales Value] | Top 7 areas by sales value | Bar chart of the seven areas with the highest sales value in the selected period. |
| `p1_insight_offplan_text` | tableEx | 198, 544, 346, 132 | Values: [Insight Off-Plan] as "Off-plan: most sales, not most value" |  |  | Insight: off-plan share of sales by number and by value in the last complete year. |
| `p1_insight_ytd_text` | tableEx | 554, 544, 346, 132 | Values: [Insight Year to Date] as "This year so far" |  |  | Insight: this year's market sales so far against the same months last year. |
| `p1_insight_2009` | textbox | 910, 544, 346, 132 |  |  |  | Insight: the 2009 registration backlog. |
| `p1_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 2 Financing

Interactions set to none: p2_Year → p2_ready_financed; p2_Year → p2_share; p2_Year → p2_rate; p2_Year → p2_per100; p2_Year → p2_mix.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p2_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p2_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p2_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p2_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p2_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: FINANCING & MARKET MIX. |
| `p2_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p2_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p2_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p2_Year` | slicer | 198, 60, 150, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p2_Area` | slicer | 358, 60, 250, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p2_PropertyType` | slicer | 618, 60, 250, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p2_Bedrooms` | slicer | 878, 60, 170, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p2_ReadyOffPlan` | slicer | 1058, 60, 196, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p2_h_glance` | textbox | 198, 124, 600, 22 |  |  |  | Section heading: Financing at a glance. |
| `p2_t1_kpi` | cardVisual | 198, 148, 204, 74 | Data: [Ready Market Sales] as "Ready sales" |  |  | KPI: Ready sales for the selected filters, with a split underneath. |
| `p2_t1_strip` | cardVisual | 198, 222, 204, 26 | Data: [Ready Sales Split] |  |  | Split of Ready sales. |
| `p2_t2_kpi` | cardVisual | 412, 148, 204, 74 | Data: [Purchase Mortgage Share] as "Mortgage share (ready)" |  |  | KPI: Mortgage share (ready) for the selected filters, with a split underneath. |
| `p2_t2_strip` | cardVisual | 412, 222, 204, 26 | Data: [Mortgage Share Split] |  |  | Split of Mortgage share (ready). |
| `p2_t3_kpi` | cardVisual | 626, 148, 204, 74 | Data: [New Mortgages per 100 Sales] as "New mortgages / 100 sales" |  |  | KPI: New mortgages / 100 sales for the selected filters, with a split underneath. |
| `p2_t3_strip` | cardVisual | 626, 222, 204, 26 | Data: [New Mortgages Split] |  |  | Split of New mortgages / 100 sales. |
| `p2_t4_kpi` | cardVisual | 840, 148, 204, 74 | Data: [Off-Plan Share (Count)] as "Off-plan share (count)" |  |  | KPI: Off-plan share (count) for the selected filters, with a split underneath. |
| `p2_t4_strip` | cardVisual | 840, 222, 204, 26 | Data: [Off-Plan Value Split] |  |  | Split of Off-plan share (count). |
| `p2_t5_kpi` | cardVisual | 1054, 148, 204, 74 | Data: [Reference Rate] as "Reference rate" |  |  | KPI: Reference rate for the selected filters, with a split underneath. |
| `p2_t5_strip` | cardVisual | 1054, 222, 204, 26 | Data: [Reference Rate Split] |  |  | Split of Reference rate. |
| `p2_h_pay` | textbox | 198, 258, 1060, 22 |  |  |  | Section heading: How ready buyers pay. |
| `p2_ready_financed` | columnChart | 198, 282, 346, 180 | Category: 'Date'[Month Start]; Y: [Purchase Mortgages] as "Matched mortgage", [Ready Sales Not Bank-Financed] as "Not bank-financed" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Ready sales: mortgage-financed or not / From 2010; not filtered by Year | Monthly ready sales split into those matched to a same-day purchase mortgage and those not bank-financed at registration. |
| `p2_share` | lineChart | 554, 282, 346, 180 | Category: 'Date'[Month Start]; Y: [Purchase Mortgage Share] as "Mortgage share (ready)" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Mortgage share of ready sales (at least) / Matched loans only; not filtered by Year | Line chart of the matched purchase-mortgage share of ready sales by month since 2010. |
| `p2_rate` | lineChart | 910, 282, 348, 180 | Category: 'Date'[Month Start]; Y: [Reference Rate] as "Rate" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | [Reference Rate Label] / Same time range; not filtered by Year | Line chart of the reference interest rate by month since 2010, on the same time range as the mortgage share. |
| `p2_h_mix` | textbox | 198, 470, 1060, 22 |  |  |  | Section heading: Off-plan versus ready. |
| `p2_per100` | lineChart | 198, 494, 346, 182 | Category: 'Date'[Year]; Y: [New Mortgages per 100 Sales] as "Per 100 sales" | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | New mortgages per 100 market sales / Incl. refinancing; not filtered by Year | New mortgages per 100 market sales by year. |
| `p2_mix` | hundredPercentStackedColumnChart | 554, 494, 346, 182 | Category: 'Date'[Year]; Y: [Market Sales] as "Market sales"; Series: 'Ready Off-Plan'[Ready / Off-Plan] | 'Date'[Year] >= 2010L; 'Date'[Is After Snapshot] in false | Off-plan vs ready share of sales / 2010-2026 (2026 partial) | Share of market sales that were off-plan or ready, by year, 2010 to 2026. |
| `p2_offplan_areas` | clusteredBarChart | 910, 494, 348, 182 | Category: 'Area'[Area]; Y: [Off-Plan Share (Count)] as "Off-plan share" | top 4 'Area'[Area] by [Market Sales] | Off-plan share, 4 busiest areas | Off-plan share of sales in the four areas with the most market sales. |
| `p2_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 3 Prices

Interactions set to none: p3_Year → p3_vs_dld; p3_Year → p3_mix_shift; p3_Year → p3_drawdown.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p3_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p3_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p3_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p3_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p3_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: PRICES & INDEX. |
| `p3_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p3_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p3_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p3_Year` | slicer | 198, 60, 110, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p3_Area` | slicer | 318, 60, 200, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p3_PropertyType` | slicer | 528, 60, 200, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p3_Bedrooms` | slicer | 738, 60, 120, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p3_ReadyOffPlan` | slicer | 868, 60, 150, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p3_IndexSegment` | slicer | 1028, 60, 230, 56 | Values: 'Price Index'[Segment] |  |  | Slicer: Index segment |
| `p3_h_glance` | textbox | 198, 124, 600, 22 |  |  |  | Section heading: Prices at a glance. |
| `p3_t1_kpi` | cardVisual | 198, 148, 257, 74 | Data: [Index Value (Latest Complete)] as "Index (Jan 2019 = 100)" |  |  | KPI: Index (Jan 2019 = 100) for the selected filters, with a split underneath. |
| `p3_t1_strip` | cardVisual | 198, 222, 257, 26 | Data: [Index Period Split] |  |  | Split of Index (Jan 2019 = 100). |
| `p3_t2_kpi` | cardVisual | 465, 148, 257, 74 | Data: [Index YoY] as "Prices YoY (like for like)" |  |  | KPI: Prices YoY (like for like) for the selected filters, with a split underneath. |
| `p3_t2_strip` | cardVisual | 465, 222, 257, 26 | Data: [Index YoY Split] |  |  | Split of Prices YoY (like for like). |
| `p3_t3_kpi` | cardVisual | 732, 148, 257, 74 | Data: [Drawdown from Peak] as "Below previous peak" |  |  | KPI: Below previous peak for the selected filters, with a split underneath. |
| `p3_t3_strip` | cardVisual | 732, 222, 257, 26 | Data: [Max Drawdown Split] |  |  | Split of Below previous peak. |
| `p3_t4_kpi` | cardVisual | 999, 148, 257, 74 | Data: [Area-Weighted Price per Sq M (Homes)] as "AED / sq m (homes)" |  |  | KPI: AED / sq m (homes) for the selected filters, with a split underneath. |
| `p3_t4_strip` | cardVisual | 999, 222, 257, 26 | Data: [Area-Weighted Price Split] |  |  | Split of AED / sq m (homes). |
| `p3_h_moved` | textbox | 198, 258, 650, 22 |  |  |  | Section heading: How prices moved. |
| `p3_h_matrix` | textbox | 858, 258, 400, 22 |  |  |  | Section heading: Price by zone and bedrooms. |
| `p3_vs_dld` | lineChart | 198, 282, 320, 180 | Category: 'Date'[Month Start]; Y: [Index Value] as "Hedonic index", [DLD Index Value] as "DLD index (to May 2024)" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Like for like vs DLD's index (2019 = 100) / Ours leads by ~6 months | Line chart comparing this project's like-for-like price index with DLD's official index since 2011, both rebased to January 2019. |
| `p3_mix_shift` | lineChart | 528, 282, 320, 180 | Category: 'Date'[Month Start]; Y: [Index Value (Apartments)] as "Like for like", [Raw Median Rebased (Apartments)] as "Raw median" | 'Date'[Year] >= 2015L; 'Date'[Is After Snapshot] in false | Apartments: raw median vs like for like | Apartment price index against the raw median price per square metre, both rebased to January 2019: the gap is the mix shift (2023: +1% raw vs +17% like for like). |
| `p3_h_falls` | textbox | 198, 470, 650, 22 |  |  |  | Section heading: Falls, and where prices are highest. |
| `p3_drawdown` | areaChart | 198, 494, 320, 182 | Category: 'Date'[Month Start]; Y: [Index Drawdown] as "Below previous peak" | 'Date'[Year] >= 2011L; 'Date'[Is After Snapshot] in false | Fall from the previous peak / 2014-2020: -24% Dubai-wide | Drawdown of the selected price index from its running peak since 2011. |
| `p3_price_areas` | clusteredBarChart | 528, 494, 320, 182 | Category: 'Area'[Area]; Y: [Median Price per Sq M] as "Median AED / sq m" | top 4 'Area'[Area] by [Median Price per Sq M]; 'Property Type'[Usage Group] in 'Residential'; [Clean Sales] >= 20L | Top 4 areas, AED / sq m (residential) | Bar chart of the four areas with the highest median price per square metre of residential sales (areas with fewer than 20 clean sales are left out). |
| `p3_bed_zone` | pivotTable | 858, 282, 400, 394 | Rows: 'Area'[Zone Short]; Columns: 'Bedrooms'[Bedrooms]; Values: [Median Price per Sq M (K)] as "Median AED / sq m" | 'Property Type'[Usage Group] in 'Residential'; 'Bedrooms'[Bedrooms] in 'Studio', '1 BR', '2 BR', '3 BR', '4 BR'; [Clean Sales] >= 20L | Median AED / sq m (K), Studio to 4 BR | Table of the residential median price per square metre in thousands of AED by zone, studios to four bedrooms; blank cells have fewer than 20 sales. |
| `p3_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 4 Yields

Interactions set to none: p4_Year → p4_trend.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p4_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p4_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p4_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p4_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p4_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: RENTAL YIELDS. |
| `p4_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p4_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p4_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p4_Year` | slicer | 198, 60, 150, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p4_Area` | slicer | 358, 60, 250, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p4_PropertyType` | slicer | 618, 60, 250, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p4_Bedrooms` | slicer | 878, 60, 170, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p4_ReadyOffPlan` | slicer | 1058, 60, 196, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p4_h_glance` | textbox | 198, 124, 600, 22 |  |  |  | Section heading: Yields and rents at a glance. |
| `p4_t1_kpi` | cardVisual | 198, 148, 346, 74 | Data: [Gross Yield (Latest 4 Quarters)] as "Gross yield, last 4 quarters" |  |  | KPI: Gross yield, last 4 quarters for the selected filters, with a split underneath. |
| `p4_t1_strip` | cardVisual | 198, 222, 346, 26 | Data: [Yield Split] |  |  | Split of Gross yield, last 4 quarters. |
| `p4_t2_kpi` | cardVisual | 554, 148, 346, 74 | Data: [New Market Rents] as "New rent contracts" |  |  | KPI: New rent contracts for the selected filters, with a split underneath. |
| `p4_t2_strip` | cardVisual | 554, 222, 346, 26 | Data: [New Rents Split] |  |  | Split of New rent contracts. |
| `p4_t3_kpi` | cardVisual | 910, 148, 346, 74 | Data: [Area-Weighted New Rent per Sq M (Homes)] as "New rent / sq m / year (homes)" |  |  | KPI: New rent / sq m / year (homes) for the selected filters, with a split underneath. |
| `p4_t3_strip` | cardVisual | 910, 222, 346, 26 | Data: [Rent per Sq M Split] |  |  | Split of New rent / sq m / year (homes). |
| `p4_h_zone` | textbox | 198, 258, 420, 22 |  |  |  | Section heading: Yield by zone. |
| `p4_h_areas` | textbox | 628, 258, 630, 22 |  |  |  | Section heading: Areas, growth and rents. |
| `p4_by_zone` | clusteredBarChart | 198, 282, 420, 394 | Category: 'Area'[Zone Short]; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse'; top 10 'Area'[Zone Short] by [Market Sales] | Gross yield, 10 busiest zones | Gross rental yield of the ten zones with the most sales, apartments and villas, over the last four complete quarters; out-of-band cells left out. |
| `p4_area_yields` | clusteredBarChart | 628, 282, 310, 180 | Category: 'Area'[Area]; Y: [Gross Yield by Area (Latest 4 Quarters)] as "Gross yield" | top 4 'Area'[Area] by [Gross Yield by Area (Latest 4 Quarters)] | Top 4 area yields | Bar chart of the four areas with the highest gross yield, where both rents and sales reach 20 per cell. |
| `p4_yield_growth` | scatterChart | 948, 282, 310, 180 | Category: 'Area'[Zone]; X: [Index Growth 3Y (Zone)] as "Price growth, 3 years"; Y: [Gross Yield (Latest 4 Quarters)] as "Gross yield"; Size: [Market Sales] as "Market sales" | 'Property Type'[Property Type] in 'Residential · Apartment'; top 8 'Area'[Zone] by [Market Sales] | Income vs growth (apartments) / 8 zones with most sales | Scatter of the eight zones with the most sales: three-year apartment price growth against gross yield, bubble size is sales. |
| `p4_trend` | lineChart | 628, 494, 310, 182 | Category: 'Date'[Quarter Start]; Y: [Gross Yield by Quarter] as "Gross yield"; Series: 'Property Type'[Property Type] | 'Property Type'[Property Type] in 'Residential · Apartment', 'Residential · Villa / Townhouse'; 'Date'[Year] >= 2012L; 'Date'[Is After Snapshot] in false | Yields by quarter / From 2012; not filtered by Year | Quarterly gross yield for apartments and villas since 2012. |
| `p4_rent_beds` | clusteredColumnChart | 948, 494, 310, 182 | Category: 'Bedrooms'[Bedrooms]; Y: [New Rent per Sq M] as "AED / sq m / year" | 'Property Type'[Property Type] in 'Residential · Apartment'; 'Bedrooms'[Bedrooms] not in 'Unknown' | New rent / sq m by bedrooms / Apartments, new contracts | Annual rent per square metre of new apartment contracts by number of bedrooms. |
| `p4_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 5 Valuation

Page filters: 'AVM Score'[Model Set] in 'Test'.

Interactions set to none: p5_Year → p5_actual_vs_avm.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p5_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p5_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p5_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p5_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p5_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: VALUATION MODEL (AVM). |
| `p5_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p5_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p5_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p5_Year` | slicer | 198, 60, 110, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p5_Area` | slicer | 318, 60, 200, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p5_PropertyType` | slicer | 528, 60, 200, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p5_Bedrooms` | slicer | 738, 60, 120, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p5_ReadyOffPlan` | slicer | 868, 60, 150, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p5_Breakdown` | slicer | 1028, 60, 230, 56 | Values: 'AVM Performance'[Breakdown] | 'AVM Performance'[Breakdown] in 'Property Type (same sales)', 'Reg Type (same sales)' |  | Slicer: Accuracy by |
| `p5_h_glance` | textbox | 198, 124, 700, 22 |  |  |  | Section heading: Accuracy on 2025-26 sales the model never saw. |
| `p5_t1_kpi` | cardVisual | 198, 148, 257, 74 | Data: [AVM Test MdAPE] as "AVM median error" |  |  | KPI: AVM median error for the selected filters, with a split underneath. |
| `p5_t1_strip` | cardVisual | 198, 222, 257, 26 | Data: [AVM MdAPE Split] |  |  | Split of AVM median error. |
| `p5_t2_kpi` | cardVisual | 465, 148, 257, 74 | Data: [AVM Test Hit Rate 10%] as "Within ±10%" |  |  | KPI: Within ±10% for the selected filters, with a split underneath. |
| `p5_t2_strip` | cardVisual | 465, 222, 257, 26 | Data: [AVM Hit 10 Split] |  |  | Split of Within ±10%. |
| `p5_t3_kpi` | cardVisual | 732, 148, 257, 74 | Data: [AVM Test Hit Rate 20%] as "Within ±20%" |  |  | KPI: Within ±20% for the selected filters, with a split underneath. |
| `p5_t3_strip` | cardVisual | 732, 222, 257, 26 | Data: [AVM Hit 20 Split] |  |  | Split of Within ±20%. |
| `p5_t4_kpi` | cardVisual | 999, 148, 257, 74 | Data: [AVM Test Sales Valued] as "Test sales valued" |  |  | KPI: Test sales valued for the selected filters, with a split underneath. |
| `p5_t4_strip` | cardVisual | 999, 222, 257, 26 | Data: [AVM Flagged Split] |  |  | Split of Test sales valued. |
| `p5_h_acc` | textbox | 198, 258, 520, 22 |  |  |  | Section heading: Accuracy. |
| `p5_h_drv` | textbox | 728, 258, 530, 22 |  |  |  | Section heading: Drivers and misses. |
| `p5_by_segment` | clusteredBarChart | 198, 282, 520, 180 | Category: 'AVM Performance'[Segment]; Y: [AVM Segment MdAPE] as "Median error"; Series: 'AVM Performance'[Model Name] | 'AVM Performance'[Split] in 'Test'; 'AVM Performance'[Model] in 'lightgbm', 'comps' | Median error by segment, same sales | Median absolute percentage error by segment for the AVM and the comparable-sales baseline on the 2025-26 test sales both can value (the model card's head-to-head). |
| `p5_actual_vs_avm` | lineChart | 198, 474, 520, 202 | Category: 'Date'[Month Start]; Y: [Median Sale Price (AVM Sample)] as "Median price", [Median AVM Value] as "Median AVM value" |  | Median price vs median AVM value / Out of sample, by month; not filtered by Year | Median sale price and median AVM value of out-of-sample sales by month. |
| `p5_features` | clusteredBarChart | 728, 282, 530, 180 | Category: 'Feature Importance'[Feature Label]; Y: [Mean Abs SHAP] as "Mean |SHAP|" | 'Feature Importance'[Rank] <= 4L | Top 4 drivers of the valuation (mean |SHAP|) | Top four features by mean absolute SHAP value, in log points of the predicted price. |
| `p5_gaps` | tableEx | 728, 474, 530, 202 | Values: 'Area'[Area], 'Project'[Project], [Valued Sales] as "Valued", [Median Gap %] as "Median gap", [Flagged for Review] as "Flagged" | top 3 'Project'[Project] by [Flagged for Review]; 'Project'[Project] not in 'Unknown' | Most review flags (anomalies, not accusations) | Table of the three projects with the most sales flagged for review (more than 25% from the AVM), with their area and median gap; project Unknown excluded. |
| `p5_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## 6 Risk

Page filters: 'Forecast'[Target] in 'Price index'.

Interactions set to none: p6_Shock → p6_heatmap; p6_LTV → p6_heatmap.

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p6_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p6_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p6_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p6_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p6_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: RISK & STRESS TEST. |
| `p6_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p6_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p6_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p6_Year` | slicer | 198, 60, 100, 56 | Values: 'Date'[Year] |  |  | Slicer: Year |
| `p6_Area` | slicer | 308, 60, 170, 56 | Values: 'Area'[Zone], 'Area'[Area] |  |  | Slicer: Zone / area |
| `p6_PropertyType` | slicer | 488, 60, 170, 56 | Values: 'Property Type'[Property Type] |  |  | Slicer: Property type |
| `p6_Bedrooms` | slicer | 668, 60, 100, 56 | Values: 'Bedrooms'[Bedrooms] |  |  | Slicer: Bedrooms |
| `p6_ReadyOffPlan` | slicer | 778, 60, 120, 56 | Values: 'Ready Off-Plan'[Ready / Off-Plan] |  |  | Slicer: Ready / off-plan |
| `p6_StressSegment` | slicer | 908, 60, 150, 56 | Values: 'Stress Grid'[Segment] | 'Stress Grid'[Segment Level] in 'Dubai', 'Type', 'Zone' |  | Slicer: Stress segment |
| `p6_Shock` | slicer | 1068, 60, 85, 56 | Values: 'Price Shock %'[Price Shock %] |  |  | Slicer: Shock % |
| `p6_LTV` | slicer | 1163, 60, 85, 56 | Values: 'LTV %'[LTV Short] |  |  | Slicer: LTV |
| `p6_h_glance` | textbox | 198, 124, 800, 22 |  |  |  | Section heading: Stress result (illustrative, not a regulatory stress test). |
| `p6_t1_kpi` | cardVisual | 198, 148, 204, 74 | Data: [Negative Equity Share] as "In negative equity" |  |  | KPI: In negative equity for the selected filters, with a split underneath. |
| `p6_t1_strip` | cardVisual | 198, 222, 204, 26 | Data: [Negative Equity Split] |  |  | Split of In negative equity. |
| `p6_t2_kpi` | cardVisual | 412, 148, 204, 74 | Data: [Negative Equity Share (CBUAE Cap)] as "At the CBUAE cap" |  |  | KPI: At the CBUAE cap for the selected filters, with a split underneath. |
| `p6_t2_strip` | cardVisual | 412, 222, 204, 26 | Data: [CBUAE Cap Split] |  |  | Split of At the CBUAE cap. |
| `p6_t3_kpi` | cardVisual | 626, 148, 204, 74 | Data: [Replay Negative Equity Share] as "2014-20 replay (Dubai-wide)" |  |  | KPI: 2014-20 replay (Dubai-wide) for the selected filters, with a split underneath. |
| `p6_t3_strip` | cardVisual | 626, 222, 204, 26 | Data: [Replay Split] |  |  | Split of 2014-20 replay (Dubai-wide). |
| `p6_t4_kpi` | cardVisual | 840, 148, 204, 74 | Data: [Forecast 12M Change] as "Price outlook, 12 months" |  |  | KPI: Price outlook, 12 months for the selected filters, with a split underneath. |
| `p6_t4_strip` | cardVisual | 840, 222, 204, 26 | Data: [Forecast Split] |  |  | Split of Price outlook, 12 months. |
| `p6_t5_kpi` | cardVisual | 1054, 148, 204, 74 | Data: [Top 10 Master Project Share (Off-Plan)] as "Top-10 master projects" |  |  | KPI: Top-10 master projects for the selected filters, with a split underneath. |
| `p6_t5_strip` | cardVisual | 1054, 222, 204, 26 | Data: [Concentration Split] |  |  | Split of Top-10 master projects. |
| `p6_h_heat` | textbox | 198, 258, 346, 22 |  |  |  | Section heading: Shock × LTV. |
| `p6_h_where` | textbox | 554, 258, 704, 22 |  |  |  | Section heading: Where risk sits, and the outlook. |
| `p6_heatmap` | pivotTable | 198, 282, 346, 394 | Rows: 'Price Shock %'[Price Shock %]; Columns: 'LTV %'[LTV Short]; Values: [Negative Equity Share] as "In negative equity" |  | Negative equity (85%* = UAE national cap) | Heatmap of the share of recent buyers in negative equity (illustrative) for price falls of 0 to 50% and loan-to-values of 50 to 85%; 85% is the UAE national first-home cap, the worst case. |
| `p6_areas` | clusteredBarChart | 554, 282, 346, 180 | Category: 'Area'[Area]; Y: [Negative Equity Share by Area] as "In negative equity" | top 4 'Area'[Area] by [Negative Equity Share by Area] | Most exposed areas (illustrative) | Bar chart of the four areas with the highest negative-equity share at the selected price shock and loan-to-value. |
| `p6_replay` | clusteredBarChart | 910, 282, 348, 180 | Category: 'Stress Replay'[Segment]; Y: [Replay Drawdown] as "2014-2020 fall" | bottom 4 'Stress Replay'[Segment] by [Replay Drawdown]; 'Stress Replay'[Used In Replay] in true | 2014-20 fall, 4 deepest series | Bar chart of the four index series with the deepest fall in the 2014 to 2020 downturn; zone series are noisier and overstate it. |
| `p6_concentration` | clusteredBarChart | 554, 494, 346, 182 | Category: 'Project'[Master Project]; Y: [Master Project Share (Off-Plan)] as "Share of off-plan sales" | top 4 'Project'[Master Project] by [Off-Plan Market Sales (Lines)]; 'Project'[Master Project] not in 'Unknown' | Top 4 master projects (off-plan share) | The four master projects with the largest shares of off-plan sales in the selected year, a proxy for developer concentration. |
| `p6_outlook` | lineChart | 910, 494, 348, 182 | Category: 'Forecast'[Month]; Y: [Forecast Actual] as "Actual", [Forecast Central] as "Forecast", [Forecast Lower 80] as "80% low", [Forecast Upper 80] as "80% high" | 'Forecast'[Month] >= datetime'2021-01-01T00:00:00' | Price index outlook, 12 months / Rates flat; dashed = 80% range | Dubai price index since 2021 and the 12-month forecast with its 80% interval, rates flat. |
| `p6_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |

## KPI guide

| Visual | Type | Position | Fields | Filters | Title | Alt text |
|---|---|---|---|---|---|---|
| `p7_frame_panel` | textbox | 182, 8, 1086, 704 |  |  |  | Content panel (decorative). |
| `p7_side_logo` | textbox | 14, 18, 150, 56 |  |  |  | Report name: Dubai Property Risk. |
| `p7_side_nav` | pageNavigator | 12, 92, 146, 324 |  |  |  | Page navigation: one button per report page. |
| `p7_side_icon` | textbox | 34, 550, 110, 130 |  |  |  | Decorative house icon. |
| `p7_hdr_title` | textbox | 198, 16, 620, 36 |  |  |  | Page title: KPI GUIDE. |
| `p7_hdr_asof` | cardVisual | 826, 20, 226, 28 | Data: [Data As Of Label] |  |  | Date of the latest transaction in the data. |
| `p7_hdr_reset` | actionButton | 1060, 18, 152, 32 |  |  |  | Button: reset the filters on this page to their defaults. |
| `p7_hdr_info` | actionButton | 1218, 18, 40, 32 |  |  |  | Button: open the KPI guide. |
| `p7Guide_Page` | slicer | 198, 60, 300, 56 | Values: 'KPI Guide'[Page] |  |  | Slicer: Filter by report page |
| `p7Guide_table` | tableEx | 198, 124, 1060, 552 | Values: 'KPI Guide'[KPI Sort] as "#", 'KPI Guide'[Page], 'KPI Guide'[KPI], 'KPI Guide'[Meaning], 'KPI Guide'[How it is calculated], 'KPI Guide'[Source table], 'KPI Guide'[Caveats] |  |  | Table of every KPI on the selected report page: what it means, how it is calculated, its source table and its caveats. |
| `p7_ftr_source` | cardVisual | 198, 684, 1060, 22 | Data: [Footer Attribution] |  |  | Data sources and licences. |
