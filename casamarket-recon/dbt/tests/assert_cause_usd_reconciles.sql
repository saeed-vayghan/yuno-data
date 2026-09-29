-- Cause USD sums to the fct total over non-exact settled rows (tolerance $0.05). `exact` rows
-- (diff_local = 0) are no discrepancy by definition, even when a cross-border FX move leaves cents.
-- Every segment type covers all settled rows.
with fct as (
    select count(*) as n, sum(-residual_usd) filter (where category <> 'exact') as net_usd
    from {{ ref('fct_transaction_discrepancy') }} where status = 'settled'
), causes as (select sum(net_usd) as net_usd from {{ ref('mart_cause_summary') }}),
segs as (
    select segment_type, sum(n) as n, sum(n_flagged) as k, max((n_flagged > n)::int) as bad
    from {{ ref('mart_segment_rates') }} group by segment_type
)
select 'cause_usd' as check_name from fct, causes where abs(fct.net_usd - causes.net_usd) > 0.05
union all
select 'segment_' || segment_type from segs, fct where segs.n <> fct.n or segs.bad = 1
