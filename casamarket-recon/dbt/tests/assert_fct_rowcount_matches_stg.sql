-- No transaction may be dropped or duplicated by the joins (e.g. a missing FX day).
select s.n as stg_rows, f.n as fct_rows
from (select count(*) as n from {{ ref('stg_transactions') }}) s,
     (select count(*) as n from {{ ref('fct_transaction_discrepancy') }}) f
where s.n <> f.n
