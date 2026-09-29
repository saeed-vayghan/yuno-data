# Review · v2/06 Monitoring Dashboard
**Verdict:** ⚠️ Pass with fixes — **Score:** 7/10 (right pick and right top 2, but the read-only DuckDB setup can block rebuilds, the worst-week answer is empty on a 500-row run, and the brief's "outliers" need has no clear page)

## Fit to brief
| Brief requirement / constraint | Served? (✅/⚠️/❌) | Note |
|---|---|---|
| FR3: visualize discrepancy trends over time | ✅ | Overview has the weekly trend. |
| FR3: drill down (country, PSP, transaction size, etc.) | ✅ | Drill-down page: country, PSP, tier, cross-border, weekday. |
| FR3: outlier transactions that need investigation | ⚠️ | No "Outliers" page. The "$50" page is a money filter, not an outlier list. The playbook and 07 define outliers as \|Δ USD\| > $50 OR robust z > 3.5 (F4). |
| FR3: week-over-week improving or worsening | ✅ | Overview shows the WoW change. The Drill-down filters can apply it per PSP or country. |
| "Which PSP had the worst week last month?" | ⚠️ | Defined (net USD loss, ISO week, last full month), but a week that crosses a month edge has no rule (F3). The page is empty on a `--rows 500` run because of the 30-row minimum (F2). |
| "Show me all transactions with discrepancies over $50" | ✅ | Page with search and sort, using USD at the auth-date rate. A CSV download is missing (F4). |
| "Runs on localhost" | ✅ | `make app`. The URL and the empty-database case are not stated (F8). |
| Stretch 4: recommendations "included in your dashboard" (optional) | ✅ | "Root causes & actions" page. |
| Frame: lean one-command build + documented AWS path | ⚠️ | Mostly lean. One dashboard file holds the DuckDB lock (F1), and six pages is one more than needed (F7). |

## Findings
| # | Severity (High/Med/Low) | Location (quote) | Problem | Proposed fix | Jamshid | Status |
|---|---|---|---|---|---|---|
| 1 | High | "`make app` opens DuckDB 1.4.x LTS read-only" | DuckDB allows one writing process **or** many read-only processes, never both at once. A running app that keeps its read-only connection open makes `make all` / `dbt build` fail with "already opened by another process". v1 said the opposite. | Open a short read-only connection for each query and close it right away. Cache results with `st.cache_data`, keyed on the DB file's modified time. Add one line: "you can rebuild while the app runs." | Accept. The DuckDB docs confirm it. The v1 claim was wrong. | Agreed |
| 2 | Med | "skip PSP-weeks with < 30 tx" | The brief's minimum dataset is 500 rows. A `--rows 500` run gives about 7 rows per PSP-week, so every week is skipped and the key question gets no answer. | Show every PSP-week. Grey out the ones with n < 30 and label them "low sample". Rank the n ≥ 30 weeks first. | Compromise: keep 30 as the ranking rule, but never return an empty answer. | Agreed |
| 3 | Med | "worst week = net USD loss per ISO week … last month = last full month in the data" | An ISO week can span two months. The file does not say which month it belongs to, or which date assigns it (the playbook says auth date). The CLI and the dashboard could give different answers. | Add: "Weeks are set by auth date. A week counts for the month that holds its Thursday (the ISO rule)." Put this in one shared `core` function. | Accept. | Agreed |
| 4 | Med | "Transactions over $50 (search, sort, masked IDs)" | The brief asks for "outlier transactions that need immediate investigation". The playbook names an "Outliers page" (`large` + `is_outlier`, min-$ filter default 50, CSV download). This page only filters by money. It has no reason column and no download. | Rename the page to "Outliers". Set the min-$ filter to 50 by default, add a "why flagged" column (> $50 or z > 3.5), and add a CSV download. | Accept. It is the same page with two more columns. | Agreed |
| 5 | Med | "No live filters or search; fails 'interact' test" | The brief allows it outright: "or even a command-line tool that generates reports". Saying it "fails" misreads the brief. | Change to: "The brief allows it, and `recon` covers it (see 05). As the dashboard it has no live filters." | Accept the wording. The verdict stays the same. | Agreed |
| 6 | Med | "only runs `SELECT`s on dbt marts, so every metric lives in dbt" | This conflicts with the page list: Alerts reads `alerts.jsonl` and Actions reads `RECOMMENDATIONS.md`. It also leaves out the shared `core` package (05, playbook §10). Without it, the SQL for worst week and over $50 could be written twice. | "Reads dbt marts, `alerts.jsonl` and `RECOMMENDATIONS.md` through the shared `core` package. These are the same functions `recon worst-week` and `recon query` use. One test checks that the CLI and the dashboard give the same worst PSP-week." | Accept. | Agreed |
| 7 | Low | "Pages: Overview … · Worst PSP-week (last month) · …" (six pages) | This is more than the brief needs. The playbook calls it a "Worst week" **card**. A whole page for one answer adds navigation. | Put the worst-week card on Overview, which answers in one click. Keep five pages. | Compromise: the card goes on Overview and links to the Drill-down page with the filters already set. No separate page. | Agreed |
| 8 | Low | "`make app` opens DuckDB …" | It does not say the URL, the bind address, or what happens if `make all` has not run yet. | Add: "Opens http://localhost:8501, bound to localhost only. With no DB it shows 'Run `make all` first', not a stack trace." | Accept. | Agreed |
| 9 | Low | "worst week = net USD loss per ISO week" | "Net" is not explained: do over-settlements cancel out losses? The playbook also ranks "by rate, min n". | Add: "net = under-settled $ minus over-settled $". Show the rate and n next to the $. | Accept, as one line of text. | Agreed |
| 10 | Low | "the evaluator as an Airflow task posting to Slack" | This does not match 07, which sends alerts through CloudWatch/SNS to Slack or PagerDuty. | Change it to "the evaluator as an Airflow task (see 07)". | Accept. | Agreed |
| 11 | Low | Option list (rows 1–8) | The brief names "a Jupyter notebook with interactive widgets". No row covers it by name. | Rename row 4 to "marimo / Jupyter + widgets". | Rebut in part: marimo is the modern form of that option and the verdict is the same. The rename is still fine. | Agreed |
| 12 | Low | "SQL + Markdown pages, static build" / "wants a static, shareable report" | The Evidence Core post (26 Aug 2026) says projects "build into Docker containers" with basic auth. "Static" may be out of date after the rewrite. | Check the Core docs. If it is not static any more, write "builds to a container". | The older docs still show a static build. I will check it, but it does not change the ranking. | Open |
| 13 | Low | "RBAC", "DuckDB-WASM", "BI as code", "Superset speaks StarRocks", "community-only", "unsigned", "LTS"; the dense 🥇 paragraph | This is hard to read. The 🥇 paragraph puts the definitions, the scale path and the pages into four long lines. | Use plain words ("user roles", "runs DuckDB in the browser", "has a StarRocks connector"). Split the 🥇 block into three short lists: Definitions, Pages, Scale path. | Accept. | Agreed |
| 14 | Low | "< 30 tx" (06) vs "minimum sample 50" (07) | Two different minimums could confuse a reader: the dashboard shows a week that the alerts call "insufficient data". | Add one line saying why they differ (30 is for display, 50 is for an alert decision), or use one number. | Rebut: they have different jobs. Accept the one-line note. | Agreed |

## Debate highlights
- ⚡ **Kaveh:** The read-only connection does not protect dbt. It blocks dbt. DuckDB lets one process write or many read, not both, so a reviewer who leaves the app open and reruns `make all` gets a lock error.
- 🏛️ **Jamshid:** Agreed, v1 got this wrong. Short connections for each query plus `st.cache_data` fix it, and nothing else in the design changes.
- ⚡ **Kaveh:** The brief's floor is 500 rows. With 4 PSPs and about 17 weeks, the "skip < 30" rule leaves no PSP-week at all, and the headline question comes back empty.
- 🏛️ **Jamshid:** 135k rows is the default, but a smoke run must not look broken. Keep 30 for the ranking, show the small weeks greyed out, and never return nothing.
- ⚡ **Kaveh:** Six pages is over-built. "Worst PSP-week" is one number, and the playbook calls it a card.
- 🏛️ **Jamshid:** Fine: a card on Overview that opens the Drill-down page already filtered. But I keep Evidence as runner-up. The Node cost is a real trade-off, not a reason to drop it.
- ⚡ **Kaveh:** Agreed on the top 2. Streamlit is still the fastest way to answer both questions in two clicks or fewer.

## Must-fix list
1. **(High, F1)** Stop holding the DuckDB file open. Open a short read-only connection for each query, cache the results, and state that you can rebuild while the app runs.
2. **(Med, F2)** Never return an empty worst-week answer. Show PSP-weeks with n < 30 greyed out as "low sample", and rank the n ≥ 30 weeks first.
3. **(Med, F3)** Define the month edge: weeks are set by auth date, and a week counts for the month that holds its Thursday. Put this in one shared function.
4. **(Med, F4)** Rename the "$50" page to "Outliers": min-$ filter default 50, a "why flagged" column (> $50 or z > 3.5), and a CSV download.
5. **(Med, F5)** Reword row 8. The brief allows a CLI report tool, and `recon` covers it.
6. **(Med, F6)** Say that the dashboard reads marts, `alerts.jsonl` and `RECOMMENDATIONS.md` through the shared `core` package that `recon` also uses. Add a test that the CLI and the dashboard give the same answer.
