# 07 · Alert System & Metrics
**Purpose:** Pick the metrics and alert rules for FR3's automated alert system (built next to the dashboard). They flag bad segments and outlier transactions, and they track week-over-week change.
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Option | Layer | What it is | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | YAML rules + Python evaluator (statsmodels) | Rules | `make alerts` reads dbt marts and applies `alerts.yml`. Peer rule: two-proportion z + Wilson + BH. Change rule: p-chart vs trailing baseline | One config; unit-testable; same code runs in prod | ~150 lines of our own code | High | High | 🥇 Best: rules as data |
| 2 | dbt tests (built-in + singular) | DQ | Contracts, duplicates, FX coverage, reconciliation. An `error` test fails the build | Already in the stack; same on StarRocks; one DQ home | No anomaly detection | High | High | 🥇 Best: owns DQ |
| 3 | Soda Core / GX Core / Elementary | DQ | Extra DQ frameworks | YAML contracts; rich checks; dbt-native anomalies | Soda is ELv2 now; GX duplicates dbt; Elementary has no StarRocks macros | Med | Med | ❌ Reject: second framework |
| 4 | `alerts.jsonl` + Markdown report + optional Slack webhook | Delivery | Deduped by `rule_id\|segment\|period` as NEW / ONGOING / RESOLVED. Slack only if `SLACK_WEBHOOK_URL` is set | Rerun gives the same output; the dashboard reads the same file; no PAN or customer IDs in payloads | Slack is not a pager; no ack | High | High | 🥇 Best: simple, deterministic |
| 5 | EWMA / CUSUM in the lean build | Rules | Small-drift charts per segment | Catch small, slow drifts | 2–7 rows per cell-week makes them noise; more code to test | Med | Med | ❌ Reject: prod only |
| 6 | Airflow → dbt on StarRocks → same evaluator → CloudWatch/SNS → Slack/PagerDuty | Scale path | The evaluator becomes an Airflow task. Metrics go out via EMF; alarms route through SNS | Same tested rules as local; native AWS alarms; PagerDuty only for SEV1 | Pager seat cost; SNS setup | Med | High | 🥇 Best: documented only |
| 7 | Grafana alerting on StarRocks SQL | Scale path | Rules as Grafana alerts that query the marts directly | Close to data; good dashboards | Rules live as UI state; hard to unit-test; per-seat cost | Med | Med | 🥈 Runner-up: if <1 h latency is needed |
| 8 | Prometheus/AMP + Alertmanager for business rules | Scale path | Business rates as Prometheus series | Good for infra alerts | PromQL is weak for proportion stats; extra stack | Low | Med | ❌ Reject: infra only |
| 9 | Opsgenie | Delivery | Paging tool | Familiar | End of support 5 Apr 2027 | Med | Low | ❌ Reject: being retired |

## Top 2 choices
**🥇 dbt tests + YAML rules + Python evaluator (rows 1, 2, 4, 6):** dbt builds the metric marts and its tests fail the build on bad data. `make alerts` then runs the peer and change rules as of the latest data timestamp and writes deduped alerts to `alerts.jsonl` and a Markdown report, with an optional Slack post. At scale, the same evaluator runs in Airflow after dbt on StarRocks and routes alerts through CloudWatch/SNS.
**🥈 Grafana alerting on StarRocks (row 7):** Rules sit next to the data and the dashboards, so no evaluator task is needed. It comes second because the rules are hard to test and live in the UI. Pick it only if the team needs alerts faster than the Airflow schedule.

## Core alert rules
| Rule | Metric | Trigger | Severity | Owner |
|---|---|---|---|---|
| Peer (chronic) | Meaningful rate per PSP×country vs the rest | BH q < 0.05 AND Wilson low > peer + 2 pp | SEV2 | PSP ops |
| Change (drift) | Segment weekly meaningful rate | Above p-chart UCL (3σ, trailing 8 weeks) | SEV3 | PSP ops |
| Week-over-week | Portfolio meaningful rate | +3 pp vs last week and p < 0.01 | SEV3 | Finance |
| Money leak | Under-settlement USD per week | Warn > $5k, crit > $10k | SEV2 | Finance |
| Outlier transactions | \|Δ USD\| > $50 OR robust z > 3.5 | Any new row goes on the investigate list | SEV3 | PSP ops |
| Pending aging | Approved, not settled, age as of the data | > 7 days (crit > 14 days) | SEV2 | PSP ops + Finance |
| Data quality | dbt tests (contracts, duplicates, FX, reconciliation) | Any `error` test fails the build | SEV2 | Data team |
| Minimum sample | n per segment-period | n < 50 → "insufficient data" (info), never alerts | Info | Data team |

Key sources: [NIST p-chart](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm) · [statsmodels multipletests (BH)](https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html) · [statsmodels Wilson CI](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html) · [Soda Core ELv2](https://soda.io/blog/soda-core-license-update-moving-to-elastic-license) · [Opsgenie end of support](https://www.atlassian.com/software/opsgenie/migration)
