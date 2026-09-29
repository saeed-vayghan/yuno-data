# Streaming path (local dev): Redpanda + Flink SQL

The batch pipeline (dbt on DuckDB) categorises each transaction once a day. This path shows the same
rules running **as events arrive**: an authorization and its settlement meet in Flink, and the category
is known the moment the settlement lands. Local only; nothing is deployed.

```
data/raw/transactions.csv ──recon stream replay──► Redpanda topics  auths, settlements
data/raw/fx_rates_daily.csv, dbt/seeds/currency_exponents.csv ─────► Flink (bounded CSV tables)
Flink SQL (infra/stream/sql/match.sql):
  auths ⋈ settlements (interval join, ≤ 15 days) ⋈ FX(auth day) ⋈ FX(settle day)
  → expected_settled, residual, residual_pct, residual_usd, category
  → data/lake/stream/matched/*.csv   (every matched row)
  → topic large_discrepancies        (category = large)
recon stream compare: matched CSV vs batch marts.fct_transaction_discrepancy (same transaction_id)
```

## Run
```bash
make all                       # batch DB + data/raw (compare needs both)
make stream-up                 # Redpanda :19092, Flink UI http://localhost:8081, topics created
make stream-job                # submit match.sql with the Flink SQL client (job keeps running)
make stream-replay             # first 20k events, 1 event-day per second (STREAM_LIMIT / STREAM_SPEED)
sleep 20                       # the CSV sink commits files on each 10 s checkpoint
make stream-compare            # category match per category; exit 5 if < 99 %
make stream-tail               # optional: print large_discrepancies
make stream-down
```
`recon stream replay --speed N --limit N --bootstrap host:port` · `recon stream compare` · `recon stream tail`.
Kafka commands use `kafka-python` through `uv run --with kafka-python` (not a project dependency yet).

Last local run (20k events = 12,767 auths + 7,233 settlements, 2026-04-01 → 04-09): 7,233 matched rows,
category match 100 % (exact 4,900 · fx_tolerance 1,296 · meaningful 670 · large 272 · rounding 95),
272 messages on `large_discrepancies`. Compare needs `data/raw` and the DB from the same `make all`.

## What it proves
- The batch rules can run per event with no batch window: first-match-wins category, rounding ≤ 1 minor
  unit, fx_tolerance ≤ 2 % and < $20, meaningful 2–5 % and < $20, large > 5 % or ≥ $20.
- `recon stream compare` checks the streaming category equals the batch category for the same
  transaction_id (≥ 99 % required; differences can only come from float rounding at a cut-off).

## Mapping to the batch model
| Batch (dbt) | Stream (Flink SQL) |
|---|---|
| `stg_transactions` rows | `auths` event at auth_ts (`authorized` / `failed`) + `settlements` event at settle_ts (settled rows only) |
| `int_transactions_usd`: FX on auth day and settle day, currency exponent | regular joins with the bounded `fx_rates` / `currency_exponents` CSV tables |
| `expected_settled_sql()` | same CASE: `round(authorized_amount * fx_settle / fx_auth, 0)` if cross-border |
| `residual`, `residual_pct` (4 dp), `residual_usd` (auth-day rate, 2 dp) | same formulas, DOUBLE maths |
| `category_case()` (`dbt/macros/discrepancy_rules.sql`, `config/thresholds.yaml`) | the same CASE text; `tests/infra/test_stream.py` renders the macro and asserts it appears in `match.sql` |
| pending / failed rows (category null) | no settlement event → no match (failed auths are filtered) |
| not covered | likely_cause (needs window counts over all rows), weekly marts, alerts |

The interval join window (15 days) = the maximum settle lag in the data (`lag_cap_days`), so every
settled row can match. Kafka offsets start at `earliest`, so `stream-job` may run before or after the replay.

## Memory (Docker has ~2 GB)
| Service | Setting | Cap (`mem_limit`) | Seen |
|---|---|---|---|
| Redpanda | `--mode dev-container --smp 1 --memory 400M` | 600m | ~110-160 MB |
| Flink jobmanager | `jobmanager.memory.process.size: 512m` (metaspace 128m) | 600m | ~325 MB |
| Flink taskmanager | `taskmanager.memory.process.size: 768m`, 1 slot, managed 64m | 850m | ~410-425 MB with the job running |
| SQL client (one-shot) | `-Xmx192m` | 350m | exits after submit |

Total with the job running: ~0.9 GB. `make stream-up` names its services, because a bare
`docker compose --profile stream up` also starts the default `recon` app. The stack does not fit next to
an Airflow run (`--profile airflow`, ~0.8-1 GB): run one at a time,
or the VM OOM-kills the Flink JVMs (exit 137).

## Notes
- Re-submitting the job appends new files to `data/lake/stream/matched/`; compare keeps the last row per
  transaction_id. `rm -rf data/lake/stream` for a clean run.
- Port 8081 taken on the host? `FLINK_UI_PORT=8082 make stream-up`.
- `make stream-down` removes only the stream containers (topics and job state go too; sink files stay).
- The replay limit cuts by event time, so late auths in the window have no settlement yet (unmatched,
  not compared). Compare only looks at matched rows.
