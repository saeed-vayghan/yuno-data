-- Guard the brief's boundaries on real rows: large = > 5% or >= $20; meaningful < $20 and 2-5%.
select transaction_id, category, residual_pct, abs_residual_usd
from {{ ref('fct_transaction_discrepancy') }}
where (category = 'meaningful' and (abs_residual_usd >= 20 or abs(residual_pct) > 5 or abs(residual_pct) <= 2))
   or (category = 'large' and abs_residual_usd < 20 and abs(residual_pct) <= 5)
   or (category = 'exact' and diff_local <> 0)
