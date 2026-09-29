# CasaMarket Anomaly Hunt: Playbook

**Source of truth:** the brief, *"Cross-Border Anomaly Hunt: CasaMarket's Silent 18% Revenue Drain"* ([scenario.md](../00-scenario/scenario.md)). If this playbook and the brief disagree, the brief wins.

**Frame: lean core + scale path.**
- **Build:** a lean, well-engineered analytical tool. The reviewer runs it locally with one command.
- **Quality:** inside that limit, pick the most correct and maintainable option. Do not cut quality because of time.
- **Scale path:** AWS / Yuno stack is **documented only** (section 11). Not built.
- **Brief rule:** *"Keep your architecture simple — this is a focused analytical tool, not an enterprise data warehouse."*

**Role lens:** Staff/Principal Data Engineer at Yuno (StarRocks, Flink, dbt, Airflow on AWS). Show reliability, data quality, observability, modeling, PCI-DSS/GDPR and AI-first work.

**Research:**
- [v3 summary + decision sheet](../../orchestrator/01-research/01-Functional-Req-v3/00-SUMMARY.md) (current picks; this playbook follows it).
- [v1 summary](../../orchestrator/01-research/00-Archived/v1/00-SUMMARY.md) (background).
- Topics: 01 system (FR1) · 02 detection & root cause (FR1, FR2, FR4) · 04 synthetic data · 05 CLI (FR3, run) · 06 dashboard (FR3) · 07 alerts (FR3).

**Stack:**
- Python 3.12 + uv · scipy + statsmodels.
- DuckDB 1.4.x LTS (support ends 17 Nov 2026; move to 1.5.x after testing with dbt-duckdb).
- dbt-core 1.12 + dbt-duckdb 1.11: raw → staging → intermediate → marts, with tests.
- Streamlit + Plotly dashboard · YAML alert rules + a small evaluator · Typer CLI `recon`.

---

## 1. Scenario at a glance

### Story facts
| Fact | Value |
|---|---|
| Merchant | CasaMarket, home goods e-commerce |
| Countries / currencies | Mexico MXN · Colombia COP · Argentina ARS · Chile CLP |
| Volume | ~45,000 transactions / month |
| PSPs | Multiple (dataset: 3–5) |
| Symptom | 18% of **approved** transactions settle for a different amount than authorized |
| Size of problem | ~$127,000 in unexplained differences last quarter |
| Why nobody looked | Platform migration, new market launches |
| Input | Transaction export from Yuno's dashboard |
| Ask | Find patterns, find root causes, build monitoring |

### Domain concepts
| Concept | Meaning |
|---|---|
| Authorization | Real-time hold at checkout for the purchase amount |
| Settlement | Funds move, usually 1–5 days later. The final amount the merchant gets |
| Settlement discrepancy / clearing variance | Settled amount ≠ authorized amount |
| FX noise | Legit small differences on cross-border payments, typically **< 2%** |

### The 6 causes in the brief
| Cause | Typical signature (our hypothesis) |
|---|---|
| Currency conversion timing | Cross-border only; small (< 2%); either sign |
| Partial capture | Under-settlement; one item of n removed |
| Tip adjustment | Over-settlement. Rare for home goods; expect to **rule it out** |
| Processor fees / adjustments | Under-settlement; a fixed amount or a % per PSP |
| Fraud holds | Under-settlement; a withheld share on risky rows |
| Tax recalculation | Either sign; a small VAT-linked share (VAT: MX 16%, CO 19%, AR 21%, CL 19%) |

---

## 2. Requirements map

| # | Requirement | Acceptance criteria (verbatim) | Rubric link | Deliverable | Lives in |
|---|---|---|---|---|---|
| 1 | Data Pipeline & Discrepancy Detection (Core) | "A reviewer should be able to run your pipeline on the test dataset and get a clean, enriched dataset with discrepancy metrics calculated for each transaction." | Pipeline 20 · Tech 15 | Working code + README | `dbt/`, `src/casarecon/`, `Makefile` |
| 2 | Root Cause Analysis (Core) | "A reviewer should be able to see your analysis outputs (tables, charts, summary statistics, or a report) and immediately understand which factors are driving the discrepancies." | RCA 25 · Insight 20 | Analysis outputs + docs | `src/casarecon/analysis/`, `reports/FINDINGS.md`, `reports/figures/` |
| 3 | Monitoring Dashboard or Alert System (Stretch) | "A reviewer should be able to interact with your monitoring solution and answer questions like "Which PSP had the worst week last month?" or "Show me all transactions with discrepancies over $50."" | Stretch 10 | Dashboard / tool | `src/casarecon/dashboard/`, `src/casarecon/cli.py` |
| 4 | Actionable Recommendations (Stretch) | "A written document (Markdown, PDF, or included in your dashboard) with clear, evidence-based recommendations." | Stretch 10 | Recommendations doc | `reports/RECOMMENDATIONS.md` |

**Core 1 must:** ingest auth + settlement records · calculate discrepancies · flag "meaningful" ones (hint: *"2 cents on a $500 transaction is probably noise, but $20 is not"*) · enrich (e.g. discrepancy %, amount, time between auth and settlement).
**Core 2 questions:** see section 7.
**Stretch 4 each item must:** reference data findings · estimate financial impact · suggest implementation.

### Deliverables (from the brief)
| Deliverable | Where |
|---|---|
| Working code for pipeline and analysis, clear README and run instructions | repo root, `README.md` |
| Generated test dataset (or script): ≥ 500 transactions, 4 countries, realistic discrepancy patterns | `src/casarecon/generate/`, `data/raw/` |
| Analysis outputs: tables, visualizations, summary statistics or report | `reports/` |
| Documentation: approach, key findings, assumptions, how to interpret the results | `README.md`, `reports/FINDINGS.md` |
| (Stretch) Dashboard/monitoring tool OR recommendations with 3–5 prioritized actions | dashboard + `reports/RECOMMENDATIONS.md` |

### "Done" list · Constraints · Scope
| Type | Item (from the brief) |
|---|---|
| Done | Process transaction data and accurately calculate discrepancies |
| Done | Surface at least 3–4 clear patterns or root causes backed by data |
| Done | Well-documented so CasaMarket's team can understand and use it |
| Done | Thoughtful data engineering practices (clean code, reproducibility, clear outputs) |
| Done | (Stretch) Interactive way to explore the data or concrete next steps |
| Constraint | Runnable locally (reviewer has Python, Node.js or Docker) |
| Constraint | Clear setup/run instructions in README |
| Constraint | Any dashboard/web app runs on localhost |
| Freedom | Language, storage (files, SQLite, Postgres, DuckDB…), viz libs, analysis techniques |
| Scope | ~2 hours with AI assistance; insights + working prototype, not production |
| Scope | Core first (pipeline + analysis); stretch is optional; partial stretch is welcome |

**Time budget (as given):** data generation/setup 15–20 min · pipeline 25–35 min · analysis and visualization 30–40 min · documentation and polish 15–20 min · stretch 20–30 min.

---

## 3. Rubric

| Criterion | Pts | What wins the points |
|---|---|---|
| Data Pipeline Quality | 20 | Exact math in minor units; FX residual per section 5; every field in section 6; one row per transaction; dbt tests on every model |
| Test Data Realism | 10 | Seeded, config-driven generator; bucket mix inside brief ranges; P1–P4 + X1–X6 + drift; per-pattern validation gate |
| Root Cause Analysis Depth | 25 | All 5 questions answered; rates with CIs; tests with BH-FDR; one logistic GLM; pattern groups; cause labels scored against truth; $ Pareto |
| Insight Quality & Clarity | 20 | Findings in one fixed format (section 7); a one-page summary at top; one chart per finding; $ impact that reconciles to the total |
| Technical Execution | 15 | 3 run paths work from a fresh clone; locked deps; contract; idempotent reruns; unit + dbt tests; clean README |
| Stretch Goals & Polish | 10 | Both stretch items; dashboard answers the two example questions in ≤ 2 clicks; recommendations with $ impact |

---

## 4. Test data spec

### Shape
| Item | Brief | Our choice |
|---|---|---|
| Volume | ≥ 500 transactions | Default 135k (45k × 3 months, enough power for P1); `--rows 500` smoke run |
| Period | 3–4 months | 3 full calendar months (135k = 45k × 3) |
| Countries / currencies | MX/MXN, CO/COP, AR/ARS, CL/CLP | Weights e.g. MX 40 / CO 25 / AR 15 / CL 20 |
| PSPs | 3–5, e.g. PSP_A… | 5 PSPs: PSP_A–PSP_E |
| Status mix | Mostly approved/settled; some failed and pending | Failed auth 4% · pending 3% (mostly in the last 7 days) |
| Settlement lag | 1–7 days, some outliers | Most 1–5 days; ~2% outliers at 8–20 days |
| Metadata | Customer ID, product category, amount tier, cross-border flag | Plus required: PSP, `payer_currency`, `item_count`, `risk_score`, card BIN country (no PAN) |
| Amount tiers | $10–$50, $50–$200, $200+ | Amounts ≥ $10 USD; long-tail (log-normal) |

### Discrepancy categories
One category per row, checked in this order. All rules use the absolute residual (section 5).

| Category | Rule | Brief tier | Target share* |
|---|---|---|---|
| `exact` | Δ = 0 | match 60–70% (exact + rounding) | 67% |
| `rounding` | \|Δ\| ≤ 1 minor unit | match | 1% |
| `fx_tolerance` | residual ≤ 2% and < $20 | small 0.1–2%: 15–20% | 18% |
| `meaningful` | residual 2–5% and < $20 | > 2%: 10–18% (with `large`) | 10% |
| `large` | residual > 5% or ≥ $20 | 3–5% ("the outliers to investigate") | 4% |

\* Share of **approved + settled** rows. Failed + pending ≤ 7% of all rows, so every brief range holds on both denominators.

- **Flag:** `is_meaningful` = `meaningful` or `large` (about 14%).
- **Outlier:** an outlier is a `large` row. No z-score.
- **$20 rule:** uses the USD residual, not the raw diff. A $2,000 order that moves 1.5% only from FX has a residual near 0, so it is not `large`. A 1.5% residual ($30) is `large`.
- **Cut-offs:** in `thresholds.yaml`. The report also shows the rate at 1%, 2% and 3% (sensitivity).
- **Share test:** bounds are n-aware (brief range ± 3 SE), so a 500-row run does not fail by chance.

### Planted patterns (one version everywhere)
| # | Pattern | Rule | How the analysis finds it |
|---|---|---|---|
| P1 | PSP_B in Argentina | Meaningful rate about +3.5 pts vs other PSPs in AR | Rate by PSP×country; GLM `psp × country` term |
| P2 | Colombia orders > $300 | Settle lag +2–4 days; more lag outliers | Lag by tier×country; Mann-Whitney |
| P3 | Weekend authorizations | Meaningful rate about 1.3× weekday | Weekend vs weekday ratio + CI |
| P4 | PSP_D rounding | Cross-border CLP and COP settlements rounded **down** to a multiple of 1,000 units | `rounding_flag` share by PSP×currency |
| X1 | FX timing | Cross-border only, < 2% | `fx_move_pct` vs diff |
| X2 | Partial capture | Settle = (n−1)/n of auth (multi-item orders); mostly `large` | `item_count` share match |
| X3 | PSP fee | PSP_C deducts a fixed fee ≥ $1 | Same $ amount on PSP_C rows |
| X4 | Tax recalculation | MX/CO: a VAT share (< 2%) | VAT-linked share by country |
| X5 | Fraud hold | High-risk rows: 10–20% withheld; `large` | `risk_score` vs withheld % |
| X6 | PSP adjustment | −2% to −5%; fills `meaningful` (P1 and P3 raise it) | Rate by PSP, weekday |
| Drift | PSP_C fee starts in month 3 | Makes the change alert fire in the demo | Weekly trend + change alert |
| — | Tips | None (home goods) | Report "ruled out" |

- **P1 note:** "3–4% higher" is read as percentage points.
- **Truth labels:** written to `data/truth/labels.parquet`. dbt never reads them.

### Validation gate (`recon validate`)
- Bucket shares are always checked.
- Pattern checks hard-fail only on the full run. A `--rows 500` smoke run only warns.
- Pattern checks: P1 gap ≥ 2.5 pts · P2 lag + ≥ 2 days · P3 ratio ≥ 1.2 · P4 ≥ 90% of rows with the round-down signature.
- The generator also writes `generation_manifest.json` (seed, row count, realized mix). One seed gives identical files.

---

## 5. Definitions to fix early

| Term | Definition (state it in README) |
|---|---|
| Currency model | Both amounts are in the merchant's local currency (MXN, COP, ARS or CLP) |
| Cross-border | `payer_currency = USD`: the customer pays in USD and the PSP converts |
| Minor units | Integer money. MXN, COP, ARS: 2 decimals. **CLP: 0 decimals** |
| FX table | `fx_rates_daily(date, currency, local_per_usd)`, generated into `data/raw` (a source, not a seed) |
| Expected settle | Cross-border: `auth × local_per_usd(settle_day) / local_per_usd(auth_day)`. Domestic: `auth` |
| Residual | `residual = settled − expected`; `residual_pct = residual / expected` |
| USD | `residual_usd` uses the auth-day rate |
| Sign | `residual < 0` = **under-settlement** (merchant loses); `> 0` = over |
| Failed auth | Kept in raw and staging; **excluded** from rates (nothing to settle) |
| Pending | Excluded from rates; shown as "pending aging" |
| Denominator | Rate = flagged / (approved **and** settled) rows |
| As-of | The max timestamp in the data |
| Lag | Fractional days between timestamps; buckets use floor |
| Week | ISO week (Mon–Sun) by auth date; it belongs to the month that holds its Thursday |
| "Last month" | The last full calendar month in the data |
| Closed week | Week end ≤ as-of − 7 days |

A hand-worked cross-border row is a unit test for the FX formula.

---

## 6. Enriched fields (grain: one row per transaction)

| Field | Notes |
|---|---|
| `diff_local` | `settled − auth`, signed, minor units |
| `expected_settled` | Section 5 formula |
| `residual`, `residual_pct`, `residual_usd` | Signed; all cut-offs use the absolute value |
| `abs_residual_usd` | For $ filters (e.g. "> $50") |
| `direction` | `under` / `over` / `none` |
| `category` | exact / rounding / fx_tolerance / meaningful / large |
| `is_meaningful` | `meaningful` or `large` |
| `settle_lag_days`, `is_lag_outlier` | Outlier: > 7 days |
| `auth_weekday`, `is_weekend`, `auth_week`, `auth_month` | Time features (Thursday rule for month) |
| `amount_usd`, `amount_tier` | $10–50 / $50–200 / $200+, plus a > $300 flag |
| `is_cross_border`, `payer_currency` | From the contract |
| `fx_move_pct` | Auth-day vs settle-day rate change |
| `rounding_flag` | P4 signature: settled is a multiple of the PSP rounding step and below expected |
| `likely_cause` | Section 7 rules; `unexplained` if none match |

- **Rounding step:** per PSP × currency in `thresholds.yaml` (PSP_D CLP/COP = 1,000 units).

---

## 7. Root-cause analysis plan

| Question (brief) | Method | Evidence to show |
|---|---|---|
| Which countries/currencies have the highest discrepancy rates? | Rate per country with Wilson 95% CI; chi² (Fisher for small cells) | Bar chart with CIs; table n, rate, $ |
| Which PSPs are most problematic? | Rate + $ per PSP and PSP×country; compare with other PSPs in the same country | Heatmap PSP×country; top cell called out |
| Do transaction sizes correlate with likelihood or magnitude? | Rate by tier; Spearman on `abs(residual_pct)` vs amount; Mann-Whitney | Rate + median % per tier |
| Time-based patterns (weekday, settlement delays)? | Rate by weekday; weekend ratio; lag buckets vs mean loss | Weekday chart; lag vs loss chart |
| Clusters: systematic vs random? | GROUP BY (`likely_cause`, PSP, currency, sign). HDBSCAN only if time allows | Cluster table: size, PSP/country mix, $, label |

**Across all questions:**
- **Tests:** Wilson CI, chi² (Fisher when an expected cell < 5), BH-FDR q-values in every findings table.
- **One logistic GLM** on `is_meaningful`: country, PSP, tier, weekend, cross-border, lag, plus `psp × country` (so P1 shows up).
- **Cause labels:** run on **all non-exact rows**. One simple rule per cause (FX move, fixed fee, (n−1)/n share, VAT share, withheld %, rounding signature, adjustment %). No match = `unexplained`.
- **Truth check:** FINDINGS reports precision/recall of `likely_cause` vs `data/truth`.
- **$ impact:** excess loss = (segment rate − peer rate) × volume × mean loss, median shown beside it. The Pareto must sum to the total.
- **Extrapolation:** compare with the $127k in the story. Label it an estimate.

**Findings format (use for every finding):**
> **F#. \<Headline\>.** X% of \<metric\> occur on \<segment\> (n = …, 95% CI …, vs … elsewhere, q = …). $ impact: \$… per quarter (…% of loss). Likely cause: … Action: see R#.

---

## 8. Recommendations template (stretch 4)

3–5 items, ranked by $ impact.

| Rank | Action | Evidence (finding) | Est. $ impact / quarter | Owner | Implementation |
|---|---|---|---|---|---|
| R1 | e.g. Escalate PSP_B Argentina variance; renegotiate terms | F2 | \$… (method: …) | Payments ops | Weekly report to PSP; SLA clause |
| R2 | e.g. FX rate locking for cross-border | F4 | … | Finance | Lock rate at auth via Yuno / PSP option |
| R3 | e.g. Fix PSP_D rounding for CLP/COP | F5 | … | Eng + PSP | Ticket with signature evidence; monitor `rounding_flag` |
| R4–R5 | … | … | … | … | … |

Impact method: excess loss (section 7) × a realistic reduction %. State the assumption.

---

## 9. Monitoring plan (stretch 3)

**Tool:** Streamlit dashboard + alert system + CLI `recon`. All three read the same DuckDB marts through one shared core.

### Dashboard (5 pages)
| Page | Shows |
|---|---|
| Overview | KPIs, weekly trend, week-over-week, worst-week card |
| Drill-down | Filters: country, PSP, tier, cross-border, cause, category → transaction table |
| Outliers | `large` rows sorted by `abs_residual_usd`; min-$ filter (default 50); CSV download |
| Root causes & actions | Cause Pareto, findings, recommendations |
| Alerts | Latest alert report |

- **DuckDB access:** a short read-only connection per query; cache keyed on file time; if locked, show "rebuilding, retry".

### The two brief questions
- **"Which PSP had the worst week last month?"** Worst-week card on Overview, or `recon worst-week --month last`.
  - Ranked by net USD loss (under − over); gross under-settlement shown too, both labelled.
  - Weeks use the Thursday rule; weeks with n < 30 are greyed as "low sample".
- **"Show me all transactions with discrepancies over $50"** Outliers page (min-$ = 50), or `recon query --min-usd 50 --format csv`.

### Alerts (`alerts.yaml`, `recon alerts`)
| Rule | Fires when |
|---|---|
| Peer | A PSP's rate is above the other PSPs in the same country |
| Change | The rate rises ≥ 2 pts vs the last closed week |
| Money leak | Under-settlement share of settled USD is above the limit |
| Large-rows summary | Count and $ of new `large` rows |
| Pending aging | Pending > 7 days, one alert per PSP × country |
| Settle lag | Lag outliers above the limit |

- Evaluated on the last **closed** week; n ≥ 50, else "insufficient data".
- No state file: status is this week vs the last closed week. Output: `alerts.jsonl` + a Markdown report.
- Data quality is not an alert rule; a failed dbt build is the signal.
- Slack is optional and off by default.

---

## 10. Repo layout, run, standards

```
casamarket-recon/
├── README.md · Makefile · pyproject.toml · uv.lock · Dockerfile · docker-compose.yml
├── contracts/transactions.yaml      # fields, types, enums, minor units, PAN ban
├── config/{generator.yaml, thresholds.yaml, alerts.yaml}
├── src/casarecon/
│   ├── generate/                    # seeded generator + validation gate
│   ├── analysis/                    # stats, cause rules, figures, FINDINGS.md
│   ├── core/                        # shared read-only queries (CLI + dashboard)
│   ├── alerts/                      # YAML rule evaluator → alerts.jsonl + report
│   ├── dashboard/                   # Streamlit app
│   └── cli.py                       # Typer `recon`
├── dbt/models/{staging, intermediate, marts}/   # dbt-duckdb + schema.yml tests
├── data/{raw/, truth/, casarecon.duckdb}        # generated; gitignored
├── reports/{FINDINGS.md, RECOMMENDATIONS.md, figures/}
└── tests/                           # unit tests: math, categories, cause rules
```

**Run paths (all in README):** `make all` · `pip install uv && uv run recon all` · `docker compose up` (supported and tested).

**Command order:** generate → build → validate → analyze → alerts → report.

**CLI:** `recon generate | build | validate | analyze | alerts | report | query | worst-week | dashboard | all`.

**Exit codes:** 0 ok · 1 error · 2 usage · 5 data-quality or validation failed.

**Make targets:** `all`, `validate`, `app`, `alerts` call `recon`. `test` and `clean` call pytest/dbt directly.

**dbt models:** `stg_transactions`, `stg_fx_rates` → `int_transactions_usd` → `fct_transaction_discrepancy` (one row per txn) → `mart_segment_rates`, `mart_psp_weekly`, `mart_outliers`, `mart_cause_summary`.

| Standard | Apply it as |
|---|---|
| Contract | One YAML; the generator uses it; one pytest checks dbt `schema.yml` matches it |
| Layers | raw → staging → intermediate → marts |
| Idempotency | Full rebuild from raw each run; same input + seed → same output |
| Tests | dbt (by hand): unique/not null `txn_id`, accepted values, `settled_at ≥ authorized_at`. pytest: math and rules |
| Reproducibility | Fixed seed, locked deps, manifest with realized mix |
| Privacy | No PAN; tokenized customer IDs; BIN country only |
| Observability | `recon build` prints row counts per layer |

---

## 11. Scale path on AWS (documented, not built)

| Local | AWS / Yuno stack |
|---|---|
| CSV/Parquet in `data/raw` | S3 + Iceberg tables |
| DuckDB | StarRocks (marts, dashboards) |
| dbt-duckdb | dbt on StarRocks (same models, minor SQL edits via macros) |
| Makefile | Airflow / MWAA daily DAG |
| Batch export | Streaming auth/settlement events: MSK + Flink |
| `alerts.yaml` + evaluator | Same evaluator as an Airflow task → SNS → Slack; add alert states then |
| Local dashboard | BI on StarRocks, SSO |
| Synthetic FX table | Real daily FX feed |

---

## 12. README template, interview prep, AI prompt, checklist

### README template
| # | Section | Content |
|---|---|---|
| 1 | Problem | Story numbers in 3 lines |
| 2 | Quick start | Prereqs, the 3 run paths, `recon dashboard`, URL, `recon --help` |
| 3 | Key findings | Top 4–6 findings in section 7 format + charts |
| 4 | Recommendations | Link + top 3 |
| 5 | Approach & architecture | Diagram, layers, why DuckDB + dbt (a few lines) |
| 6 | Definitions & assumptions | Section 5 table |
| 7 | How to read the outputs | Categories, CIs, q-values, $ columns, net vs gross |
| 8 | Data | Generator, patterns, realized mix |
| 9 | Monitoring | Dashboard pages, alert rules, example answers |
| 10 | Limitations & scale path | Section 11 |
| 11 | AI-assisted workflow | What AI wrote, how it was checked |

### Likely interview questions
| Question | Answer anchor |
|---|---|
| How did you define "meaningful"? | Residual after the FX move > 2%, or ≥ $20; cut-offs in config, with a sensitivity table |
| Why DuckDB + dbt, not StarRocks? | Brief says keep it simple; the dbt models move to StarRocks with minor edits |
| How do you know patterns are real? | CIs, BH-FDR, one GLM; cause labels scored against the truth file |
| Confounding (country vs cross-border)? | Logistic GLM; stratified rates |
| Where does the $127k come from? | Gross under-settlement; excess-loss estimate; stated as estimate |
| How would this run in production? | Section 11; daily DAG, alerts per PSP, real FX feed |
| PCI / GDPR? | No PAN; tokenized IDs; minimal PII; retention |

### AI kickoff prompt
> You are pairing with a Staff Data Engineer on the CasaMarket settlement-discrepancy take-home. Follow PLAYBOOK.md sections 4–6 exactly. **Step 1 only:** write `contracts/transactions.yaml` and the seeded generator with `config/generator.yaml`, the category rules, P1–P4, X1–X6, the drift and the truth file. Add `recon validate`, which prints the realized mix and pattern checks and fails (exit 5) on the full run if out of range. Stop after that.

Then: dbt models + tests → analysis → FINDINGS → dashboard + alerts → RECOMMENDATIONS → README.

### Glossary
- **Residual:** the part of a difference left after removing the expected FX move.
- **Peer rule:** compare one PSP with the other PSPs in the same country.
- **Wilson CI:** a safe confidence interval for a rate.
- **BH-FDR (q-value):** a correction for testing many segments at once.
- **GLM:** one regression that checks many factors together.
- **Pareto:** segments ranked by $ lost.
- **Signature:** the typical shape of a cause (e.g. rounded to 1,000).

### Final checklist
- [ ] All 3 run paths work from a fresh clone.
- [ ] ≥ 500 rows, 3–4 months, 4 countries, 3–5 PSPs, status mix, lag outliers, metadata.
- [ ] Category mix inside brief ranges; validation gate passes on the full run.
- [ ] Every field in section 6; CLP minor units correct; FX unit test passes.
- [ ] dbt tests and pytest pass.
- [ ] All 5 RCA questions answered with CIs, q-values and $ impact; ≥ 3–4 patterns.
- [ ] FINDINGS.md in the fixed format, with charts and the truth check.
- [ ] Dashboard answers both example questions.
- [ ] RECOMMENDATIONS.md: 3–5 actions with evidence, $, owner, implementation.
- [ ] README: approach, findings, assumptions, how to read results.
- [ ] No PAN anywhere.
- [ ] Walk the Deliverables, Done list and every acceptance criterion.
