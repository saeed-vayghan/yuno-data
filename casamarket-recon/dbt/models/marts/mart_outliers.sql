-- `large` rows only, with the transaction columns (core masks customer_id before it leaves).
select
    transaction_id, merchant_id, auth_date, psp, country, currency, exponent, customer_id, amount_tier,
    is_cross_border, category, likely_cause, why_flagged, authorized_amount, expected_settled,
    settled_amount, diff_local, residual_usd, abs_residual_usd, residual_pct, direction, settle_lag_days
from {{ ref('fct_transaction_discrepancy') }}
where category = 'large'
order by transaction_id
