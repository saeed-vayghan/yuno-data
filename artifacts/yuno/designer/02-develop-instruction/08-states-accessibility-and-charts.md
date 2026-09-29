# 08 · States, accessibility and charts

**Goal:** make every page behave well when data is missing, slow, broken or thin; draw every chart the same way; keep it colour-blind safe and keyboard usable.

**Time box:** 8 min (guard is already in file 02; this is a pass over all pages) · **Tag:** Core (states) + Stretch (manual a11y checks)

## Inputs
- Files 01–07 built (at least Overview + Outliers).
- UI-UX-PLAN: "States & microcopy", "Visual system", "Chart rules", "Accessibility checklist".

## Steps

### 1. State catalogue (one helper each in `layout.py`, reuse everywhere)

| State | When | What the user sees | Component |
|---|---|---|---|
| No database | DB file missing | "No data yet. Run `make all` first, then reload this page." | `st.info` + `st.stop()` |
| Rebuilding | core raises `DbBusy` | "The data is being rebuilt. Retry in a minute." + [Retry] | `st.warning` + `st.button` (reruns) |
| Loading | cache miss | "Loading…" | `show_spinner` on `st.cache_data` |
| Error | any other exception | "Something went wrong loading this view. The details are in the terminal." | `st.error`; traceback to log only |
| Empty result | filters match nothing | "No transactions match these filters." + [Clear filters] | `st.info` |
| Low sample | n < 30 (week / segment) | greyed, "low sample (n<30)", ranked last, never hidden | chart / table style |
| Insufficient data | alert n < 50 | "Not enough data (needs 50 rows per week)." | Alerts expander |
| Report missing | `alerts.jsonl` / `RECOMMENDATIONS.md` absent | "Not built yet. Run `make all`." | `st.info` |
| Table capped | > 1,000 rows | "Showing 1,000 of 12,345, largest first. Download CSV for all." | `st.caption` |
| No selection | Outliers, no row picked | "Select a row to see why it was flagged." | `st.caption` |
| Open week | week not closed | "not closed yet" on the chart | Plotly annotation |
| Bad URL param | unknown value | "Ignored unknown PSP 'PSP_Z'." | `st.toast` |

Microcopy rules: plain words ("flag rate", "discrepancy after FX", "under-settled"); never "residual" in labels; every KPI has `help=`; every empty/error state says what to do next.

### 2. Plotly conventions (`theme.py`)

```python
def style(fig, title: str, y_title: str) -> go.Figure: ...
    # template=plotly_template(); title=title; height ≤ 400; margin small;
    # hovertemplate uses the same formatters and includes n; legend with words
def bar_h(df, x, y, labels, color, low_sample_col=None, err=None) -> go.Figure: ...
def line_weekly(df, x, y, series=None, closed_col="is_closed") -> go.Figure: ...
def heatmap(df, x, y, z, text) -> go.Figure: ...
```
Call: `st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})`. Under each chart: `st.caption(<one-line takeaway from the data>)` — this is the chart's alt text.

| Rule | Detail |
|---|---|
| Trend | line (rate) and bar (USD), separate charts, no dual axes |
| Ranking | horizontal bar, sorted, value label on each bar, axis from 0 |
| Uncertainty | Wilson 95% error bars; hidden when n < 30 |
| Two-way | heatmap with the value in every cell |
| Mix | 100% stacked bar, order exact → large |
| Open week | dashed / lighter + "not closed yet" |
| Never | pie, donut, 3D, gauge, dual axis |
| Titles | say what and the unit: "Weekly flag rate (%)" |

### 3. Colour (Okabe-Ito, from `theme.py` only)
- Categories: grey / sky blue / blue / orange / vermilion, always with the label word.
- PSPs (series charts only): `#0072B2 #E69F00 #009E73 #CC79A7 #56B4E9` + direct labels.
- Category colours and PSP colours never in the same chart.
- Heatmap: single-hue `Oranges`, value in cell.
- Under = vermilion `#D55E00` + "under"; over = blue `#0072B2` + "over".
- Dark text on orange; white only on blue / vermilion.

### 4. Number formats
All through `format.py` (file 02): USD 2 dp, compact in KPIs (`$127.4k`), local with ISO code and seed exponent (`CLP 12,345`), rate 1 dp, change in pts with arrow + sign, range in brackets, ISO dates, weeks as `W25 (Jun 15–21)`.

### 5. Accessibility checklist (tick before hand-in)
- [ ] No meaning by colour alone: word, icon or sign next to every colour.
- [ ] Okabe-Ito only; checked once in a CVD simulator (protan, deutan, tritan) — Stretch.
- [ ] Text contrast ≥ 4.5:1, badges included.
- [ ] Every chart has a title with units and a one-line takeaway caption.
- [ ] Every chart's data is also in a table or CSV.
- [ ] All controls have visible labels (no `label_visibility="collapsed"`).
- [ ] Keyboard: sidebar, filters, table, buttons, download reachable by Tab; focus visible.
- [ ] Usable at 200% zoom and 1280 px wide; wide tables scroll inside themselves — Stretch.
- [ ] Change shown with arrow + sign (`▲ +1.1 pts`), not only red/green.
- [ ] Abbreviations (SEV2, n, pts, FX) explained in `help=` tooltips.
- [ ] No motion, no auto-refresh.

## Done when
- [ ] Each state in the table can be triggered and shows the right text (no DB, busy, empty, low sample, missing report, capped).
- [ ] All charts go through `theme.style` (grep: no `px.` call without it).
- [ ] Checklist items without "Stretch" are ticked.

## Serves
DoD "well documented so the team can understand and use it"; rubric Insight 20 (clear visuals) and Stretch 10 (polish); UI-UX build steps 2, 3, 11.

## Pitfalls
- `showErrorDetails = false` hides tracebacks in the browser; log them with `logging.exception` or you will debug blind.
- Plotly default colours sneaking in (a chart without `color_discrete_map`).
- Green/red deltas with no arrow: fail for deutan users.
- Captions typed by hand ("PSP_B is worst"): they go stale. Build them from the DataFrame.

## Hand-off
Pages are consistent and safe. Next: `09-tests-and-screenshots.md`.
