"""Dashboard test fixtures: a fake `data` module (monkeypatched) so tests run without the DB."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from casarecon.dashboard import data
from tests.dashboard import fakes

APP = str(Path(data.__file__).with_name("app.py"))


@pytest.fixture
def fake_data(monkeypatch):
    """Patch every data.* reader with contract-shaped fakes; week_over_week and
    transaction_detail stay 'not built', recommendations are missing (None)."""
    patches = {
        "status": lambda: fakes.STATUS, "options": lambda: dict(fakes.OPTIONS),
        "months": lambda: fakes.STATUS["months"], "worst_week": fakes.worst_week,
        "kpis": lambda f, week="last_closed": fakes.KPIS, "weekly_trend": fakes.weekly_trend,
        "week_over_week": fakes.not_built, "transactions": fakes.transactions,
        "transactions_csv": lambda f, m=None: fakes.transactions(f, m).to_csv(index=False).encode(),
        "outlier_summary": fakes.outlier_summary, "alerts": lambda: None,
        "segment_rates": fakes.segment_rates, "category_mix": fakes.category_mix,
        "cause_summary": fakes.cause_summary, "excess_loss": fakes.excess_loss,
        "findings": lambda: fakes.FINDINGS, "recommendations": lambda: None,
        "transaction_detail": fakes.not_built, "similar_count": fakes.similar_count,
    }
    for name, fn in patches.items():
        monkeypatch.setattr(data, name, fn)
    return patches


@pytest.fixture
def app():
    return AppTest.from_file(APP, default_timeout=30)
