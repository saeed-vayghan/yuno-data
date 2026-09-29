# 07 · Page: Alerts

**Goal:** show "what needs attention this week, and who owns it" from the alert evaluator's output, with NEW / ONGOING / RESOLVED status and a clear "insufficient data" state.

**Time box:** 8 min · **Tag:** Stretch

## Inputs
- Files 01–02.
- Core: `load_alerts()` (reads `reports/alerts.jsonl`), `status()` (last closed week).
- Engineer (S5.1): `recon alerts` → `reports/alerts.jsonl` + `reports/alerts.md`. The page never runs the evaluator; it only reads its output.
- Research `07-alerting-metrics.md`: the 6 rules and severities.

## Facts (from FINAL-SOLUTION §6 and research 07)
- Evaluated on the **last closed week**. Status vs the previous closed week, no state file:
  NEW = fires now, not before · ONGOING = both · RESOLVED = before, not now.
- n < 50 → "insufficient data" (Info), never an alert.
- 6 rules: peer, change, money leak, large-rows summary, pending aging, settle lag.
- Severities used here: SEV2 (same day), SEV3 (weekly review), Info (report only). SEV1 is prod-only; not shown.
- Slack is optional and off. The page needs no Slack; do not add a "send" button.

## Assumed record (A5 in file 02; reconcile with the engineer)
```json
{"rule_id": "peer", "segment": "PSP_B|AR", "psp": "PSP_B", "country": "AR",
 "period": "2026-W25", "severity": "SEV2", "status": "NEW",
 "message": "PSP_B flags 17.9% of AR rows vs 12.1% for other PSPs (+5.8 pts).",
 "owner": "PSP ops", "n": 812, "value": 0.179, "threshold": 0.141}
```
"Insufficient data" rows: `status = "INSUFFICIENT_DATA"`, `severity = "Info"`.

## Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Alerts · last closed week W25 (Jun 15–21)                                │
│ ▲ SEV2 · same day: 1   ● SEV3 · weekly: 2   ℹ Info: 4   ✓ Resolved: 1    │
│ Severity [..]   Status [..]   Rule [..]                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ Severity        | Status   | Rule   | Segment    | Message       | Owner │
│ ▲ SEV2 · same day| **NEW** | Peer   | PSP_B · AR | PSP_B flags … | PSP ops│
│ ● SEV3 · weekly | ONGOING  | Change | PSP_C · MX | …             | PSP ops│
│ ✓ Resolved      | RESOLVED | Settle lag | CO · 200+ | …          | PSP ops│
│ View segment: [ PSP_B · AR ▾ ] [Open in Drill-down →]                    │
├──────────────────────────────────────────────────────────────────────────┤
│ ▸ Insufficient data (4)          ▸ What each rule means                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Steps

1. `layout.page_header(f"Alerts · last closed week {week_label}", uses=set())`. Global filters are not used; the line says "Filters not used here (alerts cover all segments)".

   **Decision (filters on Alerts):** 🎨 Mani wanted the sidebar PSP filter to narrow alerts. 🏛️ Jamshid: alerts are a fixed weekly list from a file; filtering hides a SEV2. → Page filters only (severity, status, rule), all shown by default.

2. **Load:** `a = load_alerts()`.
   - `None` → `st.info("No alerts file yet. Run `recon alerts` or `make all` first.")`, stop.
   - All rows `INSUFFICIENT_DATA` (500-row run) → `st.info("Not enough data for alerts (each needs 50 rows per week). Run the full dataset with `make all`.")`, then show the expander only.
   - No firing rows → `st.success("No alerts for W25. All 6 rules checked.")`.

3. **Counts row** (`st.columns(4)` + `st.metric`): SEV2 · SEV3 · Info · Resolved, with the icon + word labels from `theme.SEVERITY` / `theme.RESOLVED`.

4. **Filters:** `st.multiselect` for severity, status (NEW / ONGOING / RESOLVED), rule. Defaults empty = all.

5. **Table** (`st.dataframe`), active rows only (not `INSUFFICIENT_DATA`), sorted SEV2 → SEV3 → Info, then NEW → ONGOING → RESOLVED:
   | Column | Content |
   |---|---|
   | Severity | badge text: `▲ SEV2 · same day` / `● SEV3 · weekly` / `ℹ Info` / `✓ Resolved` |
   | Status | NEW (bold via Styler) / ONGOING / RESOLVED |
   | Rule | plain name (Peer, Change, Money leak, Large rows, Pending aging, Settle lag) |
   | Segment | `PSP_B · AR` |
   | Message | from the file, as is |
   | Owner | from the file |
   | n | integer |
   - Optional colour: a pandas `Styler` on the Severity column only, background from `theme.SEVERITY`, dark text on orange, white on vermilion/blue. The word is always there.

6. **View segment:** `st.selectbox` of segments with a `psp` (and/or `country`) + button → `set_handoff(psp=…, country=…)` + `st.switch_page(PAGES["drill_down"])`. Row-select on the table is also fine if quicker.

7. **Insufficient data:** `st.expander(f"Insufficient data ({k})", expanded=False)` → small table: rule, segment, n, "needs 50 rows per week".

8. **Rule help:** `st.expander("What each rule means")`, one line per rule (text from research 07 "In plain English" column).

9. Wrap in `data.guarded(render)`.

## Done when
- [ ] Counts per severity equal the counts in `alerts.jsonl` (test 13).
- [ ] 500-row fixture → "Not enough data for alerts…" message (test 13).
- [ ] Missing file → "Run `recon alerts`…" message, no error.
- [ ] Every severity shows icon + word; colour is optional extra.
- [ ] "Open in Drill-down" lands with PSP × country set.
- [ ] Overview "Open alerts" KPI count equals NEW + ONGOING rows here.

## Serves
FR3 "automated alert system" (read side) and "monitor whether the situation is improving or getting worse" (RESOLVED vs NEW); Flow D; UI-UX build step 8.

## Pitfalls
- Computing status (NEW / ONGOING) in the page: it comes from the evaluator.
- Counting `INSUFFICIENT_DATA` rows as alerts in the Overview KPI.
- Showing a Slack button or reading `SLACK_WEBHOOK_URL`: out of scope.
- Using `alerts.md` instead of `alerts.jsonl`: parse the JSONL (via core); the MD is for humans.

## Hand-off
Alerts visible. Next: `06-page-root-causes-and-actions.md` or `08-states-accessibility-and-charts.md`.
