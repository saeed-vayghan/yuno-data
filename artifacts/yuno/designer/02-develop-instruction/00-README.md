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
| 4b | [`engineer/02-develop-instruction/02-config-and-core.md`](../../engineer/02-develop-instruction/02-config-and-core.md#core-api-contract) | **CORE API CONTRACT**: the single source for every core name, arg, column and tier. |
| 5 | `orchestrator/04-plan-review/DELIVERABLES-CHECK.md` | Why "over $50" means `> 50`, and why the UI starts after the core checkpoint. |
| 6 | `orchestrator/01-research/01-Functional-Req-v3/00-SUMMARY.md` (glossary), `06-web-ui.md`, `07-alerting-metrics.md` | Terms, dashboard pick, alert rules. |
| 7 | `architect/03-system-design/06-cli-and-dashboard.svg` | Picture: CLI and dashboard on one shared core. |

Conflict rule: `scenario.md` wins, then `FINAL-SOLUTION.md`, then `UI-UX-PLAN.md` / `IMPLEMENTATION-PLAN.md`, then these files. For core API names, the engineer contract wins over the UI-UX-PLAN and these files.

## The gate: start only after the engineer's core checkpoint

The dashboard is a **stretch** item in the brief. Do not start it until the core (FR1 pipeline + FR2 analysis + docs) is done. "Done" means all of these are true on the engineer's branch:

| # | Must exist | Quick check (run it, do not guess) |
|---|---|---|
| 1 | Engineer core checkpoint (engineer 00, work-order step 11) | `make clean && make all` exits 0 |
| 2 | The DuckDB file with the marts | `ls data/casarecon.duckdb` · tables `marts.fct_transaction_discrepancy`, `mart_psp_weekly`, `mart_outliers`, `mart_segment_rates`, `mart_cause_summary` |
| 3 | Every **Core** row of the engineer contract | `uv run python -c "from casarecon.core import connect, db_version, status, psp_weekly, worst_week, query_transactions, segment_rates, cause_summary, excess_loss, lag_by_country_tier, mask_id, exponent, to_major, Filters, DbMissing, DbBusy"` exits 0 |
| 4 | Reports | `ls reports/FINDINGS.md reports/findings.json` |
| 5 | 500-row test fixture | `tests/conftest.py` has the session fixture DB; `make test` is green |
| 6 | Brief questions in the CLI (engineer 09 part B, step 12) | `uv run recon worst-week --month last --format json` and `uv run recon query --min-usd 50 --format csv \| head` print rows |

Items 1–5 are the hard gate. Item 6 is needed only for the CLI ↔ UI tests (file 09); you may start file 01 before it lands.

Later backend outputs you do **not** wait for (the pages show a "not built yet" state until they exist):
- Stretch core rows (engineer step 13, t ≈ 160): `kpis`, `weekly_trend`, `week_over_week`, `category_mix`, `outlier_summary`, `transaction_detail`, `similar_count`, `filter_options`, `pending`, `load_*`.
- `reports/recommendations.json` + `RECOMMENDATIONS.md` (engineer 07 part B) → Root causes.
- `reports/alerts.jsonl` (engineer 08) → Alerts page and the Overview "open alerts" KPI.

**Decision (who writes the Stretch core functions):** 🏛️ Jamshid wanted the engineer to own all of `core/`; 🎨 Mani did not want to be blocked. → **One rule (same in engineer 00):** the engineer owns `core/` and writes the Stretch rows at step 13. If a row is still missing when your page needs it, you may add it in `core/queries.py` exactly as the contract names it (args, columns), with the engineer 02 part B pattern and one pytest; the engineer reviews. Pages never hold SQL.

**Tags in this set:** "Core" below means the **UI core path**. The whole dashboard is brief **Stretch**.

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

## Combined timeline (engineer + dashboard) — same table in [engineer 00](../../engineer/02-develop-instruction/00-README.md)

| t (min) | Engineer lane | UI lane (frontend dev) | Tier |
|---|---|---|---|
| 0–135 | Steps 1–11 → **✅ CORE CHECKPOINT** | — (not started) | Core |
| 135–145 | 12 · CLI brief questions | UI 01 shell (12) | Stretch |
| 145–160 | 13 · core part C (Stretch rows) | UI 02 wrappers + guard (10) → 157 | Stretch |
| 160–170 | 14 · RECOMMENDATIONS | UI 05 Outliers (12) → 169 | Stretch |
| 170–190 | 15 · alerts | UI 03 Overview (15), UI 04 table (6) → 190 | Stretch |
| 190–205 | 16 · Docker, CI | UI 10 draft (3), UI 09 core tests (7) → **200 = UI core path done** | Stretch / packaging |
| 205–240 | review UI's core functions (if any) | UI extras: 07 Alerts (8), 06 Root causes (10), 04 charts (6), 08 polish (8), 09 rest (5), 10 final (3) | Stretch |
| 240–245 | 17 · README Monitoring + final DoD walk | — | Final |

- Two builders: ~245 min wall clock. One builder: ~210 + ~110 = ~320 min; stop after step 14 (CLI + recommendations already meet the brief's stretch line), then add the UI core path if time is left.
- The brief says ~2 h. Only the core (0–135) is required; everything after the checkpoint is optional and follows the cut order.

## Cut order (after the checkpoint, cut from the top; same list in engineer 00)

1. CI workflow (E 10B).
2. Scripted screenshots → 2 manual ones (UI 09).
3. Drill-down charts + `category_mix` (UI 04, E 02C).
4. Root-causes heatmap + excess-loss table (UI 06).
5. Manual a11y passes: CVD simulator, 200% zoom (UI 08).
6. Sensitivity table 1/2/3% (E 06).
7. Slack hook (E 08).
8. Alerts page → Overview KPI links to `reports/alerts.md` (UI 07).
9. Root causes page + `load_findings`, `load_recommendations` → README links RECOMMENDATIONS.md (UI 06, E 02C).
10. Drill-down page → worst-week card links to Outliers with PSP + week set (UI 04).
11. HDBSCAN: never start it unless everything else is done.

**Never cut:** dbt tests, validation gate, FINDINGS.md, README, `make all`, idempotent rerun, `recon worst-week` / `recon query`. If the dashboard is started: Overview worst-week card, Outliers at `> 50` + CSV, data guard, masked IDs, UI tests 4 and 5, README "Monitoring", `make app`.

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
- Customer IDs arrive masked in the `customer` column (core `mask_id`); `transaction_id` stays whole.
- Money compares in USD (auth-day rate). Local amounts only on row views, with ISO code (`CLP 12,345`).
- Colour never carries meaning alone (Okabe-Ito + icon + word).
- Names stay as in the plans: `recon`, `make app`, PSP_A–E, `query_transactions`, `mask_id`.

## Done when
- [ ] You checked the 5 gate items above and they pass.
- [ ] You know the core path (steps 1–7 of the build order) and the cut order.

## Pitfalls
- Starting the UI before the marts exist: you will invent columns that later change.
- Treating the UI-UX-PLAN mockup dates (Aug 2026, W34) as real. The engineer rule: data window 2026-04-01 → 2026-06-30; `as_of` = latest timestamp in the data (`core.status()`, never wall-clock) → as-of **2026-06-30**, last full month **2026-06**, last closed week **2026-W25 (Jun 15–21)**. Use these as expected values in tests and wireframes.

## Hand-off
Go to `01-setup-and-app-shell.md`. Keep a list of any Stretch core function you had to add (never rename one); give it to the engineer at the end (file 10).
