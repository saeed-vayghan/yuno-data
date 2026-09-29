-- Dated reference seeds: valid_from < valid_to and no two ranges of one key overlap (so a join on
-- the auth date finds at most one row; assert_fct_rowcount_matches_stg catches gaps).
with ranges as (
    select 'psp_fees' as seed, psp as k, valid_from, coalesce(valid_to, date '9999-12-31') as valid_to
    from {{ ref('psp_fees') }}
    union all
    select 'vat_rates', country, valid_from, coalesce(valid_to, date '9999-12-31') from {{ ref('vat_rates') }}
), numbered as (
    select *, row_number() over (partition by seed, k order by valid_from) as rn from ranges
)
select a.seed, a.k, a.valid_from, a.valid_to
from numbered a
left join numbered b on a.seed = b.seed and a.k = b.k and a.rn <> b.rn
                    and a.valid_from <= b.valid_from and b.valid_from < a.valid_to
where a.valid_from >= a.valid_to or b.k is not null
