# 04 · dbt models and tests (`recon build`)

**Goal:** turn `data/raw` CSVs into one enriched row per transaction (`fct_transaction_discrepancy`) plus 4 small marts in `data/casarecon.duckdb`, with dbt tests that stop the run (exit 5).

**Time box:** 30 min · **Core**

## Inputs
- Files 02 part A (`dbt_vars()`, `DB_PATH`), 03 (`data/raw/*.csv`).
- IMPLEMENTATION-PLAN "Data model", S2.1–S2.6 · decision sheet "Money and FX", "Categories" · research 02 "Cause labels".
- Diagram: `../../architect/03-system-design/03-data-pipeline.svg`.

## The 13 nodes

| # | Node | Kind | Layer | Grain | Key |
|---|---|---|---|---|---|
| 1 | `raw.transactions` | source (CSV) | raw | txn | `transaction_id` |
| 2 | `raw.fx_rates_daily` | source (CSV) | raw | date × currency | `rate_date, currency` |
| 3 | `currency_exponents` | seed | ref | currency | `currency` (CLP 0, others 2) |
| 4 | `psp_fees` | seed | ref | PSP | `psp` (`contract_fee_usd` = 0 for all) |
| 5 | `vat_rates` | seed | ref | country | `country` (MX 16, CO 19, AR 21, CL 19; `tax_recalc` true for MX, CO) |
| 6 | `stg_transactions` | model | staging | txn | `transaction_id` |
| 7 | `stg_fx_rates` | model | staging | date × currency | `fx_key` |
| 8 | `int_transactions_usd` | model | intermediate | txn | `transaction_id` |
| 9 | `fct_transaction_discrepancy` | model | marts | txn (all statuses) | `transaction_id` |
| 10 | `mart_segment_rates` | model | marts | segment_type × value | `segment_key` |
| 11 | `mart_psp_weekly` | model | marts | PSP × country × ISO week | `psp_week_key` |
| 12 | `mart_outliers` | model | marts | `large` txn | `transaction_id` |
| 13 | `mart_cause_summary` | model | marts | cause × PSP × country × direction | `cause_key` |

## Steps

1. **`dbt/dbt_project.yml`:** name `casarecon`; `models: +materialized: table`; schemas `staging`, `intermediate`, `marts`; `seeds: +schema: ref`.
   Use a `generate_schema_name` macro that returns the custom schema as-is (so tables are `marts.fct_…`, not `main_marts.fct_…`).

2. **`dbt/profiles.yml`:**
   ```yaml
   casarecon:
     target: local
     outputs:
       local:
         type: duckdb
         path: "{{ env_var('CASARECON_BUILD_PATH', '../data/casarecon.duckdb') }}"
         threads: 4
   ```

3. **Seeds** in `dbt/seeds/` + `_seeds.yml` (`unique`, `not_null`; `exponent` accepted values `[0, 2]`).

4. **Sources** `models/staging/_sources.yml` (dbt-duckdb `external_location`, explicit column types from the contract):
   ```yaml
   sources:
     - name: raw
       tables:
         - name: transactions
           meta:
             external_location: >
               read_csv('{{ env_var("CASARECON_RAW_DIR", "../data/raw") }}/transactions.csv', header=true,
                 columns={'transaction_id':'VARCHAR', 'authorized_amount':'BIGINT', 'settled_amount':'BIGINT',
                          'auth_ts':'TIMESTAMP', 'settle_ts':'TIMESTAMP', ... })
           columns:
             - name: transaction_id
               data_tests: [unique, not_null]
         - name: fx_rates_daily
           meta: {external_location: "read_csv('…/fx_rates_daily.csv', header=true, columns={…})"}
   ```

5. **Staging:** `stg_transactions.sql` renames, casts, trims; keeps failed + pending rows; `contract: {enforced: true}`. `stg_fx_rates.sql` adds `fx_key = currency || '|' || rate_date`. Tests: `unique`/`not_null` keys; `accepted_values` on `status, country, currency, psp, payer_currency`; `local_per_usd > 0`; singular `tests/assert_settle_after_auth.sql`:
   ```sql
   select * from {{ ref('stg_transactions') }} where status = 'settled' and settle_ts < auth_ts
   ```

6. **Intermediate** `int_transactions_usd.sql`: put **all joins here**, so the fact model reads one input (easy unit tests).
   ```sql
   select t.*, e.exponent, v.tax_recalc,
          fa.local_per_usd as fx_auth,
          fs.local_per_usd as fx_settle,                                   -- null unless settled
          t.authorized_amount / pow(10, e.exponent) / fa.local_per_usd as amount_usd,
          (fs.local_per_usd / fa.local_per_usd - 1) * 100 as fx_move_pct
   from {{ ref('stg_transactions') }} t
   join {{ ref('currency_exponents') }} e using (currency)
   join {{ ref('vat_rates') }} v using (country)
   join {{ ref('stg_fx_rates') }} fa on fa.currency = t.currency and fa.rate_date = t.auth_ts::date
   left join {{ ref('stg_fx_rates') }} fs on fs.currency = t.currency and fs.rate_date = t.settle_ts::date
   ```
   Tests: `unique` key; `not_null` `amount_usd`, `fx_auth`; `relationships` to `stg_fx_rates`.

7. **Fact** `fct_transaction_discrepancy.sql` (the FR1 output). Skeleton:
   ```sql
   {% set t = var('thresholds') %}
   with b as (
     select *,
       case when is_cross_border then round(authorized_amount * fx_settle / fx_auth)::bigint   -- same op order as Python
            else authorized_amount end as expected_settled
     from {{ ref('int_transactions_usd') }}
   ), m as (
     select *,
       settled_amount - authorized_amount                                   as diff_local,
       settled_amount - expected_settled                                    as residual,
       round(100.0 * (settled_amount - expected_settled) / expected_settled, 4) as residual_pct,   -- percent
       round((settled_amount - expected_settled) / pow(10, exponent) / fx_auth, 2) as residual_usd -- auth-day rate
     from b
   )
   select *,
     abs(residual_usd) as abs_residual_usd,
     case when residual < 0 then 'under' when residual > 0 then 'over' else 'none' end as direction,
     case                                                     -- first match wins, table order
       when status <> 'settled' then null
       when diff_local = 0 then 'exact'
       when abs(diff_local) <= {{ t.rounding_minor_units }} then 'rounding'
       when abs(residual_pct) <= {{ t.fx_tolerance_pct }} and abs(residual_usd) < {{ t.large_usd }} then 'fx_tolerance'
       when abs(residual_pct) <= {{ t.large_pct }}        and abs(residual_usd) < {{ t.large_usd }} then 'meaningful'
       else 'large'
     end as category
     -- then: is_meaningful, why_flagged, time fields, tiers, rounding_flag, likely_cause (below)
   from m
   ```
   Other columns (IMPLEMENTATION-PLAN list, plus `why_flagged`):
   | Column | Rule |
   |---|---|
   | `is_meaningful` | `category in ('meaningful','large')` |
   | `why_flagged` | null unless flagged; e.g. `'> 5% and ≥ $20'`, `'≥ $20'`, `'> 5%'`, `'2–5%'` |
   | `settle_lag_days` | `date_diff('second', auth_ts, settle_ts) / 86400.0` |
   | `is_lag_outlier` | `settle_lag_days > lag_outlier_days` |
   | `lag_bucket` | floor of lag: `'≤1','2-3','4-5','6-7','8+'` |
   | `auth_date`, `auth_weekday` | `auth_ts::date`, `strftime(auth_ts, '%a')` (Mon…Sun) |
   | `is_weekend` | `isodow(auth_ts) in (6, 7)` (merchant local time) |
   | `auth_week` | `strftime(auth_ts, '%G-W%V')` (ISO) |
   | `week_start` | `date_trunc('week', auth_ts)::date` (Monday) |
   | `auth_month` | `strftime(auth_ts, '%Y-%m')` |
   | `week_month` | `strftime(date_trunc('week', auth_ts) + interval 3 day, '%Y-%m')` (Thursday rule) |
   | `amount_tier` | `amount_usd < 50 → '10-50'`, `< 200 → '50-200'`, else `'200+'` |
   | `is_over_300` | `amount_usd > 300` |
   | `rounding_flag` | `residual < 0 and settled_amount % step = 0 and expected_settled - settled_amount < step`, `step = (rounding_step_major * 10^exponent)::bigint` |
   | `fee_repeats` (helper) | `count(*) over (partition by psp, currency, residual)` on settled non-exact rows |

   **`likely_cause`** (non-exact settled rows only; first match wins; **no PSP names**):
   ```sql
   case
     when category is null or category = 'exact' then null
     when category = 'rounding'                                         then 'psp_rounding'
     when is_cross_border and abs(residual) <= 1                        then 'fx_timing'
     when rounding_flag                                                 then 'psp_rounding'
     when residual < 0 and item_count >= 2
      and abs(settled_amount - expected_settled * (item_count - 1) / item_count)
          <= expected_settled * {{ t.causes.partial_tolerance_pct }} / 100 then 'partial_capture'
     when residual < 0 and abs_residual_usd >= {{ t.causes.fee_min_usd }}
      and fee_repeats >= {{ t.causes.fee_min_repeats }}                 then 'psp_fee'
     when tax_recalc and not is_cross_border and abs(residual_pct) < 2  then 'tax_recalc'   -- both signs
     when residual < 0 and risk_score >= {{ t.causes.high_risk_score }}
      and -residual_pct between 10 and 20                               then 'fraud_hold'
     when residual < 0 and -residual_pct between 2 and 5                then 'psp_adjustment'
     when residual > 0                                                  then 'tip'
     else 'unexplained'
   end
   ```
   Tests: `unique`/`not_null` key; `accepted_values` on `category`, `direction`, `likely_cause`; contract enforced; `tests/assert_fct_rowcount_matches_stg.sql`.

> **Decision (tax sign):** ⚡ Kaveh: research 02 writes `tax_recalc` as "under by < 2%", but X4 is planted with both signs; positive X4 rows would fall into `tip` and break "tip: ruled out". 🏛️ Jamshid: `tax_recalc` accepts both signs (domestic MX/CO, |residual| < 2%).

8. **dbt unit tests** `models/marts/_unit_tests.yml` (hand-worked rows, input = `int_transactions_usd`):
   | Test | Input (minor units) | Expect |
   |---|---|---|
   | FX row (MXN, cross-border) | auth 100000, fx 18.00 → 18.18, settled 101000 | expected 101000, residual 0, `fx_tolerance`, `fx_timing`, not flagged |
   | CLP 0 decimals | auth 95000 CLP, fx 950, settled 90250 | residual −4750, −5.0% → `meaningful` (5% is not > 5), $ −5.00, `psp_adjustment` |
   | Brief "2¢ on $500" | MXN, fx 18, auth 900000, settled 899964 | `fx_tolerance`, not flagged |
   | Brief "$20" | MXN, fx 20, auth 1000000, settled 960000 | residual_usd −20.00 → `large` |
   | Just under $20 | same, settled 960020 | −$19.99, −4.0% → `meaningful` |
   | Rounding | CLP, settled = auth − 1 | `rounding`, `psp_rounding` |
   | One row per cause | partial (n=2, 50%), fee (repeated), tax (+1%), fraud (15%, risk 0.9), P4 (COP, ends in 00000) | the matching label |
   ```yaml
   unit_tests:
     - name: ut_brief_20_usd_is_large
       model: fct_transaction_discrepancy
       given:
         - input: ref('int_transactions_usd')
           rows:
             - {transaction_id: t1, status: settled, currency: MXN, exponent: 2, is_cross_border: false,
                authorized_amount: 1000000, settled_amount: 960000, fx_auth: 20.0, fx_settle: 20.0, ...}
       expect:
         rows:
           - {transaction_id: t1, residual_usd: -20.00, category: large, is_meaningful: true}
   ```

9. **Marts** (settled rows only for rates; `ORDER BY` the key in every model):
   - `mart_psp_weekly`: `psp, country, auth_week, week_start, week_end, week_month, n, n_flagged, rate, n_large, gross_under_usd, gross_over_usd, net_usd, low_sample (n < min_sample.worst_week), psp_week_key`.
   - `mart_segment_rates`: one Jinja loop over the 10 segment types (`country, currency, psp, psp_country ('PSP_B|AR'), amount_tier, country_tier ('CO|200+'), weekday, is_weekend, lag_bucket, cross_border`) with `union all`; columns `n, n_flagged, rate, n_large, gross_under_usd, gross_over_usd, net_usd, mean_loss_usd, median_loss_usd, segment_key`.
   - `mart_outliers`: `category = 'large'` rows with TXN columns (minus masking; core masks).
   - `mart_cause_summary`: non-exact settled rows by `likely_cause, psp, country, direction`: `n, n_flagged, gross_under_usd, gross_over_usd, net_usd, cause_key`.
   - Money sign everywhere: `gross_under_usd = sum(greatest(-residual_usd, 0))`, `gross_over_usd = sum(greatest(residual_usd, 0))`, `net_usd = under − over`. `mean_loss_usd`/`median_loss_usd` = mean/median of `-residual_usd` over flagged rows.
   - Singular tests: `assert_outliers_are_large.sql`, `assert_cause_usd_reconciles.sql` (sum `net_usd` = `sum(-residual_usd)` over settled fct rows, tolerance $0.05); `n_flagged ≤ n` on marts.

10. **`core/build.py` + wire `recon build`:**
    ```python
    def run_build() -> dict:
        tmp = DB_PATH.with_name(DB_PATH.name + ".tmp"); tmp.unlink(missing_ok=True)
        os.environ["CASARECON_BUILD_PATH"] = str(tmp)
        os.environ["CASARECON_RAW_DIR"] = str(RAW_DIR)
        res = dbtRunner().invoke(["build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
                                  "--vars", dbt_vars()])
        if res.exception: raise res.exception                   # → exit 1
        if not res.success: tmp.unlink(missing_ok=True); raise DataQualityError("dbt build failed")  # → exit 5
        counts = row_counts(tmp)                                 # raw, staging, intermediate, marts
        os.replace(tmp, DB_PATH)                                 # atomic swap: full rebuild
        write_manifest(counts, versions)                         # reports/run_manifest.json
        return counts
    ```

> **Decision (atomic swap):** IMPLEMENTATION-PLAN says "delete the old DB, rebuild". ⚡ Kaveh: build into `casarecon.duckdb.tmp` and `os.replace` at the end; it is still a full rebuild, the lock window for the dashboard shrinks to ~0, and a failed build keeps the last good DB. 🏛️ Jamshid: agreed, 3 lines.

## Done when
| Command | Expected |
|---|---|
| `cd dbt && uv run dbt seed --profiles-dir .` | exit 0 |
| `uv run recon generate --rows 500 && uv run recon build` | exit 0; log shows row counts for raw, staging, intermediate, marts; all unit tests PASS |
| `uv run python -c "import duckdb; c=duckdb.connect('data/casarecon.duckdb', read_only=True); print(c.sql('select count(*), count(distinct transaction_id) from marts.fct_transaction_discrepancy').fetchall())"` | `[(500, 500)]` |
| same, `select category, count(*) from marts.fct_transaction_discrepancy group by 1` | 5 categories + null (failed/pending) |
| edit one CSV row so `settle_ts < auth_ts`, `uv run recon build; echo $?` | `5`; old DB still there |
| full run `uv run recon generate && uv run recon build` | exit 0 in < 60 s |

## Serves
FR1 (ingest, calculate, flag, enrich) · Done "accurately calculate discrepancies" · Pipeline 20 (tests on every model, FX formula unit-tested, CLP right).

## Pitfalls
- **$20 boundary:** `large` = `≥ $20` on `abs(residual_usd)` rounded to cents; `meaningful` = `< $20`. Exactly 5% is `meaningful`; exactly 2% is `fx_tolerance`.
- **Raw Δ vs residual:** `exact` and `rounding` use `diff_local` (raw); the other three use the residual. Cross-border rows are therefore never `exact`.
- **`residual_pct` is in percent** (−3.2 = −3.2%), matching `thresholds.yaml`. Do not mix fractions.
- **CLP 0 decimals:** `pow(10, exponent)`, never `/ 100`.
- **Rounding parity:** `round(auth * fx_settle / fx_auth)` must use the same op order as `core.money.expected_settled`.
- **Integer division:** `expected_settled * (item_count - 1) / item_count` — DuckDB `/` on integers returns a double (ok); `//` would truncate.
- **Paths:** dbt resolves the DuckDB path and `read_csv` path from the process cwd. `recon build` always sets absolute paths via env vars.
- **dbt ≥ 1.10 test syntax:** generic test args go under `arguments:` (`accepted_values: {arguments: {values: [...]}}`); old style only warns, but keep logs clean.
- **Determinism:** 4 threads + no `ORDER BY` = row order changes between runs. Every mart ends with `ORDER BY` its key.
- **Truth labels** are never a dbt source.
- Do not name a PSP in any cause rule; config holds only generic numbers.

## Hand-off
- File 02 part B: write the Core query functions on these marts now.
- File 05 reads `fct_transaction_discrepancy` read-only.
- Frontend: tables `marts.*` exist; access them only through core.
