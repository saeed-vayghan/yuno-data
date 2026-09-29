"""infra/airflow DAGs: parsed with plain `ast` (Airflow is not a project dependency)."""

import ast
from pathlib import Path

DAGS = Path(__file__).resolve().parents[2] / "infra" / "airflow" / "dags"


def _tree(name: str) -> ast.Module:
    return ast.parse((DAGS / name).read_text())


def _calls(tree: ast.Module, func: str) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == func]


def _kw(call: ast.Call) -> dict[str, object]:
    return {k.arg: k.value.value for k in call.keywords if isinstance(k.value, ast.Constant)}


def test_daily_dag_runs_recon_steps_in_order():
    tree = _tree("casarecon_daily.py")
    (dag,) = _calls(tree, "DAG")
    want = {"dag_id": "casarecon_daily", "schedule": "@daily", "catchup": False, "max_active_runs": 1}
    assert want.items() <= _kw(dag).items()
    tasks = _calls(tree, "recon")
    ids = [c.args[0].value for c in tasks]
    assert ids == ["ingest_land", "ingest_load", "ingest_check", "build", "validate",
                   "analyze", "alerts", "report"]
    kw = {c.args[0].value: _kw(c) for c in tasks}
    assert kw["validate"]["retries"] == 0 and kw["ingest_check"]["retries"] == 0  # DQ gates: no retry
    assert kw["ingest_load"]["trigger_rule"] == "none_failed"  # runs when ingest_land is skipped
    # tasks are chained one after another: `for up, down in zip(steps, steps[1:]): up >> down`
    assert any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.RShift) for n in ast.walk(tree))
    src = (DAGS / "casarecon_daily.py").read_text()
    assert "--incremental --lookback-days" in src and "params.full_refresh" in src


def test_backfill_dag_calls_ops_backfill():
    tree = _tree("casarecon_backfill.py")
    (dag,) = _calls(tree, "DAG")
    assert _kw(dag)["dag_id"] == "casarecon_backfill" and _kw(dag)["schedule"] is None
    (task,) = _calls(tree, "BashOperator")
    assert _kw(task)["task_id"] == "backfill" and _kw(task)["retries"] == 0
    assert "recon ops backfill" in ast.unparse(task) and "params['from']" in ast.unparse(task)
