# core/queries
Contract read functions split by owner. One parameterized SQL per function.
- `pipeline_q.py` (rows 1-6) and `pipeline_q2.py` (rows 7-10: segment_rates, cause_summary, excess_loss, lag_by_country_tier): INFRA.
- `ui_q.py` (13-21): BACKEND. It re-exports helper modules `ui_q_overview` (#13-15), `ui_q_outliers` (#17-19),
  `ui_q_drill` (#16, 20, 21), `ui_q_base` (table name, shared SQL, as_of / closed-week rules), `ui_q_alerts` (`alert_frame`, not a contract row).
- `reports_q.py` (22-24): BACKEND.
