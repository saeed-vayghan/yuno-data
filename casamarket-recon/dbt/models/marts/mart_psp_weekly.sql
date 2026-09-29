-- Merchant x PSP x country x ISO week (by auth date) on settled rows. week_month = month of the week's Thursday.
-- is_provisional: the week ends inside the restatement window (as_of - lookback_days), so late
-- settlements can still change it. as_of = latest auth/settle timestamp (same rule as core.status).
{% set t = var('thresholds') %}
with fct as (
    select * from {{ ref('fct_transaction_discrepancy') }}
), window_start as (
    select (max(greatest(auth_ts, coalesce(settle_ts, auth_ts))) - to_days({{ var('lookback_days') }}))::date as d
    from fct
)
select
    merchant_id, psp, country, auth_week, week_start, week_end, week_month,
    count(*)                                                    as n,
    count_if(is_meaningful)::bigint                             as n_flagged,
    count_if(is_meaningful) / count(*)                          as rate,
    count_if(category = 'large')::bigint                        as n_large,
    round(sum(greatest(-residual_usd, 0)), 2)                   as gross_under_usd,
    round(sum(greatest(residual_usd, 0)), 2)                    as gross_over_usd,
    round(sum(-residual_usd), 2)                                as net_usd,
    count(*) < {{ t.min_sample.worst_week }}                    as low_sample,
    week_end >= (select d from window_start)                    as is_provisional,
    psp || '|' || country || '|' || auth_week                   as psp_week_key
from fct
where status = 'settled'
group by merchant_id, psp, country, auth_week, week_start, week_end, week_month
order by merchant_id, psp_week_key
