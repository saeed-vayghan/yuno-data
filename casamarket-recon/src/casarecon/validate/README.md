# validate
`recon validate` (`run.main()`): data-quality gate on the built fct, after `build`.
- `metrics.py`: one read-only SQL -> numbers. `checks.py`: pure `evaluate(metrics, full) -> [Check]`. `run.py`: prints the table, merges `reports/run_manifest.json["validate"]`.
- Always hard: brief spec (rows, 3-4 months, 4 countries/currencies, 3-5 PSPs, status mix, lag 1-7 d + outliers, metadata) and bucket shares on settled and all rows, brief range +/- 3 SE.
- Pattern bands P1-P4: hard when rows >= `full_run_min_rows`, else WARN (smoke).
- Any FAIL -> `DataQualityError` -> exit 5.
