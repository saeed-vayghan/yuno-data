{#- Incremental helpers (`recon build --incremental`). A full build never calls the filters. -#}

{#- Rows an incremental run reprocesses: authorised or settled inside the restatement window
    (last build's as_of - lookback_days), still pending last time, or not seen before.
    Rows outside the window are trusted as final (restating older rows needs a full build). -#}
{% macro restated_rows() %}
(
    greatest(auth_ts, coalesce(settle_ts, auth_ts)) >= (
        select max(greatest(auth_ts, coalesce(settle_ts, auth_ts))) from {{ this }}
    ) - to_days({{ var('lookback_days') }})
    or transaction_id in (select transaction_id from {{ this }} where status = 'pending')
    or transaction_id not in (select transaction_id from {{ this }})
)
{% endmacro %}

{#- expected = auth x fx_settle / fx_auth (cross-border) or auth (domestic); same op order as core.money. -#}
{% macro expected_settled_sql() %}
case when is_cross_border then round(authorized_amount * fx_settle / fx_auth)::bigint
     else authorized_amount end
{% endmacro %}
