# 06 · Page: Root causes & actions

**Goal:** show what drives the loss (FR2 findings with evidence) and what to do about it (FR4 recommendations), inside the dashboard.

**Time box:** 10 min · **Tag:** Stretch

## Inputs
- Files 01–02.
- Core: `cause_summary(filters)`, `segment_rates("psp_country")`, `excess_loss(top=5)`, `load_findings()`, `load_recommendations()`.
- Engineer: `reports/findings.json` + `FINDINGS.md` (core checkpoint), `reports/recommendations.json` + `RECOMMENDATIONS.md` (engineer 07 part B; may not exist yet).

## Cause labels (from FINAL-SOLUTION §2)
`fx_timing`, `psp_rounding`, `partial_capture`, `psp_fee`, `tax_recalc`, `fraud_hold`, `psp_adjustment`, `tip` (ruled out: 0 rows), `unexplained`. Show them with a short plain label and a `help=` line each:

| Code | Label | One line |
|---|---|---|
| `fx_timing` | FX timing | Cross-border rate moved between auth and settle beyond the expected move. |
| `psp_rounding` | PSP rounding | Settled amount rounded down to a multiple of 1,000 units. |
| `partial_capture` | Partial capture | Only some items were captured. |
| `psp_fee` | PSP fee | A fixed fee deducted at settlement. |
| `tax_recalc` | Tax recalculation | VAT share changed after the final invoice (MX, CO). |
| `fraud_hold` | Fraud hold | Part of the funds withheld after a risk check. |
| `psp_adjustment` | PSP adjustment | A correction of −2% to −5% by the PSP. |
| `tip` | Tip | Ruled out: home goods, no tips in the data. |
| `unexplained` | Unexplained | No rule matched; needs a manual look. |

## Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Root causes & actions                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Loss by likely cause (USD, full data period), largest first              │
│ Partial capture ▇▇▇▇▇▇▇▇▇▇▇ $41,200  32%                                 │
│ Fraud hold      ▇▇▇▇▇▇▇     $27,900  22%                                 │
│ …  Tip: ruled out (0 rows)                                               │
│ Drill into cause: [ Partial capture ▾ ] [Go →]                           │
├──────────────────────────────────────────────────────────────────────────┤
│ Key findings (from findings.json)                                        │
│ F1 PSP_B in AR flags 17.9% vs 12.1% peers · n 3,020 · CI 16.6–19.3%      │
│    · lift 1.48× · q < 0.001 · ~$18.4k/qtr                                │
├───────────────────────────────────┬──────────────────────────────────────┤
│ Flag rate PSP × country (heatmap) │ Excess loss vs peers (top 5)         │
│        MX    CO    AR    CL       │ PSP_B·AR  $18,400 (median $…)        │
│ PSP_B 12.1  12.3  15.9  12.0      │                                      │
├───────────────────────────────────┴──────────────────────────────────────┤
│ Recommendations (ranked by $ impact)                                     │
│ R1 Escalate PSP_B Argentina variance · Evidence F1 · ~$18k/qtr · PSP ops │
│   ▸ How to implement                                                     │
│ ▸ Full findings (FINDINGS.md)                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

## Steps

1. `layout.page_header("Root causes & actions", uses={"country", "psp"})`. Date range: not used (analysis covers the full period); the active line says so.

2. **Loss by cause** (Plotly horizontal bar, one hue — vermilion for net loss):
   - `cs = cause_summary(f)`, sorted by `net_usd` desc, value label `$41,200 · 32%`.
   - `tip` with 0 rows: not a bar; a caption "Tip: ruled out (0 rows)".
   - Caption: "Top cause: Partial capture, 32% of net loss."
   - Check: bars sum to the total net loss (test in file 09).

3. **Drill into cause:** `st.selectbox` (labels) + button "Go →" → `set_handoff(cause=(code,))` + `st.switch_page(PAGES["drill_down"])`.

4. **Key findings** (from `load_findings()["items"]`), one line each, ranked by `usd_quarter`:
   `F1 <headline> · n 3,020 · rate 17.9% [16.6–19.3] · peer 12.1% · lift 1.48× · q < 0.001 · ~$18.4k/qtr`
   - q format: `q < 0.001` when tiny, else 3 decimals.
   - Show at least the 4 findings with q < 0.05; a small `st.dataframe` is fine instead of text if faster.

5. **PSP × country heatmap:** `segment_rates("psp_country")`; split `segment_value` (`PSP_B|AR`) on `|` for the axes. Plotly `Oranges`, value printed in every cell (`15.9`), `n<30` cells grey with text "n<30". Title "Flag rate by PSP and country (%)". Caption names the highest cell.

6. **Excess loss vs peers:** `excess_loss(top=5)` → `st.dataframe`: Segment (`psp · country`), n, rate, peer rate, lift, excess $ (`excess_usd`), median loss (`median_loss_usd`). q is shown in the findings list, not here. Caption: "Excess loss = (segment rate − peer rate) × volume × mean loss. An estimate."

7. **Recommendations:** `recs = load_recommendations()`.
   - `None` → `st.info("Recommendations are not built yet. Run `make all`.")`.
   - Else, per item: `st.markdown(f"**R{r['rank']} {r['action']}** · Evidence {r['evidence']} · ~{usd_compact(r['usd_quarter'])}/qtr · Owner: {r['owner']}")` + `st.expander("How to implement")` with `implementation`.

8. **Full findings:** `st.expander("Full findings (FINDINGS.md)")` → `st.markdown(load_findings()["markdown"])`. Relative image links in the MD will not render; that is fine (figures are on the other pages).

9. Wrap in `data.guarded(render)`.

**Decision (findings block):** 🎨 Mani wanted only charts + recommendations. 🏛️ Jamshid: the rubric scores "statistical evidence"; the reviewer should see n, CI, lift, q, $ without opening a file. → Keep the compact findings list (step 4); put the long text in the expander.

## Done when
- [ ] Cause bars sum to the total net loss (± rounding).
- [ ] Each finding line shows n, rate, CI, peer rate, lift, q and $.
- [ ] 3–5 recommendations render, each with evidence F#, $ impact, owner, implementation (test 14).
- [ ] Missing `recommendations.json` (`load_recommendations()` is `None`) → "not built yet" message, page still works.
- [ ] Heatmap has a value in every cell; n<30 cells marked.
- [ ] "Drill into cause" opens Drill-down with the cause set.

## Serves
FR2 acceptance ("immediately understand which factors are driving the discrepancies"); FR4 ("included in your dashboard", 3–5 actions with $ and implementation); Flow E; UI-UX build step 9.

## Pitfalls
- Typing numbers into the page: every number comes from core / `findings.json`.
- A pie or donut for cause share: not allowed (chart rules). Bars.
- Showing `tip` as a zero bar: it reads as "missing data". Use the caption.
- Parsing RECOMMENDATIONS.md anywhere: read the JSON rows from `load_recommendations()`.

## Hand-off
FR2 + FR4 visible in the app. Next: `07-page-alerts.md` (if not done) or `08-states-accessibility-and-charts.md`.
