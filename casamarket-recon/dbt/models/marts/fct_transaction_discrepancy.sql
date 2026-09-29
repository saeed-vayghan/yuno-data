-- FR1 output: one enriched row per transaction (all statuses; money fields null unless settled).
-- expected = auth x fx_settle / fx_auth (cross-border) or auth (domestic); residual = settled - expected.
{% set t = var('thresholds') %}
with expected as (
    select *,
        case when is_cross_border then round(authorized_amount * fx_settle / fx_auth)::bigint  -- same op order as core.money
             else authorized_amount end                                        as expected_settled,
        ({{ t.causes.rounding_step_major }} * pow(10, exponent))::bigint       as rounding_step
    from {{ ref('int_transactions_usd') }}
), money as (
    select *,
        settled_amount - authorized_amount                                     as diff_local,
        settled_amount - expected_settled                                      as residual,
        round(100.0 * (settled_amount - expected_settled) / expected_settled, 4) + 0.0 as residual_pct,  -- + 0.0: no -0.0
        round((settled_amount - expected_settled) / pow(10, exponent) / fx_auth, 2) + 0.0 as residual_usd,  -- auth-day rate
        round(settled_amount / pow(10, exponent) / fx_auth, 2)                 as settled_usd,
        settle_lag_days > {{ t.lag_outlier_days }}                             as is_lag_outlier
    from expected
), categorized as (
    select *,
        abs(residual_usd)                                                      as abs_residual_usd,
        {{ category_case(t, 'abs(residual_usd)') }}                            as category
    from money
), flagged as (
    select *,
        coalesce(category in ('meaningful', 'large'), false)                   as is_meaningful,
        case when residual < 0 then 'under' when residual > 0 then 'over'
             when residual = 0 then 'none' end                                 as direction,
        coalesce(residual < 0 and settled_amount % rounding_step = 0
                 and expected_settled - settled_amount < rounding_step, false) as rounding_flag,
        case when category <> 'exact' then count(*) over (
            partition by psp, currency, residual, category <> 'exact') end    as fee_repeats
    from categorized
)
select
    * exclude (rounding_step),
    {{ why_flagged_case(t) }}                                                  as why_flagged,
    {{ likely_cause_case(t) }}                                                 as likely_cause
from flagged
order by transaction_id
