# dbt
dbt-duckdb project: seeds -> staging -> intermediate -> marts. Run it via `uv run recon build`
(sets absolute paths + `--vars` from `config/thresholds.yaml`); never `dbt` by hand.

| Layer | Nodes |
|---|---|
| seeds (`ref`) | `currency_exponents` (CLP 0), `psp_fees` + `vat_rates` dated (`valid_from` <= auth date < `valid_to`, null = open; fee 0 except PSP_C $1.5 from 2026-06-01 = generator X3; `tax_recalc` MX, CO) |
| sources (`raw`) | `transactions.csv`, `fx_rates_daily.csv` from `$CASARECON_RAW_DIR` (types per `contracts/transactions.yaml`) |
| staging | `stg_transactions` (contract enforced; `merchant_id`, default `casamarket`), `stg_fx_rates` |
| intermediate | `int_transactions_usd` (incremental): every join (exponent, dated VAT + fee on the auth date, auth/settle FX) + calendar/tier/lag fields |
| marts | `fct_transaction_discrepancy` (1 row per txn, incremental), `mart_psp_weekly` (merchant x PSP x country x ISO week, `is_provisional`), `mart_segment_rates` (10 segment types; booleans 'true'/'false', pairs 'PSP_B\|AR'), `mart_cause_summary` (cause x PSP x country x direction, non-exact rows), `mart_outliers` (`large` rows); all marts carry `merchant_id` (a group key; one merchant today) |

- Money: `expected = round(auth * fx_settle / fx_auth)` cross-border, else `auth`; `residual = settled - expected`;
  `residual_usd` at the auth-day rate, 2 dp; `residual_pct` in percent.
- Rules (first match wins) live in `macros/discrepancy_rules.sql`: category (`exact`, `rounding`, `fx_tolerance`,
  `meaningful` < $20 and 2-5%, `large` > 5% or >= $20), `why_flagged`, `likely_cause` (no PSP names).
- Weeks: ISO week of the auth date; `week_month` = month of the week's Thursday.
- Tests: generic tests in the `_*.yml` files, unit tests (hand-worked rows) in `models/marts/_unit_tests.yml`,
  singular tests in `tests/`. Any failure -> `recon build` exits 5 and keeps the last good DB.
- Incremental (`recon build --incremental [--lookback-days N]`, var `lookback_days`, default 15 = max settle lag):
  `int_transactions_usd` and `fct_transaction_discrepancy` are `delete+insert` on `transaction_id`. A run reprocesses
  rows authorised or settled after (last as_of - N days), rows still pending last time and new ids
  (`macros/incremental.sql`). The fct also reprocesses every row sharing a (psp, currency, residual) key with those,
  so the `fee_repeats` window count equals a full build. Other marts are small full tables. Older restatements need a
  full build. A contract/column change fails an incremental run (`on_schema_change: fail`): run a full build.
- Late settlements: `mart_psp_weekly.is_provisional` = week ends on/after as_of - `lookback_days`
  (`core.status()['provisional_weeks']`). W25 is the last closed week and still provisional on the full run.
