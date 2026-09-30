-- Purchase mortgages: a new mortgage and a ready sale of the same unit on the same day
-- (the Phase 1 match, reports/phase1_findings.md §2). One row per matched pair.
--
-- Why: the DLD register has no link between a sale and the loan that funded it. A
-- mortgaged purchase registers a sale line *and* a mortgage line, and new mortgages also
-- include refinancing, so "mortgages / (mortgages + sales)" double-counts. Matching the
-- two legs of one purchase gives a numerator that is a subset of the sales it divides.
--
-- Rule:
--   * pairs: Mortgage Registration <-> Sell, Delayed Mortgage <-> Delayed Sell (the two
--     mortgage procedures whose amount is a verified loan, C10, and their ready sales);
--   * key: date, area, building, project, sq m, rooms, property type and sub-type;
--   * the key must be unique on both sides (among those four procedures), otherwise two
--     units on one day could be crossed;
--   * lines of an inferred portfolio deal (C16 is_repeated_deal_value) are left out:
--     their value is a group total, not one unit's price or loan.
--
-- It is a LOWER BOUND on mortgaged purchases: a loan registered on another day, or with a
-- key field typed differently, is not matched (only 26-58% of Mortgage Registrations a
-- year find a sale). Refinancing and loans on units bought earlier never match, by design.

-- Implementation: one md5 unit key per line and a single GROUP BY on it, keeping keys
-- with exactly one sale line and one mortgage line. No self-join: a join on the key
-- columns (or on the md5 key, which has no statistics) gets a tiny row estimate and a
-- nested loop over hundreds of thousands of rows.

with legs as (

    select
        'sale' as side, transaction_id, txn_date, procedure_name, actual_worth_aed,
        is_repeated_deal_value,
        md5(concat_ws('|', txn_date, coalesce(area_id, -1), coalesce(building_name, ''),
                      coalesce(project_number, -1), area_sqm, coalesce(rooms_en, ''),
                      coalesce(property_type, ''), coalesce(property_sub_type, '')))
            as unit_key
    from {{ ref('int_market_sales') }}
    where procedure_name in ('Sell', 'Delayed Sell')
      and is_market_sale and not is_offplan
      and txn_date is not null and area_sqm is not null

    union all

    select
        'mortgage' as side, transaction_id, txn_date, procedure_name, actual_worth_aed,
        is_repeated_deal_value,
        md5(concat_ws('|', txn_date, coalesce(area_id, -1), coalesce(building_name, ''),
                      coalesce(project_number, -1), area_sqm, coalesce(rooms_en, ''),
                      coalesce(property_type, ''), coalesce(property_sub_type, '')))
    from {{ ref('int_mortgages') }}
    where procedure_name in ('Mortgage Registration', 'Delayed Mortgage')
      and txn_date is not null and area_sqm is not null

),

units as (

    select
        unit_key,
        min(transaction_id) filter (where side = 'mortgage') as mortgage_transaction_id,
        min(transaction_id) filter (where side = 'sale') as sale_transaction_id,
        min(txn_date) as txn_date,
        min(procedure_name) filter (where side = 'mortgage') as mortgage_procedure,
        min(procedure_name) filter (where side = 'sale') as sale_procedure,
        min(actual_worth_aed) filter (where side = 'mortgage') as loan_aed,
        min(actual_worth_aed) filter (where side = 'sale') as sale_price_aed,
        bool_or(is_repeated_deal_value) as has_repeated_deal_value
    from legs
    group by unit_key
    having count(*) filter (where side = 'sale') = 1
       and count(*) filter (where side = 'mortgage') = 1

)

select
    mortgage_transaction_id,
    sale_transaction_id,
    txn_date,
    mortgage_procedure,
    sale_procedure,
    loan_aed,
    sale_price_aed,
    -- Observed loan-to-value: the loan over the price of the same purchase.
    round(loan_aed / nullif(sale_price_aed, 0), 6) as purchase_ltv
from units
where (mortgage_procedure, sale_procedure) in (
    ('Mortgage Registration', 'Sell'), ('Delayed Mortgage', 'Delayed Sell')
)
  and not has_repeated_deal_value
