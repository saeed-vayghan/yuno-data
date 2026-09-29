select * from {{ ref('stg_fx_rates') }} where local_per_usd <= 0
