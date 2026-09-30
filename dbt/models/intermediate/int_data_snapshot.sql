-- The data snapshot date: the latest valid transaction date in the register (one row).
-- It ends the reporting scope (docs/04 §3), is the "Data As Of" date in the report, and
-- anchors "last 12 months". Ejari registers leases ahead of their start, so rent contracts
-- can start after it; those are flagged in int_rent_contracts (C18 is_start_after_snapshot)
-- and kept out of market rent and the rent aggregates. Owner decision 2026-09-30.

select max(txn_date) as data_snapshot_date
from {{ ref('stg_transactions') }}
where txn_date is not null
