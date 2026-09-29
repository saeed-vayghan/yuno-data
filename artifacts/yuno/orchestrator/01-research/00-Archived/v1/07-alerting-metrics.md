# Alerting & Metrics: Decision Brief (v1)

## Question
Stretch 3 of the CasaMarket take-home asks for "a dashboard or alert system". Which metrics should watch settlement discrepancies (auth amount vs settled amount, MX/CO/AR/CL, 3–5 PSPs)? Which alert rules turn those metrics into signals that are correct and not noisy? Which tools run it: a lean local build now, and a documented path to AWS on Yuno's stack (StarRocks, Flink, dbt, Airflow) later?

## Debate (🏛️ Jamshid vs ⚡ Kaveh)

**🏛️ Jamshid:** Three layers: business, data quality (DQ) and pipeline. All rules sit in one `alerts.yml` (`id, layer, metric, grain, rule, threshold, min_n, severity, owner, runbook`). The main statistical rule is a p-chart per PSP×country×week, with 3σ limits from a trailing 8-week baseline. Alerts go to `alerts.jsonl` plus `alerts.md`.

**⚡ Kaveh:** Four objections.
1. **Sample size.** The dataset has about 500–1,500 rows over 14 weeks. 16 PSP×country cells gives 2–7 rows per cell-week. A p-chart there only makes noise.
2. **Wrong tool for the question.** The planted patterns (PSP_X +3–4 pp in AR, a rounding bug) are *chronic*, so they are present from week 1. A control chart built on the segment's own baseline never sees a chronic shift, because the shift is part of the baseline.
3. **Two places for DQ.** If DQ lives in both dbt tests and YAML, the two copies will drift apart.
4. **Reproducibility.** A "pending > 7 days" rule that uses the wall clock gives a different answer every day the reviewer runs it.

**🏛️ Jamshid:** I accept (2), and it sharpens the design. We need two statistical rule types.
- **Peer rule** (chronic): segment rate vs the rest of the portfolio. Use a two-proportion z-test plus a Wilson CI, and Benjamini–Hochberg (BH) at q = 0.05, because we test many segments at once.
- **Change rule** (drift): a p-chart vs the segment's own trailing baseline.

For (1), every rule has a `min_n`. The normal approximation needs n·p̄ ≥ 5 and n·(1−p̄) ≥ 5. With p̄ ≈ 14%, that is n ≥ 36, so we set a floor of 50. Below the floor we emit `INSUFFICIENT_DATA` (info) and never alert. At real volume (45k/month ≈ 650 per cell-week), weekly PSP×country control charts work.

**⚡ Kaveh:** OK. For (3), I propose this split:
- dbt tests own the contracts: unique, not_null, accepted_values, `settled_at ≥ authorized_at`, FX coverage, reconciliation. At severity `error` they fail the build.
- YAML owns business and statistical rules only. They read the dbt marts.
- Pipeline metrics come from dbt `run_results.json` plus a small run manifest.

(5) Why not Soda, GX or Elementary for the DQ side?

**🏛️ Jamshid:** I checked each one.
- Soda Core v4 moved to Elastic License 2.0 (PyPI lists it as "Proprietary").
- GX Core is still Apache-2.0 (Fivetran has been its steward since May 2026), but it adds a second test framework next to dbt.
- Elementary supports DuckDB. But its package has no StarRocks dispatch macros (master, 23 Sep 2026), so it would not carry over to Yuno's prod.

So: dbt tests only. I also accept (4). Every rule is evaluated at `--as-of` = the max timestamp in the data, never `now()`.

**⚡ Kaveh:** (6) Money. Netting under-settlement against over-settlement hides both. Over-settlement is not "free money". It is a customer overcharge and a chargeback risk. (7) Slack payloads must never carry PANs or customer IDs, because of PCI-DSS. (8) Reruns must not duplicate alerts.

**🏛️ Jamshid:** Accepted, all three.
- Report under-settlement $, over-settlement $ and gross |Δ| $, all in USD, with net shown only as context.
- Payloads carry aggregates and rule IDs only.
- `dedupe_key = rule_id|segment|period`. A rerun with the same inputs gives byte-identical `alerts.jsonl`. A `state.json` marks each alert as NEW, ONGOING or RESOLVED against the previous run.

**⚡ Kaveh:** (9) Do we build EWMA or CUSUM too?

**🏛️ Jamshid:** In the build: p-chart (change rule) and peer z-test (chronic rule). EWMA (λ = 0.2) is documented for prod only, where the data is dense enough to catch small drifts. See Open disagreements.

**Both:** **Agreed** on:
- the 3-layer catalog;
- the dbt-tests/YAML split;
- peer and change rules with `min_n` and BH correction;
- `--as-of` evaluation and dedupe state;
- gross + net money metrics;
- PCI-safe payloads;
- one evaluator that runs locally and later as an Airflow task.

## Metric catalog
Grain for business metrics: PSP, country, currency pair and ISO week, plus the combinations. "Meaningful" and "large" use the same definitions as Core 1 (e.g. >2%; >5% or >$20).

| Layer | Metric | Example threshold | Severity | Owner |
|---|---|---|---|---|
| Business | Meaningful discrepancy rate (count), portfolio/week | warn > 12%, crit > 18% (the CFO's figure) | SEV2 | Finance |
| Business | $ discrepancy rate = gross \|Δ\| USD / auth USD | warn > 1%, crit > 2% | SEV2 | Finance |
| Business | Large-discrepancy rate | > 5% of txns (baseline 3–5%) | SEV2 | PSP ops |
| Business | Under-settlement USD / week (leakage) | warn > $5k, crit > $10k (≈ $127k/qtr pace) | SEV2 | Finance |
| Business | Over-settlement USD / week | > $2k | SEV3 | Finance + CX (overcharge risk) |
| Business | Peer rule: PSP×country (or currency pair) meaningful rate vs rest | z-test BH q < 0.05 AND Wilson low > peer + 2 pp, n ≥ 50 | SEV2 | PSP ops |
| Business | Change rule: segment weekly rate vs trailing 8-wk p-chart | > UCL (3σ, varying n), n ≥ 50 | SEV3 | PSP ops |
| Business | Week-over-week change of meaningful rate | +3 pp and p < 0.01 | SEV3 | PSP ops |
| Business | Rounding signature per PSP×pair (\|Δ\| equals a rounding unit, e.g. CLP 0-decimal) | > 20% of that pair's discrepancies | SEV3 | PSP ops |
| Business | Pending aging: approved auth with no settlement | > 7 d warn; > 14 d crit; > 1% of the week's approvals | SEV2 | PSP ops + finance |
| Business | Settlement delay p95 per PSP×country×size tier | > 5 days (e.g. CO > $300) | SEV3 | PSP ops |
| DQ | Freshness of settlement files: as_of − max(settled_at) | > 2 days | SEV2 | Data team |
| DQ | Daily volume vs trailing 4 same weekdays | ±40% | SEV3 | Data team |
| DQ | Contract: not_null, accepted_values (country, currency, PSP, status), amount > 0, settled_at ≥ authorized_at | any failing row → fail build | SEV2 | Data team + producer |
| DQ | Duplicate transaction_id / settlement line | any | SEV2 (fail build) | Data team |
| DQ | FX rate missing for (date, currency pair) | any | SEV2 (fail build) | Data team |
| DQ | Reconciliation: approved = settled + pending + voided (count and amount); orphan settlements | diff ≠ 0 | SEV2 (fail build) | Data team + PSP ops |
| Pipeline | Run success per step (generate, dbt build, evaluate) | any failure | SEV2 | Data team |
| Pipeline | Duration vs median of last 10 runs | > 2× | SEV3 | Data team |
| Pipeline | Rows in vs out: raw = staged + quarantined | mismatch | SEV2 (fail build) | Data team |

## Trade-off table

| Option | Layer | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|
| YAML rules + Python/SQL evaluator on DuckDB → `alerts.jsonl` + `alerts.md` | Business, stats | One config; unit-testable; ports to an Airflow task | Custom code (~150 lines) | High | High (rules as data) | **Build** |
| dbt tests (built-in + singular, `severity`, `store_failures`) | DQ | Already in the stack; same on StarRocks | No anomaly detection | High | High | **Build** |
| Soda Core v4 | DQ | YAML contracts | ELv2 (PyPI: "Proprietary"); second framework | Medium | Medium | Skip |
| GX Core 1.x | DQ | Apache-2.0; rich expectations | Heavy; overlaps dbt; steward just changed | Low | Medium | Skip |
| Elementary OSS | DQ anomalies | dbt-native; supports DuckDB | No StarRocks macros, so it would not reach prod | Medium | Medium | Skip (watch) |
| Slack incoming webhook | Notify | 5 lines; good demo | Not a pager; no ack | High | High | Optional (env var) |
| Prometheus/AMP + Alertmanager | Pipeline, StarRocks | StarRocks exports Prometheus metrics; SNS receiver | Another stack; PromQL is weak for business stats | Low | Medium | Scale: infra only |
| Grafana (AMG) alerting | View + alerts | Best StarRocks dashboards | Per-seat cost; rules become UI state | Medium | Medium | Scale: dashboards |
| CloudWatch alarms + EMF metrics | Pipeline + custom | Native for MWAA/Flink/MSK; composite alarms | Weak visuals | Medium | High | **Scale: alarm backbone** |
| PagerDuty / incident.io | Paging | Schedules, escalation, dedupe | Seat cost | Medium | High | Scale: SEV1 only |
| Opsgenie | Paging | Familiar | End of support 5 Apr 2027 | n/a | None | Reject |

## Recommendation

**(A) Lean build.** Python 3.12 + uv, DuckDB, dbt-duckdb. `make all` runs these steps:
1. **generate** the dataset.
2. **dbt build** (models + tests). An `error` test stops the run.
3. **evaluate** `config/alerts.yml`. It writes:
   - `out/metrics.parquet` (every metric × grain × week);
   - `out/alerts.jsonl`;
   - `out/alerts.md` (grouped by owner, NEW first).
4. **report.**

Behaviour of the evaluator:
- The stats use statsmodels (`proportion_confint` Wilson, `proportions_ztest`, `multipletests` BH). These are the same helpers Core 2 uses, so the evidence is consistent.
- `--as-of` defaults to the max data timestamp.
- The exit code is non-zero only for SEV2 DQ or pipeline failures.
- Posts to Slack only if `SLACK_WEBHOOK_URL` is set, and never fails the run.
- The localhost dashboard (if built) reads `metrics.parquet` and `alerts.jsonl`. It computes nothing on its own.

Tests:
- one firing and one silent fixture per rule type;
- a `min_n` guard test;
- an idempotency test (two runs give the same output).

**(B) Scale path (documented, not built).**
- **Batch path:** Airflow runs dbt on StarRocks. Tests use `store_failures`, and quarantine tables block publishing of the marts.
- **Evaluator:** the same `alerts.yml` evaluator runs as the next Airflow task. It writes alerts to a StarRocks table and publishes metrics to CloudWatch via EMF.
- **Streaming path:** Flink joins settlement events to auths (keyed state, TTL 14 d). It emits a "late/unmatched" side output for pending aging in near real time.
- **Alarms:** CloudWatch alarms cover MWAA, Flink, freshness and reconciliation.
- **Dashboards:** StarRocks' Prometheus metrics go to AMP. Grafana is for dashboards.
- **Routing:** EventBridge → SNS.
  - SEV1 (settlement pipeline down past the daily close, or a reconciliation break) goes to PagerDuty or incident.io.
  - SEV2/3 go to Slack plus a Jira ticket for PSP ops or finance.
- **Change rules at volume:** EWMA per PSP×country.
- **Rules as code:** rules live in the repo and are reviewed in PRs.

## Alert design rules
- **Two statistical questions, two rules.** "Is this segment worse than its peers?" is the peer z-test with BH. "Did it get worse?" is the p-chart, or EWMA at scale. Never alert on a rate without a CI.
- **Minimum sample size.** `min_n` ≥ 50 and n·p̄ ≥ 5. Below that, emit `INSUFFICIENT_DATA` (info) and never page.
- **Severity.** SEV1 is a page (prod only). SEV2 is handled the same day. SEV3 goes to a weekly review. INFO goes to the report. Business alerts never page.
- **Routing by owner.** PSP ops gets PSP×country and rounding alerts. Finance gets leakage and $ rates. The data team gets DQ and pipeline alerts. Producers get contract breaks.
- **Dedupe.** Key = `rule_id|segment|period`. Show state as NEW, ONGOING or RESOLVED. Group child segments under the parent alert.
- **Money.** Show gross under- and over-settlement separately, in USD using FX at settlement date. A missing FX rate fails the build rather than guessing.
- **Deterministic and PCI-safe.** Evaluate `--as-of` the data, not the wall clock. Payloads carry aggregates, rule IDs and runbook links only, never PAN or customer IDs.
- **Keep alerts lean.** Every rule has an owner and a runbook line. A rule with no action taken in 30 days is downgraded or deleted.

## Open disagreements
- **EWMA in the lean build.**
  - Jamshid: add it (~15 lines). It detects small persistent drifts that a p-chart misses, and it shows depth.
  - Kaveh: with 2–7 rows per cell-week it only adds noise and untested code. The peer rule already finds the chronic patterns.
  - Deciding rule: include EWMA only at portfolio or country grain, where weekly n ≥ 50. Otherwise document it for prod.
- **Where prod business rules evaluate.**
  - Jamshid: StarRocks SQL surfaced as Grafana alert rules, closer to the data.
  - Kaveh: the Python evaluator in Airflow, the same tested code as local.
  - Leaning towards Kaveh for v1. Revisit if latency needs are under 1 hour.

## Sources
1. NIST/SEMATECH e-Handbook, 6.3.3.2 Proportions (p) control charts: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm
2. NIST/SEMATECH e-Handbook, 6.3.2.4 EWMA control charts: https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm
3. DuckDB, "DuckDB Now Ships inside dbt v2" (dbt 2.0.0, 14 Sep 2026; some dbt-duckdb features not yet at parity): https://duckdb.org/2026/09/22/dbt-fusion
4. dbt-duckdb adapter (PyPI 1.11.0, dbt-core 1.12.x): https://github.com/duckdb/dbt-duckdb
5. Soda, "Soda Core License Update: Moving to Elastic License 2.0" (27 Jan 2026): https://soda.io/blog/soda-core-license-update-moving-to-elastic-license
6. Fivetran, steward of GX Core (May 2026; Apache-2.0): https://www.fivetran.com/press/fivetran-to-become-steward-of-the-great-expectations-open-source-community-and-gx-core-project
7. Elementary dbt package (adapter dispatch macros include duckdb, clickhouse, trino; no starrocks, checked 29 Sep 2026): https://github.com/elementary-data/dbt-data-reliability
8. StarRocks monitoring metrics (Prometheus endpoint): https://docs.starrocks.io/docs/administration/management/monitoring/metrics/
9. AWS, "Alerting best practices with Amazon Managed Service for Prometheus": https://aws.amazon.com/blogs/mt/alerting-best-practices-with-amazon-managed-service-for-prometheus/
10. Atlassian, Migrate from Opsgenie (end of sale 4 Jun 2025, end of support 5 Apr 2027): https://www.atlassian.com/software/opsgenie/migration
