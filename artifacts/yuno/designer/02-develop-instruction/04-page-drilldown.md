# 04 · Page: Drill-down

**Goal:** slice the data by segment (country, PSP, size tier, cross-border, weekday, category, cause, dates), see flag rates with 95% ranges, and see the rows behind them.

**Time box:** 12 min (filters + table 6 min, Core · charts 6 min, Stretch) · **Tag:** Stretch (table part Core)

## Inputs
- Files 01–02. Global filters (dates, country, PSP) already in the sidebar.
- Core: `kpis(filters)`, `segment_rates(dim, filters)`, `category_mix(filters)`, `query_transactions(filters, limit=1000)`, `filter_options()`.
- Arrivals from: Overview card (PSP + week dates), Outliers "See similar rows" (PSP + country + cause), Alerts "View segment" (PSP + country), Root causes "Drill into cause" (cause).

## Wireframe

```
┌ Sidebar (global) ┐┌─────────────────────────────────────────────────────────┐
│ Auth dates [..]  ││ Drill-down        Active: PSP_B · AR   [Clear filters]  │
│ Country  [AR]    │├─────────────────────────────────────────────────────────┤
│ PSP      [PSP_B] ││ Size tier [..]  Cross-border (All|Cross|Domestic)       │
└──────────────────┘│ Weekday [..]    Category [..]   Cause [..]              │
                    ├──────────────┬──────────────┬───────────────────────────┤
                    │ Rows 8,410   │ Flag rate    │ Net loss $12,300          │
                    │              │ 17.9%        │                           │
                    ├──────────────┴──────────────┴───────────────────────────┤
                    │ Group by: (Country|PSP|Size tier|Weekday|Cross-border|  │
                    │            Settle lag)                                  │
                    │ Flag rate by <group>, with 95% range (horizontal bars)  │
                    │ ▇▇▇▇▇▇▇▇▇▇▇▇ PSP_B  21.3% [19.8–22.9]  n 3,020          │
                    │ ░░░░         PSP_E   9.0%  low sample (n<30)            │
                    ├─────────────────────────────────────────────────────────┤
                    │ Category mix by week (100% stacked bar)                 │
                    ├─────────────────────────────────────────────────────────┤
                    │ Transactions (showing 1,000 of 8,410, largest first)    │
                    │ txn_id | auth date | PSP | ctry | category | cause |    │
                    │ disc. after FX (USD) | raw diff (local) | lag (d)       │
                    │                                        [Download CSV]   │
                    └─────────────────────────────────────────────────────────┘
```

## Steps

1. **Arrivals.** At the top: `set_now = filters.apply_handoff()`. If it returns values, `st.toast("Filters set: PSP_B · Jun 8–14")`. Then `layout.page_header("Drill-down", uses=ALL)`.

2. **Page filters** (in the body, 2 rows of `st.columns`), stored in plain session keys:
   | Filter | Widget | Values |
   |---|---|---|
   | Size tier | `st.multiselect` | `10-50`, `50-200`, `200+` |
   | Cross-border | `st.radio(horizontal=True)` | All / Cross-border / Domestic |
   | Weekday | `st.multiselect` | Mon…Sun |
   | Category | `st.multiselect`, labels from `theme.CATEGORY_LABELS` | exact…large |
   | Cause | `st.multiselect` | from `filter_options()["cause"]` |

   **Decision (week handoff):** 🎨 Mani wanted a separate `week` filter. 🏛️ Jamshid: one more param to keep in sync. → A week arrives as the global date range (`week_start`–`week_end`). The active line shows it as "W24 (Jun 8–14)" when the range is exactly one ISO week.

3. **Summary KPIs** (`kpis(f)`, no `week`): Rows, Flag rate, Net loss. Same `help=` texts as Overview.

4. **Empty state:** if `kpis["n"] == 0`: `st.info("No transactions match these filters.")` + Clear filters button; `st.stop()`.

5. **Transaction table (Core part):**
   ```python
   rows = data.get_transactions(f, min_usd=None, limit=1000)
   st.dataframe(view(rows), hide_index=True, column_config=COLS, use_container_width=True)
   if k["n"] > 1000:
       st.caption(f"Showing 1,000 of {k['n']:,}, largest first. Download CSV for all.")
   ```
   - Columns (same helper as Outliers): `transaction_id`, auth date, PSP, country, category (label), likely cause, **Discrepancy after FX (USD)** (`residual_usd`, signed), **Raw difference** (`diff_local` formatted as `CLP −58,000`), lag (days, integer).
   - CSV: `st.download_button` with `data.transactions_csv(f)` (all rows, no limit, masked IDs). For large results, see Pitfalls.

6. **Group-by chart (Stretch):**
   - `st.segmented_control("Group by", ["Country", "PSP", "Size tier", "Weekday", "Cross-border", "Settle lag"])` → `dim`.
   - `seg = data.get_segment_rates(dim, f)`. Plotly horizontal bar, sorted by rate, value label on each bar (`21.3% [19.8–22.9] n 3,020`), error bars from `ci_low/ci_high`.
   - `low_sample` rows: 40% opacity grey, no error bar, label "low sample (n<30)", sorted last.
   - Caption: "Highest: PSP_B at 21.3%, range 19.8–22.9%."

7. **Category mix by week (Stretch):** Plotly 100% stacked bar, `CATEGORY_ORDER`, `CATEGORY_COLORS`, legend with words. Caption with the share of `large` in the last closed week.

8. Wrap in `data.guarded(render)`.

## Done when
- [ ] Each filter narrows the table (and KPIs) — check one at a time.
- [ ] Arriving from the Overview card shows PSP + that week's dates, and the active line says so.
- [ ] Empty state shows the message + Clear filters.
- [ ] > 1,000 rows → cap caption shows; CSV holds all rows.
- [ ] (Stretch) low-sample groups are greyed and have no range bar.

## Serves
FR3 "Drill down into specific segments (by country, PSP, transaction size…)"; FR2 questions visible (country, PSP, size, time); Flows A step 4, C step 4, D step 4, E step 4; UI-UX build step 7.

## Pitfalls
- Building CSV bytes for 135k rows on every rerun: wrap the CSV builder in `st.cache_data` (same key as the query), or offer the button only when `n ≤ 50,000` and point to `recon query --format csv` above that.
- Error bars on n < 30 look precise but are not. Hide them.
- Category colours and PSP colours in the same chart: never (UI-UX rule).
- Using category code names in the UI (`fx_tolerance`): show labels ("FX noise").

## Hand-off
Drill-down receives every cross-page link. Next: `05-page-outliers.md` (if not done) or `07-page-alerts.md`.
