# generate

Seeded synthetic data -> `data/raw` (dbt sources) and `data/truth` (labels dbt never reads).
Entry: `run.main(rows, seed)`. Run: `uv run recon generate [--rows 500] [--seed 42]` (defaults from `config/generator.yaml`).

| Output | Content |
|---|---|
| `data/raw/transactions.csv` | columns of `contracts/transactions.yaml`, in that order, sorted by `transaction_id`; money = int minor units (CLP 0 dp) |
| `data/raw/fx_rates_daily.csv` | `rate_date, currency, local_per_usd` (6 dp), every day of the window + 15 days |
| `data/raw/generation_manifest.json` | seed, rows, window, realized status/bucket/cause mix, package versions (no clock time) |
| `data/truth/labels.parquet` | `transaction_id, true_bucket, true_cause, pattern_ids` (e.g. `P1;X6`) |

## Flow (all pure except `writer.py`; one `numpy` RNG, fixed call order -> same bytes per seed)
| Module | Does |
|---|---|
| `fx.py` | capped daily random walk per currency (every step ≤ 0.13%, so any 15-day move < 2%) |
| `rows.py` | base rows: ids, country/currency, PSP, cross-border (payer USD), tier then amount, items, risk, lag |
| `settle.py` | authorized amount, P2 lag, as-of status (settle after window end -> `pending`), `expected_settled` via `core.money` |
| `patterns.py` | P4 first (PSP_D cross-border CLP/COP floored to 1,000 major units), then buckets, causes, sizes |
| `buckets.py` | hit 67/1/18/10/4 on settled rows (incl. P4); P1 and the X3 drift add points to `meaningful`; P3 weekend × 1.3 |
| `causes.py` | cause that fits bucket and row (X1–X6, `rounding`), sized inside the bucket limits with a safety margin |
| `classify.py` | the dbt category rule in numpy, so `true_bucket` = what SQL computes |
| `truth.py` | labels + realized mix |
| `writer.py` | the only I/O |

## Notes
- `pending` comes only from the as-of rule (auth late in June), so its share is ~3.8%, not a random 3%.
- A few cross-border rows (~0.2%) land in `exact`/`rounding` when the FX walk returns to the same level; truth keeps the realized bucket.
- Sample: `data/sample/transactions_500.csv`, `fx_rates_daily.csv`, `labels_500.parquet` (= `--rows 500 --seed 42`).
