-- A settled row can never settle before it was authorized.
select * from {{ ref('stg_transactions') }} where status = 'settled' and settle_ts < auth_ts
