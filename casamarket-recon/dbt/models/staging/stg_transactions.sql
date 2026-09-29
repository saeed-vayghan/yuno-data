-- One row per raw transaction (all statuses). Trim + cast only; no business logic.
select
    trim(transaction_id)                  as transaction_id,
    trim(customer_id)                     as customer_id,
    trim(product_category)                as product_category,
    upper(trim(country))                  as country,
    upper(trim(currency))                 as currency,
    upper(trim(payer_currency))           as payer_currency,
    is_cross_border::boolean              as is_cross_border,
    upper(trim(psp))                      as psp,
    lower(trim(status))                   as status,
    auth_ts::timestamp                    as auth_ts,
    settle_ts::timestamp                  as settle_ts,
    authorized_amount::bigint             as authorized_amount,
    settled_amount::bigint                as settled_amount,
    item_count::integer                   as item_count,
    risk_score::double                    as risk_score,
    upper(trim(card_bin_country))         as card_bin_country
from {{ source('raw', 'transactions') }}
