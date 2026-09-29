-- PSP x country x ISO week (by auth date) on settled rows. week_month = month of the week's Thursday.
{% set t = var('thresholds') %}
select
    psp, country, auth_week, week_start, week_end, week_month,
    count(*)                                                    as n,
    count_if(is_meaningful)::bigint                             as n_flagged,
    count_if(is_meaningful) / count(*)                          as rate,
    count_if(category = 'large')::bigint                        as n_large,
    round(sum(greatest(-residual_usd, 0)), 2)                   as gross_under_usd,
    round(sum(greatest(residual_usd, 0)), 2)                    as gross_over_usd,
    round(sum(-residual_usd), 2)                                as net_usd,
    count(*) < {{ t.min_sample.worst_week }}                    as low_sample,
    psp || '|' || country || '|' || auth_week                   as psp_week_key
from {{ ref('fct_transaction_discrepancy') }}
where status = 'settled'
group by psp, country, auth_week, week_start, week_end, week_month
order by psp_week_key
