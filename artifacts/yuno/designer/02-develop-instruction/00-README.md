# 00 · How to use these instructions (Dashboard + Alerts page)

**Goal:** give the frontend developer one clear path to build the Streamlit monitoring dashboard (5 pages) on top of the engineer's shared core, in the right order and within the time box.

Written by 🏛️ Jamshid (Principal Architect) and 🎨 Mani (Product Designer / Frontend). Where we disagreed, a short **Decision** note says what we picked.

**Time box:** 5 min to read this file · **Tag:** Core

---

## Inputs (read in this order)

| # | File | Why |
|---|---|---|
| 1 | `architect/00-scenario/scenario.md` | Source of truth. FR3 and the two brief questions. |
| 2 | `orchestrator/01-research/FINAL-SOLUTION.md` §5 (dashboard), §6 (alerts) | The decided solution. |
| 3 | `designer/01-ui-ux/UI-UX-PLAN.md` | Users, flows, wireframes, colours, states, tests. |
| 4 | `architect/02-implementation-plan/IMPLEMENTATION-PLAN.md` | Repo layout, marts, core names (`query_transactions`, `mask_id`, `worst_week`…). |
| 5 | `orchestrator/04-plan-review/DELIVERABLES-CHECK.md` | Why "over $50" means `> 50`, and why the UI starts after the core checkpoint. |
| 6 | `orchestrator/01-research/01-Functional-Req-v3/00-SUMMARY.md` (glossary), `06-web-ui.md`, `07-alerting-metrics.md` | Terms, dashboard pick, alert rules. |
| 7 | `architect/03-system-design/06-cli-and-dashboard.svg` | Picture: CLI and dashboard on one shared core. |

Conflict rule: `scenario.md` wins, then `FINAL-SOLUTION.md`, then `UI-UX-PLAN.md` / `IMPLEMENTATION-PLAN.md`, then these files.

## The gate: start only after the engineer's core checkpoint

The dashboard is a **stretch** item in the brief. Do not start it until the core (FR1 pipeline + FR2 analysis + docs) is done. "Done" means all of these are true on the engineer's branch:

| # | Must exist | Quick check (run it, do not guess) |
|---|---|---|
| 1 | Implementation Plan core checkpoint (end of S4.2) | `make clean && make all` exits 0 |
| 2 | The DuckDB file with the marts | `ls data/casarecon.duckdb` · tables `marts.fct_transaction_discrepancy`, `mart_psp_weekly`, `mart_outliers`, `mart_segment_rates`, `mart_cause_summary` |
| 3 | Core read layer from S3.1 | `uv run python -c "from casarecon.core.queries import worst_week, query_transactions, segment_rates, cause_summary, mask_id; from casarecon.core.db import connect, DbBusy"` exits 0 |
| 4 | Reports | `ls reports/FINDINGS.md reports/findings.json` |
| 5 | 500-row test fixture | `tests/conftest.py` has the session fixture DB; `make test` is green |
| 6 | Brief questions in the CLI (S4.3) | `uv run recon worst-week --month last --format json` and `uv run recon query --min-usd 50 --format csv \| head` print rows |

Items 1–5 are the hard gate. Item 6 is needed only for the CLI ↔ UI tests (file 09); you may start file 01 before it lands.

Later backend outputs you do **not** wait for (the pages show a "not built yet" state until they exist):
- `reports/alerts.jsonl` (S5.1) → Alerts page and the Overview "open alerts" KPI.
- `reports/RECOMMENDATIONS.md` (S5.2) → Recommendations block on Root causes.

**Decision (who writes the extra core functions):** 🏛️ Jamshid wanted the engineer to own all of `core/queries.py`; 🎨 Mani did not want to be blocked. → The frontend dev adds the missing read functions from file 02 into `src/casarecon/core/queries.py` (parameterized SQL, one pytest each, as S5.3 says). The engineer reviews them. Pages never hold SQL.

## Files and time box

Reading order = file number. Build order is slightly different (see next table).

| File | Topic | Min | Tag | Serves (brief / DoD) |
|---|---|---|---|---|
| 00 | This guide | 5 | Core | — |
| 01 | Setup and app shell | 12 | Core | FR3 "runs on localhost"; Tech (runnable) |
| 02 | Data-access contract | 10 | Core | FR3 shared core; "no logic in UI"; PII masking |
| 03 | Page: Overview | 15 | Core | FR3 trends, week-over-week, **"worst week last month?"** |
| 04 | Page: Drill-down | 12 | Stretch (table part Core) | FR3 "drill down into segments" |
| 05 | Page: Outliers | 12 | Core | FR3 outliers, **"discrepancies over $50"** |
| 06 | Page: Root causes & actions | 10 | Stretch | FR2 shown in UI; FR4 recommendations "included in your dashboard" |
| 07 | Page: Alerts | 8 | Stretch | FR3 "automated alert system" |
| 08 | States, accessibility, charts | 8 | Core (guard) + Stretch (polish) | "Well documented, team can use it"; Insight clarity |
| 09 | Tests and screenshots | 12 | Core (tests 1, 2, 4, 5, 6, 11, 15) + Stretch (rest) | Tech 15; "Done: reproducible, clean" |
| 10 | README Monitoring + hand-off | 6 | Core | Deliverable 1 (run instructions); Deliverable 5; DoD "well documented" |
| | **Total** | **~110** | | Core path ≈ 70 min |

Honest note: the brief gives stretch goals 20–30 min in total. The full UI plan does not fit that. The **core path** (01, 02, 05, 03, the Drill-down table, 09 core tests, 10) answers both brief questions and is the target. Everything else is bonus.

## Build order

| Step | File | Why this order |
|---|---|---|
| 1 | 01 | Shell, theme, filters. Nothing works without it. |
| 2 | 02 | Cached wrappers + data guard ("Run `make all` first", "Rebuilding"). |
| 3 | 05 | Brief question 2. Simplest page; proves the data contract. |
| 4 | 03 | Brief question 1 (worst-week card) + trend + WoW. |
| 5 | 04 (filters + table only) | The card, "similar rows" and "view segment" all link here. |
| 6 | 10 (Monitoring section, first draft) | So docs exist even if time runs out now. |
| 7 | 09 (core tests) | Lock the two brief answers with CLI ↔ UI tests. |
| 8 | 07 | Alerts page (small; reads a file). |
| 9 | 06 | Root causes & actions. |
| 10 | 04 (charts), 08 (polish), 09 (rest) | Bonus. |

**Decision (build Drill-down early):** 🏛️ Jamshid wanted Drill-down last (the Implementation Plan cuts "pages beyond Overview + Outliers" first). 🎨 Mani: three links land on Drill-down. → Build its filters + table early (step 5, ~6 min); its charts are cut first.

## Cut order (if time is short, cut from the top)

1. README screenshots made by script → take 2 manual screenshots instead (file 09).
2. Drill-down charts (group-by bars with ranges, category mix). Keep filters + table + CSV.
3. Root causes: heatmap and excess-loss table. Keep loss-by-cause bars + recommendations.
4. Manual a11y passes (CVD simulator, 200% zoom). Keep "never colour alone" rules in code.
5. Alerts page → the Overview KPI links to `reports/alerts.md` text instead. `recon alerts` still serves FR3.
6. Root causes page → README links to `reports/RECOMMENDATIONS.md`.
7. Drill-down page → the worst-week card links to Outliers with PSP + week set.

**Never cut:** Overview worst-week card · Outliers page at `> $50` with CSV · data guard (no DB / rebuilding) · masked customer IDs · CLI ↔ UI tests 4 and 5 · README "Monitoring" section · `make app`.

## Map: file → brief deliverable / DoD

| Brief item | Where it is proven |
|---|---|
| FR3 "Visualize discrepancy trends over time" | 03 (weekly flag rate + net loss) |
| FR3 "Drill down into specific segments" | 04 |
| FR3 "Identify outlier transactions" | 05 |
| FR3 "Monitor week-over-week" | 03 (KPI deltas + WoW table) |
| FR3 acceptance "Which PSP had the worst week last month?" | 03 card + 09 test 4 |
| FR3 acceptance "all transactions with discrepancies over $50" | 05 + 09 test 5 |
| FR3 "automated alert system" (UI side) | 07 |
| FR4 "included in your dashboard" | 06 |
| Constraint "runs on localhost" | 01 (`make app` → `localhost:8501`) |
| Deliverable 1 "README / run instructions" | 10 |
| Rubric Stretch 10 "each brief question in ≤ 2 clicks" | 03, 05, 10 (newcomer test) |
| Rubric Tech 15 (tested, reproducible) | 09 |

## Global rules (apply to every file)

- 5 pages exactly: Overview · Drill-down · Outliers · Root causes & actions · Alerts.
- Pages call `casarecon.core` only. No `duckdb` import, no SQL, no reading raw CSV in `dashboard/`.
- "Over $50" = discrepancy after FX, in USD, `abs_residual_usd > 50`.
- Customer IDs are masked by core (`mask_id`); `transaction_id` stays whole.
- Money compares in USD (auth-day rate). Local amounts only on row views, with ISO code (`CLP 12,345`).
- Colour never carries meaning alone (Okabe-Ito + icon + word).
- Names stay as in the plans: `recon`, `make app`, PSP_A–E, `query_transactions`, `mask_id`.

## Done when
- [ ] You checked the 5 gate items above and they pass.
- [ ] You know the core path (steps 1–7 of the build order) and the cut order.

## Pitfalls
- Starting the UI before the marts exist: you will invent columns that later change.
- Treating the wireframe dates (July/Aug) as real: data is 3 months from `2026-04-01`, so "last full month" is **June 2026** and the last closed week is **W25 (Jun 15–21)** if as-of is Jun 30.

## Hand-off
Go to `01-setup-and-app-shell.md`. Keep a list of any core function you had to add or rename; give it to the engineer at the end (file 10).
