{#- Category + cause rules (config/thresholds.yaml via --vars). First match wins, in table order. -#}

{% macro fmt_num(x) %}{{ '%g' % x }}{% endmacro %}

{% macro category_case(t, abs_usd='abs_residual_usd') %}
    case
        when status <> 'settled' then null
        when diff_local = 0 then 'exact'
        when abs(diff_local) <= {{ t.rounding_minor_units }} then 'rounding'
        when abs(residual_pct) <= {{ t.fx_tolerance_pct }} and {{ abs_usd }} < {{ t.large_usd }} then 'fx_tolerance'
        when abs(residual_pct) <= {{ t.large_pct }} and {{ abs_usd }} < {{ t.large_usd }} then 'meaningful'
        else 'large'
    end
{% endmacro %}

{% macro why_flagged_case(t) %}
    case
        when category = 'meaningful' then '{{ fmt_num(t.fx_tolerance_pct) }}–{{ fmt_num(t.large_pct) }}%'
        when category <> 'large' or category is null then null
        when abs(residual_pct) > {{ t.large_pct }} and abs_residual_usd >= {{ t.large_usd }}
            then '> {{ fmt_num(t.large_pct) }}% and ≥ ${{ fmt_num(t.large_usd) }}'
        when abs_residual_usd >= {{ t.large_usd }} then '≥ ${{ fmt_num(t.large_usd) }}'
        else '> {{ fmt_num(t.large_pct) }}%'
    end
{% endmacro %}

{#- No PSP names here: the analysis must *find* the PSP behind a cause. -#}
{% macro likely_cause_case(t) %}
    {%- set c = t.causes -%}
    case
        when category is null or category = 'exact' then null
        when category = 'rounding' then 'psp_rounding'
        when is_cross_border and abs(residual) <= 1 then 'fx_timing'
        when rounding_flag then 'psp_rounding'
        when residual < 0 and item_count >= 2
         and abs(settled_amount - expected_settled * (item_count - 1) / item_count)
             <= expected_settled * {{ c.partial_tolerance_pct }} / 100 then 'partial_capture'
        when residual < 0 and abs_residual_usd >= {{ c.fee_min_usd }}
         and fee_repeats >= {{ c.fee_min_repeats }} then 'psp_fee'
        when tax_recalc and not is_cross_border and abs(residual_pct) < 2 then 'tax_recalc'
        when residual < 0 and risk_score >= {{ c.high_risk_score }}
         and -residual_pct between 10 and 20 then 'fraud_hold'
        when residual < 0 and -residual_pct between 2 and 5 then 'psp_adjustment'
        when residual > 0 then 'tip'
        else 'unexplained'
    end
{% endmacro %}
