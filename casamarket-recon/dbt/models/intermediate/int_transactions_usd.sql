-- All joins live here, so the fact model reads exactly one input (easy unit tests).
-- Also the per-row calendar, tier and lag fields (merchant local time).
with joined as (
    select
        t.*,
        e.exponent,
        v.tax_recalc,
        f.contract_fee_usd,
        fa.local_per_usd                                               as fx_auth,
        fs.local_per_usd                                               as fx_settle,  -- null unless settled
        t.authorized_amount / pow(10, e.exponent) / fa.local_per_usd   as amount_usd,
        (fs.local_per_usd / fa.local_per_usd - 1) * 100                as fx_move_pct,
        round(date_diff('second', t.auth_ts, t.settle_ts) / 86400.0, 2) as settle_lag_days
    from {{ ref('stg_transactions') }} t
    join {{ ref('currency_exponents') }} e using (currency)
    join {{ ref('vat_rates') }} v using (country)
    join {{ ref('psp_fees') }} f using (psp)
    join {{ ref('stg_fx_rates') }} fa on fa.currency = t.currency and fa.rate_date = t.auth_ts::date
    left join {{ ref('stg_fx_rates') }} fs on fs.currency = t.currency and fs.rate_date = t.settle_ts::date
)
select *,
    auth_ts::date                                                      as auth_date,
    strftime(auth_ts, '%a')                                            as auth_weekday,
    isodow(auth_ts) in (6, 7)                                          as is_weekend,
    strftime(auth_ts, '%G-W%V')                                        as auth_week,
    date_trunc('week', auth_ts)::date                                  as week_start,
    (date_trunc('week', auth_ts) + interval 6 day)::date               as week_end,
    strftime(auth_ts, '%Y-%m')                                         as auth_month,
    strftime(date_trunc('week', auth_ts) + interval 3 day, '%Y-%m')    as week_month,  -- month of the Thursday
    case when amount_usd < 50 then '10-50' when amount_usd < 200 then '50-200' else '200+' end as amount_tier,
    amount_usd > 300                                                   as is_over_300,
    case when settle_lag_days is null then null
         when floor(settle_lag_days) <= 1 then '≤1'
         when floor(settle_lag_days) <= 3 then '2-3'
         when floor(settle_lag_days) <= 5 then '4-5'
         when floor(settle_lag_days) <= 7 then '6-7'
         else '8+' end                                                 as lag_bucket
from joined
