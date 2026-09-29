# 07 · Alert System & Metrics
**Purpose:** Pick the engine and the rules for FR3's automated alert system (built next to the dashboard). The rules flag bad segments and large rows, and the report shows week-over-week change both ways.
**Frame:** lean local build (one command) + AWS scale path, documented only. [scenario.md](../../../architect/00-scenario/scenario.md) is the source of truth; the [decision sheet](00-SUMMARY.md) overrides everything else.

## Engine choice

| # | Option | What it is | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | YAML rules + small Python evaluator | `recon alerts` reads dbt marts and applies `alerts.yaml` | Rules are data; easy to unit-test | ~150 lines of our own code | High | High | 🥇 Best |
| 2 | Alert rules as SQL in dbt | A `mart_alerts` model with fixed thresholds | No extra code; runs in the build | No BH or p-chart; weaker stats | High | Med | 🥈 Runner-up |
| 3 | Grafana alerting on StarRocks | Alert queries on the marts | Rules can be provisioned as code | Stats are hard in alert SQL; per-seat cost | Med | Med | ❌ Scale-path only |
| 4 | Soda / GX Core / Elementary | Extra data-quality tools | Rich checks | A second DQ framework next to dbt | Med | Med | ❌ Reject |
| 5 | EWMA / CUSUM charts | Small-drift charts per segment | Catch slow drifts | The p-chart already covers drift; little gain in ~13 weeks | Med | Med | ❌ Prod only |
| 6 | Prometheus + Alertmanager | Business rates as metric series | Good for infra alerts | Weak for rate statistics; extra stack | Low | Med | ❌ Reject |

**Parts used (with option 1):**
- **dbt tests:** a failed build is the data-quality signal (exit code 5). It is not an alert rule.
- **dbt marts:** weekly counts and rates per segment.
- **Config:** `alerts.yaml` (rules) and `thresholds.yaml` (money limits).
- **Evaluator:** `make alerts` = `uv run recon alerts`. It uses statsmodels for BH and Wilson.
- **Output:** `reports/alerts.jsonl` + `reports/alerts.md`. The dashboard Alerts page reads the same file.
- **Slack:** optional, off by default. It posts only if `SLACK_WEBHOOK_URL` is set.
- **AWS path:** the same evaluator as an Airflow task after dbt on StarRocks → SNS → Slack.

## Top 2 choices
**🥇 YAML rules + small Python evaluator (row 1):** dbt builds the marts, and a failed dbt test stops the run. `recon alerts` then applies the 6 rules to the last closed week and writes `alerts.jsonl` and a Markdown report. The same code runs at scale as an Airflow task.
**🥈 Alert rules as SQL in dbt (row 2):** simpler, since there is no evaluator. It comes second because fixed SQL thresholds cannot do BH or a p-chart, so the peer and change rules get weaker.

## How rules are evaluated
- **Closed week:** an ISO week (Mon–Sun, by auth date) whose end is ≤ as-of − 7 days. As-of = the latest data timestamp, not the wall clock.
- **Which week:** weekly rules use the last closed week. An open week is half-settled, so its rate is biased.
- **n:** approved + settled rows in the window.
- **Min sample:** n < 50 → "insufficient data" (info), never an alert.
  - Why 50: alerts need the normal approximation (n·p ≥ 5 at p ≈ 14%).
  - The worst-week card uses 30, because a ranking only needs a stable $ sum.
- **Status (no state file):** key = `rule_id|segment`, with `period` kept as a field.
  - NEW = fires this week, not last closed week.
  - ONGOING = fires in both.
  - RESOLVED = fired last closed week, not now.
  - A rerun on the same data gives the same output.
- **Week-over-week (info):** portfolio and each PSP × country, last closed week vs the one before, in pts.
  - ▲ worse / ▼ better, both shown.
  - In the report and on the dashboard Overview. It is not an alert.
- **Severity:** SEV1 = page (prod only, pipeline down) · SEV2 = same day · SEV3 = weekly review · Info = report only.
- **Money section of the report:** gross under, gross over and net (USD). Over-settlement is a report line, not an alert.

## Core alert rules (6)

| Rule | In plain English | Metric | Trigger | Severity | Owner |
|---|---|---|---|---|---|
| Peer | Is this PSP worse than the other PSPs in the same country? | Meaningful rate, PSP × country, trailing 4 closed weeks | BH q < 0.05 AND gap ≥ 2 pts | SEV2 | PSP ops |
| Change | Is this week worse than usual? | Weekly meaningful rate, portfolio + each PSP × country | Above the p-chart upper limit (3σ, trailing 8 closed weeks) | SEV3 | PSP ops |
| Money leak | Are we losing more money than usual? | Under-settled USD ÷ settled USD, on the FX residual | Warn % / crit % from `thresholds.yaml` | Warn SEV3 · crit SEV2 | Finance |
| Large-rows summary | How many rows need a closer look? | `large` rows in the last closed week | Any → one alert per run: count, $ total, top 3 PSP × country | SEV3 | PSP ops |
| Pending aging | Is money stuck unsettled? | Pending rows per PSP × country: count, $, oldest age | Oldest > 7 days (SEV3); > 14 days (SEV2) | SEV3 / SEV2 | PSP ops + Finance |
| Settle lag | Are orders settling late? | Late share per country × size tier, trailing 4 closed weeks | Late share > limit in `alerts.yaml` | SEV3 | PSP ops |

Rule notes (one line each):
- **Peer:** the Wilson CI is shown in the alert text, but it does not gate the alert.
- **Money leak:** the residual uses auth-date FX, so normal FX moves do not count. `thresholds.yaml` also holds one weekly USD line for the CFO story.
- **Large-rows summary:** the rows themselves go to the dashboard Outliers page (min $50 filter) and `recon query`.
- **Pending aging:** uses as-of = the latest data timestamp, not the closed week.
- **Settle lag:** late = settled more than 7 days after auth, or still pending after 7 days.

## Demo and tests
- **Planted drift:** the PSP_C fee starts in month 3, so the change rule fires in the demo ("worse this week").
- **Planted patterns:** P1 fires the peer rule (PSP_B in AR). P2 fires the settle-lag rule (CO $200+).
- **Fixtures:** one firing test and one silent test per rule (12 tests).
- **Smoke run:** at `--rows 500`, every rule returns "insufficient data" (n ≈ 2 per cell-week). This is expected, and a test checks it. Alerts need the 135k default.

Key sources: [NIST p-chart](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm) · [statsmodels multipletests (BH)](https://www.statsmodels.org/dev/generated/statsmodels.stats.multitest.multipletests.html) · [statsmodels Wilson CI](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_confint.html) · [Grafana alert provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/) · [Soda Core ELv2](https://soda.io/blog/soda-core-license-update-moving-to-elastic-license)
