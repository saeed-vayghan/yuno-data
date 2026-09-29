# infra/stream: local Redpanda + Flink SQL (profile `stream`, off by default)

Streams auth / settlement events and categorises each settled transaction with the batch dbt rules.
Full guide: [docs/STREAM.md](../../docs/STREAM.md). Owner: STREAM.

| File | What |
|---|---|
| `compose.yml` | Redpanda (1 node, `--memory 400M`), topic init, Flink jobmanager + taskmanager (1 slot), one-shot `sql-client` (profile `stream-job`) |
| `flink.Dockerfile` | `flink:1.20.3-java17` + Kafka SQL connector jar from Maven Central (filesystem + CSV/JSON ship with Flink) |
| `sql/match.sql` | interval join auths ⋈ settlements, FX, residual, category → CSV sink + `large_discrepancies` topic |
| `targets.mk` | `make stream-up / stream-job / stream-replay / stream-compare / stream-tail / stream-down` |

Python side: `src/casarecon/stream/` (`recon stream replay | compare | tail`).
Ports: Kafka `localhost:19092`, Flink UI `http://localhost:8081`.
