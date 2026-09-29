# dbt
dbt-duckdb project: seeds -> staging -> intermediate -> marts. Run it via `uv run recon build`
(sets absolute paths + `--vars` from `config/thresholds.yaml`); never `dbt` by hand.

| Layer | Nodes |
|---|---|
| seeds (`ref`) | `currency_exponents` (CLP 0), `psp_fees` (0 for all), `vat_rates` (`tax_recalc` MX, CO) |
| sources (`raw`) | `transactions.csv`, `fx_rates_daily.csv` from `$CASARECON_RAW_DIR` (types per `contracts/transactions.yaml`) |
| staging | `stg_transactions` (contract enforced), `stg_fx_rates` |
| intermediate | `int_transactions_usd`: every join (exponent, VAT, fee, auth/settle FX) + calendar/tier/lag fields |
| marts | `fct_transaction_discrepancy` (1 row per txn), `mart_psp_weekly` (PSP x country x ISO week) |

- Money: `expected = round(auth * fx_settle / fx_auth)` cross-border, else `auth`; `residual = settled - expected`;
  `residual_usd` at the auth-day rate, 2 dp; `residual_pct` in percent.
- Rules (first match wins) live in `macros/discrepancy_rules.sql`: category (`exact`, `rounding`, `fx_tolerance`,
  `meaningful` < $20 and 2-5%, `large` > 5% or >= $20), `why_flagged`, `likely_cause` (no PSP names).
- Weeks: ISO week of the auth date; `week_month` = month of the week's Thursday.
- Tests: generic tests in the `_*.yml` files, unit tests (hand-worked rows) in `models/marts/_unit_tests.yml`,
  singular tests in `tests/`. Any failure -> `recon build` exits 5 and keeps the last good DB.
