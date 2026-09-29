-- Flag rate + USD per segment, settled rows, one block per segment type (union all).
-- Booleans are labelled 'true'/'false'; pairs are 'PSP_B|AR', 'CO|200+'.
-- Keep in sync with SEGMENT_SQL in core/queries/pipeline_q2.py (used when filters are applied).
{% set segments = {
    'country': 'country', 'currency': 'currency', 'psp': 'psp',
    'psp_country': "psp || '|' || country", 'amount_tier': 'amount_tier',
    'country_tier': "country || '|' || amount_tier", 'weekday': 'auth_weekday',
    'is_weekend': 'is_weekend::varchar', 'lag_bucket': 'lag_bucket',
    'cross_border': 'is_cross_border::varchar',
} %}
with settled as (
    select * from {{ ref('fct_transaction_discrepancy') }} where status = 'settled'
), segments as (
    {% for type, expr in segments.items() %}
    select '{{ type }}' as segment_type, {{ expr }} as segment_value, * from settled
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)
select
    segment_type, segment_value,
    count(*)                                                             as n,
    count_if(is_meaningful)::bigint                                      as n_flagged,
    count_if(is_meaningful) / count(*)                                   as rate,
    count_if(category = 'large')::bigint                                 as n_large,
    round(sum(greatest(-residual_usd, 0)), 2)                            as gross_under_usd,
    round(sum(greatest(residual_usd, 0)), 2)                             as gross_over_usd,
    round(sum(-residual_usd), 2)                                         as net_usd,
    round(coalesce(avg(-residual_usd) filter (where is_meaningful), 0), 2)    as mean_loss_usd,
    round(coalesce(median(-residual_usd) filter (where is_meaningful), 0), 2) as median_loss_usd,
    segment_type || ':' || segment_value                                 as segment_key
from segments
group by segment_type, segment_value
order by segment_key
