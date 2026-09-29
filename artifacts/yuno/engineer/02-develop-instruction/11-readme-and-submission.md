# 11 · README and submission

**Goal:** a README a reviewer can follow in 5 minutes (approach, findings, assumptions, how to run, how to read outputs, scale path), then a final walk of every brief deliverable and Done item before submitting.

**Time box:** part A 10 min (before the core checkpoint) · part B 5 min (at the end)
**Tag:** A **Core** · B final check (after stretch)

## Inputs
- All earlier files; `reports/run_manifest.json` (versions, realized mix), `reports/findings.json`.
- PLAYBOOK §12 README template · IMPLEMENTATION-PLAN S4.2 `### Assumptions` list · UI-UX-PLAN build step 11 (README "Monitoring").
- Diagrams: `../../architect/03-system-design/01-high-level.svg`, `10-aws-solution.svg`.

## Steps

### Part A (Core)

1. **Write `README.md` with these 11 sections** (H2 headings, this order):
   | # | Section | Content |
   |---|---|---|
   | 1 | Problem | 3 lines: 45k txns/month, 18% of approved settle differently, ~$127k/quarter |
   | 2 | Quick start | prereqs; the 3 run paths; `recon --help`; `make app` → `http://localhost:8501` |
   | 3 | Key findings | top 4–6 findings copied **by `recon report`** or linked to `reports/FINDINGS.md` (no hand-typed numbers in README either; link, or generate a block) |
   | 4 | Recommendations | link `reports/RECOMMENDATIONS.md` + top 3 titles |
   | 5 | Approach & architecture | `01-high-level.svg` (copy to `docs/`), layers raw → staging → intermediate → marts, why DuckDB + dbt (3 lines) |
   | 6 | Definitions & assumptions | money, cross-border, FX formula, categories table, week rule, local time; then `### Assumptions` (below) |
   | 7 | How to read the outputs | categories, flag, CI, q-value, lift, net vs gross, "discrepancy after FX" |
   | 8 | Data | generator, seed, P1–P4 + X1–X6 + drift, realized mix from `run_manifest.json`, 500-row sample |
   | 9 | Monitoring | CLI answers to both brief questions; alerts (6 rules, closed week); dashboard pages (filled in part B) |
   | 10 | Limitations & scale path | synthetic data; single-node; AWS path table (below) |
   | 11 | AI-assisted workflow | what AI wrote, how it was checked (dbt unit tests, truth check, gate) |

2. **Quick start block (exact):**
   ```bash
   # 1) with make
   make all            # generate → build → validate → analyze → alerts → report
   make app            # dashboard on http://localhost:8501
   # 2) without make
   pip install uv && uv run recon all
   # 3) without Python
   docker compose up   # then open http://localhost:8501
   # brief questions
   uv run recon worst-week --month last
   uv run recon query --min-usd 50 --format csv > over_50.csv
   ```

3. **`### Assumptions`** (one bullet each):
   - Data is synthetic and follows the brief's ranges (flagged ≈ 14%, non-exact ≈ 33%; the CFO's 18% and $127k are not reproduced, only compared as estimates).
   - Both amounts are in the merchant's local currency, integer minor units (CLP 0 decimals).
   - Cross-border = `payer_currency = USD`; expected settle removes the auth→settle FX move; USD uses the auth-day rate.
   - "Meaningful" = |residual| > 2% or ≥ $20; cut-offs live in `config/thresholds.yaml` (sensitivity at 1/2/3% in FINDINGS).
   - Times are merchant local time; weekend = Sat/Sun local.
   - A week is ISO (Mon–Sun, by auth date) and belongs to the month of its Thursday; "last month" = last full calendar month in the data; alerts use the last closed week (end ≤ as-of − 7 days).
   - No tips in the data (home goods); the tip cause is reported as "ruled out".
   - $ impact and savings are estimates; savings = excess loss × a stated reduction %.
   - Tool versions: the resolved DuckDB / dbt versions from `run_manifest.json` (and any pin fallback from file 01).

4. **Scale path on AWS** (docs only; embed or link `10-aws-solution.svg`):
   | Local | AWS / Yuno stack |
   |---|---|
   | CSV in `data/raw` | PSP settlement files → S3 + Iceberg |
   | DuckDB file | StarRocks (marts) |
   | dbt-duckdb | dbt on StarRocks (same models, macros for dialect) |
   | `make all` | Airflow (MWAA) daily DAG (Cosmos) |
   | batch export | MSK + Flink for auth/settlement events |
   | `recon alerts` | same evaluator as an Airflow task → SNS → Slack/PagerDuty, with alert state |
   | Streamlit | Superset on StarRocks, SSO |
   | synthetic FX | real daily FX feed |

5. Commit. **✅ Core checkpoint** (see file 00): `git add -A && git commit -m "core: pipeline, analysis, findings, README"` including `reports/FINDINGS.md`, `findings.json`, `analysis/*.csv`, `figures/*`.

### Part B (after stretch)

6. Fill README **"Monitoring"**: how to open the app, one line per page (Overview, Drill-down, Outliers, Root causes & actions, Alerts), and how to answer both brief questions in ≤ 2 clicks (worst-week card on Overview; Outliers page opens at "over $50"). Add the 2 screenshots from the frontend developer.

7. **Final DoD walk** (tick every box before submitting):

   **Brief deliverables**
   - [ ] D1 Working code + README with run steps: `make clean && make all` exits 0; every README command runs as written.
   - [ ] D2 Generator + seed + `data/sample/transactions_500.csv`; ≥ 500 rows, 3 months, 4 countries, 5 PSPs, statuses, lag outliers, metadata.
   - [ ] D3 Analysis outputs committed: `reports/analysis/*.csv`, `findings.json`, `figures/*`, `FINDINGS.md`.
   - [ ] D4 Docs: approach, key findings, `### Assumptions`, how to read outputs.
   - [ ] D5 (Stretch) `RECOMMENDATIONS.md` with 3–5 actions ($, owner, implementation) and/or alerts + dashboard.

   **What "Done" looks like**
   - [ ] Accurate discrepancies: dbt unit tests (FX row, CLP row, 2¢/$500, $20) pass; truth check ≥ 0.9.
   - [ ] ≥ 3–4 patterns: ≥ 4 F# with q < 0.05, each with n, CI, lift, q, $ and a figure.
   - [ ] Well documented: all 11 README sections present (`grep -c '^## ' README.md` ≥ 11; `grep -c '^### Assumptions' README.md` = 1).
   - [ ] Good engineering: `make test` green; idempotency check prints `IDEMPOTENT`; `uv.lock` committed; no PAN (`test_security.py`).
   - [ ] (Stretch) Both brief questions answered by `recon worst-week --month last` and `recon query --min-usd 50`, and in the dashboard.

   **Acceptance criteria**
   - [ ] FR1: `fct_transaction_discrepancy` has one row per transaction with all enriched fields.
   - [ ] FR2: FINDINGS answers all 5 questions.
   - [ ] FR3: worst-week card = CLI answer; Outliers rows = CLI `query` rows.
   - [ ] FR4: each recommendation cites an existing F#, shows $, owner, implementation.

8. Fresh-clone test (file 10 step 10), then submit the repo link.

## Done when
| Command | Expected |
|---|---|
| `grep -c '^## ' README.md` | ≥ 11 |
| `grep -c '^### Assumptions' README.md` | `1` |
| `grep -c '10-aws-solution' README.md` | ≥ 1 |
| copy-paste every command in README Quick start into a fresh clone | all exit 0 |
| `git status --porcelain reports/` after the final `make all` | empty (committed outputs match a fresh run) |
| every box in step 7 | ticked |

## Serves
Deliverable 1 (README/run instructions) · Deliverable 4 (approach, findings, assumptions, how to interpret) · Done "well-documented so CasaMarket's team can understand and use it" · Tech 15 · the whole "What Done Looks Like" list.

## Pitfalls
- **Numbers in the README drift** from reports after a regenerate. Link to FINDINGS.md or let `recon report` write the README findings block between markers (`<!-- findings:start -->…<!-- findings:end -->`).
- **SVG path:** the diagrams live outside the repo in the planning folder; copy the ones you reference into `docs/` so links work on GitHub.
- Do not promise what is not built: the AWS path is "documented, not built".
- State the CFO 18% vs our ~14% flagged share up front; reviewers ask.
- Keep README short: tables over prose; details live in FINDINGS.md.

## Hand-off
- Reviewer: README → Quick start → FINDINGS.md → RECOMMENDATIONS.md → dashboard.
- Frontend developer: README "Monitoring" is theirs to verify (newcomer answers both questions using only the README).
