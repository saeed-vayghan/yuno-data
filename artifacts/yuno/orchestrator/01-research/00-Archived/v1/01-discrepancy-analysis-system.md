# Discrepancy Analysis & Monitoring System: Decision Brief (v1)

## Question
What shape should the CasaMarket system have, end to end: ingest → validate → enrich → detect → analyze → report/dashboard/alerts?
It must be a lean local tool with one-command run (scenario.md: "a focused analytical tool, not an enterprise data warehouse").
Inside that limit we pick the most correct and maintainable option. We also document (not build) a scale path on AWS with Yuno's stack.
This brief fixes the **reference stack** that the other briefs reuse. Processing is **batch** in the lean build.

## Debate (🏛️ Jamshid vs ⚡ Kaveh)

**🏛️ Jamshid (1):** Yuno runs StarRocks, Flink, dbt and Airflow. Let's ship a mini lakehouse in Docker Compose (Iceberg + StarRocks + Airflow). It proves we can run their stack.

**⚡ Kaveh (1):** No.
1. scenario.md says "keep your architecture simple". A lakehouse is the exact thing it warns against.
2. 500 rows (45k/month real) fit in RAM 1,000 times over. A JVM cluster adds startup, memory and failure points on the reviewer's laptop.
3. Infra earns no rubric points. Pipeline (20), RCA (25) and insight (20) do.

**🏛️ Jamshid (2):** Accepted. Then: Python 3.12 + uv, DuckDB file, dbt-duckdb (raw → staging → marts), stats in Python, one command. dbt is Yuno's real transform layer, so the model code is the part that ports.

**⚡ Kaveh (2):** Mostly yes. Three risks.
1. dbt v2 (Rust, Sep 14 2026) ships DuckDB as **Beta, CLI only**. It may not infer schemas of `read_csv()` sources. A reviewer who runs `pip install dbt` gets v2.
2. Why not plain polars scripts? Fewer moving parts.
3. Make is not on every machine (Windows).

**🏛️ Jamshid (3):**
1. Pin **dbt-core 1.12 + dbt-duckdb 1.11** (stable, Aug 2026) in `uv.lock`. v1 is "fully supported". We move to v2 when DuckDB leaves Beta.
2. Plain scripts would re-invent what dbt gives for free: DAG order, model contracts, generic tests, unit tests, docs and lineage. That *is* "good data engineering practice" (15 pts).
3. The real entry point is `uv run casa all`. The Makefile is sugar. The Dockerfile covers a machine with no Python.

**⚡ Kaveh (3):** Agreed. Now correctness of money.
1. No floats. Store amounts as **integer minor units** plus the currency exponent from `dim_currency` (CLP has 0 decimals; COP is used with 0 in practice). A float breaks the "rounding issue" pattern we must detect.
2. "Meaningful" must be data, not code: tier thresholds live in dbt `vars` (noise < 0.1%; small 0.1–2%; meaningful > 2%; large > 5% or > $20 USD).
3. Failed auths and pending settlements are **not** discrepancies. They leave the rate's denominator.

**🏛️ Jamshid (4):** Accepted, plus one addition. An `fx_rates_daily` table (date × currency → USD). For each cross-border row we compute the *expected* settlement at the settle-day rate. Then `diff = fx_explained + unexplained_residual`. That split separates "legit FX noise (<2%)" from real leakage. It is the core root-cause lever.

**⚡ Kaveh (4):** Good. Re-runs and late data.
1. Settlements arrive days after auth. Pending rows must be re-checked on the next run.
2. Incremental models are a classic source of silent drift. At this size a full rebuild takes about a second.

**🏛️ Jamshid (5):** Compromise. Raw is **append-only** (each file gets `batch_id`, `extracted_at`). Staging keeps the latest version per `transaction_id`. `fct_transactions` is a dbt **incremental merge on `transaction_id`**. It reads new raw rows **plus all rows still open** (pending, or inside a 10-day re-open window). A pending row that settles later is updated in place. Re-running the same file changes nothing.

**⚡ Kaveh (5):** Agreed, if a test guards it: a **parity test** (incremental result == `--full-refresh` result) runs in `make test`. Also `make rebuild` for a clean start. Next: statistics (25 pts).
1. Many segments means false positives. Use chi-square/Fisher per dimension with **Benjamini-Hochberg** correction, a minimum segment size, and effect sizes with 95% CIs, not only p-values.
2. Argentina, ARS, cross-border and PSP overlap. One **logistic regression** (statsmodels) gives odds ratios *controlling* for the others.
3. Clusters: first a readable **signature** (PSP × currency pair × tier × residual shape, e.g. "residual is always a multiple of 10"). ML clustering only if it adds something.

**🏛️ Jamshid (6):** Accepted. Findings go to a `findings` table (test, effect, CI, p_adj, $ impact). The report and the recommendations read that table. No hand-typed numbers. Now the dashboard: Metabase or Superset would mirror a prod BI tool.

**⚡ Kaveh (6):** No, for the lean build.
1. Metabase's DuckDB driver is a third-party plugin in a JVM container. That is one more thing to break.
2. DuckDB allows one writer **or** many readers across processes. A BI server holding the file blocks the pipeline.
3. Streamlit is one Python process. It opens DuckDB `read_only=True`. It answers "worst PSP last month" and "all rows > $50" with filters.

**🏛️ Jamshid (7):** Agreed. Alerts are a dbt mart (`mart_alerts`: week-over-week rate jump, large-$ outliers, overdue pending > 7 days) with thresholds in `vars`. `casa alerts` prints them and can post to a Slack webhook, off by default. Scale path: settlement data comes as **daily PSP files**, so batch stays the default there too. Streaming only feeds auth events (to know what is open in real time).

**⚡ Kaveh (7):** Agreed. One flag: `dbt-starrocks` is still labelled experimental. The scale path must say "spike it first".

**🏛️ Jamshid (8):** Agreed. **Final: lean batch tool (uv + DuckDB + dbt-duckdb 1.x + Python stats + Streamlit + Typer, Makefile wrapper) now; Iceberg + StarRocks + dbt + Airflow (+ Flink for auth events) documented as the scale path.**

**⚡ Kaveh (8):** Agreed.

## Trade-off table

| Option | Pros | Cons | Simplicity | Maintainability | Scales later? | Verdict |
|---|---|---|---|---|---|---|
| Notebook only | Fastest to insight; good visuals | Hidden state; no tests; weak "pipeline" story; hard one-command run | High | Low | No | Reject (a notebook may *read* marts) |
| Python scripts + pandas/polars + Parquet | Few deps; fast | Re-invents DAG, tests, contracts, lineage; logic hidden in dataframes | High | Med | Partly | Reject |
| **Python + DuckDB + dbt-duckdb** | SQL models port to Yuno's dbt; tests, contracts, unit tests, docs free; in-process; one file | dbt setup; pin v1 (v2 DuckDB is Beta) | High | **High** | **Yes (same dbt project)** | **Pick** |
| SQLite + SQL | Zero install | Weak analytics SQL, no dbt-first adapter, poor types for money/time | High | Med | No | Reject |
| Postgres + SQL | Real server; dbt-postgres | A container to run for 500 rows; not Yuno's OLAP | Med | Med | Partly | Reject |
| Spark | Scales to TBs | JVM, slow start, heavy for 45k rows/month | Low | Med | Yes | Reject |
| BI tool (Metabase/Superset) on top | Rich drill-down | JVM container; DuckDB plugin; file-lock clash | Med | Med | Yes | Scale path only |
| Full lakehouse (Iceberg + StarRocks + Airflow) | Mirrors Yuno prod | Brief says "not an enterprise DW"; heavy on a laptop | Low | High (at scale) | Yes | Scale path only |

## Reference stack

| Capability | Lean build (local) | Scale path (AWS / Yuno stack) | Why |
|---|---|---|---|
| Runtime & packaging | Python 3.12, **uv** + `uv.lock`, `pyproject.toml`, `src/` package | Same image on ECS/EKS; built in CI | One lockfile = same result on every machine |
| Ingest (batch) | Seeded generator writes CSV to `data/raw/`; loader appends to `raw` with `batch_id`, `extracted_at` | PSP settlement files (SFTP/API) → S3 landing → Airflow load into Iceberg | Settlement data is file-based and daily |
| Ingest (stream) | None | Auth events: Yuno event bus → **MSK → Managed Flink 2.3** → Iceberg + StarRocks | Only auth needs real time (open-auth view) |
| Storage | **DuckDB 1.5.x** single file (`casa.duckdb`); pin, skip 2.0 until stable | **S3 + Iceberg** (Glue catalog) = truth; **StarRocks 4.1** Primary Key tables = serving | Same SQL dialect family; PK tables absorb late updates |
| Transforms | **dbt-core 1.12 + dbt-duckdb 1.11** (raw → staging → marts); not dbt v2 yet | Same dbt project, `dbt-starrocks` target (spike first: experimental) | Models are the part that ports |
| Idempotency / late data | Append-only raw; latest-version staging; incremental **merge** on `transaction_id` + re-open window for pending; `make rebuild` | Same model; Iceberg MERGE / StarRocks PK upsert | Pending settlements re-evaluated each run |
| DQ tests & contracts | dbt: model contracts on marts, `unique`/`not_null`/`accepted_values`/`relationships`, dbt unit tests for tier + FX logic, parity test; pytest for Python | Same + dbt source freshness + row-count reconciliation vs PSP file totals | One test home; fail the build, not the dashboard |
| Money & FX | Integer minor units + `dim_currency.exponent`; `fx_rates_daily` seed (USD base) | FX feed (e.g. central-bank/PSP rates) loaded daily into Iceberg | No float drift; FX split explains legit noise |
| Analysis / stats | **pandas + scipy + statsmodels** (chi-square/Fisher, BH, logit odds ratios, bootstrap CIs); scikit-learn only if clustering adds value | Same package as a scheduled job (Airflow → container) | Evidence, not eyeballing (25 pts) |
| Charts & report | **Plotly**; `reports/findings.md` + HTML charts generated from `findings` table | Same report job; stored in S3 | Numbers come from data, never typed |
| Dashboard | **Streamlit** on localhost, DuckDB `read_only=True` | **Superset** (or Grafana) on StarRocks for ops; Streamlit kept for analysts | One process locally; shared BI at scale |
| CLI | **Typer** `recon` (`all`, `generate`, `build`, `analyze`, `alerts check`, `dashboard`, …) | Same CLI as container entrypoint | One entry point for humans and schedulers |
| Alerts | `mart_alerts` in dbt (WoW jump, >$ outliers, overdue pending); `casa alerts`; Slack webhook off by default | Airflow task on `mart_alerts` → SNS → Slack/PagerDuty | Alert rules are versioned SQL + `vars` |
| Orchestration | **Makefile** wraps `uv run casa …`; dbt owns the DAG; no Dagster/Airflow | **MWAA (Airflow 3.3)** + Cosmos for dbt | No extra service for a 1-second DAG |
| Docker | Optional `Dockerfile` + 1-service Compose (build + dashboard) | Same image, Terraform-managed | Fallback for a reviewer without Python |
| Reproducibility | Fixed RNG seed; pinned deps; `run_manifest.json` (seed, versions, row counts, git SHA) | Same + OpenLineage from Airflow/dbt | Any number can be traced to a run |
| Security / PCI | No PAN; tokenised `customer_id`; synthetic data only | IAM least privilege, KMS on S3, no PAN in analytics, audit logs | Keep analytics out of PCI scope |

## Data model

| Table | Grain | Key columns |
|---|---|---|
| `raw.transactions` | 1 row per exported row per file | `transaction_id`, `batch_id`, `extracted_at`, raw fields |
| `stg_transactions` | 1 row per `transaction_id` (latest version) | typed amounts (minor units), `auth_ts`, `settle_ts`, `status` |
| `dim_psp` / `dim_country` / `dim_currency` | 1 row per PSP / country / currency | `psp_id`; `country_code`, `currency_code`; `exponent` |
| `dim_date` | 1 row per day | `date_key`, `dow`, `is_weekend`, `week_start` |
| `fx_rates_daily` | 1 row per date × currency | `rate_date`, `currency_code`, `usd_rate` |
| `fct_transactions` | 1 row per transaction | FKs, `auth_amt`, `settle_amt`, `diff_amt`, `diff_pct`, `diff_usd`, `fx_explained_usd`, `residual_usd`, `tier`, `days_to_settle`, `is_cross_border`, `amount_tier`, `is_pending` |
| `mart_discrepancy_weekly` | week × PSP × country × currency pair | counts, rate, $ totals, p95 diff |
| `mart_alerts` | 1 row per alert | `alert_id`, `week`, `segment`, `metric`, `value`, `threshold`, `severity` |
| `findings` (Python) | 1 row per tested hypothesis | `finding_id`, `test`, `effect`, `ci_low/high`, `p_adj`, `usd_impact` |

## Recommendation

**(A) Lean build**
- Batch pipeline: generate (seeded) → load raw (append-only) → dbt build (staging, dims, fact, marts, tests) → analyze (findings) → report + alerts → Streamlit.
- One command: `make all` = `uv run casa all`. Fresh-clone test it before the interview.
- Pin dbt-core 1.12 + dbt-duckdb 1.11 and DuckDB 1.5.x. Do not use dbt v2 (DuckDB adapter is Beta).
- Money in integer minor units. Tier thresholds and alert thresholds in dbt `vars`.
- FX split: `diff = fx_explained + residual`. Findings table drives report and $ recommendations.
- Streamlit opens DuckDB read-only. Alerts are a dbt mart plus a CLI.

**(B) Scale path (documented only)**
- PSP settlement files → S3 → Airflow (MWAA 3.3) → Iceberg (Glue) as truth.
- Auth events → MSK → Managed Flink 2.3 → Iceberg + StarRocks, so open auths are visible live.
- Same dbt project on StarRocks 4.1 (spike `dbt-starrocks` first; fall back to StarRocks MVs if it lacks features).
- StarRocks Primary Key tables serve marts; Superset for ops; alerts via Airflow → SNS → Slack/PagerDuty.
- Same Python analysis package and CLI image, run by Airflow. Terraform for infra.

## Key practices
- Raw is append-only and immutable. Every change is a new version, never an overwrite.
- Re-runs are idempotent: merge on `transaction_id`. A parity test proves incremental == full refresh.
- Pending and failed rows are states, not discrepancies. Overdue pending is its own alert.
- Money is integer minor units per currency. Never floats. Report in USD with a dated FX rate.
- Split FX-explained from unexplained residual before blaming a PSP.
- Correct for many tests (BH), show effect sizes + CIs, and control confounders with one regression.
- Every number in the report comes from a table produced by the run. The run manifest makes it replayable.
- Config (thresholds, seed) is data in `vars`/YAML. Logic is code with tests.

## Open disagreements
- **ML clustering in the lean build.** Jamshid: add HDBSCAN on (diff_pct, residual, days_to_settle) to show "systematic vs random". Kaveh: readable signatures already find the planted patterns; HDBSCAN clusters are hard to explain to a CFO. Tie-break: ship signatures; add HDBSCAN only if it finds a group the signatures miss.
- **dbt-starrocks vs StarRocks MVs at scale.** Jamshid: one dbt project everywhere. Kaveh: adapter is experimental; MVs are native. Tie-break: a one-day spike decides.

## Sources
1. DuckDB, "DuckDB Now Ships inside dbt v2" (Sep 22, 2026): https://duckdb.org/2026/09/22/dbt-fusion
2. dbt Docs, "Upgrading to v2" (DuckDB adapter Beta, CLI only; v1.x fully supported): https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v2
3. PyPI, dbt-duckdb 1.11.0 (Aug 7, 2026; incremental merge, external sources): https://pypi.org/project/dbt-duckdb/
4. DuckDB Docs, Concurrency (one writer or many readers): https://duckdb.org/docs/current/connect/concurrency
5. DuckDB, "Announcing DuckDB 1.5.6" (v2.0 due Oct 2026): https://duckdb.org/2026/09/28/announcing-duckdb-156
6. Streamlit, 2026 release notes: https://docs.streamlit.io/develop/quick-reference/release-notes/2026
7. MotherDuck, Metabase DuckDB driver (third-party plugin): https://github.com/motherduckdb/metabase_duckdb_driver
8. AWS, Amazon MWAA supports Airflow 3.3.1 (Sep 2026): https://aws.amazon.com/about-aws/whats-new/2026/09/amazon-mwaa-apache-airflow-3-3-1/
9. AWS, Managed Service for Apache Flink supports Flink 2.3 (Jul 2026): https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-managed-service-flink-2-3/
10. StarRocks 4.1 release notes; dbt StarRocks setup (experimental): https://docs.starrocks.io/releasenotes/release-4.1/ · https://docs.getdbt.com/docs/local/connect-data-platform/starrocks-setup
