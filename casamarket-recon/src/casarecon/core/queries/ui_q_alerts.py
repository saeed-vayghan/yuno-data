"""alert_frame: the one weekly aggregate the alert rules need (BACKEND; helper, not a contract row).

Grain: psp x country x amount_tier x ISO week, settled + pending rows. Small (~1k rows), so every
rule window / peer group is a pandas groupby on this frame (alerts/ stays pure, no SQL there).
"""

import pandas as pd

from casarecon.core.metrics import FLAGGED_SQL, LARGE_SQL, OVER_SQL, SETTLED_SQL, UNDER_SQL
from casarecon.core.queries.ui_q_base import AS_OF, FCT, store_of
from casarecon.ports import Store

ALERT_FRAME_COLS = ["psp", "country", "amount_tier", "auth_week", "n", "n_flagged", "n_large",
                    "large_usd", "gross_under_usd", "gross_over_usd", "settled_usd", "n_open",
                    "n_open_old", "n_late"]

_S = SETTLED_SQL
_AGE = "date_diff('second', auth_ts, a.as_of) / 86400.0"  # days since auth, vs as_of


def alert_frame(late_days: float, pending_days: float = 7, *,
                store: Store | None = None) -> pd.DataFrame:
    """n* = settled counts; n_open = pending; n_open_old = pending older than pending_days;
    n_late = settled lag > late_days or pending age > late_days. Ages vs as_of (data time)."""
    return store_of(store).query(
        f"with a as ({AS_OF}) select psp, country, amount_tier, auth_week, "
        f"count(*) filter (where {_S}) as n, "
        f"count(*) filter (where {_S} and {FLAGGED_SQL}) as n_flagged, "
        f"count(*) filter (where {_S} and {LARGE_SQL}) as n_large, "
        f"round(coalesce(sum(abs_residual_usd) filter (where {LARGE_SQL}), 0), 2) as large_usd, "
        f"round(coalesce(sum({UNDER_SQL}) filter (where {_S}), 0), 2) as gross_under_usd, "
        f"round(coalesce(sum({OVER_SQL}) filter (where {_S}), 0), 2) as gross_over_usd, "
        f"round(coalesce(sum(settled_usd) filter (where {_S}), 0), 2) as settled_usd, "
        "count(*) filter (where status = 'pending') as n_open, "
        f"count(*) filter (where status = 'pending' and {_AGE} > ?) as n_open_old, "
        f"count(*) filter (where ({_S} and settle_lag_days > ?) or (status = 'pending' "
        f"and {_AGE} > ?)) as n_late "
        f"from {FCT}, a where status in ('settled', 'pending') "
        "group by psp, country, amount_tier, auth_week order by psp, country, amount_tier, auth_week",
        [float(pending_days), float(late_days), float(late_days)])[ALERT_FRAME_COLS]
