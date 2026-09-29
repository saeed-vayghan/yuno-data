-- Weekly mart totals equal the fact table (settled rows): counts exact, net USD within $0.05.
select m.n, f.n as fct_n, m.net_usd, f.net_usd as fct_net_usd
from (select sum(n) as n, sum(net_usd) as net_usd from {{ ref('mart_psp_weekly') }}) m,
     (select count(*) as n, sum(-residual_usd) as net_usd
      from {{ ref('fct_transaction_discrepancy') }} where status = 'settled') f
where m.n <> f.n or abs(m.net_usd - f.net_usd) > 0.05
   or (select count(*) from {{ ref('mart_psp_weekly') }} where n_flagged > n or n_large > n_flagged) > 0
