# 00 · How to use these instructions

**Goal:** build the CasaMarket settlement-discrepancy backend (pipeline, analysis, reports, alerts, CLI, core API for the dashboard) in a fixed order, core first.

Written by 🏛️ Jamshid (Principal Architect) and ⚡ Kaveh (Senior Data Engineer).

## Source of truth (in this order)
1. [scenario.md](../../architect/00-scenario/scenario.md): the brief. It wins every conflict.
2. [FINAL-SOLUTION.md](../../orchestrator/01-research/FINAL-SOLUTION.md): the decided solution.
3. [IMPLEMENTATION-PLAN.md](../../architect/02-implementation-plan/IMPLEMENTATION-PLAN.md): steps S0.1–S6.3, repo layout, data model.
4. [DELIVERABLES-CHECK.md](../../orchestrator/04-plan-review/DELIVERABLES-CHECK.md) · [PLAYBOOK.md](../../architect/01-playbook/PLAYBOOK.md) · [decision sheet](../../orchestrator/01-research/01-Functional-Req-v3/00-SUMMARY.md).
5. [UI-UX-PLAN.md](../../designer/01-ui-ux/UI-UX-PLAN.md): only for what the dashboard needs from `casarecon.core`.

Diagrams: [`../../architect/03-system-design/`](../../architect/03-system-design/) → `01-high-level.svg`, `02-data-generation.svg`, `03-data-pipeline.svg`, `04-analysis-reports.svg`, `05-alert-system.svg`, `06-cli-and-dashboard.svg`, `07-run-and-ci.svg`, `10-aws-solution.svg`.

## Prerequisites
- macOS/Linux, `git`, `make`, [uv](https://docs.astral.sh/uv/) ≥ 0.5 (installs Python 3.12 for you).
- Docker + Docker Compose (only for file 10).
- No database server, no cloud account.

## Files

| # | File | One topic | Tag |
|---|---|---|---|
| 01 | [01-setup-repo.md](01-setup-repo.md) | uv project, pins, layout, Makefile, CLI stubs, pre-flight version check | Core |
| 02 | [02-config-and-core.md](02-config-and-core.md) | `thresholds.yaml`, `alerts.yaml`, shared core, **CORE API CONTRACT** | Core (parts A, B) + Stretch (part C) |
| 03 | [03-synthetic-data-generator.md](03-synthetic-data-generator.md) | seeded generator, P1–P4, X1–X6, drift, truth labels | Core |
| 04 | [04-dbt-models-and-tests.md](04-dbt-models-and-tests.md) | seeds, staging, marts, category + cause rules, dbt tests, `recon build` | Core |
| 05 | [05-validate.md](05-validate.md) | `recon validate`: bucket shares + pattern bands | Core |
| 06 | [06-analysis.md](06-analysis.md) | segment tests, GLM, cause truth check, signature table, $ impact | Core |
| 07 | [07-reports.md](07-reports.md) | FINDINGS.md (core), RECOMMENDATIONS.md (stretch), figures | Core + Stretch |
| 08 | [08-alerts.md](08-alerts.md) | 6 rules, `alerts.jsonl` + `alerts.md` | Stretch |
| 09 | [09-cli.md](09-cli.md) | `recon` commands, `all`, exit codes, brief questions | Core (A) + Stretch (B) |
| 10 | [10-run-paths-docker-ci.md](10-run-paths-docker-ci.md) | `make all`, `uv run recon all`, Docker, idempotency, CI | Core (A) + Packaging (B) |
| 11 | [11-readme-and-submission.md](11-readme-and-submission.md) | README incl. `### Assumptions`, scale path, final DoD | Core (A) + final check (B) |

## Work order and time budget

Files are numbered by topic. **Work in this order** (some files are done in parts):

| Order | Work | Time (min) | Running total | Brief budget line |
|---|---|---|---|---|
| 1 | 01 setup | 10 | 10 | Setup 15–20 |
| 2 | 02 part A: config, paths, errors, db, money, `mask_id`, `Filters` | 5 | 15 | Setup |
| 3 | 03 generator | 20 | 35 | Data generation 15–20 |
| 4 | 04 dbt models + tests + `recon build` | 30 | 65 | Pipeline 25–35 |
| 5 | 02 part B: core query functions (Core rows of the contract) | 5 | 70 | Pipeline |
| 6 | 05 validate | 5 | 75 | Data generation |
| 7 | 06 analysis | 30 | 105 | Analysis 30–40 |
| 8 | 07 part A: FINDINGS.md + figures | 10 | 115 | Analysis |
| 9 | 09 part A: `recon all`, exit codes | 5 | 120 | Docs & polish |
| 10 | 10 part A: `make all` twice, hash check, `make test` | 5 | 125 | Docs & polish |
| 11 | 11 part A: README | 10 | **135** | Docs 15–20 |
| **✅ CORE CHECKPOINT** | FR1 + FR2 + docs done. **Commit now**, including `reports/FINDINGS.md`, `reports/findings.json`, `reports/analysis/*.csv`, `reports/figures/*`. | | **135** | |
| 12 | 09 part B: `recon worst-week`, `recon query` (both brief questions) | 10 | 145 | Stretch 20–30 |
| 13 | 02 part C: dashboard core functions (Stretch rows of the contract) | 15 | 160 | Stretch |
| 14 | 07 part B: RECOMMENDATIONS.md + `recommendations.json` | 10 | 170 | Stretch |
| 15 | 08 alerts | 20 | 190 | Stretch |
| 16 | 10 part B: Docker, CI | 15 | 205 | (not in brief) |
| 17 | 11 part B: README Monitoring + final DoD walk (after the UI lane ends) | 5 | 210 | |

> **Decision (budget):** ⚡ Kaveh: the plan is 135 min core vs the brief's ~100–115; stretch + packaging add ~75. 🏛️ Jamshid: accepted; the core checkpoint is the hard line. RECOMMENDATIONS moves before alerts (FR4 is cheap and scored). 🎨 Mani: part C moves up to step 13 so the UI lane never waits for it.

## Combined timeline (engineer + dashboard) — same table in [designer 00](../../designer/02-develop-instruction/00-README.md)

| t (min) | Engineer lane | UI lane (frontend dev) | Tier |
|---|---|---|---|
| 0–135 | Steps 1–11 above → **✅ CORE CHECKPOINT** | — (not started) | Core |
| 135–145 | 12 · CLI brief questions | UI 01 shell (12) | Stretch |
| 145–160 | 13 · core part C (Stretch rows) | UI 02 wrappers + guard (10) → 157 | Stretch |
| 160–170 | 14 · RECOMMENDATIONS | UI 05 Outliers (12) → 169 | Stretch |
| 170–190 | 15 · alerts | UI 03 Overview (15), UI 04 table (6) → 190 | Stretch |
| 190–205 | 16 · Docker, CI | UI 10 draft (3), UI 09 core tests (7) → **200 = UI core path done** | Stretch / packaging |
| 205–240 | review UI's core functions (if any) | UI extras: 07 Alerts (8), 06 Root causes (10), 04 charts (6), 08 polish (8), 09 rest (5), 10 final (3) | Stretch |
| 240–245 | 17 · README Monitoring + final DoD walk | — | Final |

- Two builders: ~245 min wall clock. One builder: ~210 + ~110 = ~320 min; stop after step 14 (CLI + recommendations already meet the brief's stretch line), then add the UI core path if time is left.
- The brief says ~2 h. Only the core (0–135) is required; everything after the checkpoint is optional and follows the cut order.

**Cut order** (after the checkpoint, cut from the top; same list in designer 00):
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

## Map: file → brief deliverable / Done item

| File | Brief deliverable | "What Done Looks Like" / rubric | FR |
|---|---|---|---|
| 01 | D1 working code + run instructions | Tech 15: locked deps, reproducible | — |
| 02 | D1 | Tech 15: config, no logic in UI; FR3 shared core | FR1 "define meaningful", FR3 |
| 03 | D2 generated dataset / script | Test data 10: ≥ 500 rows, 4 countries, patterns | Test data spec |
| 04 | D1 | Done: "accurately calculate discrepancies"; Pipeline 20 | FR1 |
| 05 | D2 | Test data 10: realistic distributions, gate | Test data spec |
| 06 | D3 analysis outputs | Done: "≥ 3–4 patterns backed by data"; RCA 25 | FR2 |
| 07 | D3, D4, D5 (recommendations) | Insight 20; Stretch 10 | FR2, FR4 |
| 08 | D5 monitoring | Stretch 10 | FR3 alerts |
| 09 | D1, D5 | Stretch 10: both brief questions | FR3 CLI |
| 10 | D1 | Done: "reproducibility"; Tech 15 | — |
| 11 | D1, D4 docs incl. assumptions | Done: "well-documented" | all |

## Hand-off to the frontend developer
- They start **after the core checkpoint** (start gate: [designer 00](../../designer/02-develop-instruction/00-README.md)).
- They consume only `casarecon.core` (contract in [02](02-config-and-core.md#core-api-contract)); it is the single source for core names, args and columns. No SQL in pages.
- Owner rule: the engineer owns `core/` and writes the Stretch rows (step 13). If one is missing when a page needs it, the frontend dev may add it exactly as in the contract + one pytest; the engineer reviews.
- They get a built DB at `data/casarecon.duckdb`, `reports/*.json|jsonl|md`, and a 500-row pytest fixture DB (file 10).
