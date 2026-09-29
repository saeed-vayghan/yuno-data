-- USD by merchant x likely cause x PSP x country x direction, non-exact settled rows.
select
    merchant_id, likely_cause, psp, country, direction,
    count(*)                                                 as n,
    count_if(is_meaningful)::bigint                          as n_flagged,
    round(sum(greatest(-residual_usd, 0)), 2)                as gross_under_usd,
    round(sum(greatest(residual_usd, 0)), 2)                 as gross_over_usd,
    round(sum(-residual_usd), 2)                             as net_usd,
    likely_cause || '|' || psp || '|' || country || '|' || direction as cause_key
from {{ ref('fct_transaction_discrepancy') }}
where status = 'settled' and category <> 'exact'
group by merchant_id, likely_cause, psp, country, direction
order by merchant_id, cause_key
