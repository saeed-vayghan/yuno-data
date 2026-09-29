# 03 · Page: Overview

**Goal:** answer "How bad is it, is it getting better, and which PSP had the worst week last month?" on the landing page. Brief question 1 in 0–1 clicks.

**Time box:** 15 min · **Tag:** Core

## Inputs
- File 01 shell, file 02 wrappers + guard + formatters.
- Core: `status()`, `kpis(filters, week="last_closed")`, `worst_week(month)`, `weekly_trend(filters, by)`, `week_over_week(filters)`, `load_alerts()`, `filter_options()["months"]`.
- Engineer: `recon worst-week --month last --format json` (for the test in file 09).

## Rules (from FINAL-SOLUTION §5)
- Week = ISO week (Mon–Sun) by **auth date**. A week belongs to the month of its **Thursday**.
- "Last month" = last **full** calendar month in the data (June 2026 for data Apr 1–Jun 30).
- Worst week = PSP-week ranked by **net USD loss** (under − over). Gross under-settled shown beside it.
- PSP-weeks with **n < 30**: shown greyed, labelled "low sample", ranked last. The card is never empty.
- KPIs use the **last closed week** (week end ≤ as-of − 7 days), compared with the closed week before.

## Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Overview            Data as of 2026-06-30 · Last closed week W25 (Jun 15–21)
│ Active: PSP all · Country all        (date range not used here)           │
├──────────────┬──────────────┬──────────────┬─────────────────────────────┤
│ Flag rate    │ Net loss     │ Large rows   │ Open alerts                 │
│ 14.2%        │ $9,840       │ 212          │ 3 (1 SEV2)   → Alerts       │
│ ▲ +1.1 pts   │ ▲ +$1,200    │ ▼ −8         │                             │
├──────────────┴──────────────┴──────────────┴─────────────────────────────┤
│ Worst PSP week · Month [ 2026-06 ▾ ]                                     │
│ PSP_B · W24 (Jun 8–14) · Net loss $4,210 · Gross under $4,900            │
│ Flag rate 21.3% · n = 812            [Open PSP_B · W24 in Drill-down →]  │
│ Next: PSP_C W25 $3,050 · PSP_D W23 $2,870 · ░PSP_E W26 $900 low sample░  │
├──────────────────────────────────────────────────────────────────────────┤
│ Weekly flag rate (%)       ( Portfolio | By PSP )                         │
│  line chart; open weeks dashed + "not closed yet"                        │
├──────────────────────────────────────────────────────────────────────────┤
│ Weekly net loss (USD)      bar chart                                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Week-over-week: W25 vs W24, PSP × country, biggest rise first            │
│ PSP_C · MX   12.0% → 15.4%   ▲ +3.4 pts   n 1,204                         │
└──────────────────────────────────────────────────────────────────────────┘
```
(Numbers are illustrative.)

## Steps

1. **Header.** `layout.page_header("Overview", uses={"country", "psp"})`. The date filter is ignored here; the line says so.

2. **KPI row** (`st.columns(4)`):
   ```python
   k = data.get_kpis(f, week="last_closed")      # has prev_week, delta_rate_pts, delta_net_usd, delta_n_large
   st.metric("Flag rate", fmt.rate(k["flag_rate"]),
             delta=fmt.delta_pts(k["delta_rate_pts"]),
             delta_color="inverse", help="Share of settled rows with a meaningful or large discrepancy after FX.")
   ```
   - Net loss: `fmt.usd_compact(k["net_usd"])`, delta `k["delta_net_usd"]` in $, `delta_color="inverse"` (more loss = red + ▲).
   - Large rows: `k["n_large"]`, delta `k["delta_n_large"]` as integer.
   - Open alerts: count of `load_alerts()` rows with status NEW or ONGOING (not Info), "(1 SEV2)" in the value; `st.page_link(PAGES["alerts"], label="→ Alerts")`. If the file is missing: value "—", caption "Run `recon alerts`".
   - Every metric has `help=` with a one-sentence definition.

3. **Worst-week card** (`st.container(border=True)`):
   - Month picker: `st.selectbox("Month", options=filter_options()["months"], index=last)`. Default = last full month. Label it "Month (week belongs to the month of its Thursday)" in `help=`.
   - `ww = data.get_worst_week(month)`. **Ignore sidebar filters** here, so the card equals `recon worst-week`.
   - Line 1: top row: PSP · `week_label` · Net loss · Gross under.
   - Line 2: flag rate · n.
   - Line 3 ("Next"): ranks 2–4, low-sample ones in grey text with "low sample (n<30)".
   - If the top row is itself low sample: still show it, greyed, with "low sample" — never an empty card.
   - Button "Open PSP_B · W24 in Drill-down →": `filters.set_handoff(psp=(psp,), date_from=week_start, date_to=week_end)` then `st.switch_page(PAGES["drill_down"])`.
   - Optional: `st.expander("All PSP-weeks this month")` with the full ranked table (same DataFrame).

   **Decision (card and filters):** 🎨 Mani: users expect the sidebar PSP filter to change the card. 🏛️ Jamshid: then the card would disagree with `recon worst-week`, and the brief asks a portfolio question. → Card ignores sidebar filters; a caption says "All PSPs and countries (same as `recon worst-week`)".

4. **Weekly flag-rate trend** (Plotly line):
   - `st.segmented_control` (or `st.radio(horizontal=True)`) "Portfolio | By PSP".
   - x = `week_start`, y = `rate`. Closed weeks solid; `is_closed == False` weeks dashed/lighter with annotation "not closed yet".
   - By PSP: one line per `series` value, PSP colours from `theme.PSP_COLORS` + direct labels at line ends (not only a legend).
   - Title "Weekly flag rate (%)". Caption under it: one line takeaway from data, e.g. "Highest closed week: W24 at 16.1%."

5. **Weekly net loss** (Plotly bar): y = `net_usd`, vermilion bars, same open-week style. Separate chart; no dual axis.

6. **Week-over-week table** (`st.dataframe`):
   - Columns: PSP, Country, `rate_prev` (header = `week_prev`, e.g. W24), `rate_last` (header = `week_last`, e.g. W25), Change (`delta_pts`) with ▲/▼ text, `n_last`.
   - Sorted by `delta_pts` desc. Rows with `low_sample` get "low sample" in a note column.
   - `column_config.NumberColumn` for rates (format `%.1f%%` on ×100 values) so sort works.

7. Wrap the body in `data.guarded(render)`.

## Done when
- [ ] Card (month = last) shows the same PSP, week and net USD as `recon worst-week --month last --format json` (test 4).
- [ ] Changing the month updates the card; the list of months holds only full months.
- [ ] On the 500-row fixture every PSP-week is low sample, and the card still shows the top one, greyed, labelled.
- [ ] KPI deltas show ▲/▼ + sign + "pts", not colour alone.
- [ ] Open weeks are dashed and labelled "not closed yet".
- [ ] "Open in Drill-down" lands on Drill-down with PSP and dates set.
- [ ] Missing `alerts.jsonl` → Alerts KPI shows "—" and a hint, page does not fail.

## Serves
FR3: "visualize trends over time", "week-over-week", acceptance question "Which PSP had the worst week last month?"; Flows A and F; UI-UX build step 6; rubric Stretch 10 (≤ 2 clicks).

## Pitfalls
- Using the calendar month of the week's Monday: a week like Jun 29–Jul 5 belongs to **July** (Thursday Jul 2), so it is not in June.
- Ranking by gross instead of net, or by rate: the rule is net USD loss.
- Hiding low-sample weeks: they must show, greyed and last.
- KPI of the open week: it is half-settled and looks better than it is. Always last closed week.
- `delta_color="normal"` makes a rise in loss look green. Use `"inverse"`.

## Hand-off
Brief question 1 answered. Next in build order: `04-page-drilldown.md` (filters + table only), then file 10's first draft.
