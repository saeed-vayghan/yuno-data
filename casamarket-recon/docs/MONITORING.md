## Monitoring

### Open the dashboard
```bash
make all      # builds data/casarecon.duckdb and reports/ (first time: about a minute)
make app      # or: uv run recon dashboard
```
Open http://localhost:8501. Docker: `docker compose up`, then the same URL.
No data yet? Every page says "No data yet. Run `make all` first". Rebuilding while the app is open
is safe: the app says "The data is being rebuilt. Retry in a minute." for a moment.

### Answer the two brief questions
| Question | In the app | In the terminal |
|---|---|---|
| Which PSP had the worst week last month? | **Overview** → "Worst PSP week" card (0 clicks). Change the month in the card. | `uv run recon worst-week --month last` |
| Show me all transactions with discrepancies over $50 | **Outliers** in the sidebar (1 click). Opens at min $50. "Download CSV" for all rows. | `uv run recon query --min-usd 50 --format csv` |

### Pages
| Page | What it answers |
|---|---|
| Overview | How bad is it this week? Flag rate, net loss, large rows and open alerts for the last closed week (with change vs the week before), weekly trends, week-over-week by PSP × country, and the worst PSP week of a month. |
| Drill-down | Where exactly? Filter by dates, country, PSP, size tier, cross-border, weekday, category and cause; see flag rates by group with 95% ranges, the category mix by week, and the rows (CSV up to 50,000 rows). |
| Outliers | Which rows need a look now? Rows over a USD threshold (default $50, strict "over"), largest first; click a row to see why it was flagged, its likely cause and how many similar rows exist. |
| Root causes & actions | Why is money lost and what do we do? Loss by likely cause, PSP × country heatmap, excess loss vs peers, key findings with evidence (n, CI, lift, q, $), and the ranked recommendations. |
| Alerts | What fired this week and who owns it? Alerts from `recon alerts` with severity, NEW / ONGOING / RESOLVED, owner, and a link to the segment in Drill-down. |

Cross-page links ("Open in Drill-down", "See similar rows", "View segment", "Drill into cause") set
exactly the filters they name. The sidebar filters (dates, country, PSP) follow you between pages;
each page says which ones it does not use.

### Alert rules (plain English)
`recon alerts` (part of `make all`) checks the **last closed week** and writes `reports/alerts.jsonl`
and `reports/alerts.md`. Limits live in `config/alerts.yaml` and `config/thresholds.yaml`.

| Rule | Question | Fires when | Severity | Owner |
|---|---|---|---|---|
| Peer | Is this PSP worse than the other PSPs in the same country? | Flag rate over the last 4 closed weeks is at least 2 pts above peers and the gap is significant (q < 0.05). If one PSP fires in 3+ countries, you get one PSP-wide alert instead | SEV2 | PSP ops |
| Change | Is this week worse than usual? | Last closed week is above the normal range of the 8 weeks before it (3 sigma) | SEV3 | PSP ops |
| Money leak | Are we losing more money than usual? | Under-settled USD is more than 2.5% (SEV3) or 3.5% (SEV2) of settled USD, after FX (normal weeks: 1.6–2.0%) | SEV3 / SEV2 | Finance |
| Large rows | How many rows need a closer look? | Any large rows last week: one summary with count, $ and top 3 segments (rows are on Outliers) | SEV3 | PSP ops |
| Pending aging | Is money stuck unsettled? | More than 10% (SEV3) or 25% (SEV2) of pending rows are older than 7 days | SEV3 / SEV2 | PSP ops + Finance |
| Settle lag | Are orders settling late? | More than 6% of a country × size tier settles after 7 days (last 4 weeks) | SEV3 | PSP ops |

- **Severity:** ▲ SEV2 = act the same day · ● SEV3 = weekly review · ℹ Info = report only.
- **Status** compares with the week before: NEW = fires now, not before · ONGOING = both ·
  RESOLVED = before, not now · INSUFFICIENT_DATA = fewer than 50 rows, never an alert.
- The Overview "Open alerts" KPI counts SEV2 + SEV3 alerts that are NEW or ONGOING.
- **Open since:** first week of the current run of weeks the alert kept firing (from the alert
  history in `data/alerts/history.jsonl`, one line per alert per week).
- **Ack / mute** (`config/alert_state.yaml`): `uv run recon alert ack 'peer|PSP_B|AR' --note "JIRA-1"`
  marks it seen; `uv run recon alert mute KEY --until 2026-W27` keeps recording it (`muted: true`) but
  does not send it. `recon alert list` shows open alerts; `recon alert history KEY` shows its weeks.
- **Notifications (local):** `reports/notifications.jsonl` lists what would be sent: SEV2 / SEV3 only,
  not muted, NEW as `trigger`, ONGOING only if not sent before in its streak, RESOLVED as `resolve`
  (dedupe key = alert key + week). Slack posting is off by default (`slack.enabled: false`; also
  needs `SLACK_WEBHOOK_URL`).

### How to read it
- **Discrepancy after FX:** settled minus expected settle, with the normal FX move removed, in USD
  at the auth-day rate. "Over $50" means strictly greater than $50.
- **Flag rate:** share of settled rows that are *meaningful* (2–5%, under $20) or *large*
  (over 5% or at least $20).
- **Week:** ISO week (Mon–Sun) by auth date; a week belongs to the month of its Thursday. KPIs and
  alerts use the last **closed** week; open weeks are dashed and marked "not closed yet".
- **Low sample:** fewer than 30 rows; shown in italics or grey with the words "low sample", ranked
  last, no 95% range.
- Changes always show an arrow and a sign (`▲ +1.1 pts`), never colour alone. Every chart has its
  numbers in a "Chart data (table)" expander.
- Customer IDs are masked (`cus_••••7f3a`) in the app and in CSVs. Transaction IDs are whole, for
  PSP disputes. Local amounts carry their ISO code (`CLP 12,345`, `MXN 1,234.56`).
- The 500-row smoke run (`make smoke`) shows mostly "low sample" / "not enough data"; use
  `make all` for real numbers.
