{{ config(alias='transactions') }}

-- Transaction lines for Power BI, reporting scope only (2004 onwards, valid date).
-- Left out to keep the import small (docs/06 §1): the text ids (transaction, deal and batch
-- group ids), building names, and the individual C-rule flags, which collapse to
-- "Is Clean Market Sale" / "Has Quality Flag" (the full flags stay in gold.fct_transaction).
--
-- Sum "AED Counted Once" for values: "Price AED" repeats a portfolio deal's total on every
-- unit line (C16) and is for per-line display only. Area-weighted AED per sq m: clean
-- sales with "Area Above Class Cap" = false, within one property class.
select
    txn_date as "Date",
    area_key as "Area Key",
    property_type_key as "Property Type Key",
    procedure_key as "Procedure Key",
    project_key as "Project Key",

    trans_group as "Transaction Group",
    procedure_category as "Procedure Category",
    is_market_sale as "Is Market Sale",
    is_clean_market_sale as "Is Clean Market Sale",
    has_quality_flag as "Has Quality Flag",
    is_new_mortgage as "Is New Mortgage",
    is_portfolio_mortgage as "Is Portfolio Mortgage",
    has_purchase_mortgage as "Has Purchase Mortgage",
    is_purchase_mortgage as "Is Purchase Mortgage",
    is_deal_group_lead as "Is Deal Lead",
    is_lease_to_own as "Is Lease to Own",
    is_offplan as "Is Off-Plan",
    reg_type as "Registration Type",

    property_usage as "DLD Property Usage",
    property_type as "DLD Property Type",
    property_sub_type as "DLD Property Sub-Type",
    rooms_en as "Rooms",
    bedrooms as "Bedrooms",
    has_parking as "Has Parking",
    is_area_above_class_cap as "Area Above Class Cap",

    round(area_sqm, 2) as "Area Sq M",
    {{ rpt_aed('actual_worth_aed') }} as "Price AED",
    {{ rpt_aed('aed_counted_once') }} as "AED Counted Once",
    {{ rpt_aed('price_per_sqm_aed') }} as "Price per Sq M AED",
    {{ rpt_aed('mortgage_amount_once_aed') }} as "Loan Amount AED",
    {{ rpt_aed('portfolio_mortgage_value_once_aed') }} as "Portfolio Mortgage Value AED",
    round(purchase_ltv, 4) as "Purchase LTV"
from {{ ref('fct_transaction') }}
where is_in_report_scope
