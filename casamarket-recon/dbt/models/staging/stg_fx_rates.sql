-- Daily FX: local currency units per 1 USD, every calendar day.
select
    currency || '|' || rate_date::varchar  as fx_key,
    rate_date::date                        as rate_date,
    upper(trim(currency))                  as currency,
    local_per_usd::double                  as local_per_usd
from {{ source('raw', 'fx_rates_daily') }}
