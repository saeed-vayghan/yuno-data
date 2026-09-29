# Implementation Plan: CasaMarket Settlement Discrepancies

## Scope & rules
1. **Source of truth:** the brief ([scenario.md](../00-scenario/scenario.md)). Then [FINAL-SOLUTION.md](../../orchestrator/01-research/FINAL-SOLUTION.md), then the [PLAYBOOK](../01-playbook/PLAYBOOK.md). If FINAL-SOLUTION and PLAYBOOK disagree, FINAL-SOLUTION wins (3 months, PSP_A–E, 135k rows).
2. **Covers:** infra, shared core, CLI, data pipeline, DB, config, tests, security, alerts, docs and reports. **Not covered:** dashboard UI design (only its data wiring is here).
3. **Stack (no other tools):** Python 3.12 + uv · DuckDB 1.4.x LTS · dbt-core 1.12 + dbt-duckdb 1.11 · scipy + statsmodels · Typer · Streamlit + Plotly · pydantic · pytest · Make · Docker.
4. **Brief rule:** "Keep your architecture simple." One DuckDB file, full rebuild each run, no servers. The AWS scale path is written down, not built.
5. **Order:** core first (FR1 pipeline + FR2 analysis + docs), then stretch (FR3 alerts/dashboard wiring, FR4 recommendations), then packaging.

## Discussion highlights

| # | Voice | Point |
|---|---|---|
| 1 | 🏛️ Jamshid | Keep FINAL-SOLUTION's shape: CSV in `data/raw` → dbt staging → intermediate → marts in one DuckDB file. Analysis, CLI, alerts and dashboard all read marts through one `core` package. |
| 2 | ⚡ Kaveh | The playbook says 4 months and PSP_A–D. FINAL-SOLUTION says 3 months, PSP_A–E, 135k rows. We need one number. |
| 3 | 🏛️ Jamshid | FINAL-SOLUTION is the latest and matches 45k × 3. We use it. "Last month" is still a full month, because we generate 3 full calendar months. |
| 4 | ⚡ Kaveh | Where do the category and cause rules live? If Python and SQL both hold them, they will drift. |
| 5 | 🏛️ Jamshid | In SQL only, in `fct_transaction_discrepancy`. dbt unit tests use hand-worked rows (FX row, CLP row, the brief's "2¢ on $500" and "$20" rows). `recon build` passes `thresholds.yaml` to dbt as `--vars`, so there is one source for cut-offs. |
| 6 | ⚡ Kaveh | OK. pytest covers only Python: generator, validate, stats, alerts, CLI, contract. Also: PNG export needs kaleido + Chrome, and that breaks Docker and CI. |
| 7 | 🏛️ Jamshid | PNG export is best-effort. If it fails, write HTML and log a warning. We commit the PNGs from our own run, so the reviewer sees them in FINDINGS.md. |
| 8 | ⚡ Kaveh | Messaging, a cache server, a metrics server, log shipping: none of that belongs here. One line each, plus a scale path. And the plan runs about 3h10 against a 2h brief. The core must be done first, with a cut list after it. |
| 9 | 🏛️ Jamshid | Agreed. Core is done at about 2h15 (Phases 0–4). Stretch and packaging come after, in cut order. Only `build` writes to DuckDB; every other command opens it read-only. |
| 10 | ⚡ Kaveh | Agreed. Exit 5 on any failed dbt test or validation gate, and the plan is final. |

## Repo layout

```
casamarket-recon/
├── README.md · Makefile · pyproject.toml · uv.lock · .python-version
├── Dockerfile · docker-compose.yml · .dockerignore · .gitignore · .env.example
├── .github/workflows/ci.yml
├── contracts/transactions.yaml            # fields, types, enums, minor units, PII tags, PAN ban
├── config/
│   ├── generator.yaml                     # seed, rows, months, weights, patterns P1–P4, X1–X6, drift
│   ├── thresholds.yaml                    # category cut-offs, lag outlier, rounding steps, money limits
│   └── alerts.yaml                        # 6 rules, severities, Slack off
├── src/casarecon/
│   ├── __init__.py
│   ├── cli.py                             # Typer `recon` (thin shell)
│   ├── core/
│   │   ├── config.py                      # pydantic models for the 3 YAML files
│   │   ├── paths.py                       # repo paths, CASARECON_DB
│   │   ├── db.py                          # read-only DuckDB connection + "rebuilding, retry"
│   │   ├── queries.py                     # worst_week, outliers, weekly, segments, pending, lag
│   │   ├── build.py                       # dbtRunner wrapper, row counts per layer
│   │   └── log.py                         # stdlib logging setup
│   ├── generate/
│   │   ├── fx.py · rows.py · patterns.py · writer.py
│   │   └── validate.py                    # validation gate (shares + pattern bands)
│   ├── analysis/
│   │   ├── stats.py                       # Wilson, chi²/Fisher, BH-FDR, Spearman, Mann-Whitney
│   │   ├── glm.py                         # one logistic GLM
│   │   ├── rca.py                         # Q1–Q5, signature table, truth check, $ Pareto
│   │   ├── figures.py                     # one Plotly chart per finding
│   │   └── findings.py                    # builds reports/findings.json
│   ├── alerts/
│   │   ├── rules.py · evaluate.py · render.py
│   ├── report/
│   │   ├── render.py
│   │   └── templates/{FINDINGS.md.j2, RECOMMENDATIONS.md.j2, alerts.md.j2}
│   └── dashboard/app.py + pages/          # data wiring only; UI design is a separate plan
├── dbt/
│   ├── dbt_project.yml · profiles.yml
│   ├── seeds/{currency_exponents.csv, psp_fees.csv, vat_rates.csv, _seeds.yml}
│   ├── models/staging/{_sources.yml, _staging.yml, stg_transactions.sql, stg_fx_rates.sql}
│   ├── models/intermediate/{_intermediate.yml, int_transactions_usd.sql}
│   ├── models/marts/{_marts.yml, _unit_tests.yml, fct_transaction_discrepancy.sql,
│   │                 mart_segment_rates.sql, mart_psp_weekly.sql, mart_outliers.sql, mart_cause_summary.sql}
│   └── tests/{assert_settle_after_auth.sql, assert_fct_rowcount_matches_stg.sql,
│              assert_cause_usd_reconciles.sql, assert_outliers_are_large.sql}
├── data/
│   ├── sample/transactions_500.csv         # committed smoke sample
│   ├── raw/ · truth/ · casarecon.duckdb   # generated; gitignored
├── reports/
│   ├── FINDINGS.md · RECOMMENDATIONS.md · alerts.md · alerts.jsonl
│   ├── findings.json · run_manifest.json · analysis/*.csv · figures/*.png
└── tests/
    ├── conftest.py                        # session fixture: 500-row DB in tmp dir
    ├── test_contract.py · test_generator.py · test_validate.py · test_stats.py
    ├── test_alerts.py · test_cli.py · test_security.py · test_e2e.py
```

## Data model

Money is integer minor units in local currency (CLP 0 decimals, others 2). Rate base = `status = 'settled'` rows.

| Model | Layer | Grain | Key columns | Tests |
|---|---|---|---|---|
| `raw.transactions` (CSV) | raw (source) | 1 row per txn | `transaction_id` | source `not_null`, `unique` |
| `raw.fx_rates_daily` (CSV) | raw (source) | date × currency | `rate_date`, `currency` | `not_null` |
| `currency_exponents` | seed | currency | `currency` | `unique`; `exponent` in (0, 2) |
| `psp_fees` | seed | PSP | `psp` | `unique` (contracted fee, USD) |
| `vat_rates` | seed | country | `country` | `unique` (MX 16, CO 19, AR 21, CL 19; `tax_recalc` flag) |
| `stg_transactions` | staging | 1 row per txn | `transaction_id` | `unique`, `not_null`; `accepted_values` on status, country, currency, psp, payer_currency; contract enforced; `assert_settle_after_auth` |
| `stg_fx_rates` | staging | date × currency | `fx_key` (= currency‖date) | `unique` `fx_key`; `local_per_usd > 0` |
| `int_transactions_usd` | intermediate | 1 row per txn | `transaction_id` | `unique`; `relationships` to `stg_fx_rates` on auth and settle day; `amount_usd` not null |
| `fct_transaction_discrepancy` | marts | 1 row per txn (all statuses) | `transaction_id` | `unique`, `not_null`; `accepted_values` on `category`, `direction`, `likely_cause`; contract enforced; dbt unit tests; `assert_fct_rowcount_matches_stg` |
| `mart_segment_rates` | marts | segment_type × segment_value | `segment_key` | `unique`; `n_flagged ≤ n` |
| `mart_psp_weekly` | marts | PSP × country × ISO week | `psp_week_key` | `unique`; `week_month` not null (Thursday rule) |
| `mart_outliers` | marts | 1 row per `large` txn | `transaction_id` | `unique`; `assert_outliers_are_large` |
| `mart_cause_summary` | marts | cause × PSP × country × direction | `cause_key` | `unique`; `assert_cause_usd_reconciles` (sum = fct total) |

**`fct_transaction_discrepancy` columns:** contract columns + `diff_local`, `expected_settled`, `residual`, `residual_pct`, `residual_usd`, `abs_residual_usd`, `direction`, `category`, `is_meaningful`, `settle_lag_days`, `is_lag_outlier`, `auth_weekday`, `is_weekend`, `auth_week`, `auth_month`, `week_month`, `amount_usd`, `amount_tier`, `is_over_300`, `is_cross_border`, `payer_currency`, `fx_move_pct`, `rounding_flag`, `likely_cause`.

**`mart_segment_rates` segment types:** country, currency, psp, psp_country, amount_tier, country_tier, weekday, is_weekend, lag_bucket, cross_border. Columns: `n`, `n_flagged`, `rate`, `n_large`, `gross_under_usd`, `gross_over_usd`, `net_usd`, `mean_loss_usd`, `median_loss_usd`.

## Phases & steps

Time budget per phase (with AI help):

| Phase | What | Est. | Brief budget line |
|---|---|---|---|
| 0 | Scaffold: uv, Makefile, config, contract, CLI skeleton | 15 min | Setup 15–20 |
| 1 | Generator + validation gate | 25 min | Data generation 15–20 |
| 2 | dbt pipeline + tests | 35 min | Pipeline 25–35 |
| 3 | Analysis + figures + findings | 40 min | Analysis 30–40 |
| 4 | Report + brief CLI questions + README | 20 min | Docs 15–20 |
| **Core total** | | **135 min** | 100–115 (core lines only) |
| 5 | Stretch: alerts, recommendations, dashboard wiring | 40 min | Stretch 20–30 |
| 6 | Packaging: Docker, CI, fresh-clone check | 15 min | (not in brief) |
| **Grand total** | | **190 min** | **105–145 min** |

**Verdict:** about 45–85 min over the brief. Core (Phases 0–4) fits near the top of the brief. After Phase 4, cut in this order if time runs out: CI workflow → dashboard pages beyond Overview + Outliers → sensitivity table → Slack hook. Never cut: dbt tests, validation gate, FINDINGS, README, `make all`.

---

### Phase 0: Scaffold (15 min)

**S0.1 Project and dependencies**
- **Goal:** one locked Python env.
- **Files:** `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.env.example`, `src/casarecon/__init__.py`.
- **Do:**
  - `uv init --package casarecon --python 3.12`.
  - `uv add "duckdb>=1.4,<1.5" "dbt-core~=1.12" "dbt-duckdb~=1.11" numpy pandas scipy statsmodels typer streamlit plotly kaleido pydantic pyyaml jinja2`.
  - `uv add --dev pytest`.
  - `[project.scripts] recon = "casarecon.cli:app"`.
  - `.gitignore`: `data/raw/`, `data/truth/`, `data/*.duckdb`, `dbt/target/`, `dbt/logs/`, `.env`.
  - `.env.example`: `CASARECON_DB=data/casarecon.duckdb`, `SLACK_WEBHOOK_URL=` (empty).
- **Done when:** `uv sync --frozen && uv run python -c "import duckdb, dbt, statsmodels"` exits 0.
- **Serves:** Tech 15 (locked deps, reproducible); constraint "runnable locally".

**S0.2 Config files + loader**
- **Goal:** every cut-off in YAML, typed and checked at start.
- **Files:** `config/generator.yaml`, `config/thresholds.yaml`, `config/alerts.yaml`, `src/casarecon/core/config.py`, `src/casarecon/core/paths.py`.
- **Do:**
  - `generator.yaml`: `seed: 42`, `rows: 135000`, `start: 2026-04-01`, `months: 3`, country weights (MX 40 / CO 25 / AR 20 / CL 15), PSP weights (A 30 / B 25 / C 20 / D 15 / E 10), status (settled 93 / failed 4 / pending 3), cross-border 20%, tier mix (45/40/15), over-$300 ≈ 6%, lag (1–7, mode 2, 2% at 8–15), bucket targets (67/1/18/10/4), P1–P4, X1–X6, drift, `tips: none`.
  - `thresholds.yaml`: `fx_tolerance_pct: 2`, `large_pct: 5`, `large_usd: 20`, `rounding_minor_units: 1`, `lag_outlier_days: 7`, `rounding_steps: {PSP_D: {CLP: 1000, COP: 1000}}`, `sensitivity_pcts: [1, 2, 3]`, `money_leak: {warn_pct, crit_pct, weekly_usd}`, `min_sample: {alerts: 50, worst_week: 30}`.
  - `alerts.yaml`: 6 rules (peer, change, money_leak, large_rows, pending_aging, settle_lag) with trigger, severity, owner; `slack: {enabled: false}`.
  - `config.py`: one pydantic model per file; `load_config()` raises a clear error on a bad value; `dbt_vars()` returns thresholds as JSON for dbt `--vars`.
- **Done when:** `uv run python -c "from casarecon.core.config import load_config; load_config()"` exits 0; a bad value (e.g. `large_pct: -1`) raises.
- **Serves:** FR1 "define meaningful"; Tech 15.

**S0.3 Data contract**
- **Goal:** one schema for generator, dbt and tests.
- **Files:** `contracts/transactions.yaml`.
- **Do:** list each column with type, nullability, enum, unit and `pii` tag:
  - `transaction_id` (str, `txn_` + 12 hex), `customer_id` (str, `cus_` + hash token, `pii: token`), `product_category`, `country` {MX, CO, AR, CL}, `currency` {MXN, COP, ARS, CLP}, `payer_currency` {local, USD}, `is_cross_border` (bool), `psp` {PSP_A..PSP_E}, `status` {settled, pending, failed}, `auth_ts`, `settle_ts` (local merchant time; null unless settled), `authorized_amount`, `settled_amount` (int minor units), `item_count` (int ≥ 1), `risk_score` (0–1), `card_bin_country` (ISO-2).
  - `banned_fields: [pan, card_number, cvv, email, name]`.
- **Done when:** `uv run python -c "import yaml; yaml.safe_load(open('contracts/transactions.yaml'))"` exits 0.
- **Serves:** Tech 15 (contract); security/PII.

**S0.4 CLI skeleton, logging, Makefile**
- **Goal:** `recon` exists with all 10 commands and fixed exit codes.
- **Files:** `src/casarecon/cli.py`, `src/casarecon/core/log.py`, `Makefile`.
- **Do:**
  - Typer app with `generate | build | validate | analyze | alerts | report | query | worst-week | dashboard | all`; stubs print "not built yet" and exit 1.
  - Global `--verbose`. Exit codes: 0 ok · 1 error · 2 usage (Typer default) · 5 data-quality/validation failed. One `DataQualityError` → exit 5.
  - `log.py`: stdlib `logging`, one line per step: `step=build layer=staging rows=135000 secs=3.1`.
  - Makefile: `all validate app alerts` call `uv run recon …`; `smoke` = `uv run recon all --rows 500`; `test` = `uv run pytest -q`; `clean` removes `data/raw data/truth data/*.duckdb dbt/target`.
- **Done when:** `uv run recon --help` lists 10 commands; `uv run recon build; echo $?` prints 1.
- **Serves:** FR3 (CLI); deliverable "run instructions".

---

### Phase 1: Synthetic data + validation gate (25 min)

**S1.1 FX table**
- **Goal:** daily rates with capped moves.
- **Files:** `src/casarecon/generate/fx.py`.
- **Do:** random walk per currency from a base rate (e.g. MXN 18, COP 4,000, ARS 1,000, CLP 950 per USD); cap so any auth→settle move (≤ 15 days) stays < 2%; include weekends. Output `rate_date, currency, local_per_usd`.
- **Done when:** unit test: max 15-day move < 2% for all currencies.
- **Serves:** Test data 10 (X1 FX timing); FR1 FX formula.

**S1.2 Base rows + planted patterns**
- **Goal:** 135k seeded rows that hit the bucket targets and carry P1–P4, X1–X6 and the drift.
- **Files:** `src/casarecon/generate/rows.py`, `src/casarecon/generate/patterns.py`.
- **Do (in this order, per research doc 04):**
  1. Draw base rows: date, country, PSP, currency, cross-border, customer token, category, `item_count`, `risk_score`, log-normal amount ≥ $10, status, lag.
  2. P2: CO orders > $300 get lag +2–4 days and more lag outliers. Pending rows go mostly in the last 7 days.
  3. P4 first: PSP_D cross-border CLP/COP settles rounded **down** to a multiple of 1,000 units.
  4. Assign buckets to other settled rows to hit 67/1/18/10/4. P1 (PSP_B × AR) and P3 (weekend 1.3×) raise the `meaningful` weight.
  5. Pick a cause that fits bucket and row (X1 cross-border; X2 multi-item (n−1)/n; X3 PSP_C fixed fee ≥ $1, month 3 only = drift; X4 MX/CO VAT share < 2%; X5 high-risk 10–20% withheld; X6 −2% to −5%). No tips.
  6. Draw the diff inside the bucket limits (e.g. X6 in `meaningful` stays < $20).
  - All randomness from one `numpy.random.default_rng(seed)`.
- **Done when:** `pytest tests/test_generator.py` passes: same seed → same bytes; no field outside the contract; P4 rows all end in `000` and are ≤ expected.
- **Serves:** Test data 10; brief test-data spec (all bullets).

**S1.3 Writer + `recon generate`**
- **Goal:** files on disk, truth kept apart.
- **Files:** `src/casarecon/generate/writer.py`; wire `generate` in `cli.py`; `data/sample/transactions_500.csv`.
- **Do:**
  - Write `data/raw/transactions.csv`, `data/raw/fx_rates_daily.csv`, `data/truth/labels.parquet` (`transaction_id, true_bucket, true_cause, pattern_ids`), `data/raw/generation_manifest.json` (seed, rows, realized mix, versions).
  - `--rows N` overrides the row count. `--seed` overrides the seed.
  - Commit one 500-row sample CSV.
- **Done when:** `uv run recon generate --rows 500` exits 0 in < 5 s; running it twice gives the same `sha256sum data/raw/transactions.csv`.
- **Serves:** Deliverable 2 (dataset or script); Tech 15 (reproducibility).

**S1.4 Validation gate (`recon validate`)**
- **Goal:** prove the data meets the brief ranges and the patterns exist. Write it now; its "Done when" runs at the end of Phase 2 (it reads the fact table).
- **Files:** `src/casarecon/generate/validate.py`; wire `validate`; `tests/test_validate.py`.
- **Do:**
  - Reads `fct_transaction_discrepancy` (after build) read-only. Bucket shares on both denominators, with n-aware bounds (brief range ± 3 SE).
  - Pattern bands: P1 gap ≥ 2.5 pts · P2 median lag + ≥ 2 days · P3 ratio ≥ 1.2 · P4 ≥ 90% round-down signature.
  - Full run: any miss → exit 5. `--rows < 10000`: pattern misses only warn.
  - Prints a table: target, realized, bounds, PASS/WARN/FAIL. Writes result into `reports/run_manifest.json`.
- **Done when:** after Phase 2, `uv run recon generate && uv run recon build && uv run recon validate` exits 0; test with a doctored mix exits 5.
- **Serves:** Test data 10 (validation gate); Tech 15.

---

### Phase 2: dbt pipeline + DB (35 min)

**S2.1 dbt project, profile, seeds**
- **Goal:** dbt writes to one DuckDB file.
- **Files:** `dbt/dbt_project.yml`, `dbt/profiles.yml`, `dbt/seeds/currency_exponents.csv`, `dbt/seeds/psp_fees.csv`, `dbt/seeds/vat_rates.csv`, `dbt/seeds/_seeds.yml`.
- **Do:**
  - `profiles.yml`: `type: duckdb`, `path: "{{ env_var('CASARECON_DB', '../data/casarecon.duckdb') }}"`, `threads: 4`.
  - Models materialized as `table` (full rebuild). Schemas: `staging`, `intermediate`, `marts`.
  - Seeds: `currency_exponents(currency, exponent)` (CLP 0, others 2); `psp_fees(psp, contract_fee_usd)` (all 0: any fixed deduction is unexpected); `vat_rates(country, vat_pct, tax_recalc)` (MX/CO true).
- **Done when:** `uv run dbt seed --project-dir dbt --profiles-dir dbt` exits 0.
- **Serves:** FR1; FINAL-SOLUTION "reference data as seeds".

**S2.2 Sources + staging**
- **Goal:** typed, clean inputs.
- **Files:** `dbt/models/staging/_sources.yml`, `stg_transactions.sql`, `stg_fx_rates.sql`, `_staging.yml`, `dbt/tests/assert_settle_after_auth.sql`.
- **Do:**
  - Sources via dbt-duckdb `external_location` with `read_csv(..., columns={...})` (explicit types from the contract).
  - `stg_transactions`: rename, cast, trim; keep failed and pending rows. Contract enforced.
  - `stg_fx_rates`: add `fx_key`.
- **Done when:** `uv run dbt build --select staging` passes all tests.
- **Serves:** FR1 "ingests transaction records"; Pipeline 20.

**S2.3 Intermediate: FX + USD**
- **Goal:** each txn gets auth-day and settle-day rates.
- **Files:** `dbt/models/intermediate/int_transactions_usd.sql`, `_intermediate.yml`.
- **Do:** join `stg_fx_rates` twice (auth day, settle day) and `currency_exponents`; compute `amount_usd = authorized_amount / 10^exp / local_per_usd_auth`, `fx_move_pct`.
- **Done when:** `dbt build --select int_transactions_usd` passes; `relationships` tests pass.
- **Serves:** FR1 enrichment; Pipeline 20.

**S2.4 Fact: discrepancy metrics, category, cause**
- **Goal:** one enriched row per txn. This is the core FR1 output.
- **Files:** `dbt/models/marts/fct_transaction_discrepancy.sql`, `_marts.yml`, `_unit_tests.yml`, `dbt/tests/assert_fct_rowcount_matches_stg.sql`.
- **Do:**
  - `expected_settled` = cross-border: `auth × fx_settle / fx_auth` (rounded to minor units); domestic: `auth`.
  - `diff_local`, `residual`, `residual_pct`, `residual_usd` (auth-day rate), `abs_residual_usd`, `direction`.
  - `category` (first match): exact (Δ = 0) → rounding (|Δ| ≤ 1 minor unit) → fx_tolerance (≤ 2% and < $20) → meaningful (2–5% and < $20) → large (> 5% or ≥ $20). Null if not settled. Cut-offs from `{{ var('thresholds') }}`.
  - `is_meaningful`, time fields (`auth_weekday`, `is_weekend`, ISO `auth_week`, `auth_month`, `week_month` = month of the week's Thursday), `settle_lag_days` (fractional), `is_lag_outlier` (> 7), `amount_tier`, `is_over_300`, `rounding_flag`.
  - `likely_cause` on all non-exact rows, first match: fx_timing → psp_rounding → partial_capture → psp_fee → tax_recalc → fraud_hold → psp_adjustment → tip → unexplained. Rules never name a PSP.
  - dbt unit tests (hand-worked rows): one cross-border MXN row; one CLP 0-decimal row; 2¢ on $500 → `fx_tolerance`, not flagged; $20 residual → `large`; one row per cause label.
- **Done when:** `uv run dbt build --select +fct_transaction_discrepancy --vars "$(uv run python -c 'from casarecon.core.config import dbt_vars; print(dbt_vars())')"` (from `dbt/`, with `--profiles-dir .`) passes, including unit tests.
- **Serves:** FR1 (calculate, flag, enrich); Pipeline 20.

**S2.5 Marts**
- **Goal:** small tables for analysis, CLI, alerts and dashboard.
- **Files:** `mart_segment_rates.sql`, `mart_psp_weekly.sql`, `mart_outliers.sql`, `mart_cause_summary.sql`; `dbt/tests/assert_outliers_are_large.sql`, `assert_cause_usd_reconciles.sql`.
- **Do:** grains and keys as in the Data model table. All rates use settled rows only. `mart_psp_weekly` holds `n`, `n_flagged`, `rate`, `gross_under_usd`, `gross_over_usd`, `net_usd`, `low_sample` (n < 30).
- **Done when:** `dbt build` passes; `select sum(net_usd) from marts.mart_cause_summary` equals the fct total.
- **Serves:** FR2, FR3; Pipeline 20.

**S2.6 `recon build`**
- **Goal:** one command runs dbt and fails loudly.
- **Files:** `src/casarecon/core/build.py`; wire `build`.
- **Do:** delete the old DuckDB file (full rebuild); call `dbtRunner().invoke(["build", "--project-dir", "dbt", "--profiles-dir", "dbt", "--vars", json])`; `success=False` → exit 5; exception → exit 1. Log row counts per layer. Append to `reports/run_manifest.json` (dbt/duckdb versions, row counts).
- **Done when:** `uv run recon generate --rows 500 && uv run recon build` exits 0 and logs counts for raw, staging, intermediate, marts. Breaking one row by hand (settle before auth) → exit 5.
- **Serves:** FR1 acceptance ("run your pipeline… get a clean, enriched dataset"); Tech 15.

---

### Phase 3: Root-cause analysis (40 min)

**S3.1 Shared read-only core**
- **Goal:** one query layer for analysis, CLI, alerts and dashboard.
- **Files:** `src/casarecon/core/db.py`, `src/casarecon/core/queries.py`.
- **Do:**
  - `connect()`: `duckdb.connect(path, read_only=True)` as a context manager; on lock error raise `DbBusy("rebuilding, retry")`.
  - Functions with fixed, parameterized filters (no raw SQL from users): `segment_rates(type)`, `psp_weekly()`, `worst_week(month)`, `outliers(min_usd)`, `cause_summary()`, `pending()`, `lag_by_country_tier()`, `transactions(filters)`.
- **Done when:** `pytest tests/test_cli.py -k core` passes on the 500-row fixture DB.
- **Serves:** FR3 (shared core); Tech 15 (no logic in UI).

**S3.2 Stats helpers**
- **Goal:** tested statistics.
- **Files:** `src/casarecon/analysis/stats.py`, `tests/test_stats.py`.
- **Do:** Wilson CI (`statsmodels proportion_confint(method="wilson")`); lift; chi² (`scipy.stats.chi2_contingency`), Fisher when an expected cell < 5; BH-FDR (`multipletests(method="fdr_bh")`); Spearman; Mann-Whitney; `excess_loss = (rate − peer_rate) × volume × mean_loss` with median beside it.
- **Done when:** tests match known values (e.g. Wilson 10/100); Pareto sums to the total.
- **Serves:** RCA 25 (statistical evidence).

**S3.3 Answer Q1–Q5 + GLM + truth check**
- **Goal:** all 5 brief questions with evidence.
- **Files:** `src/casarecon/analysis/rca.py`, `src/casarecon/analysis/glm.py`.
- **Do:**
  - Q1 country/currency rates + CI + chi². Q2 PSP and PSP × country vs peers (same country). Q3 rate by tier + Spearman on |residual %| vs amount. Q4 weekday, weekend ratio, lag buckets vs mean loss, Mann-Whitney on lag (P2). Q5 signature table: PSP × country × cause × sign × settled-ends-in-000.
  - One logistic GLM on `is_meaningful`: country, PSP, tier, weekend, cross-border, lag bucket, PSP × country. If it fails to converge, drop sparse levels and log it.
  - Sensitivity: flag rate at 1%, 2%, 3%.
  - Truth check: precision/recall of `likely_cause` vs `data/truth/labels.parquet` (goal ≥ 0.9 each).
  - $ Pareto by cause × PSP × country; gross and net; "compared with $127k (estimate)".
  - Write `reports/analysis/*.csv`.
- **Done when:** on the full run, `reports/analysis/` has one CSV per question + `glm.csv` + `truth_check.csv`; P1–P4 each appear with q < 0.05.
- **Serves:** FR2 (all 5 questions); RCA 25.

**S3.4 Findings table + figures + `recon analyze`**
- **Goal:** numbers in one place; one chart per finding.
- **Files:** `src/casarecon/analysis/findings.py`, `src/casarecon/analysis/figures.py`; wire `analyze`.
- **Do:**
  - `reports/findings.json`: list of `{id, key, headline, metric, segment, n, rate, ci, peer_rate, q, usd_quarter, share_of_loss, likely_cause, figure}`, ranked by $.
  - Plotly figures: country bars with CI, PSP × country heatmap, tier chart, weekday chart, lag vs loss, cause Pareto, weekly trend. PNG via kaleido; on failure write `.html` and warn.
- **Done when:** `uv run recon analyze` exits 0; `findings.json` has ≥ 4 findings; `reports/figures/` has one file per finding.
- **Serves:** Insight 20; deliverable "analysis outputs".

---

### Phase 4: Report, brief questions, README (20 min)

**S4.1 `recon report` → FINDINGS.md**
- **Goal:** a report with no hand-typed numbers.
- **Files:** `src/casarecon/report/render.py`, `src/casarecon/report/templates/FINDINGS.md.j2`, `reports/FINDINGS.md`.
- **Do:** Jinja2 (ships with dbt) renders: one-page summary on top; each finding in the fixed format ("**F#. Headline.** X% of … (n, 95% CI, vs …, q). $ impact … Likely cause … Action: see R#"); figure under each; sensitivity table; truth check; "tip: ruled out"; latest alerts section (if present).
- **Done when:** `uv run recon report` exits 0; `grep -c '^\*\*F[0-9]' reports/FINDINGS.md` ≥ 4.
- **Serves:** FR2 acceptance; Insight 20; "Done: ≥ 3–4 patterns".

**S4.2 Brief questions in the CLI**
- **Goal:** answer both example questions from the terminal.
- **Files:** `cli.py` (`query`, `worst-week`), `tests/test_cli.py`.
- **Do:**
  - `recon worst-week --month last`: last full calendar month; PSP-weeks by `week_month`; ranked by net USD loss; gross beside it; n < 30 marked "low sample".
  - `recon query --min-usd 50 [--psp] [--country] [--format table|csv|json]`: `abs_residual_usd > 50`, sorted desc.
- **Done when:** `uv run recon worst-week --month last` prints one ranked table; `uv run recon query --min-usd 50 --format csv | head` shows rows; CliRunner tests pass.
- **Serves:** FR3 acceptance (both questions); Stretch 10.

**S4.3 `recon all` + README**
- **Goal:** one command end to end; docs a reviewer can follow.
- **Files:** `cli.py` (`all`), `README.md`.
- **Do:**
  - `all` = generate → build → validate → analyze → alerts (skipped until Phase 5) → report. Stops at the first non-zero exit.
  - README sections (playbook §12): Problem · Quick start (3 run paths, `recon --help`, URL) · Key findings (links to FINDINGS) · Recommendations · Approach & architecture (diagram, layers, why DuckDB + dbt) · Definitions & assumptions (money, cross-border, FX formula, categories, week rule, local time, CFO 18% vs our 14% flagged / ~33% non-exact) · How to read outputs · Data (patterns, realized mix) · Monitoring · Limitations & scale path · AI-assisted workflow.
- **Done when:** `make clean && make all` exits 0 in about a minute; every README command runs as written.
- **Serves:** Deliverables 1 and 4; Tech 15; "Done: well-documented".

**Core checkpoint:** FR1 + FR2 + docs done. Commit here.

---

### Phase 5: Stretch (40 min)

**S5.1 Alert rules + evaluator**
- **Goal:** automated weekly alerts.
- **Files:** `src/casarecon/alerts/rules.py`, `evaluate.py`, `render.py`, `src/casarecon/report/templates/alerts.md.j2`, `tests/test_alerts.py`.
- **Do:**
  - Window: last closed ISO week (week end ≤ as-of − 7 days; as-of = max data timestamp).
  - 6 rules: peer (trailing 4 weeks, BH q < 0.05 and gap ≥ 2 pts) · change (p-chart, 3σ, trailing 8 weeks) · money leak (warn/crit %) · large-rows summary · pending aging (> 7 d SEV3, > 14 d SEV2) · settle lag (late share > limit).
  - n < 50 → "insufficient data" (info). Status NEW / ONGOING / RESOLVED vs the previous closed week; key `rule_id|segment`; no state file.
  - Output `reports/alerts.jsonl` + `reports/alerts.md` (with week-over-week ▲/▼ and gross/net money lines).
  - Slack: post only if `slack.enabled` and `SLACK_WEBHOOK_URL` set (stdlib `urllib`).
- **Done when:** 12 tests pass (fire + silent per rule) + small-n test; on the full run, peer fires for PSP_B × AR, change fires for PSP_C (drift), settle lag fires for CO $200+.
- **Serves:** FR3 alert system; Stretch 10.

**S5.2 RECOMMENDATIONS.md**
- **Goal:** 3–5 ranked actions with $.
- **Files:** `src/casarecon/report/templates/RECOMMENDATIONS.md.j2`, `reports/RECOMMENDATIONS.md`.
- **Do:** template holds action text, owner and implementation per finding `key` (e.g. PSP_B AR escalation, FX rate lock, PSP_D rounding fix, PSP_C fee dispute, CO large-order settlement SLA). Numbers come from `findings.json`: evidence F#, excess loss, saving = excess × stated reduction %. Ranked by $.
- **Done when:** `uv run recon report` writes 3–5 rows; each row cites an F# that exists in FINDINGS.md.
- **Serves:** FR4 acceptance; Stretch 10.

**S5.3 Dashboard data wiring (UI design out of scope)**
- **Goal:** the 5 pages get their data from `core`, never their own SQL.
- **Files:** `src/casarecon/dashboard/app.py`, `src/casarecon/dashboard/pages/*.py`; wire `dashboard` (`streamlit run … --server.port 8501`); Makefile `app`.
- **Do:** `@st.cache_data` keyed on the DuckDB file's mtime; catch `DbBusy` → show "rebuilding, retry". Overview uses `psp_weekly` + `worst_week`; Outliers uses `outliers(min_usd=50)` + CSV download; Root causes reads `findings.json`; Alerts reads `alerts.jsonl`.
- **Done when:** `make app` serves `localhost:8501`; the worst-week card equals `recon worst-week --month last`; Outliers row count equals `recon query --min-usd 50 | wc -l` (minus header).
- **Serves:** FR3 dashboard; Stretch 10.

---

### Phase 6: Packaging (15 min)

**S6.1 Docker**
- **Goal:** run path 3 for reviewers with no Python.
- **Files:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- **Do:**
  - `FROM python:3.12-slim`; copy `uv` binary; `uv sync --frozen --no-dev`; non-root user; `EXPOSE 8501`.
  - Compose service `recon`: `command: sh -c "recon all && recon dashboard"`; ports `8501:8501`; volumes `./data`, `./reports`.
- **Done when:** `docker compose up` builds, finishes `recon all`, and `curl -sf localhost:8501` returns 200.
- **Serves:** Constraint "Docker available"; Tech 15 (3 run paths).

**S6.2 CI + security checks + e2e**
- **Goal:** every push proves the build.
- **Files:** `.github/workflows/ci.yml`, `tests/test_security.py`, `tests/test_contract.py`, `tests/test_e2e.py`.
- **Do:**
  - CI: checkout → install uv → `uv sync --frozen` → `make test` → `make smoke` → `docker build .`.
  - `test_security.py`: no banned field names in raw CSV or marts; no 13–19 digit runs (PAN) in `data/raw` or `reports/`; `query` rejects unknown filters.
  - `test_contract.py`: dbt `_staging.yml` columns and types equal the contract.
  - `test_e2e.py`: `recon all --rows 500` twice → identical hash of `fct_transaction_discrepancy` export (idempotent); smoke alerts all "insufficient data".
- **Done when:** CI is green; `make test` passes locally.
- **Serves:** Tech 15; security/PII; reproducibility.

**S6.3 Fresh-clone walk-through**
- **Goal:** the reviewer's first 5 minutes work.
- **Files:** none new (fix README if needed); commit `reports/*` and `reports/figures/*.png` from the full run.
- **Do:** in a temp dir: `git clone … && make all`, then `pip install uv && uv run recon all`, then `docker compose up`. Walk the Definition of done below.
- **Done when:** all 3 paths exit 0 from a fresh clone.
- **Serves:** "Done: reproducibility"; Tech 15.

## Cross-cutting

| Item | Lean build | Scale path |
|---|---|---|
| Config | `config/{generator,thresholds,alerts}.yaml` + pydantic loader; thresholds passed to dbt as `--vars`; `CASARECON_DB` env var | Same files in Git; per-env overrides in Airflow Variables |
| Logs | stdlib `logging` to stderr, one key=value line per step; `--verbose`; `run_manifest.json` (seed, versions, row counts, gate result). Not in the build: log shipping (one local process). | CloudWatch Logs + OpenLineage |
| Metrics | Business metrics are the dbt marts (rates, $ per segment/week). Not in the build: a metrics server (no long-running service to scrape). | Marts on StarRocks; Grafana/Superset |
| Cache | `st.cache_data` keyed on DuckDB file mtime. Not in the build: a cache server (one reader, 135k rows). | StarRocks/BI built-in cache |
| Messaging | Not in the build: data arrives as a batch export, not events. | MSK + Flink for auth/settlement events |
| Orchestration | `make all` / `recon all`, fixed order. Not in the build: a scheduler (one manual run). | Airflow (MWAA) + Cosmos daily DAG |
| Storage | One DuckDB file; CSV raw; full rebuild | S3 + Iceberg → StarRocks; incremental MERGE |
| Alerts delivery | `alerts.jsonl` + `alerts.md`; Slack optional, off | Same evaluator as Airflow task → SNS → Slack/PagerDuty; add alert state |
| Security / PII | No PAN (contract ban + test); tokenized `customer_id`; BIN country only; read-only DB for all but `build`; fixed-filter `query`, no raw SQL; secrets only via env; non-root container; synthetic data only | IAM least privilege, KMS on S3, PCI-DSS scope review, GDPR retention |
| Testing | dbt generic + singular + unit tests (in every build); pytest: contract, generator, validate, stats, alerts (12), CLI, security, e2e idempotency | Same in CI + source freshness + row counts vs PSP file totals |
| CI | GitHub Actions: `make test`, `make smoke`, `docker build` | Build and push image; deploy via Terraform |

## Definition of done

**Brief deliverables**
- [ ] Working code + README with run steps (S0–S4.3) → Deliverable 1.
- [ ] Generator script + seed + 500-row sample; ≥ 500 rows, 3 months, 4 countries, 5 PSPs, status mix, lag outliers, metadata (S1) → Deliverable 2.
- [ ] Analysis outputs: `reports/analysis/*.csv`, `findings.json`, figures, FINDINGS.md (S3–S4.1) → Deliverable 3.
- [ ] Docs: approach, findings, assumptions, how to read results (README + FINDINGS) → Deliverable 4.
- [ ] Stretch: alerts + dashboard wiring + RECOMMENDATIONS.md with 3–5 actions (S5) → Deliverable 5.

**Brief acceptance criteria**
- [ ] FR1: `make all` → `fct_transaction_discrepancy` has one row per txn with all enriched fields.
- [ ] FR2: FINDINGS answers all 5 questions; ≥ 4 patterns with CI, q and $.
- [ ] FR3: "Which PSP had the worst week last month?" → `recon worst-week --month last` + Overview card. "Discrepancies over $50" → `recon query --min-usd 50` + Outliers page.
- [ ] FR4: each recommendation cites a finding, has $ impact and an implementation.

**Rubric**
- [ ] Pipeline 20: FX residual formula unit-tested; CLP minor units right; dbt tests on every model.
- [ ] Test data 10: bucket mix in brief ranges; P1–P4 + X1–X6 + drift; gate passes on full run.
- [ ] RCA 25: Wilson CI, chi²/Fisher, BH-FDR, one GLM, signature table, truth check, $ Pareto.
- [ ] Insight 20: fixed finding format; summary on top; one chart per finding; $ reconciles to total.
- [ ] Tech 15: 3 run paths from a fresh clone; `uv.lock`; contract; idempotent rerun; `make test` green.
- [ ] Stretch 10: both stretch items; each brief question answered in ≤ 2 clicks.
- [ ] No PAN anywhere; `test_security.py` green.

## Risks & fallbacks

| Risk | Sign | Fallback |
|---|---|---|
| Time overrun (plan ≈ 190 min vs 105–145) | Phase 3 not done at 110 min | Core first; then cut list: CI → extra dashboard pages → sensitivity table → Slack |
| dbt-duckdb 1.11 vs DuckDB 1.4 pin conflict | `uv sync` fails | Let uv pick the dbt-duckdb-compatible DuckDB 1.4.x; document the version in README |
| kaleido / Chrome missing (Docker, CI) | PNG export error | Write HTML figures and warn; committed PNGs come from the author's run |
| Generator misses a bucket share after P4 | `recon validate` exit 5 | P4 first, then fill buckets to target; tune weights in `generator.yaml`, not code |
| P1 not significant | q ≥ 0.05 on PSP_B × AR | Default is 135k rows for power; gate checks P1 gap ≥ 2.5 pts |
| GLM does not converge (sparse PSP × country cells) | statsmodels warning | Drop sparse levels, keep main effects, log it in FINDINGS |
| DuckDB file locked while dashboard is open | IO lock error | Short read-only connections; "rebuilding, retry" message |
| Cause rules overlap (e.g. tax vs FX) | Truth-check precision < 0.9 | Fix rule order in SQL; unit test each cause row |
| 135k CSV too big for Git | ~20 MB file | Gitignore `data/raw`; commit a 500-row sample + seed |
| DuckDB 1.4 LTS support ends 17 Nov 2026 | Date | Pinned for the take-home; README notes the 1.5.x upgrade after dbt-duckdb testing |
| Reader confuses CFO 18% with our 14% flag | Review question | README states: data follows brief ranges; 14% flagged, ~33% non-exact |
