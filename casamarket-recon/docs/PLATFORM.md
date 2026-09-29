# Local dev workflow

Everything runs on one machine. No cloud, no servers.

## Daily loop
```bash
make all          # default path: raw CSV -> dbt (full rebuild) -> validate -> analyze -> alerts -> report
make lake         # lake path: ingest land -> load -> check, then build with CASARECON_SOURCE=lake
make dev-check    # PII scan + lineage summary
make test         # pytest on a 500-row fixture DB
```

## Replay / backfill
`uv run recon ops backfill --from 2026-06-01 --to 2026-06-07 --dry-run` prints the steps; drop
`--dry-run` to run them:
0. The range must have landing files (`data/lake/landing/psp=*/date=D/`), else exit 1.
1. `recon ingest load`: loads new or changed landing files (a PSP re-sent a day) into staged.
   Unchanged files are skipped by hash.
2. `recon ingest check --as-of D2`: freshness, volume and schema-drift checks.
3. `CASARECON_SOURCE=lake recon build --incremental --lookback-days N`, with N = days from `--from`
   to the data as-of (the latest timestamp in the DB, or `--as-of`). So every replayed day is inside
   the restatement window and is rebuilt.
A step that fails a data-quality check stops the replay with exit 5; the last good DB is kept.
Example: replace a PSP's file for one day in `landing/`, then
`uv run recon ops backfill --from D --to D`; the fact table shows the corrected amounts.

## Lineage
`uv run recon ops lineage` runs `dbt docs generate` and writes `reports/lineage/LINEAGE.md`
(each model, its parents, its upstream sources/seeds, and a mermaid graph). The full dbt docs site
is in `data/.dbt/lineage/target`: `cd data/.dbt/lineage/target && python -m http.server 8080`.

## PII rules
- `customer_id` is a token (`pii: token` in the contract). Raw files and the lake may hold it.
- Outputs (`reports/`, `data/alerts/`) show only masked IDs (`cus_••••7f3a`, `core/privacy.mask_id`).
- Banned fields (`banned_fields` in `contracts/*.yaml`: pan, card_number, cvv, email, name) must not
  be a record field anywhere (CSV column, parquet column, JSONL key): raw, lake (landing,
  quarantine, staged), reports, alerts.
- `uv run recon ops pii-scan` checks both rules and exits 5 on a hit. It never prints a full ID.
