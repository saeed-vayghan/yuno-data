# adapters
Concrete implementations of `ports.py`; the only place with I/O libraries.
- `duckdb_store.py`: `DuckDbStore(path)`, short read-only connections; DATE columns -> `datetime.date`; lock -> `DbBusy`, missing -> `DbMissing`.
- `dbt_runner.py`: `run_dbt(args, env)` runs the venv's `dbt` from `dbt/`, output to stderr, returns the exit code.
- `files.py` (json/md/jsonl): BACKEND.
- `notify_slack.py` (the optional alert channel, off by default; used by `core.deps.get_notifier`): ALERTS. The local alert outbox is `reports/notifications.jsonl` (written by `alerts/sink.py`).
