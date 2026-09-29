# pipeline
`recon build` (`build.main()`): the only writer of the DuckDB file.
1. Checks `data/raw/*.csv` exist (else exit 1, "run `recon generate` first").
2. Runs `dbt build` (via `adapters/dbt_runner.py`) into `<stem>_tmp.duckdb` next to the DB; dbt target/logs go to `<db dir>/.dbt/`.
3. dbt exit 1 (model or test failed) -> `DataQualityError` -> exit 5, tmp deleted, last good DB kept.
4. Logs row counts per table, `os.replace` tmp -> DB (atomic swap), writes `reports/run_manifest.json`.
