# 08 · Alert system (`recon alerts`)

**Goal:** evaluate 6 YAML rules on the last closed week and write `reports/alerts.jsonl` + `reports/alerts.md`, with NEW / ONGOING / RESOLVED status and no state file.

**Time box:** 20 min · **Stretch**

## Inputs
- File 02 (`alerts.yaml`, `thresholds.yaml`, `status()`, `psp_weekly()`, `pending()`, `lag_by_country_tier()`, `week_over_week()`), file 06 (`stats.bh`, `stats.wilson`).
- Research 07 "Core alert rules" · decision sheet "Alerts" · IMPLEMENTATION-PLAN S5.1.
- Diagram: `../../architect/03-system-design/05-alert-system.svg`.

## Steps

1. **Window rules** (in `alerts/evaluate.py`):
   - `as_of` = max data timestamp (`core.status()`).
   - Closed week = ISO week whose end (Sunday) ≤ `as_of − 7 days`. `W` = last closed week, `W−1` = the one before.
   - `n` = settled rows in the rule's window. `n < min_sample.alerts (50)` → one row with `status = "INSUFFICIENT_DATA"`, `severity = "INFO"`; never an alert.

2. **The 6 rules** (`alerts/rules.py`, one pure function each: `(data, rule_cfg, week) -> list[Alert]`):
   | Rule | Segment | Metric | Fires when | Severity | Owner |
   |---|---|---|---|---|---|
   | `peer` | PSP × country | flag rate, trailing 4 closed weeks, vs other PSPs in same country | BH q < 0.05 **and** gap ≥ 2 pts (Wilson CI shown, not gating) | SEV2 | PSP ops |
   | `change` | portfolio + each PSP × country | weekly flag rate | above p-chart UCL: `p̄ + 3·sqrt(p̄(1−p̄)/n)`, `p̄` from trailing 8 closed weeks before `W` | SEV3 | PSP ops |
   | `money_leak` | portfolio | `gross_under_usd / settled_usd` in `W` | ≥ `warn_pct` → SEV3; ≥ `crit_pct` → SEV2 | SEV3/SEV2 | Finance |
   | `large_rows` | portfolio | count and $ of `large` rows in `W` | any → one alert: count, $ total, top 3 PSP × country | SEV3 | PSP ops |
   | `pending_aging` | PSP × country | oldest pending age vs `as_of` | > 7 d → SEV3; > 14 d → SEV2 | SEV3/SEV2 | PSP ops + Finance |
   | `settle_lag` | country × amount tier | late share (lag > 7 d, or pending > 7 d), trailing 4 closed weeks | > `max_late_share` | SEV3 | PSP ops |

3. **Status without a state file:** run each rule for `W` and for `W−1`. Key = `rule_id|segment`.
   | Fires in W | Fired in W−1 | Status |
   |---|---|---|
   | yes | no | NEW |
   | yes | yes | ONGOING |
   | no | yes | RESOLVED |
   `pending_aging` is measured at `as_of` only, so it has no "previous week": report it as NEW.

4. **Output `reports/alerts.jsonl`** (one JSON per line, sorted by severity, rule_id, segment; no wall-clock time):
   ```json
   {"period": "2026-W25", "rule_id": "peer", "segment": "PSP_B|AR", "key": "peer|PSP_B|AR", "psp": "PSP_B", "country": "AR",
    "severity": "SEV2", "status": "NEW", "owner": "PSP ops", "n": 612, "value": 0.179, "threshold": 0.141,
    "message": "PSP_B flags 17.9% of AR rows vs 12.1% for other PSPs (+5.8 pts, q < 0.001)."}
   ```
   Fields = `load_alerts()` columns in the core contract. `psp` / `country` are null when the segment has none (e.g. `money_leak` is portfolio; `settle_lag` `CO|200+` has `country` only); the dashboard uses them for "View segment".

5. **`reports/alerts.md`** via `templates/alerts.md.j2`: header (period, as-of), counts by severity, table of non-info alerts, money lines (gross under, gross over, net USD for `W` vs `W−1`), week-over-week table from `core.week_over_week()` with ▲ worse / ▼ better, and a closed "Insufficient data" list.

6. **Slack (optional, off):** post the Markdown summary only if `alerts.yaml: slack.enabled: true` **and** env `SLACK_WEBHOOK_URL` is set; stdlib `urllib.request`, 5 s timeout; failure logs a warning, never fails the command.

7. **Wire `recon alerts`**: exit 0 even when alerts fire (alerts are output, not errors).

8. **`tests/test_alerts.py`:** 12 tests (one firing + one silent fixture per rule) + small-n test (n < 50 → `INSUFFICIENT_DATA`) + status test (NEW / ONGOING / RESOLVED from two synthetic weeks).

## Done when
| Command | Expected |
|---|---|
| `uv run pytest -q tests/test_alerts.py` | 14+ tests pass |
| smoke: `uv run recon all --rows 500 && grep -c INSUFFICIENT_DATA reports/alerts.jsonl` | every line is `INSUFFICIENT_DATA` |
| full run: `grep '"rule_id": "peer"' reports/alerts.jsonl \| grep 'PSP_B|AR'` | one line, status NEW or ONGOING |
| full run: `grep '"rule_id": "change"' reports/alerts.jsonl \| grep PSP_C` | ≥ 1 line (drift) |
| full run: `grep '"rule_id": "settle_lag"' reports/alerts.jsonl \| grep 'CO|200+'` | one line |
| run `recon alerts` twice, `shasum reports/alerts.jsonl` | same hash |

## Serves
FR3 "automated alert system" (monitor week-over-week, find outliers) · Stretch 10 · Deliverable 5.

## Pitfalls
- **Open week bias:** the current week is half-settled; never evaluate it. Use the last **closed** week.
- **As-of is data time,** not `datetime.now()`. With synthetic June data, wall-clock time would make every week "closed" and pending ages huge.
- `change` needs 8 prior closed weeks; with 3 months (~13 weeks) that is fine, but guard for fewer (→ `INSUFFICIENT_DATA`).
- The drift starts on 1 June; by the last closed week the p-chart baseline still holds mostly pre-drift weeks, so it fires. If it stops firing after you tune the generator, check the baseline window, not the rule.
- `money_leak` uses the FX residual (auth-day rate), so normal FX moves never count.
- `settle_lag` tiers use the same `amount_tier` labels as the fact table (`200+`), so the P2 segment is `CO|200+`.
- `money_leak` and `settle_lag` limits are placeholders: after the first full run set them just above the portfolio baseline and note it in README.
- Data quality is **not** an alert; a failed dbt build (exit 5) is that signal.

## Hand-off
- File 07 part A: FINDINGS "Latest alerts" section reads `alerts.jsonl` when present.
- File 09: `alerts` runs between `analyze` and `report` in `recon all`.
- Frontend: `core.load_alerts()` (DataFrame or None) for the Alerts page and the Overview "open alerts" KPI.
