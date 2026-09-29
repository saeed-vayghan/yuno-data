# ingest

Local lake for PSP settlement files: landing -> contract check -> staged parquet (or quarantine),
plus arrival data-quality checks. Local folder only; `storage.py` is the one seam to swap later.

```bash
uv run recon generate && uv run recon ingest land && uv run recon ingest load && uv run recon ingest check
CASARECON_SOURCE=lake uv run recon build     # dbt reads staged parquet instead of data/raw CSVs
```

## Lake layout (`data/lake`, or env `CASARECON_LAKE_DIR`; default `<CASARECON_RAW_DIR>/../lake`)
| Zone | Path | Written by |
|---|---|---|
| landing | `landing/psp=<PSP>/date=<YYYY-MM-DD>/settlements.csv`, `landing/reference/fx_rates_daily.csv` | `land` |
| staged | `staged/transactions/settle_month=<YYYY-MM>/part-<PSP>-<date>.parquet`, `staged/fx_rates_daily/fx_rates_daily.parquet` | `load` |
| quarantine | `quarantine/psp=<PSP>/date=<date>/settlements.csv` + `reason.json` | `load` |
| manifest | `_manifest.jsonl` (file, sha256, rows, status, target) | `load` |

## Commands
| Command | Does |
|---|---|
| `recon ingest land [--no-reset]` | splits `data/raw/transactions.csv` into one file per PSP and report day (settle date, or auth date for pending/failed rows), each in its PSP's format. Resets the lake first (a new `generate` = a new delivery history). |
| `recon ingest load` | parses each new/changed file with its format adapter, checks it against `contracts/*.yaml` (columns, banned fields, types, nulls, enums, min/max, psp = folder). Good file -> one parquet part. Bad file -> quarantine with `reason.json` (all-or-nothing per file; banned columns are dropped before the copy is kept). Same sha256 again -> skipped. `--from D1 --to D2` forces the files of those dates again (replay/backfill), also quarantined ones; a file that now passes leaves quarantine. |
| `recon ingest check [--as-of D]` | freshness (latest file per PSP vs as_of, FAIL -> exit 5), volume (settled rows per PSP-day vs the median of the previous 7 days, ±50%, WARN), schema drift (new/missing columns vs the contract, WARN), quarantined files (WARN). Writes `reports/ingest_dq.json`. |

## Files
| Module | Role |
|---|---|
| `settings.py` | `config/ingest.yaml`, contracts, lake keys |
| `formats.py` | PSP format adapters (pure): `standard` (PSP_A-C) and `legacy` (PSP_D/E: renamed columns, `dd/mm/yyyy`, `;`) |
| `contract.py` | contract check + typing to Arrow (pure) |
| `dq.py` | freshness / volume / drift checks (pure) |
| `storage.py` | `LocalStorage` adapter (the only file I/O) |
| `land.py`, `load.py`, `check.py` | entry `main()` per command; `cli.py` = Typer group |
