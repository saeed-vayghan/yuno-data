# alerts
`recon alerts` -> `run.main()`: evaluates the 6 rules in `config/alerts.yaml` on the **last closed week** W
(from `core.status()` / `core.weeks`: Sunday <= as_of - 7 d, as_of = data time) and writes `reports/alerts.jsonl` + `reports/alerts.md`. Exit 0 even
when alerts fire. Slack is off unless `slack.enabled: true` **and** env `SLACK_WEBHOOK_URL` is set.

| File | Role |
|---|---|
| `run.py` | thin shell: core reads -> evaluate -> render -> write -> Slack (opt-in) |
| `rules_rate.py` | `peer` (BH q + gap), `change` (p-chart vs 8 prior weeks), `settle_lag` (country x tier) |
| `group.py` | one PSP firing `peer` in ≥ 3 countries → one PSP-wide alert (`PSP_C|ALL`) |
| `rules_money.py` | `money_leak` (under / settled USD), `large_rows` (count, $, top 3), `pending_aging` (share of pending older than `age_days`, warn 10% / crit 25%) |
| `evaluate.py` | runs each rule for W and W-1 -> NEW / ONGOING / RESOLVED (no state file); sorts |
| `record.py` | record shape = `core.load_alerts()` columns; `RuleInput`; window helpers |
| `stats.py` | one-sided two-proportion z-test, Benjamini-Hochberg, Wilson CI (stdlib) |
| `markdown.py` / `sink.py` | alerts.md text (pure) / the only file writes |

Rules are pure: `(RuleInput, rule_cfg, week) -> list[dict]`. Data comes from core:
`ui_q_alerts.alert_frame` (psp x country x tier x week aggregate, incl. pending counts).
Any segment with n < `min_sample.alerts` (50) is one `INSUFFICIENT_DATA` / `INFO` row, never an alert,
so a 500-row smoke run is all `INSUFFICIENT_DATA`. Output is byte-stable (no wall-clock time).
