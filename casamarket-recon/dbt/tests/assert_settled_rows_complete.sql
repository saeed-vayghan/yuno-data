-- Settled rows carry settle_ts + settled_amount; other statuses carry neither.
select * from {{ ref('stg_transactions') }}
where (status = 'settled') <> (settle_ts is not null and settled_amount is not null)
