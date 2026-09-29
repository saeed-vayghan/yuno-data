# 05 · Page: Outliers

**Goal:** answer "Show me all transactions with discrepancies over $50" in one click, and start every investigation: sortable table, CSV download, masked IDs, a "why flagged" panel.

**Time box:** 12 min · **Tag:** Core (build this page first)

## Inputs
- Files 01–02.
- Core: `query_transactions(filters, min_usd, limit)`, `outlier_summary(filters, min_usd)`, `transaction_detail(txn_id)`, `similar_count(txn_id)`.
- Engineer: `recon query --min-usd 50 --format csv` (same function; used by test 5).

## Rules
- "Discrepancy" here = **discrepancy after FX** = settled minus expected settle (FX move removed), in **USD** at the auth-day rate.
- Filter is **strictly greater**: `abs_residual_usd > min_usd`. Default `min_usd = 50`.
- Every row over $50 is `large` by rule (≥ $20), so this page reads `mart_outliers`. `min_usd = 0` shows all `large` rows.
- Customer IDs arrive masked from core (`cus_••••7f3a`). `transaction_id` stays whole (PSP disputes need it).

## Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Outliers           Data as of 2026-06-30 · Active: all · Apr 1–Jun 30    │
│ Min discrepancy after FX (USD) [ 50 ]   Size tier [..]  Cross-border (..)│
│ Cause [..]                                                               │
│ ⓘ Discrepancy = settled minus expected settle (FX move removed), in USD.│
│ 1,284 transactions · $148,210 under · $3,020 over          [Download CSV]│
├──────────────────────────────────────────────────────────────────────────┤
│ txn_id      |auth date |PSP  |ctry|disc. after FX|raw diff    |customer  │
│ why flagged        |likely cause |lag (d)                                │
│ txn_00a91f3c7b2e|2026-06-14|PSP_D|CL  |−$62.10 under |CLP −58,000 |cus_••••7f3a
│ > 5% and ≥ $20     |psp_rounding |3                                      │
├──────────────────────────────────────────────────────────────────────────┤
│ ▼ Selected: txn_00a91f3c7b2e                                                 │
│  Authorized CLP 1,058,000 ($1,128.40)   Expected CLP 1,058,000           │
│  Settled    CLP 1,000,000 ($1,066.30)   FX move 0.0% (domestic)          │
│  Lag 3 days · Weekend: no · Items 2 · Risk score 0.12                    │
│  Why flagged: −5.5% (> 5%) and −$62.10 (≥ $20)                           │
│  Likely cause: psp_rounding (settled is a multiple of 1,000, below exp.) │
│  Similar rows: 142 in PSP_D · CL · psp_rounding  [See similar rows →]    │
└──────────────────────────────────────────────────────────────────────────┘
```

## Steps

1. `layout.page_header("Outliers", uses={"date", "country", "psp", "tier", "xb", "cause"})`.

2. **Min-$ input:** `st.number_input("Min discrepancy after FX (USD)", min_value=0, value=st.session_state.get("f_min_usd", 50), step=10, help="Shows rows where |settled − expected settle| in USD is greater than this.")`. Save to `f_min_usd`.

3. Page filters: size tier, cross-border, cause (same widgets as Drill-down; share one helper). Caption line: "ⓘ Discrepancy = settled minus expected settle (FX move removed), in USD."

4. **Summary line:** `s = outlier_summary(f, min_usd)` → "1,284 transactions · $148,210 under · $3,020 over".

5. **Table:**
   ```python
   rows = data.get_transactions(f, min_usd=min_usd, limit=1000)
   ev = st.dataframe(view(rows), hide_index=True, use_container_width=True,
                     column_config=COLS, on_select="rerun", selection_mode="single-row", key="out_tbl")
   ```
   | Column label | From | Format |
   |---|---|---|
   | Transaction | `transaction_id` | text, whole |
   | Auth date | `auth_ts` | `YYYY-MM-DD` |
   | PSP · Country | `psp`, `country` | text |
   | Discrepancy after FX (USD) | `residual_usd` | NumberColumn `$%.2f`; sign kept; "under/over" in a text column next to it |
   | Raw difference | `diff_local` + `currency` + `currency_exponent` | `CLP −58,000` (text; for reading only) |
   | Customer | `customer_id` (masked) | text |
   | Why flagged | `why_flagged` | text from core |
   | Likely cause | `likely_cause` | text |
   | Lag (days) | `settle_lag_days` | integer |
   - Sorted by `abs_residual_usd` desc (core does it). Users can re-sort by header click.
   - Cap: if `s["n"] > 1000`: caption "Showing 1,000 of 1,284, largest first. Download CSV for all."

6. **CSV:** `st.download_button("Download CSV", data=data.transactions_csv(f, min_usd), file_name=f"casamarket_outliers_min{min_usd:g}usd_{as_of:%Y-%m-%d}.csv", mime="text/csv")`. All rows, same columns, masked IDs, numbers unformatted.

7. **Detail panel:** if `ev.selection.rows` is empty → `st.caption("Select a row to see why it was flagged.")`. Else:
   - `d = transaction_detail(txn_id)`, inside `st.container(border=True)`.
   - Show authorized / expected / settled (local + USD), FX move, lag, weekend, items, risk score, why flagged, likely cause + `cause_note`.
   - `sim = similar_count(txn_id)` → "Similar rows: 142 in PSP_D · CL · psp_rounding" + button "See similar rows →" → `set_handoff(psp=…, country=…, cause=…)` + `st.switch_page(PAGES["drill_down"])`.
   - `st.code(txn_id)` gives a one-click copy.

8. **Empty state:** `s["n"] == 0` → `st.info(f"No transactions over ${min_usd:,.0f}. Try a lower minimum.")`.

9. Wrap in `data.guarded(render)`.

**Decision (raw difference column):** 🏛️ Jamshid: only the after-FX number is correct for the filter. 🎨 Mani: users will compare with the bank statement. → Show both; the filter and sort use after-FX USD; the raw column is labelled "Raw difference (local)".

## Done when
- [ ] Page opens with min = 50 and every row has |discrepancy after FX| > 50 (test 6).
- [ ] The set of `transaction_id` equals `recon query --min-usd 50 --format csv` and the CSV bytes (test 5).
- [ ] Min 100 + PSP = PSP_B → all rows match both (test 7).
- [ ] No full customer ID in table or CSV (test 11).
- [ ] CLP amounts show no decimals; USD columns 2 decimals (test 12).
- [ ] Selecting a row opens the detail panel; "See similar rows" opens Drill-down with 3 filters set.

## Serves
FR3 "Identify outlier transactions that need immediate investigation"; acceptance "Show me all transactions with discrepancies over $50"; Flows B and C; privacy (masking); UI-UX build step 5.

## Pitfalls
- `>=` instead of `>`: DELIVERABLES-CHECK fixed it to `> 50` everywhere.
- Filtering on the raw difference: a cross-border row moved only by FX would look like a loss.
- Formatting the USD column as a string: sort becomes alphabetical.
- The selected row index refers to the displayed frame; map it back with the same DataFrame (do not re-query between display and lookup).
- Showing a bare "$" next to a local amount. Always the ISO code.

## Hand-off
Brief question 2 answered. Next: `03-page-overview.md`.
