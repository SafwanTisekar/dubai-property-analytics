# Phase 3 findings: market cycles, financing, prices and rents

These are the findings of Phase 3 (exploratory analysis), taken from `notebooks/01_market_cycles.ipynb`, `02_financing_mix.ipynb` and `03_prices_and_rents.ipynb`.

- **Data.** DLD transactions and Ejari rent contracts to the snapshot date, **2026-09-25**. Scope starts 2004-01-01. **2026 is a partial year** (1 Jan – 25 Sep) wherever it appears.
- **Definitions.** Market sales, clean sales, the purchase-mortgage share of ready sales and the rest are defined in docs/01 §4 and docs/04.
- **Revised 2026-09-30** after owner review: the mortgage KPI was redefined (F2.1), the villa vs apartment comparison was withdrawn (F3.1), a 2026 momentum check was added (F1.5), and the LTV caps were verified against the CBUAE rulebook and dated (F2.4).
- **Regenerate.** Run `make eda` after `make dbt`. The charts are written to `reports/figures/`.
- **Code.** Every number comes from a function in `src/dubai_property/analysis/`, which aggregates in SQL over `gold` and `rpt`. The functions are named below as `module.function`.

## Executive summary

1. **Record boom.** Dubai recorded **211,007 market sales worth AED 668.3bn in 2025**: 6.6× the count and 10.2× the value of 2020. ([chart](figures/q1_market_sales_by_year.png))
2. **2026 has slowed, led by ready homes.** Market sales for January–August 2026 are **down 19% on the same months of 2025** (−22% by value). Ready sales fell **37%**, off-plan only **7%**. Registration-lag checks show no sign that the fall is late data. ([chart](figures/q1_2026_ytd_vs_2025.png))
3. **The 2009 "spike" was paperwork, not demand.** **93.5%** of the 29,898 off-plan sales registered in 2009 were applied for in earlier years. They are a backlog of 2004–08 deals entered into the new off-plan register. ([chart](figures/q1_2009_registration_lag.png))
4. **Off-plan is most sales but not most value.** Off-plan made up **63% of 2025 market sales but 44% of their value** (69% and 50% in 2026 to date). ([chart](figures/q2_offplan_share_count_value.png))
5. **Between 28% and 48% of ready purchases were bank-financed in 2025.** 27.9% are matched to a same-day mortgage of the same unit (a lower bound). All ready-unit mortgages, including refinancing, come to 48.1% of ready sales (the upper bound). Most other purchases are off-plan, paid to developers in instalments, so they are **not bank-financed at registration** rather than "cash". ([chart](figures/q2_purchase_mortgage_share_vs_fedfunds.png))
6. **Lenders moved from a 75% to an 80% loan-to-value norm when the CBUAE raised the caps in April 2020.** The median observed LTV was exactly 75% every year 2014–2019, the expatriate first-home cap at the time. Within weeks of the April 2020 change (75% → 80%), loans at exactly 75% fell from about a third of the total to under a tenth, and **half of 2026 loans sit at exactly 80%**. ([chart](figures/q2_ltv_by_year.png))
7. **The raw median hid a double-digit price rise in 2023.** The apartment median per sq m rose **+1.2%**, but like-for-like prices rose **+14.5%**, because sales shifted to cheaper zones. This is why the Phase 4 index is hedonic. ([chart](figures/q3_mix_shift_example.png))

---

## Q1. Volume and value through the cycles (notebook 01)

**F1.1 Records every year since 2021.** Market sales rose from 32,138 (AED 65.5bn) in 2020 to 211,007 (AED 668.3bn) in 2025. 2026 to 25 Sep: 118,698 sales, AED 364.8bn.
- Chart: [q1_market_sales_by_year.png](figures/q1_market_sales_by_year.png), [q1_market_sales_by_month.png](figures/q1_market_sales_by_month.png)
- Function: `market_cycles.sales_by_year` / `sales_by_month` (Σ over `gold.agg_area_month`, reconciled to `rpt.transactions` by `tests/test_analysis.py`)
- Caveat: AED is nominal (not inflation-adjusted) and counted once per deal (C16). Market sales exclude gifts, grants, lease-to-own and development transfers.

**F1.2 The 2014–19 correction halved activity.** Sales fell from 58,159 (AED 135.8bn) in 2013 to 29,712 (AED 66.1bn) in 2018: −49% by count and −51% by value. The 2020 COVID low was 32,138.
- Chart: [q1_market_sales_by_year.png](figures/q1_market_sales_by_year.png)
- Function: `market_cycles.sales_by_year`, with phases from `market_cycles.CYCLE_PHASES`
- Caveat: phase boundaries are whole calendar years, used to label the charts. They are not a dating of turning points (the Phase 4 index does that).

**F1.3 The 2009 spike is a registration backlog, not market activity.**

| Test | Result |
|---|---|
| Composition | 29,898 of 2009's 56,340 market sales (53%) are `Sell - Pre registration`, against 13 in 2008 |
| Application year | 93.5% of 2009 off-plan registrations (78.4% in 2010) carry a `transaction_id` year before the registration year, with a median lag of 2 years. 11,550 carry 2007 alone. From 2011 onwards the share is 0% |
| Timing | They came in an April–August 2009 wave (5,267 in April), with no matching surge in ready sales |
| Ready market | Ready sales rose 24% (21,311 → 26,442) while ready value fell 53% (AED 103.2bn → 48.9bn) |
| Prices | Off-plan apartments registered in 2009 have a median of AED 10,194 per sq m, against 7,253 for 2009 ready sales, consistent with contracts priced near the 2007–08 peak |

- Chart: [q1_2009_spike_by_procedure_offplan.png](figures/q1_2009_spike_by_procedure_offplan.png), [q1_2009_registration_lag.png](figures/q1_2009_registration_lag.png), [q1_2009_monthly_registrations.png](figures/q1_2009_monthly_registrations.png)
- Functions: `market_cycles.sales_by_procedure`, `registration_lag` + `registration_lag_summary`, `ppsqm_offplan_vs_ready`, `offplan_by_project_first_year`
- External source: [Dubai Law No. 13 of 2008](https://dlp.dubai.gov.ae/Legislation%20Reference/2008/Law%20No.%20%2813%29%20of%202008.html) (issued 14 Aug 2008) created the Interim Property Register for off-plan units. Article 3(2) required developers to register off-plan sales made before the law within 60 days of it coming into force. That fits a one-off wave of back-dated registrations.
- Caveat: the law doesn't explain the **timing**. The wave peaked in April–August 2009, well after a 60-day window. Whether that is late compliance, an extension, or how DLD migrated the register into the open data needs confirmation from DLD. That the ID year is the application year is an inference (phase1_findings §4), not documented by DLD.

**F1.4 2004–2008 volumes understate the market.** The register holds 0–13 off-plan sales a year before 2009, and about 36,000 off-plan sales registered in 2009–10 carry 2004–08 application years. Pre-2009 volumes are effectively ready-only, so trends and rate comparisons in this project start in 2010.
- Chart: [q1_2009_registration_lag.png](figures/q1_2009_registration_lag.png)
- Function: `market_cycles.registration_lag`
- Caveat: pre-2009 counts are also thin (2,487–7,275 a year in 2004–07), so pre-2009 growth rates are not comparable with later years.

**F1.5 2026 is running well below 2025, and the checks point to a real slowdown, not late registrations.** Market sales for January–August 2026 were 109,093 (AED 339.7bn): −18.8% by count and −21.5% by value on January–August 2025 (134,339, AED 432.9bn).
- **By type:** ready sales fell from 53,808 to 33,863 (−37.1%; −33.4% by value). Off-plan fell only from 80,531 to 75,230 (−6.6%; −4.3%).
- **By month:** January (+19%) and February (+7%) were up. The fall began in March (−9%) and deepened from April (−22% in April, −46% in May, −34% in August).
- **By zone:** Marina, JBR & JLT fell 50%, Downtown & Business Bay 48%, Bur Dubai & Karama 47% and JVC, JVT & Arjan 34%. Jebel Ali, Dubai South & Waterfront rose 40% and Palm & Islands 11%, by count.
- **Lag check 1 (daily shape):** working-day registrations in the last 7 days before the snapshot run at 0.97× the previous 4 weeks, so recent days are not thin.
- **Lag check 2 (published vs extracted):** DLD published Q1 2026 on 9 Apr 2026 (60,303 transactions, AED 252bn; [DLD](https://dubailand.gov.ae/en/news-media/dubai-s-real-estate-transactions-surge-31-to-reach-aed-252-billion-in-q1-2026/)) and H1 2025 on 20 Jul 2025 (125,538, ~AED 431bn; [Dubai Media Office](https://www.mediaoffice.ae/en/news/2025/july/20-07/dubai-real-estate-transactions-exceed-aed431-billion-in-h1-2025)). Our September 2026 extract has 59,951 / AED 250.8bn and 123,032 / AED 429.7bn for the same periods, 0.6% and 2.0% *fewer*, not more. Lines don't keep arriving after the period closes. Our Q1 2026 is +5.9% on Q1 2025 by count, matching DLD's reported +6%.
- Chart: [q1_2026_ytd_vs_2025.png](figures/q1_2026_ytd_vs_2025.png)
- Functions: `market_cycles.ytd_by_zone` + `ytd_summary`, `daily_registrations` + `snapshot_tail_ratio`, `sales_by_month`
- Caveat: there is a single bulk snapshot, so a lag of more than a few weeks can't be ruled out directly; September 2026 is excluded as partial. The data shows *that* ready sales fell, not *why*.

## Q2. Financing mix (notebook 02)

**F2.1 Between about 28% and 48% of ready purchases were bank-financed in 2025 (headline KPI, redefined).**
- **Lower bound:** 21,537 of 77,154 ready market sales (27.9%) are matched to a Mortgage Registration or Delayed Mortgage of the same unit on the same day.
- **Upper bound:** all such mortgage lines, which include refinancing, equal 48.1% of ready sales.
- **Trend:** the matched share rose from 5.9% (2013) to 19.5% (2023) and 27.9% (2025). The match rate (matched ÷ all ready-unit mortgages) also rose, from 22–40% before 2020 to 58% in 2024–25, so much of that rise is better matching, not only more borrowing.
- **2026 to date:** both bounds jump (33.7% / 70.2%) because ready sales fell 37% while mortgage registrations held (23,306 in Jan–Aug vs 24,430).
- **Secondary indicator:** new mortgages per 100 market sales has been flat at about 18 since 2022 (17.9 in 2025), against 26–34 in 2016–2020, as the market shifted to off-plan.
- Chart: [q2_purchase_mortgage_share_vs_fedfunds.png](figures/q2_purchase_mortgage_share_vs_fedfunds.png)
- Function: `financing.mortgage_indicators_monthly` / `mortgage_indicators_by_year`, reading `fct_transaction.has_purchase_mortgage` (dbt `int_purchase_mortgage_pairs`). It reconciles silver → rpt in `reports/kpi_reconciliation.md` and matches `reports/dq_report.md` §5
- Caveat: **this replaces the earlier "mortgage share"** (new mortgages ÷ (new mortgages + market sales), 15.2% in 2025). That ratio double-counted: a mortgaged purchase registers both a sale and a mortgage line, and new mortgages include refinancing (docs/04 Decisions). The match misses loans registered on a different day or keyed differently. Sales without a matched mortgage are **not bank-financed at registration**, not necessarily cash: most are off-plan, paid to the developer in instalments. Portfolio mortgages are excluded.

**F2.2 Rates explain little of the mortgage share.** Since 2010 the trailing-12-month matched share and the effective Fed Funds rate correlate at +0.72 in levels, but that is two series trending up together in 2022–25. In 12-month changes the correlation is −0.22. The 2020 cuts and the 2022–23 rises both coincided with a steady or rising matched share.
- Chart: [q2_purchase_mortgage_share_vs_fedfunds.png](figures/q2_purchase_mortgage_share_vs_fedfunds.png)
- Function: `financing.share_rate_correlation`
- Caveat: Fed Funds stands in for EIBOR, which isn't loaded yet; the AED is pegged to the USD. This is an association, not a causal estimate. The lower bound's rising match rate adds its own trend.

**F2.3 Off-plan is most sales but not most value.** The off-plan share rose from 40.6% by count (31.0% by value) in 2021 to 63.4% (43.6%) in 2025, and to 68.7% (49.5%) in 2026 to date.
- Chart: [q2_offplan_share_count_value.png](figures/q2_offplan_share_count_value.png)
- Function: `market_cycles.sales_by_year` (`offplan_share_count`, `offplan_share_value`)
- Caveat: off-plan is DLD's `reg_type` at registration. The lower value share reflects cheaper units and locations, not a like-for-like discount.

**F2.4 Observed LTVs follow the CBUAE caps, and moved when the caps changed in April 2020.** The median loan ÷ same-day price was exactly 0.75 every year 2014–2019, with 28–34% of loans at exactly 75%: the expatriate first-home cap (≤ AED 5M) under Circular No. 31/2013. CBUAE Board Resolution 31/2/2020 (effective 8 April 2020) raised that cap to 80% and the UAE-national cap from 80% to 85%. From 2021 the median is 0.80, and 41.1% (2025) and 50.3% (2026) of loans sit at exactly 80%. The shift is visible within weeks: loans at exactly 75% were 32–40% of monthly pairs from October 2019 to March 2020, and 7–10% from July 2020. A second cluster at exactly **84.8%**, absent before April 2020, appeared from April–June 2020 (10–14% of monthly pairs from July), peaked at 22.4% of 2024 pairs, and is 0.0% in 2026. Its timing is **consistent with** the national first-home cap rising to 85%, but nationality isn't in the data, so this is not proven. Why the loans sit at 84.8% rather than 85%, and why the cluster vanishes in 2026, is not explained by the rules.
- Chart: [q2_ltv_by_year.png](figures/q2_ltv_by_year.png), [q2_ltv_distribution_by_year.png](figures/q2_ltv_distribution_by_year.png)
- Function: `financing.ltv_by_year`, `financing.ltv_histogram`, `financing.ltv_cluster_shares_monthly` (`fct_transaction.purchase_ltv` on the matched pairs, `int_purchase_mortgage_pairs`; 1,551–21,537 pairs a year from 2010)
- Source: caps and dates in `seed_ltv_rules`, verified against the [CBUAE rulebook](https://rulebook.centralbank.ae/en/rulebook/regulations-regarding-mortgage-loans) (Regulations Regarding Mortgage Loans, Art. 3(2), as amended by Board Resolution 31/2/2020); pre-2020 caps also per the [Al Tamimi summary](https://www.tamimi.com/law-update-articles/the-new-uae-mortgage-regulations/) of Circular No. 31/2013
- Caveat: this covers purchase mortgages matched to a same-day sale (Mortgage Registration ↔ Sell, Delayed Mortgage ↔ Delayed Sell), not refinancing. The caps are maxima. A loan below a cap says nothing about the borrower's category, and the data has no nationality, residency or first-home flag, so no loan can be assigned to a specific cap.

**F2.5 Portfolio mortgages are lumpy and kept separate.** Since 2004 there have been 1,873 portfolio mortgage deals worth AED 245.0bn (once per deal). 2022 alone had AED 80.8bn across 151 deals.
- Chart: [q2_portfolio_mortgages.png](figures/q2_portfolio_mortgages.png)
- Function: `financing.portfolio_by_year`
- Caveat: the value is as registered, not a verified loan amount (C10). Deals are inferred by rule C16.

## Q3. Prices and rents (notebook 03)

**F3.1 Villa prices roughly doubled from 2020 to 2025, and apartments rose about 65% (compare growth, not levels).**
- **Apartments:** median AED per sq m went from 11,314 (2020) to 18,657 (2025), +65%; +50% per unit.
- **Villas / townhouses:** on sales with a bedroom count, AED per sq m went from 7,934 to 16,080 (+103%), and the median price per unit from AED 1.66m to 3.55m (+114%).
- **Area-weighted:** area-weighted apartment prices run 10–26% above the median every year from 2010 (larger units cost more per sq m).
- Chart: [q3_price_per_sqm_apartments_villas.png](figures/q3_price_per_sqm_apartments_villas.png)
- Function: `prices_rents.ppsqm_by_year`, `prices_rents.area_basis`
- Caveat: **villa and apartment AED per sq m are not comparable, so the earlier claim that villas passed apartments in 2026 is withdrawn.**
  - DLD doesn't say whether a villa's `procedure_area` is the plot or the built-up area.
  - Villa sales with a bedroom count have built-up-sized areas (a median of ~190–200 sq m).
  - Villa sales without one have plot-sized areas (a median of 550–600 sq m). They were about 50% of villa sales before 2017, 20–26% in 2019–20 and 10% in 2026.
  - The all-villa median area fell from 400 sq m (2010) to 224 (2025) and 188 (2026), which alone lifts the all-villa median per sq m.
  - Within-class growth is quoted on the bedroom-known subset and per unit for that reason. 1 sq m = 10.7639 sq ft.

**F3.2 Zone growth ranges from +13% to +108%.** From 2019 to 2025, median apartment prices per sq m rose +108% in DIFC, Trade Centre & Za'abeel (to AED 42,285), +104% in Marina, JBR & JLT and +104% in Palm & Islands, but +13% in Mirdif, Mizhar, Warqa & Khawaneej.
- Chart: [q3_price_per_sqm_by_zone.png](figures/q3_price_per_sqm_by_zone.png)
- Function: `prices_rents.ppsqm_by_zone_year` (min-n applied)
- Caveat: a zone median still mixes projects and unit sizes. Al Barsha, Al Quoz & Tecom (+189%) blends Tecom towers with Al Quoz and moves mostly on mix.

**F3.3 New rents rose faster than prices from the 2021 low.** The Dubai-wide median new apartment rent went from AED 526 per sq m a year (2021) to 962 (2025), +83%. The highest in 2025 were MBR City, Meydan & Dubai Hills (1,502), Palm & Islands (1,485) and Downtown & Business Bay (1,433).
- Chart: [q3_new_rent_per_sqm_by_zone.png](figures/q3_new_rent_per_sqm_by_zone.png)
- Function: `prices_rents.rent_ppsqm_by_zone_year` (grouped in SQL over `gold.fct_rent_contract`, `is_market_rent`, lines with a real area)
- Caveat: new, single-unit contracts only (C11, C13). Renewals lag the market and are excluded. Ejari coverage before 2010 is too thin to show.

**F3.4 Sales value is concentrated and mostly off-plan.** The top 10 areas took 37% of market-sales value from Oct 2025 to Sep 2026. Business Bay leads with AED 31.7bn (70% off-plan), followed by Madinat Al Mataar with AED 25.2bn (79% off-plan). 8 of the 10 were down on the prior 12 months (Marsa Dubai −52%).
- Chart: [q3_top10_areas_last12m.png](figures/q3_top10_areas_last12m.png)
- Function: `prices_rents.top_areas_by_value` (12 calendar months to the snapshot month, as in `kpi_reconciliation.md` §3)
- Caveat: September 2026 is partial (to the 25th), which slightly lowers the latest window against the prior one.

**F3.5 Mix shift: the raw median understated 2023–25 growth.** In 2023 the raw apartment median rose +1.2%, but like-for-like (zone × bedrooms) it rose +14.5%. JVC, JVT & Arjan grew from 13.9% to 21.4% of apartment sales, while Downtown & Business Bay fell from 20.4% to 13.7%. 2024 (+7.3% raw vs +13.6%) and 2025 (+5.8% vs +12.4%) point the same way; 2022 ran the other way (+30.2% vs +17.4%).
- Chart: [q3_mix_shift_example.png](figures/q3_mix_shift_example.png)
- Function: `prices_rents.mix_shift_inputs` + `prices_rents.like_for_like` (fixed basket: cells with n ≥ 20 in both years, weighted by base-year sales; cells cover 96–100% of sales from 2010)
- Caveat: zone × bedrooms still leaves mix within a cell (project, size, off-plan vs ready). **Implication for Phase 4:** a median confounds composition with price, so the price index must be a hedonic time-dummy model.

## Q4 preview. Gross yields (notebook 03, **preview, proper yields in Phase 4**)

**F4.1 Yields are highest in outer and value zones.** Apartment gross yields over the last 12 months range from 3.1–3.4% in older and prime zones (Qusais roll-up, Bur Dubai & Karama, Jumeirah) to 7.3–9.8% in JVC, Dubailand, Jebel Ali / Dubai South and Silicon Oasis. Villa yields run from 2.9% (Jumeirah) to 7.8% (Deira, roll-up).
- Chart: [q4_gross_yield_preview_by_zone.png](figures/q4_gross_yield_preview_by_zone.png)
- Function: `prices_rents.yield_preview_cells` + `prices_rents.yield_by_zone` (median new rent ÷ median **ready** clean sale price per zone × class × bedrooms, min-n 20 on both sides, sales-weighted, else a zone roll-up)
- Caveat: **preview only.**
  - Coverage: 21 zone × class segments use bedroom cells, 7 use the roll-up and 5 are below min-n.
  - Sanity band: 1 cell (Al Barsha 3-bed apartments, 20%) is outside the 2–15% band (docs/04 §4) and left out.
  - Grain: yields are gross (no service charges or vacancy), and a zone is coarser than the area × sub-type × quarter grain that `agg_yield_quarter` will use in Phase 4.

---

## Sanity check against DLD's published figures, 2023–2025

DLD reports headline "real estate transactions" (sales, mortgages and gifts) and "investments". It does not publish our market-sales definition. So the closest comparisons are our **whole register** (every Sales, Mortgages and Gifts line, AED once per deal) and our **Sales group** (every Sales procedure, including lease-to-own and development). Query: grouped counts and Σ `aed_counted_once` over `gold.fct_transaction` by calendar year.

| Year | Measure | DLD reported | Ours | Difference |
|---|---|---|---|---|
| 2023 | All real-estate transactions | 166,400 / AED 634bn ([Dubai Media Office, 7 Feb 2024](https://mediaoffice.ae/en/news/2024/February/07-02/Dubai-Land-Department-marks-strongest-performance)) | 165,257 / AED 631.3bn | −0.7% / −0.4% |
| 2024 | All real-estate transactions | 226,000 / AED 761bn ([DLD, 26 Jan 2025](https://dubailand.gov.ae/en/news-media/dubai-s-real-estate-sector-records-aed761-billion-in-transactions-in-2024)) | 224,473 / AED 755.2bn | −0.7% / −0.8% |
| 2025 | All real-estate transactions | "over 270,000" / AED 917bn ([Dubai Media Office, 12 Jan 2026](https://dmo.dof.gov.ae/en/news-and-publications/latest-press-releases/dubai-s-real-estate-market-records-new-historic-milestone-with-transactions-exceeding-aed917-billion-usd-2497-bn-in-2025/)); 275,442 / AED 919bn per Gulf News | 266,966 / AED 916.5bn | ≈ −1 to −3% / −0.1 to −0.3% |
| 2024 | Sales | 180,860 / AED 522.36bn (DLD data via [Gulf News, 1 Jan 2026](https://gulfnews.com/amp/story/business%2Fproperty%2Fdubai-property-market-closes-2025-with-record-dh6825-billion-in-sales-1.500396068), secondary) | Sales group 179,240 / AED 518.5bn | −0.9% / −0.7% |
| 2025 | Sales | 214,912 / AED 682.49bn (same Gulf News source) | Sales group 214,529 / AED 680.7bn | −0.2% / −0.3% |
| 2025 | Gifts | 9,556 / AED 57.25bn (same Gulf News source) | 9,556 / AED 57.3bn | exact / +0.1% |
| 2025 | Mortgages | 50,974 / AED 179.26bn (same Gulf News source) | 42,881 lines / AED 178.4bn | **−15.9%** / −0.5% |
| 2023 | Sales | **not verified**: no sales-only figure found in a DLD or Media Office source | Sales group 132,004 / AED 406.8bn | — |

**Reading the check.**
- Totals, sales and gifts agree within about 1% on value and 0–3% on count. The register is complete and the once-per-deal AED correction behaves like DLD's own totals.
- DLD's figures were published at the time. Ours come from the September 2026 extract, so later cancellations and corrections could explain small gaps.
- The **mortgage count** gap (−16% with value within 0.5%) is not explained. DLD may count mortgage procedures differently (for example, one row per party or per release). It doesn't affect any KPI here, which count new mortgages only, but it is worth asking DLD.
- Our headline **market sales** (2023: 129,195 / AED 398.9bn; 2024: 175,437 / AED 506.0bn; 2025: 211,007 / AED 668.3bn) are smaller than DLD's sales by design, because they exclude lease-to-own and development transfers (docs/04 C3, C17).
- DLD's "investments" figures (2023: 157,798 / ~AED 412bn; 2024: 217,000 / AED 526bn; 2025: 258.6k / > AED 680bn) are a different measure. They seem to be counted per investor, so the counts are not comparable; the values are within about 1.5% of our Sales group.

## Phase 4a: price index and yields (see the model reports)

Phase 4a replaced the Q3 and Q4 previews above with models; the full write-ups are separate reports, regenerated by `make train score model-reports`.

- **Hedonic price index:** [`price_index.md`](price_index.md). Rolling-window time-dummy index from January 2011 for Dubai, apartments, villas and 15 zone × type segments, Jan 2019 = 100; validated against DLD's official index (timing-aligned YoY correlation 0.93 / 0.92 / 0.91); 2014→2020 is one drawdown episode; the raw median misreads growth both ways (2022 +30% raw vs +13% like for like, 2023 +1% vs +17%).
- **Gross rental yields:** [`yields.md`](yields.md). New single-line rents vs ready sale prices by area / zone × type × bedrooms × quarter with min-n on both sides: apartments 7.2%, villas 5.2% (Q3 2025–Q2 2026); yields fell from 2016–19 to a 2021 low and partly recovered. It supersedes the Q4 preview.

**F4a.1 The off-plan premium is not a constant: it rose from ~6% to ~38%.** In the rolling-window hedonic fits for apartments, the off-plan coefficient (per sq m, against a ready unit with the same area, bedrooms and size) is **+0.06 log points in the 2011–13 window, +0.06 to +0.08 through 2015–17, then climbs to +0.24 (2018–20), +0.29 (2019–21) and +0.32 (2023–25)**, i.e. a premium of about +6% → +38%. One pooled 2011–2026 fit would apply a single +0.27 (+30%) to every year; that is why the published index uses rolling windows (owner decision, 2026-10-01).
- Chart: [price_index_robustness.png](figures/price_index_robustness.png) (right panel); table in [price_index.md](price_index.md#robustness-rolling-windows-vs-one-pooled-fit)
- Function: `models.hedonic_index.rolling_window_index` (window coefficients in `artifacts/hedonic_index/diagnostics.json`)
- Caveat: a premium per sq m, not per unit, and only for what the data controls (area, bedrooms, size, parking). New off-plan stock also differs in quality and amenities the data doesn't record, so the coefficient carries those too. A trial run that started in 2008 found +0.29 for 2008–10, but those years are dominated by backlog registrations (F1.3) and are not in the published index.

**F4a.2 Villa prices fell 11% from their December 2025 peak to July 2026.** The villa index (bedroom-known villas, monthly) peaked at 243.5 in December 2025 and fell to 216.4 in July 2026, a −11.1% drawdown, the first ≥ 10% villa episode since 2015–20. It stood at 223.6 in September 2026 (−8% from the peak; partial month). Apartments and Dubai overall are flat on a year earlier (+0.1%, +0.8%). This fits the 2026 slowdown led by ready homes (F1.5).
- Chart: [price_index_levels.png](figures/price_index_levels.png); episodes table in [price_index.md](price_index.md#peak-to-trough-episodes)
- Function: `models.hedonic_index.add_metrics` / `find_episodes` on `ml.fct_price_index`
- Caveat: **the latest months of a rolling-window index revise as new data arrives.** The most recent periods come from the last 36-month window, which is re-estimated at every refresh, and late registrations still arrive for recent months. Villa months are also thin (as few as 61 sales), so the size of the fall may change; treat it as provisional until a few more months are in.

## Limitations and what's out of Phase 3

- **Q9 (developer concentration, HHI)** is deferred. It needs developer names from the DLD projects file, which isn't loaded (docs/08 Phase 0).
- **EIBOR** is not loaded, so Fed Funds is the rate proxy (docs/04 Decisions).
- All AED is nominal. No inflation adjustment is made anywhere in this phase.
- Medians and yields follow the min-n rule (20). Blank cells in the charts are below it, not zero.
