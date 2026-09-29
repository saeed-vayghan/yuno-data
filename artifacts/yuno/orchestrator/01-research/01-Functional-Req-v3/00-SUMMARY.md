# v3 Summary: Final Picks + Decision Sheet (CasaMarket)

**Source of truth:** [scenario.md](../../../architect/00-scenario/scenario.md).
**Frame:** lean local build (one command) + AWS scale path, documented only. Avoid over-engineering; use simple English.
**What changed from v2:** all agreed fixes from the [review](../00-Archived/v3-review/00-SUMMARY.md).

## Picks

| # | Topic | Serves | 🥇 Best | 🥈 Runner-up |
|---|---|---|---|---|
| 01 | [System](01-discrepancy-analysis-system.md) | FR1 | Python 3.12 + uv, DuckDB, dbt-duckdb, full rebuild each run | DuckDB + plain SQL files (no dbt) |
| 02 | [Detection & root cause](02-detection-root-cause-methods.md) | FR1, FR2, FR4 | Segment tests + logistic GLM | Rule-based cause labels |
| 04 | [Synthetic data](04-synthetic-data-tools.md) | Test data | Custom seeded generator (YAML spec) | DuckDB SQL generator |
| 05 | [CLI](05-cli-tool.md) | FR3 (CLI reports), run | Typer `recon` | Click |
| 06 | [Dashboard](06-web-ui.md) | FR3 dashboard | Streamlit + Plotly | Evidence |
| 07 | [Alerts](07-alerting-metrics.md) | FR3 alert system | YAML rules + small Python evaluator | Alert rules as SQL in dbt |

## Decision sheet (all docs follow this)

### Money and FX
- **Currency model:**
  - both amounts (`authorized_amount`, `settled_amount`) are in the merchant's local currency (MXN, COP, ARS or CLP);
  - a **cross-border** row has `payer_currency = USD`: the customer pays in USD and the PSP converts.
- **Money type:** integer minor units. CLP has 0 decimals; MXN, COP and ARS have 2.
- **FX table:** `fx_rates_daily(date, currency, local_per_usd)`, generated into `data/raw` (a source, not a seed).
- **Expected settle amount:**
  - cross-border: `expected = auth × local_per_usd(settle_day) / local_per_usd(auth_day)`;
  - domestic: `expected = auth`.
- **Residual:** `residual = settled − expected`, and `residual_pct = residual / expected`.
- **USD:** `residual_usd` uses the auth-day rate.
- **All cut-offs** use the absolute residual (`|residual_pct|`, `|residual_usd|`).

### Categories (one per row, checked in this order)

| Category | Rule | Brief tier | Target share* |
|---|---|---|---|
| `exact` | Δ = 0 | match 60–70% (exact + rounding) | 67% |
| `rounding` | \|Δ\| ≤ 1 minor unit | match | 1% |
| `fx_tolerance` | residual ≤ 2% and < $20 | small 0.1–2%: 15–20% | 18% |
| `meaningful` | residual 2–5% and < $20 | > 2%: 10–18% (with large) | 10% |
| `large` | residual > 5% or ≥ $20 | 3–5% ("the outliers to investigate") | 4% |

\* Share of **approved + settled** rows. Failed + pending ≤ 7% of all rows (failed 4%, pending 3%), so every brief range holds on both denominators.

- **Flag:** `is_meaningful` = `meaningful` or `large`, a share of about 14%.
- **Outlier:** an outlier is a `large` row, which is how the brief itself describes the large tier. There is no z-score.

### Planted patterns (one version everywhere)

| # | Pattern | Rule |
|---|---|---|
| P1 | PSP_B in Argentina | meaningful rate about +3.5 pts vs the other PSPs in AR |
| P2 | Colombia orders > $300 | longer settle lag (+2–4 days) and more lag outliers |
| P3 | Weekend authorizations | meaningful rate about 1.3× weekday |
| P4 | PSP_D rounding | cross-border CLP and COP settlements rounded **down** to a multiple of 1,000 units |
| X1 | FX timing | cross-border only, < 2% |
| X2 | Partial capture | settle = (n−1)/n of auth (multi-item orders) → mostly `large` |
| X3 | PSP fee | PSP_C deducts a fixed fee ≥ $1 |
| X4 | Tax recalculation | MX/CO: a VAT share (< 2%) |
| X5 | Fraud hold | high-risk rows: 10–20% withheld → `large` |
| X6 | PSP adjustment | −2% to −5% (this fills `meaningful`; P1 and P3 raise it) |
| Drift | PSP_C fee starts in month 3 | makes the change rule fire in the demo |
| — | Tips | none (home goods) → report "ruled out" |

- **Pending rows:** mostly in the last 7 days of data.
- **Truth labels:** kept in `data/truth`, never used as a dbt source.
- **Validation gate:**
  - bucket shares are always checked;
  - pattern checks (below) hard-fail only on the full run; a `--rows 500` smoke run only warns.
- **Pattern checks:**
  - P1 gap ≥ 2.5 pts;
  - P2 lag + ≥ 2 days;
  - P3 ratio ≥ 1.2;
  - P4 ≥ 90% of rows with the round-down signature.

### Analysis
- **Cause labels** run on **all non-exact rows**, not only flagged ones.
- **Tests:** Wilson CI, chi² (Fisher for small cells), BH-FDR, and one logistic GLM.
- **HDBSCAN** is optional, only if time allows. No decision tree.
- **$ impact:** excess loss = (segment rate − peer rate) × volume × mean loss, with the median shown beside it. Compare with $127k as an estimate.

### Time and "worst week"
- **Week:** ISO week (Mon–Sun) by auth date. A week belongs to the month that holds its Thursday.
- **"Last month":** the last full calendar month in the data.
- **Worst week:**
  - ranked by net USD loss (under − over), with gross under-settlement shown too;
  - weeks with n < 30 are shown greyed as "low sample".
- **Minimum sample:** 50 for alerts; 30 only for the worst-week card.

### Run and tools
- **Three run paths**, all in the README:
  - `make all`;
  - `pip install uv && uv run recon all`;
  - `docker compose up` (supported and tested).
- **Command order:** generate → build → validate → analyze → alerts → report.
- **CLI:** `recon generate | build | validate | analyze | alerts | report | query | worst-week | dashboard | all`.
- **Exit codes:** 0 ok · 1 error · 2 usage · 5 data-quality or validation failed.
- **Build:** a full rebuild from raw each run (no incremental merge).
- **DuckDB:** each query opens a short read-only connection and closes it. Results are cached, keyed on the file's modified time. If the file is locked, the app shows "rebuilding, retry".
- **DuckDB version:** 1.4.x LTS; community support ends 17 Nov 2026, so move to 1.5.x after testing it with dbt-duckdb.
- **Config:** `thresholds.yaml` and `alerts.yaml`.
- **Dashboard (5 pages):**
  - Overview (KPIs, trend, week-over-week, worst-week card);
  - Drill-down;
  - Outliers (min-$ filter, default 50);
  - Root causes & actions;
  - Alerts.
- **Alerts (6 rules):** peer, change, money leak, large-rows summary, pending aging, settle lag.
  - They are evaluated on the last **closed** week (week end ≤ as-of − 7 days).
  - There is no state file: status is this week vs the last closed week.
  - Data quality is not an alert rule; a failed dbt build is the signal.
  - Slack is optional and off by default.

## Glossary
- **Residual:** the part of a difference left after removing the expected FX move.
- **Peer rule:** compare one PSP with the other PSPs in the same country.
- **p-chart:** a weekly rate chart with an upper limit; above the limit means "worse than usual".
- **BH-FDR:** a correction for testing many segments at once.
- **Wilson CI:** a safe confidence interval for a rate.
