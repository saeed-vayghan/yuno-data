# UI/UX Plan: CasaMarket Monitoring Dashboard

## Scope & rules (5 lines)
1. Serves FR3 (dashboard + alerts) and stretch 4 (recommendations "included in your dashboard"). Source of truth: [scenario.md](../../architect/00-scenario/scenario.md); stack and rules follow [FINAL-SOLUTION.md](../../orchestrator/01-research/FINAL-SOLUTION.md).
2. Streamlit + Plotly on `localhost:8501` (`make app` / `recon dashboard`). No other frontend framework, no custom JS components, no auth.
3. Exactly 5 pages: Overview · Drill-down · Outliers · Root causes & actions · Alerts.
4. No logic in the UI: pages call the shared `casarecon.core` functions (same as the CLI). Pages only lay out, format and label.
5. Acceptance target: both brief questions answered in ≤ 2 clicks. Scale path (docs only): the same marts on StarRocks behind Superset.

## Discussion highlights (🏛️ Jamshid vs 🎨 Mani)

| # | Who | Point |
|---|---|---|
| 1 | 🎨 Mani | Start from the two brief questions. Each must be answered in ≤ 2 clicks: the worst-week card on the landing page, and the Outliers page opening at "over $50". |
| 2 | 🏛️ Jamshid | Agreed, but both answers must come from `core.worst_week()` and `core.query_transactions()`, the same functions `recon worst-week` and `recon query` call. One test proves they match. |
| 3 | 🎨 Mani | Users will read "discrepancy over $50" as settled minus authorized. A cross-border row that moved only with FX will look "missing". |
| 4 | 🏛️ Jamshid | The filter must use the residual after the expected FX move; FX-only moves are not losses. 🎨 Mani: then label it "Discrepancy after FX (USD)", show the raw difference as a second column, and add a one-line caption. **Agreed.** |
| 5 | 🎨 Mani | "$" is ambiguous: MXN, COP, ARS and CLP all use "$". |
| 6 | 🏛️ Jamshid | All comparisons in USD (auth-day rate). Local amounts only on row views, with the ISO code (`CLP 12,345`) and decimals taken from the currency-exponent seed, so CLP has none. **Agreed.** |
| 7 | 🎨 Mani | I want colour for categories and severity. 🏛️ Jamshid: colour must never carry meaning alone. **Agreed:** Okabe-Ito palette + icon + word on every badge; heatmap cells carry their value. |
| 8 | 🏛️ Jamshid | No 135k rows in pandas. Filtered aggregates run in DuckDB via core; tables cap at 1,000 rows; CSV has all. 🎨 Mani: then say so: "Showing 1,000 of 12,345. Download CSV for all." **Agreed.** |
| 9 | 🎨 Mani | An analyst needs a "why is this row flagged" panel. 🏛️ Jamshid: use built-in `st.dataframe` row selection, no custom component; "similar rows" is a link to Drill-down with filters set. **Agreed.** |
| 10 | Both | Mask customer IDs in core (UI and CSV match); keep `txn_id` whole, since PSP ops need it to raise a dispute. Low-sample weeks are never hidden: greyed, labelled, ranked last. **Plan agreed.** |

## Users & jobs

| User | Job to be done | Key question | Main page | How often |
|---|---|---|---|---|
| Ops analyst (CasaMarket) | Triage and investigate problem transactions | "Which rows need a look today, and why were they flagged?" | Outliers → Drill-down | Daily |
| PSP ops / partner manager | Hold each PSP to account with evidence | "Which PSP had the worst week last month? Is it still bad?" | Overview (card) → Alerts | Weekly |
| Finance / CFO | Know the size of the leak and whether it is shrinking | "How much did we lose, is it better week-over-week, what do we do?" | Overview → Root causes & actions | Weekly / monthly |
| Reviewer / data engineer | Check the tool answers the brief and matches the CLI | "Do the dashboard and `recon` agree?" | All | Once per build |

## User flows

**Flow A: "Which PSP had the worst week last month?"** (1 click)
1. Open `localhost:8501`. Overview loads.
2. Read the worst-week card: PSP, ISO week and dates, net USD loss, gross under-settled, rate, n.
3. (Optional) Change the month in the card's month picker (default "last full month").
4. (Optional) Click "Open in Drill-down" → Drill-down opens with `psp` and `week` set.

**Flow B: "Show me all transactions with discrepancies over $50"** (1 click)
1. Click **Outliers** in the sidebar.
2. The table already shows rows with discrepancy after FX ≥ $50 (USD), sorted largest first.
3. Search, sort, or change the minimum.
4. Click "Download CSV". The file holds all matching rows, with masked customer IDs.

**Flow C: Investigate an outlier**
1. On Outliers, click a row. The detail panel opens below the table.
2. Read: authorized, expected, settled (local + USD), FX move, lag, likely cause, and why flagged (> 5% or ≥ $20).
3. Read "Similar rows: 142 in PSP_D · Chile · psp_rounding".
4. Click "See similar rows" → Drill-down with PSP, country and cause filters set.
5. Copy `txn_id` or download CSV to raise a ticket with the PSP.

**Flow D: Read alerts**
1. Overview shows "3 open alerts (1 SEV2)". Click it, or click **Alerts**.
2. The table lists alerts for the last closed week: severity, status (NEW / ONGOING / RESOLVED), rule, segment, plain message, owner.
3. Filter by severity or status. "Insufficient data" rows sit in a closed expander at the bottom.
4. Click "View segment" → Drill-down with that PSP × country set.

**Flow E: Read recommendations**
1. Click **Root causes & actions**.
2. Read the cause chart ($ impact, largest first) and the PSP × country heatmap.
3. Read the 3–5 ranked recommendations (from `RECOMMENDATIONS.md`): action, evidence, $ impact, owner.
4. Pick a cause in "Drill into cause" and click Go → Drill-down with that cause set.

**Flow F: Is it getting better or worse?**
1. On Overview, read the KPI deltas (▲ worse / ▼ better, in pts) for the last closed week.
2. Read the weekly trend. The open week is drawn dashed and labelled "not closed yet".
3. Read the week-over-week table (PSP × country, sorted by the biggest rise).

## Information architecture

```
Sidebar (st.navigation)                 Top of every page
├── 📊 Overview      (default, /)        Data as of 2026-08-31 · last closed week: W34 (Aug 17–23)
├── 🔎 Drill-down    (/drill-down)       Active filters: PSP_B × AR  [Clear filters]
├── 🚩 Outliers      (/outliers)
├── 🧭 Root causes & actions (/root-causes)
└── 🔔 Alerts        (/alerts)
Sidebar bottom: shared filters (on pages that use them)
```

- Navigation: `st.navigation` + `st.Page` with fixed `url_path`, so every page has a stable link.
- Cross-page links: `st.page_link` / `st.switch_page` carry filters (see Filters & state).
- No extra pages. Help text lives in `help=` tooltips and short captions, not a help page.

### Filters & state

| Param | Values | Used on |
|---|---|---|
| `country` | MX, CO, AR, CL (multi) | Overview, Drill-down, Outliers, Root causes |
| `psp` | PSP_A…PSP_E (multi) | Overview, Drill-down, Outliers, Root causes |
| `tier` | 10-50, 50-200, 200+ (multi) | Drill-down, Outliers |
| `xb` | all / cross / domestic | Drill-down, Outliers |
| `weekday` | Mon…Sun (multi) | Drill-down |
| `category` | exact…large (multi) | Drill-down |
| `cause` | fx_timing…unexplained (multi) | Drill-down, Outliers |
| `week` | ISO week, e.g. 2026-W20 | Drill-down, Outliers |
| `from`, `to` | ISO dates (auth date) | Drill-down, Outliers |
| `min_usd` | number, default 50 | Outliers |
| `month` | YYYY-MM, default last full month | Overview card |
| `sev`, `status` | SEV2/SEV3/Info · NEW/ONGOING/RESOLVED | Alerts |

Rules:
- One `Filters` dataclass in `dashboard/filters.py`. It reads `st.query_params`, validates values against allowed lists, and writes back on change. Bad values are dropped with a small warning ("Ignored unknown PSP 'PSP_Z'").
- Pages pass `Filters` to core. Core builds parameterized SQL. Pages never write SQL.
- Filters live in the URL, so a link can be shared or bookmarked. `st.session_state` keeps them when switching pages.
- Defaults are empty (= all). Only non-default values go in the URL, to keep links short.
- Every page shows an "Active filters" line and one **Clear filters** button.
- A page ignores filters it does not use, and says so in the line ("PSP filter applies; tier filter not used here").

## Pages

### 1. Overview
**Purpose:** "How bad is it, is it getting better, and which PSP had the worst week?" Answers brief Q1 and "week-over-week".

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Overview                     Data as of 2026-08-31 · Last closed week W34 │
├──────────────┬──────────────┬──────────────┬─────────────────────────────┤
│ Flag rate    │ Net loss     │ Large rows   │ Open alerts                 │
│ 14.2%        │ $9,840       │ 212          │ 3  (1 SEV2)  → Alerts       │
│ ▲ +1.1 pts   │ ▲ +$1,200    │ ▼ −8         │                             │
├──────────────┴──────────────┴──────────────┴─────────────────────────────┤
│ WORST PSP WEEK · [ July 2026 ▾ ]                                         │
│ PSP_B · W29 (Jul 13–19) · Net loss $4,210 · Gross under $4,900           │
│ Flag rate 21.3% · n = 812                          [Open in Drill-down →] │
│ Next: PSP_C W30 $3,050 · PSP_D W28 $2,870 · ░PSP_E W27 $900 low sample░  │
├──────────────────────────────────────────────────────────────────────────┤
│ Weekly flag rate            [Portfolio | By PSP]                          │
│  %│   ___/\__/‾‾\__ _ _ (dashed = not closed yet)                         │
│   └──────────────────────────── ISO week                                 │
├──────────────────────────────────────────────────────────────────────────┤
│ Weekly net loss (USD) — bars                                             │
├──────────────────────────────────────────────────────────────────────────┤
│ Week-over-week (W34 vs W33), PSP × country, biggest rise first           │
│ PSP_C · MX  12.0% → 15.4%  ▲ +3.4 pts   n 1,204                          │
└──────────────────────────────────────────────────────────────────────────┘
```

| Component | Streamlit | Source (core fn → mart) |
|---|---|---|
| As-of banner | `st.caption` | `core.status()` → `fct_transaction_discrepancy` (max ts), closed-week rule |
| 4 KPIs + deltas | `st.metric(delta_color="inverse")` | `core.kpis(filters, week="last_closed")` → `mart_psp_weekly` |
| Open alerts KPI | `st.metric` + `st.page_link` | `core.load_alerts()` → `reports/alerts.jsonl` |
| Worst-week card | `st.container(border=True)`, `st.selectbox` month | `core.worst_week(month)` → `mart_psp_weekly` (shared with `recon worst-week`) |
| Weekly flag-rate trend | Plotly line | `core.weekly_trend(filters, by)` → `mart_psp_weekly` |
| Weekly net loss | Plotly bar | `core.weekly_trend(...)` → `mart_psp_weekly` |
| Week-over-week table | `st.dataframe` | `core.week_over_week(filters)` → `mart_psp_weekly` |

States: no DB → "Run `make all` first" · locked → "Rebuilding, retry" · worst-week with only low-sample weeks → card still shows the top one, greyed, with "low sample" · no alerts file → Alerts KPI shows "—" with "Run `recon alerts`".

### 2. Drill-down
**Purpose:** slice by segment and see rates with ranges, then the rows behind them.

```
┌ Sidebar filters ┐┌──────────────────────────────────────────────────────┐
│ Country  [MX..] ││ Drill-down        Active: PSP_B · AR   [Clear filters]│
│ PSP      [..]   │├──────────────┬──────────────┬─────────────────────────┤
│ Size tier[..]   ││ Rows 8,410   │ Flag rate    │ Net loss $12,300        │
│ Cross-border ◉  ││              │ 17.9%        │                         │
│ Weekday  [..]   │├──────────────┴──────────────┴─────────────────────────┤
│ Category [..]   ││ Group by: [Country|PSP|Size tier|Weekday|Cross-border│
│ Cause    [..]   ││            |Settle lag]                               │
│ Auth dates [..] ││ Flag rate by <group>, with 95% range  (horizontal bar)│
└─────────────────┘│ ▇▇▇▇▇▇▇▇▇▇▇▇ PSP_B  21.3% [19.8–22.9] n 3,020         │
                   │ ▇▇▇▇▇▇▇     PSP_A  12.1% ...                         │
                   ├───────────────────────────────────────────────────────┤
                   │ Category mix by week (100% stacked bar)               │
                   ├───────────────────────────────────────────────────────┤
                   │ Transactions (showing 1,000 of 8,410, largest first) │
                   │ [search] txn_id | date | PSP | country | category |  │
                   │ cause | disc. after FX (USD) | raw diff | lag       │
                   │                                  [Download CSV]      │
                   └───────────────────────────────────────────────────────┘
```

| Component | Streamlit | Source |
|---|---|---|
| Filter widgets | `st.multiselect`, `st.radio`, `st.date_input` in sidebar | `dashboard/filters.py`; option lists from `core.filter_options()` |
| Summary KPIs | `st.metric` | `core.kpis(filters)` → `fct_transaction_discrepancy` |
| Rate by group + Wilson range | Plotly bar with error bars | `core.segment_rates(dim, filters)`; unfiltered → `mart_segment_rates`, filtered → aggregate on `fct_transaction_discrepancy` |
| Category mix by week | Plotly 100% stacked bar | `core.category_mix(filters)` → `fct_transaction_discrepancy` |
| Transaction table | `st.dataframe` + `column_config` | `core.query_transactions(filters, limit=1000)` |
| CSV download | `st.download_button` | same function, no limit |

States: no rows → "No transactions match these filters." + Clear filters · group with n < 30 → greyed bar, "low sample" label, no range drawn.

### 3. Outliers
**Purpose:** "Show me all transactions with discrepancies over $50" and the start of every investigation.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Outliers                                                                 │
│ Min discrepancy after FX (USD): [ 50 ]   Country [..] PSP [..] Cause [..]│
│ ⓘ Discrepancy = settled minus expected settle (FX move removed), in USD.│
│ 1,284 transactions · total $148,210 under · $3,020 over    [Download CSV]│
├──────────────────────────────────────────────────────────────────────────┤
│ txn_id      | auth date | PSP  | ctry | disc. after FX | raw diff  |     │
│ customer    | why flagged        | likely cause  | lag (d)              │
│ T-00A91F3C  | 2026-07-14| PSP_D| CL   | −$62.10 under  | CLP −58,000|    │
│ cus_••••7f3a| ≥ $20 and > 5%     | psp_rounding  | 3                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ▼ Selected: T-00A91F3C                                                   │
│  Authorized  CLP 1,058,000 ($1,128.40)   Expected CLP 1,058,000           │
│  Settled     CLP 1,000,000 ($1,066.30)   FX move 0.0% (domestic)          │
│  Lag 3 days · Weekend: no · Items 2 · Risk score 0.12                     │
│  Why flagged: residual −5.5% (> 5%) and −$62.10 (≥ $20)                   │
│  Likely cause: psp_rounding (settled is a multiple of 1,000, below exp.) │
│  Similar rows: 142 in PSP_D · CL · psp_rounding  [See similar rows →]     │
└──────────────────────────────────────────────────────────────────────────┘
```

| Component | Streamlit | Source |
|---|---|---|
| Min-$ input (default 50) | `st.number_input(min_value=0, step=10)` | `Filters.min_usd` |
| Summary line | `st.markdown` | `core.outlier_summary(filters)` → `mart_outliers` |
| Outlier table | `st.dataframe(on_select="rerun", selection_mode="single-row")` | `core.query_transactions(filters, min_usd=…)` → `mart_outliers` (same as `recon query --min-usd 50`) |
| Detail panel | `st.container(border=True)` | `core.transaction_detail(txn_id)` → `fct_transaction_discrepancy` |
| Similar rows | `st.page_link` with filters | `core.similar_count(txn_id)` |
| CSV download | `st.download_button` | same query, all rows, masked customer IDs |

Notes:
- Every row with |residual| ≥ $50 is `large` by rule (≥ $20), so "over $50" is always a subset of outliers. Setting min to 0 shows all `large` rows.
- "Why flagged" text comes from core, not built in the page.

States: min too high → "No transactions over $5,000. Try a lower minimum." · no row selected → "Select a row to see why it was flagged."

### 4. Root causes & actions
**Purpose:** "What is driving the loss, and what should we do?" Shows FR2 results and the FR4 recommendations in the dashboard.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Root causes & actions                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Loss by likely cause (USD, last full quarter in data), largest first     │
│ partial_capture ▇▇▇▇▇▇▇▇▇▇▇ $41,200  32%                                 │
│ fraud_hold      ▇▇▇▇▇▇▇     $27,900  22%                                 │
│ ... tip: ruled out (0 rows)                                              │
│ Drill into cause: [ select ▾ ] [Go →]                                    │
├───────────────────────────────────┬──────────────────────────────────────┤
│ Flag rate PSP × country (heatmap) │ Excess loss vs peers (top 5 segments)│
│        MX    CO    AR    CL       │ PSP_B·AR  $18,400 (median $…)        │
│ PSP_A 12.0  11.8  12.4  11.9      │ ...                                  │
│ PSP_B 12.1  12.3 ▓15.9▓ 12.0      │                                      │
├───────────────────────────────────┴──────────────────────────────────────┤
│ Recommendations (ranked by $ impact)                                     │
│ R1 Escalate PSP_B Argentina variance · Evidence F2 · ~$18k/qtr · PSP ops │
│   ▸ How to implement                                                     │
│ R2 ...                                                                   │
│ ▸ Full findings (FINDINGS.md)                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

| Component | Streamlit | Source |
|---|---|---|
| Loss by cause | Plotly horizontal bar | `core.cause_summary(filters)` → `mart_cause_summary` |
| Drill into cause | `st.selectbox` + `st.page_link` | option list from `mart_cause_summary` |
| PSP × country heatmap | Plotly heatmap, values printed in cells | `core.segment_rates("psp_country")` → `mart_segment_rates` |
| Excess loss vs peers | `st.dataframe` | `core.excess_loss()` → `mart_segment_rates` |
| Recommendations | `st.markdown` per item + `st.expander` | `core.load_recommendations()` → `reports/RECOMMENDATIONS.md` |
| Full findings | `st.expander` + `st.markdown` | `core.load_findings()` → `reports/FINDINGS.md` |

States: missing report files → "Recommendations are not built yet. Run `make all`." · heatmap cell n < 30 → hatched grey, "n<30".

### 5. Alerts
**Purpose:** "What needs attention this week, and who owns it?"

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Alerts · last closed week W34 (Aug 17–23)                                │
│ ▲ SEV2 · same day: 1   ● SEV3 · weekly: 2   ℹ Info: 4   ✓ Resolved: 1    │
│ Severity [..]  Status [..]  Rule [..]                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ▲ SEV2 | NEW      | Peer   | PSP_B · AR | PSP_B flags 17.9% of AR rows  │
│        |          |        |            | vs 12.1% for other PSPs      │
│        |          |        |            | (+5.8 pts). Owner: PSP ops   │
│        |          |        |            |              [View segment →] │
│ ● SEV3 | ONGOING  | Change | PSP_C · MX | ...                           │
├──────────────────────────────────────────────────────────────────────────┤
│ ▸ Insufficient data (4)   ▸ What each rule means                         │
└──────────────────────────────────────────────────────────────────────────┘
```

| Component | Streamlit | Source |
|---|---|---|
| Severity counts | `st.columns` + `st.metric` | `core.load_alerts()` → `reports/alerts.jsonl` |
| Alert table | `st.dataframe` (badge text columns) | same |
| View segment | `st.page_link` with `psp`, `country` | alert `segment` field |
| Insufficient data | `st.expander` (closed) | rows with status "insufficient data" |
| Rule help | `st.expander` | static text, one line per rule (from 07) |

States: no alerts → "No alerts for W34. All 6 rules checked." · all insufficient (500-row run) → "Not enough data for alerts (each needs 50 rows per week). Run the full dataset." · file missing → "Run `recon alerts` or `make all` first."

## Visual system

### Theme (`.streamlit/config.toml`)
```toml
[theme]
base = "light"
primaryColor = "#0072B2"          # Okabe-Ito blue: links, buttons, focus
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F3F5F7"
textColor = "#1F2328"
font = "sans serif"

[server]
address = "localhost"
headless = true

[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
showErrorDetails = false          # friendly messages; details go to the terminal log
```
- Light theme only (one theme to test). Plotly uses one shared template in `dashboard/theme.py` (font, grid, colours, hover format).
- No custom CSS by default. If one is truly needed, it is one short, reviewed `st.markdown` style block.

### Colours (Okabe-Ito, colourblind-safe; never colour alone)

| Use | Value | Colour | Always paired with |
|---|---|---|---|
| Category `exact` | Exact match | `#8C8C8C` grey | Label "Exact" |
| Category `rounding` | ≤ 1 minor unit | `#56B4E9` sky blue | Label "Rounding" |
| Category `fx_tolerance` | FX noise ≤ 2% | `#0072B2` blue | Label "FX noise" |
| Category `meaningful` | 2–5%, < $20 | `#E69F00` orange | Label "Meaningful" |
| Category `large` | > 5% or ≥ $20 | `#D55E00` vermilion | Label "Large" |
| Severity SEV2 | Same day | `#D55E00` | "▲ SEV2 · same day" |
| Severity SEV3 | Weekly review | `#E69F00` (dark text) | "● SEV3 · weekly" |
| Info / insufficient data | Report only | `#0072B2` | "ℹ Info" |
| Status RESOLVED | Better | `#009E73` green | "✓ Resolved" |
| Direction under / over | Loss / gain | `#D55E00` / `#0072B2` | "under" / "over" + sign |
| Low sample | n < 30 | 40% opacity grey | "low sample (n<30)" |
| PSPs A–E (series charts only) | — | `#0072B2 #E69F00 #009E73 #CC79A7 #56B4E9` | Legend + direct labels |
| Heatmap | Rate | Plotly "Oranges" (single hue, light→dark) | Value in each cell |

- Rule: category colours and PSP colours never appear in the same chart.
- Text on orange uses dark text (`#1F2328`); white only on blue/vermilion (contrast ≥ 4.5:1).
- Status NEW / ONGOING are plain text, bold for NEW. Meaning is in the word.

### Typography
- Streamlit default sans serif. Sentence case for titles ("Weekly flag rate", not "WEEKLY FLAG RATE").
- One `st.title` per page, `st.subheader` per section, `st.caption` for "what this means".
- Numbers right-aligned in tables (`column_config.NumberColumn`).

### Number and currency formats
All formatters live in `dashboard/format.py` (pure, unit-tested). The currency exponent comes from core (seed), never hard-coded in a page.

| Kind | Format | Example |
|---|---|---|
| USD amount | `$` + thousands + 2 dp | `$1,234.56` |
| USD in KPIs / cards | compact | `$127.4k` |
| USD signed | minus sign + word | `−$62.10 under`, `+$4.00 over` |
| Local amount | ISO code + exponent dp | `MXN 1,234.56` · `COP 123,456.78` · `ARS 9,870.00` · `CLP 12,345` (no decimals) |
| Rate | 1 dp % | `14.2%` |
| Rate change | pts, signed, arrow | `▲ +1.1 pts` (worse), `▼ −0.4 pts` (better) |
| Range | brackets | `21.3% [19.8–22.9]` |
| Count | thousands | `12,345` |
| Date | ISO | `2026-07-14` |
| Week | ISO + dates | `W29 (Jul 13–19)` |
| Lag | days, 1 dp in detail, integer in tables | `3.4 days` / `3` |

- USD everywhere for comparisons (auth-day rate). Local amounts only in row tables and the detail panel.
- Never show a bare "$" next to a local amount.

### Chart rules
| Rule | Detail |
|---|---|
| Trend over time | Line (rate) and bar (USD). Separate charts; no dual axes. |
| Ranking | Horizontal bar, sorted, value label on each bar. Bars start at 0. |
| Uncertainty | Wilson 95% range as error bars on rate bars; hidden for n < 30. |
| Two-way comparison | Heatmap (PSP × country) with value in every cell. |
| Mix over time | 100% stacked bar, category order exact → large. |
| Open week | Dashed / lighter, labelled "not closed yet". |
| Not used | Pie, donut, 3D, gauges, dual axes. |
| Titles | Plain, say what is shown and the unit ("Weekly flag rate (%)"). |
| Hover | Formatted with the same formatters; includes n. |
| Size | `use_container_width=True`; height ≤ 400 px; toolbar minimal. |
| Alt text | A one-line `st.caption` under each chart stating the main takeaway (from core data, not hand-typed). |

## States & microcopy

| State | When | What the user sees | Component |
|---|---|---|---|
| No database | `data/casarecon.duckdb` missing | "No data yet. Run `make all` first, then reload this page." | `st.info` + `st.stop()` |
| Rebuilding | DuckDB file locked by a build | "The data is being rebuilt. Retry in a minute." + [Retry] | `st.warning` + `st.button` (reruns) |
| Loading | Query running (cache miss) | "Loading…" | `st.spinner` |
| Error | Any other exception | "Something went wrong loading this view. The details are in the terminal." | `st.error`; traceback logged, not shown |
| Empty result | Filters match nothing | "No transactions match these filters." + [Clear filters] | `st.info` |
| Low sample | n < 30 in a week/segment | Greyed item with "low sample (n<30)"; ranked last; never hidden | table/chart style |
| Insufficient data | Alert n < 50 | "Not enough data (needs 50 rows per week)." | Alerts expander |
| Reports missing | `RECOMMENDATIONS.md` / `alerts.jsonl` absent | "Not built yet. Run `make all`." | `st.info` |
| Table capped | > 1,000 rows | "Showing 1,000 of 12,345, largest first. Download CSV for all." | `st.caption` |
| No selection | Outliers, no row picked | "Select a row to see why it was flagged." | `st.caption` |
| Open week | Current week not closed | "not closed yet" label on chart | chart annotation |
| Bad URL param | Unknown value | "Ignored unknown PSP 'PSP_Z'." | `st.toast` |

Microcopy rules:
- Plain words: "flag rate", "discrepancy after FX", "under-settled" (with `help=` tooltip), not "residual" in labels.
- Every KPI has a `help=` tooltip with its definition in one sentence.
- Say what to do next in every empty or error state.

### Privacy
- Customer IDs masked in core: `cus_••••7f3a` (last 4 kept), in the UI and in CSV. The CLI uses the same function.
- `txn_id` shown in full (needed for PSP disputes; not personal data). No PAN exists anywhere.
- CSV file name: `casamarket_outliers_min50usd_2026-08-31.csv` (filters + as-of).

## Accessibility checklist
- [ ] No meaning by colour alone: every colour has a word, icon or sign next to it.
- [ ] Okabe-Ito palette; checked in a CVD simulator (protan, deutan, tritan).
- [ ] Text contrast ≥ 4.5:1, including badges (dark text on orange).
- [ ] Every chart has a title with units and a one-line caption with the takeaway.
- [ ] Every chart's data is also available as a table or CSV.
- [ ] All controls have visible labels (no `label_visibility="collapsed"`).
- [ ] Keyboard: sidebar, filters, table, buttons and download reachable by Tab; focus visible.
- [ ] Page usable at 200% zoom and 1280 px width without horizontal page scroll (wide tables scroll inside).
- [ ] Arrows plus signs for change (▲ +1.1 pts), not only red/green.
- [ ] Plain English; abbreviations (SEV2, n, pts, FX) explained in tooltips.
- [ ] No motion or auto-refresh.

## Build order
Prerequisite: marts built and core functions (`worst_week`, `query_transactions`, `kpis`, `weekly_trend`, `segment_rates`, `cause_summary`, `load_alerts`, `load_recommendations`, `mask_id`) exist with pytest coverage.

| # | Step | Done when |
|---|---|---|
| 1 | App shell: `dashboard/app.py` with `st.navigation`, 5 empty pages, `.streamlit/config.toml`, `make app` | `make app` opens 5 pages on `localhost:8501`; bound to localhost |
| 2 | Data guard: DB missing / locked / error wrapper; as-of banner | AppTest shows "Run `make all` first" with no DB and "Rebuilding" when core raises the lock error |
| 3 | `format.py` + `theme.py` (formatters, colours, Plotly template) | Unit tests pass: `CLP 12,345`, `MXN 1,234.56`, `−$62.10 under`, `▲ +1.1 pts` |
| 4 | `filters.py`: `Filters` dataclass ↔ `st.query_params`, Clear filters, active-filter line | AppTest: query params set → widgets preset; bad value dropped with toast |
| 5 | Outliers page (brief Q2) incl. detail panel and CSV | Opens at min $50; row set equals `recon query --min-usd 50`; CSV masked |
| 6 | Overview (brief Q1): KPIs, worst-week card, trend, WoW | Card equals `recon worst-week --month last`; low-sample greyed; link opens Drill-down with filters |
| 7 | Drill-down: filters, group-by chart with ranges, mix chart, table | Every filter narrows the table; empty state shows; cap message shows > 1,000 |
| 8 | Alerts page | Severity counts match `alerts.jsonl`; 500-row run shows "not enough data" |
| 9 | Root causes & actions | Cause bars sum to total loss; 3–5 recommendations render; missing file message shows |
| 10 | CLI ↔ UI consistency test + full AppTest suite in `make test` | `make test` green on the fixture DB |
| 11 | Polish: microcopy pass, accessibility checklist, 2 README screenshots (card, Outliers) | Checklist ticked; both brief questions answered in ≤ 2 clicks by someone new |

## UI test plan
Tests use `streamlit.testing.v1.AppTest` on a small fixture DuckDB (built once per session from the 500-row seed), plus pure pytest for formatters.

| # | Test | Check |
|---|---|---|
| 1 | Smoke | Each of the 5 pages runs with no exception (`at.exception` empty) |
| 2 | No DB | Point the app at a missing path → info text contains "Run `make all` first" |
| 3 | Locked DB | Monkeypatch core to raise the DuckDB lock error → "being rebuilt" text + Retry button |
| 4 | Worst week (CLI ↔ UI) | `CliRunner` runs `recon worst-week --month last --format json`; its PSP, week and net USD equal `core.worst_week()` and the Overview card text |
| 5 | Over $50 (CLI ↔ UI) | Set of `txn_id` from `recon query --min-usd 50 --format csv` equals the Outliers dataframe and its CSV bytes |
| 6 | Default filter | Outliers `number_input` value = 50; every row has |disc. after FX| ≥ 50 |
| 7 | Filter change | Set min to 100 and PSP = PSP_B → all rows match both |
| 8 | URL params | `at.query_params["psp"] = "PSP_B"` → Drill-down multiselect preset; unknown value dropped |
| 9 | Empty state | Filters with no match → "No transactions match these filters." |
| 10 | Low sample | Fixture week with n < 30 → card/table shows "low sample" and ranks it last |
| 11 | Masking | No full customer ID appears in any dataframe or CSV |
| 12 | Currency format | CLP rows show no decimals; USD columns have 2 dp |
| 13 | Alerts | Counts per severity match `alerts.jsonl`; smoke-run fixture → "not enough data" message |
| 14 | Recommendations | 3–5 items render; missing file → "Not built yet" message |
| 15 | Formatters (pytest) | Table-driven cases for every row in the number-format table |

Manual checks before hand-in: CVD simulator pass, keyboard-only pass, 200% zoom, and a timed run of both brief questions (≤ 2 clicks each).
