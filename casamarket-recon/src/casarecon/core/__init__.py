"""casarecon.core: the one read-only API used by CLI, analysis, alerts and dashboard.

`from casarecon import core; core.worst_week("last")`. See the CORE API CONTRACT.
"""

from casarecon.core.errors import BadFilter, CasaReconError, DataQualityError, DbBusy, DbMissing
from casarecon.core.filters import Filters
from casarecon.core.money import exponent, expected_settled, round_half_up, to_major
from casarecon.core.privacy import mask_id
from casarecon.core.queries.pipeline_q import (
    TXN_COLUMNS, connect, db_version, psp_weekly, query_transactions, status, worst_week,
)
from casarecon.core.queries.pipeline_q2 import (
    cause_summary, excess_loss, lag_by_country_tier, segment_rates, settled_facts,
)
from casarecon.core.queries.reports_q import load_alerts, load_findings, load_recommendations
from casarecon.core.queries.ui_q import (
    category_mix, filter_options, kpis, outlier_summary, pending, similar_count, transaction_detail,
    week_over_week, weekly_trend,
)

__all__ = [
    "BadFilter", "CasaReconError", "DataQualityError", "DbBusy", "DbMissing", "Filters", "TXN_COLUMNS",
    "cause_summary", "category_mix", "connect", "db_version", "excess_loss", "expected_settled",
    "exponent", "filter_options", "kpis", "lag_by_country_tier", "load_alerts", "load_findings",
    "load_recommendations", "mask_id", "outlier_summary", "pending", "psp_weekly", "query_transactions",
    "round_half_up", "segment_rates", "settled_facts", "similar_count", "status", "to_major", "transaction_detail",
    "week_over_week", "weekly_trend", "worst_week",
]
