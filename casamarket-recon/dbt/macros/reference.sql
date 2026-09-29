{#- Dated reference data (SCD2 seeds). -#}

{#- True when `valid_from <= day < valid_to` (valid_to null = open) for a dated reference seed. -#}
{% macro valid_on(alias, day) %}
({{ alias }}.valid_from <= {{ day }} and ({{ alias }}.valid_to is null or {{ day }} < {{ alias }}.valid_to))
{% endmacro %}
