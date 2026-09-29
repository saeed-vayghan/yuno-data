# ops (`recon ops`)

Local dev tooling. Owner: DEV-OPS. Exit codes as in the main CLI (0 ok, 1 error, 2 usage, 5 data quality).

| Command | What it does | Output |
|---|---|---|
| `recon ops lineage` | `dbt docs generate` (empty catalog, no DB touched) + a model → sources summary | `reports/lineage/LINEAGE.md`, docs site in `data/.dbt/lineage/target` |
| `recon ops pii-scan` | Banned fields (from `contracts/*.yaml`) as a CSV/parquet column or JSONL key anywhere; full customer IDs in outputs | exit 5 on a hit |
| `recon ops backfill --from D1 --to D2 [--as-of D] [--dry-run]` | `recon ingest load` → `recon ingest check --as-of D2` → `CASARECON_SOURCE=lake recon build --incremental --lookback-days N` (N reaches back to D1) | the replayed DB |

Files: `cli.py` (Typer shell) · `lineage.py` · `pii.py` · `backfill.py` (pure `plan()` + runner) ·
`shell.py` (the only subprocess call). Backfill uses other groups only through the `recon` command line.
