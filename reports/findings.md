# Phase 3 findings: market cycles, financing, prices and rents

These are the findings of Phase 3 (exploratory analysis), taken from `notebooks/01_market_cycles.ipynb`, `02_financing_mix.ipynb` and `03_prices_and_rents.ipynb`.

- **Data.** DLD transactions and Ejari rent contracts to the snapshot date, **2026-09-25**. Scope starts 2004-01-01. **2026 is a partial year** (1 Jan – 25 Sep) wherever it appears.
- **Definitions.** Market sales, clean sales, mortgage share and the rest are defined in docs/01 §4 and docs/04.
- **Regenerate.** Run `make eda` after `make dbt`. The charts are written to `reports/figures/`.
- **Code.** Every number comes from a function in `src/dubai_property/analysis/`, which aggregates in SQL over `gold` and `rpt`. The functions are named below as `module.function`.

## Executive summary

1. **Record boom.** Dubai recorded **211,007 market sales worth AED 668.3bn in 2025**: 6.6× the count and 10.2× the value of 2020. ([chart](figures/q1_market_sales_by_year.png))
2. **The 2009 "spike" was paperwork, not demand.** **93.5%** of the 29,898 off-plan sales registered in 2009 were applied for in earlier years. They are a backlog of 2004–08 deals entered into the new off-plan register. ([chart](figures/q1_2009_registration_lag.png))
3. **Off-plan is most sales but not most value.** Off-plan made up **63% of 2025 market sales but 44% of their value** (69% and 50% in 2026 to date). ([chart](figures/q2_offplan_share_count_value.png))
4. **Cash buyers drive the boom.** Only about **1 purchase in 7 is mortgaged** (15.2% in 2025), and since 2010 the mortgage share has barely tracked interest rates (correlation −0.23 with Fed Funds). ([chart](figures/q2_mortgage_share_vs_fedfunds.png))
5. **Lenders moved from a 75% to an 80% loan-to-value norm.** The median observed LTV was exactly 75% every year 2014–2019, and **half of 2026 loans sit at exactly 80%**. ([chart](figures/q2_ltv_by_year.png))
6. **The raw median hid a double-digit price rise in 2023.** The apartment median per sq m rose **+1.2%**, but like-for-like prices rose **+14.5%**, because sales shifted to cheaper zones. This is why the Phase 4 index is hedonic. ([chart](figures/q3_mix_shift_example.png))
7. **Villas have caught up with apartments per sq m.** Villa prices per sq m **more than doubled from 2020 to 2025 (+109%)** against +65% for apartments. In 2026 the villa median has passed the apartment median for the first time. ([chart](figures/q3_price_per_sqm_apartments_villas.png))

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

## Q2. Financing mix (notebook 02)

**F2.1 About one purchase in seven is mortgaged.** Mortgage share was 15.0–15.2% every year from 2022 to 2025, down from a 25.1% peak in 2018 and a 12.2% low in 2013. It is 18.3% in 2026 to date and 23.7% in September 2026.
- Chart: [q2_mortgage_share_vs_fedfunds.png](figures/q2_mortgage_share_vs_fedfunds.png)
- Function: `financing.mortgage_share_monthly` (matches `reports/dq_report.md` §5 and `kpi_reconciliation.md`)
- Caveat: individual new mortgages only; portfolio mortgages are excluded (docs/01 §4). The 27–39% shares of 2004–07 sit on the thin, ready-only register (F1.4).

**F2.2 Rates explain little of the mortgage share.** Since 2010 the trailing-12-month share and the effective Fed Funds rate correlate at −0.23 in levels and −0.20 in 12-month changes. The 2022–23 hikes (0.1% → 5.3%) coincided with the share falling from 20.2% (2021) to 15.0% (2022), but the 2016–19 hikes coincided with a rising share.
- Chart: [q2_mortgage_share_vs_fedfunds.png](figures/q2_mortgage_share_vs_fedfunds.png)
- Function: `financing.share_rate_correlation`
- Caveat: Fed Funds stands in for EIBOR, which isn't loaded yet; the AED is pegged to the USD. This is an association, not a causal estimate. The share falls when cash-heavy off-plan volume rises, whatever rates do.

**F2.3 Off-plan is most sales but not most value.** The off-plan share rose from 40.6% by count (31.0% by value) in 2021 to 63.4% (43.6%) in 2025, and to 68.7% (49.5%) in 2026 to date.
- Chart: [q2_offplan_share_count_value.png](figures/q2_offplan_share_count_value.png)
- Function: `market_cycles.sales_by_year` (`offplan_share_count`, `offplan_share_value`)
- Caveat: off-plan is DLD's `reg_type` at registration. The lower value share reflects cheaper units and locations, not a like-for-like discount.

**F2.4 Observed LTVs follow the regulatory caps.** The median loan ÷ same-day price was exactly 0.75 every year 2014–2019, with 28–34% of loans at exactly 75%. From 2021 the median is 0.80, and 41.1% (2025) and 50.3% (2026) of loans sit at exactly 80%. A second cluster at exactly **84.8%** appeared in 2020 (8.5% of pairs), peaked at 22.4% in 2024, and is 0.0% in 2026.
- Chart: [q2_ltv_by_year.png](figures/q2_ltv_by_year.png), [q2_ltv_distribution_by_year.png](figures/q2_ltv_distribution_by_year.png)
- Function: `financing.ltv_by_year`, `financing.ltv_histogram` (the Phase 1 same-day match rebuilt on `gold.fct_transaction`; 1,572–21,743 pairs a year)
- Caveat: this covers purchase mortgages matched to a same-day sale (Mortgage Registration ↔ Sell, Delayed Mortgage ↔ Delayed Sell), not refinancing. 0.848 = 0.80 × 1.06 suggests a loan sized on price plus costs, but the cause **needs an external source**. The CBUAE caps behind 75% and 80% are to be cited in `seed_ltv_rules` (owner to verify).

**F2.5 Portfolio mortgages are lumpy and kept separate.** Since 2004 there have been 1,873 portfolio mortgage deals worth AED 245.0bn (once per deal). 2022 alone had AED 80.8bn across 151 deals.
- Chart: [q2_portfolio_mortgages.png](figures/q2_portfolio_mortgages.png)
- Function: `financing.portfolio_by_year`
- Caveat: the value is as registered, not a verified loan amount (C10). Deals are inferred by rule C16.

## Q3. Prices and rents (notebook 03)

**F3.1 Villas have caught up with apartments per sq m.** The median apartment price per sq m went from AED 11,314 (2020) to 18,657 (2025), +65%. Villas / townhouses went from 7,528 to 15,700, +109%. In 2026 to date the villa median (18,672) is above the apartment median (18,568) for the first time. Area-weighted apartment prices run 10–26% above the median every year from 2010 (larger units cost more per sq m).
- Chart: [q3_price_per_sqm_apartments_villas.png](figures/q3_price_per_sqm_apartments_villas.png)
- Function: `prices_rents.ppsqm_by_year` (exact medians over clean sales; area-weighted Σ AED ÷ Σ sq m from `agg_area_month`)
- Caveat: these are raw medians, so composition shifts move them (F3.5). 1 sq m = 10.7639 sq ft.

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

## Limitations and what's out of Phase 3

- **Q9 (developer concentration, HHI)** is deferred. It needs developer names from the DLD projects file, which isn't loaded (docs/08 Phase 0).
- **EIBOR** is not loaded, so Fed Funds is the rate proxy (docs/04 Decisions).
- All AED is nominal. No inflation adjustment is made anywhere in this phase.
- Medians and yields follow the min-n rule (20). Blank cells in the charts are below it, not zero.
