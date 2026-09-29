# M4: data architecture work (dev env)

Goal: build the open data-architecture items **locally** (dev env). AWS parts are code only
(Terraform / Airflow / Flink files that validate) — **never applied or deployed**.

Rules (same as before): functional style, small files (< 150 lines), adapters between layers,
simple English, a short README per new folder, a **few** tests only. `make all` must stay green
and keep the default behaviour (full rebuild, same outputs) unless a flag is passed.

## Owners (edit only your paths; requests go to HANDOFF.md)

| Agent | Items | Owns |
|---|---|---|
| **DATA** (dbt + model) | 1 incremental loads, 2 late settlements / restatement window, 3 dated reference data (SCD2 fees, VAT, FX valid_from/to), 16 `merchant_id` through the data layer | `dbt/models/staging/*.sql`, `dbt/models/intermediate/**`, `dbt/models/marts/**`, `dbt/seeds/**`, `dbt/tests/**`, `dbt/macros/**`, `dbt_project.yml`, `src/casarecon/pipeline/**`, `core/weeks.py`, `core/queries/pipeline_q*.py`, `cli.py` (build command only) |
| **INGEST** (landing + lake + DQ) | 7 per-PSP file landing, contract check on arrival, quarantine; 8 lake zones raw → staged (partitioned parquet, Iceberg-like layout); 13 freshness / volume / schema-drift checks; 6 calibration toward ~$127k; `merchant_id` at source | `src/casarecon/generate/**`, `config/generator.yaml`, `contracts/**`, `src/casarecon/ingest/**` (+ `ingest/cli.py` → `recon ingest`), `dbt/models/staging/_sources.yml`, `config/ingest.yaml`, `data/sample/**`, `tests/infra/test_ingest*.py`, `tests/infra/test_generate*.py` |
| **ALERTS** (metrics + alert memory + delivery) | 4 alert history (open since, ack, mute), 5 one metric-definition module, 17 routing + dedupe (Slack / PagerDuty / SNS adapters, all off by default) | `src/casarecon/alerts/**` (+ `alerts/cli.py` → `recon alert`), `adapters/slack.py`, `adapters/notify_*.py`, `core/metrics.py`, `config/alerts.yaml`, `core/queries/ui_q*.py`, `core/queries/reports_q.py`, `tests/backend/test_alerts*.py` |
| **PLATFORM** (AWS path as code) | 9 Flink SQL job (auth ↔ settlement match), 10 dbt-starrocks target, 11 Airflow DAG, 12 StarRocks compose profile, 14 lineage (dbt docs + OpenLineage), 15 security/PII policy, 18 replay/backfill, Terraform for the AWS diagram | `infra/**` (terraform, airflow, flink, starrocks), `dbt/profiles.yml`, `src/casarecon/ops/**` (+ `ops/cli.py` → `recon ops`), `docker-compose.yml`, `Dockerfile`, `docs/PLATFORM.md`, `tests/infra/test_ops*.py` |

Shared: `README.md` and `docs/ARCH-M4.md` are updated by the coordinator at the end.

## Interfaces (agree on these; do not change them)

- **Lake layout** (INGEST writes, DATA reads through `_sources.yml`):
  `data/lake/landing/psp=<PSP>/date=<YYYY-MM-DD>/settlements.csv` (per-PSP files)
  `data/lake/quarantine/...` (bad files + `reason.json`)
  `data/lake/staged/transactions/settle_month=<YYYY-MM>/part-*.parquet` and `data/lake/staged/fx_rates_daily/*.parquet`.
  `_sources.yml` reads `staged/` when `CASARECON_SOURCE=lake`, else the raw CSVs (default, so `make all` is unchanged).
- **New column** `merchant_id` (VARCHAR, default `casamarket`) in the contract, raw CSV, staging, fct and marts.
- **Reference data** seeds get `valid_from` / `valid_to` (DATE, `valid_to` null = open). PSP_C fee change is dated in `psp_fees.csv` (month 3).
- **Incremental**: `recon build --incremental [--lookback-days N]` (default full rebuild). The restatement window = `lookback_days` (default 15 = max lag). Weeks inside the window are `is_provisional = true` in `mart_psp_weekly`.
- **Alert history**: `data/alerts/history.jsonl` (append-only; one line per evaluation) + `config/alert_state.yaml` (ack / mute by `key`). Output `alerts.jsonl` keeps its current fields and adds `open_since` and `muted` (nullable).
- **Metrics**: `core/metrics.py` holds the definitions (flag rate, net loss, leak share, excess loss) as pure functions / SQL fragments; new code uses it.
- **CLI groups** load from `cli.py` `PLUGINS`: `recon ingest`, `recon alert`, `recon ops`.
