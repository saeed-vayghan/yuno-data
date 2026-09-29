"""One read-only SQL over the fact table -> the numbers the validation gate checks.

The validator may name PSPs: it checks the planted spec (the dbt cause rules may not).
"""

from casarecon.ports import Store

FCT = "marts.fct_transaction_discrepancy"

METRICS_SQL = f"""
with f as (select * from {FCT}), s as (select * from f where status = 'settled')
select
  (select count(*) from f)                                              as rows,
  (select count(*) from s)                                              as settled,
  (select count(distinct auth_month) from f)                            as months,
  (select list(distinct country order by country) from f)               as countries,
  (select list(distinct currency order by currency) from f)             as currencies,
  (select count(distinct psp) from f)                                   as psps,
  (select count_if(status = 'failed') from f)                           as failed,
  (select count_if(status = 'pending') from f)                          as pending,
  (select median(settle_lag_days) from s)                               as median_lag,
  (select count_if(is_lag_outlier) from s)                              as lag_outliers,
  (select count_if(customer_id is null or product_category is null or amount_tier is null
                   or is_cross_border is null) from f)                  as null_metadata,
  (select count_if(category in ('exact', 'rounding')) from s)           as k_match,
  (select count_if(category = 'fx_tolerance') from s)                   as k_small,
  (select count_if(category in ('meaningful', 'large')) from s)         as k_meaningful,
  (select count_if(category = 'large') from s)                          as k_large,
  (select avg(is_meaningful::int) filter (where psp = 'PSP_B') - avg(is_meaningful::int) filter (where psp <> 'PSP_B')
     from s where country = 'AR')                                        as p1_gap,
  (select median(settle_lag_days) filter (where is_over_300) - median(settle_lag_days) filter (where not is_over_300)
     from s where country = 'CO')                                        as p2_gap_days,
  (select avg(is_meaningful::int) filter (where is_weekend) / avg(is_meaningful::int) filter (where not is_weekend)
     from s)                                                             as p3_ratio,
  (select avg(rounding_flag::int) from s
     where psp = 'PSP_D' and is_cross_border and currency in ('CLP', 'COP')) as p4_share
"""


def read_metrics(store: Store) -> dict:
    row = store.query(METRICS_SQL).iloc[0].to_dict()
    return {k: (list(v) if k in ("countries", "currencies") else v) for k, v in row.items()}
