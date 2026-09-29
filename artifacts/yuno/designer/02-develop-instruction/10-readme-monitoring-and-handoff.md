# 10 · README "Monitoring" section and hand-off

**Goal:** write the README "Monitoring" section so a newcomer can open the app and answer both brief questions, then tick the final UI Definition of Done and hand open items to the engineer.

**Time box:** 6 min (first draft right after the Drill-down table; final pass at the end) · **Tag:** Core

## Inputs
- Working `make app`; pages 03 and 05 at least.
- README from the engineer (S4.2) with a "Monitoring" heading (11 sections).
- Screenshots from file 09.
- Your list of added core functions and wrong assumptions (A1–A6, file 02).

## Steps

### 1. README "Monitoring" section (paste and fill; keep it short)

```markdown
## Monitoring

### Open the dashboard
    make all      # builds data/casarecon.duckdb and reports/ (first time: about a minute)
    make app      # or: uv run recon dashboard
Open http://localhost:8501. Docker: `docker compose up`, then the same URL.
No data yet? The app says "Run `make all` first".

### Answer the two brief questions
| Question | In the app | In the terminal |
|---|---|---|
| Which PSP had the worst week last month? | **Overview** → "Worst PSP week" card (0 clicks). Change the month in the card. | `recon worst-week --month last` |
| Show me all transactions with discrepancies over $50 | **Outliers** in the sidebar (1 click). Opens at min $50. "Download CSV" for all rows. | `recon query --min-usd 50 --format csv` |

![Worst-week card](docs/screenshots/overview-worst-week.png)
![Outliers over $50](docs/screenshots/outliers-over-50.png)

### Pages
| Page | Use it to |
|---|---|
| Overview | See flag rate, net loss, large rows and open alerts for the last closed week; weekly trend; week-over-week by PSP × country; worst PSP week. |
| Drill-down | Filter by country, PSP, size tier, cross-border, weekday, category, cause and dates; see rates with 95% ranges and the rows. |
| Outliers | Triage rows over a USD threshold (default $50); click a row to see why it was flagged and similar rows. |
| Root causes & actions | Loss by likely cause, PSP × country rates, key findings with evidence, and the 3–5 recommendations. |
| Alerts | This week's alerts from `recon alerts`: severity, NEW / ONGOING / RESOLVED, owner. |

### How to read it
- **Discrepancy after FX:** settled minus expected settle, with the normal FX move removed, in USD at the auth-day rate.
- **Flag rate:** share of settled rows that are `meaningful` (2–5%, < $20) or `large` (> 5% or ≥ $20).
- **Week:** ISO week by auth date; a week belongs to the month of its Thursday. KPIs use the last **closed** week.
- **Low sample:** fewer than 30 rows; shown greyed, ranked last. Alerts need 50 rows per week.
- Customer IDs are masked (`cus_••••7f3a`). Transaction IDs are whole, for PSP disputes.
- Rebuilding while the app is open is safe; the app says "Rebuilding, retry" for a moment.
- The 500-row smoke run (`make smoke`) shows mostly "low sample" / "not enough data"; use `make all` for real numbers.
```

### 2. Final UI Definition of Done

**Brief**
- [ ] "Which PSP had the worst week last month?" answered on Overview in ≤ 1 click; equals `recon worst-week --month last` (test 4).
- [ ] "Transactions with discrepancies over $50" answered on Outliers in 1 click; equals `recon query --min-usd 50` (test 5); CSV works.
- [ ] Trends over time, drill-down by segment, outliers, week-over-week: all visible (FR3 bullets).
- [ ] Recommendations visible in the dashboard (FR4), or the cut note says where they are.
- [ ] Runs on `localhost:8501` via `make app`.

**Quality**
- [ ] Exactly 5 pages; no SQL or `duckdb` in `dashboard/`.
- [ ] Customer IDs masked in UI and CSV (test 11).
- [ ] All states from file 08 work (no DB, rebuilding, empty, low sample, missing report).
- [ ] Accessibility checklist (file 08) core items ticked.
- [ ] `make test` green, incl. core UI tests 1, 2, 4, 5, 6, 11, 15.
- [ ] README "Monitoring" section filled; 2 screenshots linked.
- [ ] Newcomer answered both questions in ≤ 2 clicks using only the README.

### 3. Hand-off note to the engineer (post in the PR description)

| Item | Ask |
|---|---|
| Core functions added by UI | list names + tests, for review |
| Assumptions A1–A6 (file 02) | confirm or tell us what changed |
| `alerts.jsonl` fields | `psp`, `country` split; `INSUFFICIENT_DATA` status |
| Docker | set `STREAMLIT_SERVER_ADDRESS=0.0.0.0` in compose (config binds localhost) |
| Tie-break in `worst_week` | net USD desc, then PSP name, same in CLI |
| Cuts made | which items from the cut order (file 00) were skipped |

## Done when
- [ ] README "Monitoring" section is in the repo and every command in it runs as written.
- [ ] Final DoD boxes ticked (or each unticked one listed under "Cuts made").
- [ ] Hand-off note posted.

## Serves
Deliverable 1 (README / run instructions) and Deliverable 5 (dashboard); DoD "well-documented so CasaMarket's team can use it"; DELIVERABLES-CHECK item 8 (Monitoring section updated for the dashboard); UI-UX build step 11.

## Pitfalls
- Writing the Monitoring section only at the very end: if time runs out, the dashboard has no docs. Draft it at build step 6.
- Copying numbers from your screen into the README: they change on rebuild. Describe, do not quote.
- README commands that differ from the Makefile (`make dashboard` vs `make app`): use `make app`.

## Hand-off
UI work is done. The engineer takes the hand-off note into the final fresh-clone walk-through (Implementation Plan S6.3).
