# alerts
`recon alerts` -> `run.main()`: evaluates the 6 rules in `config/alerts.yaml` on the **last closed week** W
(from `core.status()` / `core.weeks`: Sunday <= as_of - 7 d, as_of = data time), adds alert memory
(`open_since`, `muted`), routes + dedupes, and writes `reports/alerts.jsonl`, `reports/alerts.md`,
`reports/notifications.jsonl` (local outbox) and `data/alerts/history.jsonl`. Exit 0 even when
alerts fire. Local dev only: Slack is the one optional channel, off unless `slack.enabled: true`
**and** env `SLACK_WEBHOOK_URL` is set.

| File | Role |
|---|---|
| `run.py` | thin shell: core reads -> evaluate -> `remember` (memory + routing, pure) -> write -> Slack (opt-in) |
| `rules_rate.py` | `peer` (BH q + gap), `change` (p-chart vs 8 prior weeks), `settle_lag` (country x tier) |
| `group.py` | one PSP firing `peer` in ≥ 3 countries → one PSP-wide alert (`PSP_C|ALL`) |
| `rules_money.py` | `money_leak` (under / settled USD), `large_rows` (count, $, top 3), `pending_aging` (share of pending older than `age_days`, warn 10% / crit 25%) |
| `evaluate.py` | runs each rule for W and W-1 -> NEW / ONGOING / RESOLVED; sorts |
| `record.py` | record shape: `RULE_FIELDS` (rules) + `open_since`, `muted` = `FIELDS` (alerts.jsonl order) |
| `memory.py` | pure: `open_since` from history, mute / ack from `config/alert_state.yaml`, history lines |
| `notify.py` | pure: routing + dedupe -> outbox lines; Slack text |
| `manage.py` / `cli.py` | `recon alert list [--all] \| ack KEY --note \| mute KEY --until W \| unmute KEY \| history KEY` |
| `markdown.py` / `sink.py` | alerts.md text (pure) / the only file reads + writes (atomic) |

Metric definitions (flag rate, leak share, Wilson, BH, two-proportion test) come from `core/metrics.py`.

**Alert memory.** `history.jsonl` has one line per alert per evaluated week:
`period, key, rule_id, severity, status, open_since, muted, sent` (`sent` = trigger / resolve / null).
Only weeks **before** W are read, and re-running W replaces W's lines, so two runs give the same bytes.
`open_since` = first week of the current open streak: NEW -> W; ONGOING / RESOLVED -> walk back from
W-1 while history says the key fired (no history -> W-1, since ONGOING means it fired in W-1);
INSUFFICIENT_DATA -> null. Override paths with env `CASARECON_ALERT_HISTORY` / `CASARECON_ALERT_STATE`.

**Ack / mute** (`config/alert_state.yaml`, by `key`): `ack: {KEY: {period, note}}` marks the current
streak as seen (shown by `recon alert list`); `mute: {KEY: {until: YYYY-Www, note}}` keeps recording
the alert (`muted: true`) but does not send it while W <= until. Changes apply on the next `recon alerts`.

**Routing + dedupe** (`notify.py`): SEV2 / SEV3 -> `outbox` (+ `slack` if the severity is in
`slack.severities`); INFO / INSUFFICIENT_DATA / muted -> nothing. NEW -> `trigger`; ONGOING -> `trigger`
only if no trigger was sent earlier in its streak; RESOLVED -> `resolve`. Dedupe key = `key|period`.

Rules are pure: `(RuleInput, rule_cfg, week) -> list[dict]`. Data comes from core:
`ui_q_alerts.alert_frame` (psp x country x tier x week aggregate, incl. pending counts).
Any segment with n < `min_sample.alerts` (50) is one `INSUFFICIENT_DATA` / `INFO` row, never an alert,
so a 500-row smoke run is all `INSUFFICIENT_DATA`. Output is byte-stable (no wall-clock time).
