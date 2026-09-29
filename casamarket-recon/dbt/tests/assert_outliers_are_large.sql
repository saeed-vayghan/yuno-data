-- mart_outliers holds exactly the fct `large` rows.
select o.transaction_id from {{ ref('mart_outliers') }} o
left join {{ ref('fct_transaction_discrepancy') }} f using (transaction_id)
where f.category is distinct from 'large'
union all
select transaction_id from {{ ref('fct_transaction_discrepancy') }}
where category = 'large' and transaction_id not in (select transaction_id from {{ ref('mart_outliers') }})
