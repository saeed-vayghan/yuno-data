# CasaMarket Anomaly Hunt: Playbook

**Source of truth:** the brief, *"Cross-Border Anomaly Hunt: CasaMarket's Silent 18% Revenue Drain"* ([scenario.md](../00-scenario/scenario.md)). If this playbook and the brief disagree, the brief wins.

**Frame: lean core + scale path.**
- **Build:** a lean, well-engineered analytical tool. The reviewer runs it locally with one command.
- **Quality:** inside that limit, pick the most correct and maintainable option. Do not cut quality because of time.
- **Scale path:** AWS / Yuno stack is **documented only** (section 11). Not built.
- **Brief rule:** *"Keep your architecture simple — this is a focused analytical tool, not an enterprise data warehouse."*

**Role lens:** Staff/Principal Data Engineer at Yuno (StarRocks, Flink, dbt, Airflow on AWS). Show reliability, data quality, observability, modeling, PCI-DSS/GDPR and AI-first work.

**Research:** [v2 summary](../../orchestrator/01-research/v2/00-SUMMARY.md) (current picks) · [v1 summary](../../orchestrator/01-research/v1/00-SUMMARY.md). Topics: 01 discrepancy analysis system (FR1), 02 detection & root-cause methods (FR1, FR2, FR4), 04 synthetic data (test data), 06 dashboard (FR3), 07 alert system (FR3).

**Stack:** Python 3.12 + uv · DuckDB 1.4.x LTS · dbt-core 1.12 + dbt-duckdb 1.11 (raw → staging → marts, with tests) · scipy + statsmodels · Streamlit + Plotly dashboard on localhost · YAML alert rules + Python evaluator · Typer CLI `recon` (thin shell over the shared core) · Makefile one-command run (targets call `recon`) · optional Docker Compose.

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
| Currency conversion timing | Cross-border only; small (< 2%); either sign; tracks FX move between auth and settle |
| Partial capture | Under-settlement; often a "round" share (e.g. one item of n removed) |
| Tip adjustment | Over-settlement. Rare for home goods; expect to **rule it out** |
| Processor fees / adjustments | Under-settlement; fixed amount or fixed % per PSP |
| Fraud holds | Under-settlement; a withheld share on risky transactions |
| Tax recalculation | Either sign; share close to a country VAT rate (MX 16%, CO 19%, AR 21%, CL 19%) |

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
| Documentation: approach, key findings, assumptions, how to read results | `README.md`, `reports/FINDINGS.md` |
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
| Data Pipeline Quality | 20 | Exact math in minor units; USD normalization with a documented rate rule; every enriched field in section 6; one row per transaction; dbt tests on every model |
| Test Data Realism | 10 | Seeded, config-driven generator; realized bucket mix inside the brief ranges; 4 brief patterns + hidden cause patterns; a verification report that fails the build if a pattern is missing |
| Root Cause Analysis Depth | 25 | All 5 questions answered; rates with CIs; significance tests; a multivariable model to separate confounded factors (e.g. country vs cross-border mix); clusters of signatures; cause labels; $ Pareto |
| Insight Quality & Clarity | 20 | Findings in one fixed format (section 7); a one-page summary at top; one chart per finding; $ impact that reconciles to the total |
| Technical Execution | 15 | `make all` from a fresh clone; locked deps; contract; idempotent reruns; unit + dbt tests; short ADR notes; clean README |
| Stretch Goals & Polish | 10 | Both stretch items; dashboard answers the two example questions in ≤ 2 clicks; recommendations with $ impact |

---

## 4. Test data spec

### Shape
| Item | Brief | Our choice (suggestion) |
|---|---|---|
| Volume | ≥ 500 transactions | Default 135k (45k × 3 months: enough power for a 3–4 pt effect in one PSP×country cell); `--rows` flag; `--rows 500` smoke run |
| Period | 3–4 months | 4 full calendar months, so "last month" has full weeks |
| Countries / currencies | MX/MXN, CO/COP, AR/ARS, CL/CLP | Country weights e.g. MX 40 / CO 25 / AR 15 / CL 20 |
| PSPs | 3–5, e.g. PSP_A… | 4 PSPs: PSP_A–PSP_D |
| Status mix | Mostly approved/settled; some failed auths and pending settlements | e.g. 90% approved+settled · 6% failed auth · 4% approved+pending |
| Settlement lag | 1–7 days after auth, some outliers | Most 1–5 days; ~2% outliers at 8–20 days |
| Metadata | Customer ID, product category, amount tier, cross-border flag | Plus: PSP, payer currency, card BIN country (no PAN), risk score (suggestion) |
| Amount tiers | $10–$50, $50–$200, $200+ | Amounts ≥ $10 USD; long-tail (log-normal) |

### Discrepancy buckets
Brief ranges overlap: "meaningful > 2%" includes "large > 5% or > $20". Make them consistent like this:

| Category (one per row, checked in this order) | Rule (on FX-adjusted residual for cross-border) | Brief tier | Generator target |
|---|---|---|---|
| `exact` | Δ = 0 in minor units | match 60–70% | 65% |
| `rounding` | \|Δ\| ≤ 1 minor unit or \|Δ USD\| < $0.50 | not in brief | label only (P4 residue lives here) |
| `fx_tolerance` | residual ≤ 2% and ≤ $20 | small 0.1–2%: 15–20% | 18% |
| `meaningful` | residual 2–5% and ≤ $20 | > 2%: 10–18% (with `large`) | 13% |
| `large` | residual > 5% **or** \|Δ USD\| > $20 | 3–5% | 4% |

- **Flag:** `is_meaningful` = `meaningful` or `large`, so the > 2% share is ~17% (close to the CFO's "18%").
- **"> $20" rule:** a 1.5% diff on a $2,000 order is > $20, so it is `large`. The generator caps `fx_tolerance` rows below $20 so the realized mix stays in range.
- **Cut-offs** live in `thresholds.yaml`; the report also shows the rate at 1%, 2% and 3% bands (sensitivity).
- **Check:** the pipeline re-classifies generated rows with the same rule. A test asserts each realized share is inside the brief range.

### Patterns to embed
| # | Pattern (brief) | How we embed it | How the analysis should find it |
|---|---|---|---|
| P1 | One PSP has 3–4% higher discrepancy rates in Argentina | PSP_B in AR: meaningful rate +3.5 pts vs other PSPs in AR | Rate by PSP×country, rate ratio + CI, logistic regression interaction |
| P2 | Large transactions (> $300) in Colombia have settlement timing issues | CO & amount > $300: lag +3–5 days, more > 7-day outliers | Lag distribution by tier×country; Mann-Whitney |
| P3 | Weekend authorizations have higher discrepancy rates | Sat/Sun auth: higher meaningful rate (~1.5×) | Rate by weekday, weekend vs weekday ratio + CI |
| P4 | One PSP has a systematic rounding issue for certain currency pairs | PSP_D, cross-border USD→CLP and USD→COP: rounds down to 100 / 10 units | `rounding_flag`, residue analysis, signature cluster |

### Hidden patterns (suggestion; map to the 6 causes)
| Cause | Embed |
|---|---|
| FX timing | Cross-border diff = amount × FX move between auth and settle day; ARS drifts most |
| Partial capture | Some multi-item orders settle at (n−1)/n of auth; category-linked (e.g. furniture) |
| Processor fee | PSP_C deducts a fixed fee (e.g. ~$0.35) at settlement on some rows |
| Fraud hold | High `risk_score` rows: 10–20% withheld |
| Tax recalculation | A few MX/CO rows move by a VAT-rate share |
| Tip | None embedded; the analysis should show "not a driver" |

**Generator rules:** one seed → identical files · config YAML for shares and patterns · write raw CSV/Parquet + a `generation_manifest.json` (seed, row count, realized mix) · verification step fails if a pattern's lift is < 1.5× or p ≥ 0.01.

---

## 5. Definitions to fix early

| Term | Definition (our choice, state it in README) |
|---|---|
| Discrepancy | `diff_local = settled_amount − authorized_amount`, same currency, computed in integer minor units |
| Sign | `diff < 0` = **under-settlement** (merchant loses) · `diff > 0` = over-settlement. Report gross loss, gross gain and net |
| Meaningful | Category `meaningful` or `large` (table above). Cross-border rows are judged on the residual after the FX move: expected settle = auth × fx(settle day) / fx(auth day) |
| Minor units | MXN, COP, ARS: 2 decimals · **CLP: 0 decimals**. A 1-unit CLP diff is rounding, not a discrepancy |
| Failed auth | Kept in raw and staging; **excluded** from discrepancy rates (nothing to settle) |
| Pending settlement | Excluded from rates; shown as "pending aging" (> 7 days pending = outlier) |
| Denominator | Discrepancy rate = flagged / (approved **and** settled) transactions |
| FX reference rates | Synthetic daily rates per currency→USD, seeded random walk from rough real levels (ARS drifts most); generated into `data/raw` as a source (`fx_rates_daily`), not a dbt seed |
| USD normalization | Use the **auth-date** rate (what the merchant expected). Also store the settle-date rate for FX-timing tests |
| Week / "last month" | ISO week (Mon–Sun), assigned by auth date. "Last month" = last full calendar month in the data |

---

## 6. Enriched fields (grain: one row per transaction)

| Field | Notes |
|---|---|
| `diff_local`, `diff_usd` | Signed |
| `pct_diff`, `abs_pct_diff` | `diff / authorized` |
| `abs_diff_usd` | For $ thresholds (e.g. "> $50") |
| `direction` | `under` / `over` / `none` |
| `category` | exact / rounding / fx_tolerance / meaningful / large |
| `is_meaningful` | Section 5 rule |
| `settle_lag_days`, `is_lag_outlier` | Outlier: > 7 days |
| `auth_weekday`, `is_weekend`, `auth_week`, `auth_month` | Time features |
| `amount_usd`, `amount_tier` | $10–50 / $50–200 / $200+ (and a flag for > $300) |
| `is_cross_border`, `currency_pair` | e.g. `USD→CLP` |
| `fx_move_pct` | Auth vs settle rate change |
| `rounding_flag`, `rounding_residue` | Diff < 1 rounding step of the currency |
| `likely_cause`, `cause_confidence` | From rules in section 7 |
| `is_outlier` | Robust z-score of `diff_usd` within PSP×country |

---

## 7. Root-cause analysis plan

| Question (brief) | Method | Evidence to show |
|---|---|---|
| Which countries/currencies have the highest discrepancy rates? | Rate per country with Wilson 95% CI; chi-square | Bar chart with CIs; table n, rate, $ |
| Which PSPs are most problematic? | Rate + $ per PSP and PSP×country; rate ratio vs rest with CI | Heatmap PSP×country; top cell called out |
| Do transaction sizes correlate with likelihood or magnitude? | Rate by tier; Spearman on `abs_pct` vs amount; Mann-Whitney | Rate + median `abs_pct` per tier |
| Time-based patterns (weekday, settlement delays)? | Rate by weekday; weekend ratio; lag buckets vs mean `abs_diff_usd` | Weekday chart; lag vs diff chart |
| Clusters: systematic vs random? | Rule-based signatures first, then HDBSCAN (scikit-learn) on (pct, sign, lag, residue, cross-border) as a cross-check only | Cluster table: size, PSP/country mix, $, label |

**Across all questions:**
- **Multivariable check:** logistic regression on `is_meaningful` with country, PSP, tier, weekend, cross-border, lag. Shows which effects survive controls.
- **$ impact / Pareto:** share of gross under-settlement per segment and per cause. Must sum to the total.
- **Cause labeling rules:** match section 1 signatures (FX move, fixed fee, (n−1)/n share, VAT share, withheld %, rounding residue). Unmatched = `unexplained`.
- **Extrapolation:** $ per 1,000 transactions × 135k/quarter, compared to the $127k in the story (label it an estimate).

**Findings format (use for every finding):**
> **F#. \<Headline\>.** X% of \<metric\> occur on \<segment\> (n = …, 95% CI …, vs … elsewhere, p = …). $ impact: \$… per quarter (…% of loss). Likely cause: … Action: see R#.

---

## 8. Recommendations template (stretch 4)

3–5 items, ranked by $ impact.

| Rank | Action | Evidence (finding) | Est. $ impact / quarter | Owner | Implementation |
|---|---|---|---|---|---|
| R1 | e.g. Escalate PSP_B Argentina variance; renegotiate terms | F2 | \$… (method: …) | Payments ops | Weekly reconciliation report to PSP; SLA clause |
| R2 | e.g. FX rate locking for cross-border | F4 | … | Finance | Lock rate at auth via Yuno / PSP option |
| R3 | e.g. Fix PSP_D rounding for USD→CLP/COP | F5 | … | Eng + PSP | Ticket with residue evidence; monitor `rounding_flag` |
| R4–R5 | … | … | … | … | … |

Impact method: `$ lost in segment × realistic reduction %`, scaled to 135k tx/quarter. State the assumption.

---

## 9. Monitoring plan (stretch 3)

**Tool:** Streamlit dashboard on localhost (`make app`) + alert system (`make alerts`) + CLI `recon` for reports and queries, all over the same DuckDB marts and one shared core. Build all three.

| Need (brief) | View / command |
|---|---|
| Trends over time | Weekly meaningful rate and $ lost, by PSP and country |
| Drill-down | Filters: country, PSP, tier, cross-border, cause, bucket → transaction table |
| Outliers | Table of `large` + `is_outlier` rows, sorted by `abs_diff_usd` |
| Week-over-week | WoW change per PSP/country; flag if rate ↑ > X pts with n ≥ 30 |
| "Which PSP had the worst week last month?" | `mart_psp_weekly` ranked by $ lost (and by rate, min n); Dashboard "Worst week" card (net USD loss per ISO week, min 30 txns; last full month in the data); CLI `recon worst-week --month last` |
| "Show me all transactions with discrepancies over $50" | Filter `abs_diff_usd > 50`; Dashboard Outliers page, min-$ filter default 50, CSV download; CLI `recon query --min-usd 50 --format csv` |

**Alert system:** rules in `alerts.yaml` (peer rule + change rule, minimum sample); `make alerts` runs the Python evaluator → `alerts.jsonl` + Markdown report; new/ongoing/resolved dedupe; optional Slack webhook. Details: research v2/07.

---

## 10. Repo layout, one-command run, standards

```
casamarket-recon/
├── README.md · Makefile · pyproject.toml · uv.lock · docker-compose.yml (optional)
├── contracts/transactions.yaml      # fields, types, enums, minor units, PAN ban
├── config/{generator.yaml, thresholds.yaml, alerts.yaml}
├── src/casarecon/
│   ├── generate/                    # seeded generator + verification
│   ├── analysis/                    # stats, clusters, cause rules, figures, FINDINGS.md
│   ├── core/                        # shared read-only queries (used by CLI + dashboard)
│   ├── alerts/                      # YAML rule evaluator → alerts.jsonl + report
│   ├── dashboard/                   # Streamlit app (read-only DuckDB)
│   └── cli.py                       # Typer `recon` (thin shell over core)
├── dbt/models/{staging, intermediate, marts}/   # dbt-duckdb + tests
├── data/{raw/, casarecon.duckdb}    # generated; gitignored (small sample committed)
├── reports/{FINDINGS.md, RECOMMENDATIONS.md, figures/}
└── tests/                           # unit tests: math, buckets, cause rules
```

**Make targets** (each calls `uv run recon …`): `make all` (= generate → build → validate → analyze → alerts → report) · `make app` · `make alerts` · `make test` · `make clean`. Docker: `docker compose up` runs the same steps.

**dbt models:** `stg_transactions`, `stg_fx_rates` → `int_transactions_usd` → `fct_transaction_discrepancy` (one row per txn) → `mart_segment_rates`, `mart_psp_weekly`, `mart_outliers`, `mart_cause_summary`.

| Standard | Apply it as |
|---|---|
| Contract | One YAML drives generator, dbt tests and input checks |
| Layers | raw (as exported) → staging (typed, cleaned) → marts (analysis-ready) |
| Idempotency | Full rebuild from raw; same input + seed → same output |
| Tests | dbt: unique/not null `txn_id`, accepted values, `settled_at ≥ authorized_at`, bucket shares in range. pytest: math and rules |
| Reproducibility | Fixed seed, locked deps, manifest with realized mix |
| Privacy | No PAN; tokenized customer IDs; BIN country only |
| Observability | Run log with row counts per layer and test results |

---

## 11. Scale path on AWS (documented, not built)

| Local | AWS / Yuno stack |
|---|---|
| CSV/Parquet in `data/raw` | S3 + Iceberg tables |
| DuckDB | StarRocks (marts, dashboards) |
| dbt-duckdb | dbt on StarRocks (same models, adapter swap) |
| Makefile | Airflow / MWAA daily DAG |
| Batch export | Streaming auth/settlement events: MSK + Flink |
| `alerts.yaml` + evaluator | Same evaluator as an Airflow task → CloudWatch / SNS → Slack / PagerDuty |
| Local dashboard | BI on StarRocks, SSO |
| Synthetic FX table | Real daily FX feed |

---

## 12. README template, interview prep, AI prompt, checklist

### README template
| # | Section | Content |
|---|---|---|
| 1 | Problem | Story numbers in 3 lines |
| 2 | Quick start | Prereqs, `make all`, `make app`, URL, `recon --help` |
| 3 | Key findings | Top 4–6 findings in section 7 format + charts |
| 4 | Recommendations | Link + top 3 |
| 5 | Approach & architecture | Diagram, layers, why DuckDB + dbt |
| 6 | Definitions & assumptions | Section 5 table |
| 7 | Data | Generator, patterns, realized mix |
| 8 | Monitoring | Dashboard pages, alert rules, example answers |
| 9 | Limitations & scale path | Section 11 |
| 10 | AI-assisted workflow | What AI wrote, how it was checked |

### Likely interview questions
| Question | Answer anchor |
|---|---|
| How did you define "meaningful"? | FX-adjusted residual > 2%, or > $20 absolute; rounding (≤ 1 minor unit) excluded; all cut-offs in config, with a sensitivity table |
| Why DuckDB + dbt, not StarRocks? | Brief says keep it simple; same dbt models move to StarRocks |
| How do you know patterns are real? | CIs, tests, multivariable model; verify against the generator |
| Confounding (country vs cross-border)? | Logistic regression; stratified rates |
| Where does the $127k come from? | Gross under-settlement; extrapolated per 1k txns; stated as estimate |
| How would this run in production? | Section 11; daily DAG, alerts per PSP, real FX feed |
| PCI / GDPR? | No PAN; tokenized IDs; minimal PII; retention |

### AI kickoff prompt
> You are pairing with a Staff Data Engineer on the CasaMarket settlement-discrepancy take-home. Follow PLAYBOOK.md sections 4–6 exactly. **Step 1 only:** write `contracts/transactions.yaml` and the seeded generator with `config/generator.yaml`, the bucket rules and patterns P1–P4 plus hidden causes. Add the verification step that prints the realized mix and pattern lifts and fails if out of range. Stop after that.

Then: dbt models + tests → analysis → FINDINGS → dashboard + alerts → RECOMMENDATIONS → README.

### Final checklist
- [ ] `make all` works from a fresh clone (and `docker compose up`).
- [ ] ≥ 500 rows, 3–4 months, 4 countries, 3–5 PSPs, status mix, lag outliers, metadata.
- [ ] Realized bucket mix inside brief ranges; P1–P4 verified.
- [ ] Every enriched field in section 6; CLP minor units correct.
- [ ] dbt tests and pytest pass.
- [ ] All 5 RCA questions answered with CIs and $ impact; ≥ 3–4 patterns.
- [ ] FINDINGS.md in the fixed format, with charts.
- [ ] Dashboard answers both example questions.
- [ ] RECOMMENDATIONS.md: 3–5 actions with evidence, $, owner, implementation.
- [ ] README: approach, findings, assumptions, how to read results.
- [ ] No PAN anywhere.
- [ ] Walk the Deliverables, Done list and every acceptance criterion.
