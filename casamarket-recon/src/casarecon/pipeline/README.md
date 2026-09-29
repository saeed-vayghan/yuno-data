# pipeline
`recon build` (`build.main()`): the only writer of the DuckDB file.
1. Checks `data/raw/*.csv` exist (else exit 1, "run `recon generate` first").
2. Runs `dbt build` (via `adapters/dbt_runner.py`) into `<stem>_tmp.duckdb` next to the DB; dbt target/logs go to `<db dir>/.dbt/`.
3. dbt exit 1 (model or test failed) -> `DataQualityError` -> exit 5, tmp deleted, last good DB kept.
4. Logs row counts per table, `os.replace` tmp -> DB (atomic swap), writes `reports/run_manifest.json`.
5. `--incremental [--lookback-days N]`: tmp starts as a **copy** of the current DB (no DB -> exit 1), dbt updates only
   the restatement window (see `dbt/README.md`), then the same test gate + atomic swap. Tradeoff: one file copy
   (~30 MB) per run instead of writing in place, so a failed test never leaves a half-updated DB and readers are never
   locked out; at 135k rows the dbt time is about the same as a full build (tests dominate); the gain grows with history.
   Rows changed outside the window stay stale until the next full build (the default).
