"""Core contract rows 13-21 (used by the dashboard and alerts). Owner: BACKEND.

Implementation lives in small helper modules, re-exported here so `core.ui_q.<fn>` is the one name:
- ui_q_overview: #13 kpis, #14 weekly_trend, #15 week_over_week
- ui_q_outliers: #17 outlier_summary, #18 transaction_detail, #19 similar_count
- ui_q_drill:    #16 category_mix, #20 filter_options, #21 pending
- ui_q_base:     table name, SQL aggregate block, prev_week (weeks: pipeline_q.status + core.weeks)
- ui_q_alerts:   alert_frame (weekly grain for alerts/, not a contract row)

Every function takes `store=` (default core.deps.get_store()), runs parameterized SQL on
`marts.fct_transaction_discrepancy` (settled rows for rates/money) and returns a DataFrame / dict.
"""

from casarecon.core.queries.ui_q_drill import category_mix, filter_options, pending
from casarecon.core.queries.ui_q_outliers import outlier_summary, similar_count, transaction_detail
from casarecon.core.queries.ui_q_overview import kpis, week_over_week, weekly_trend

__all__ = ["category_mix", "filter_options", "kpis", "outlier_summary", "pending", "similar_count",
           "transaction_detail", "week_over_week", "weekly_trend"]
