# 10 · Run paths, idempotency, Docker, CI

**Goal:** the reviewer can run everything 3 ways (`make all`, `pip install uv && uv run recon all`, `docker compose up`), and a rerun gives the same output.

**Time box:** part A 5 min · part B 15 min (Docker 10, CI 5)
**Tag:** A (make, idempotency, test fixture) **Core** · B (Docker, CI) **Packaging** (CI is first in the cut order)

## Inputs
- Files 01–09 · IMPLEMENTATION-PLAN S4.2, S6.1–S6.3 · decision sheet "Run and tools".
- Diagram: `../../architect/03-system-design/07-run-and-ci.svg`.

## Steps

### Part A (Core)

1. **Test fixture** `tests/conftest.py`: a session fixture that runs generate (500 rows, seed 42) + build into a `tmp_path` DB, sets `CASARECON_DB` (and raw/reports dirs) to that temp location, and yields the path. All core/CLI/alert tests use it. Never touch `data/casarecon.duckdb` from tests.

2. **Run path 1:** `make clean && make all` (full 135k run).

3. **Idempotency check** (run twice, compare):
   ```bash
   make all && shasum -a 256 data/raw/transactions.csv reports/findings.json > /tmp/h1
   make all && shasum -a 256 data/raw/transactions.csv reports/findings.json > /tmp/h2
   diff /tmp/h1 /tmp/h2 && echo IDEMPOTENT
   ```
   Also add `tests/test_e2e.py`: `recon all --rows 500` twice → identical hash of
   `COPY (SELECT * FROM marts.fct_transaction_discrepancy ORDER BY transaction_id) TO 'fct.csv'`, identical `findings.json`, and all smoke alerts `INSUFFICIENT_DATA`.

4. **Run path 2** (no make): `pip install uv && uv run recon all` from a clean clone.

5. **`make test`** must be green before the core checkpoint.

### Part B (Packaging)

6. **`Dockerfile`:**
   ```dockerfile
   FROM python:3.12-slim
   COPY --from=ghcr.io/astral-sh/uv:0.X.Y /uv /usr/local/bin/uv    # pin to your local `uv --version`
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   RUN uv sync --frozen --no-dev --no-install-project
   COPY . .
   RUN uv sync --frozen --no-dev && useradd -m app && chown -R app /app
   USER app
   ENV PATH="/app/.venv/bin:$PATH" CASARECON_DB=/app/data/casarecon.duckdb
   EXPOSE 8501
   CMD ["sh", "-c", "recon all && recon dashboard --host 0.0.0.0"]
   ```
   `.dockerignore`: `.venv`, `data/raw`, `data/truth`, `data/*.duckdb*`, `dbt/target`, `dbt/logs`, `.git`.

7. **`docker-compose.yml`:**
   ```yaml
   services:
     recon:
       build: .
       ports: ["8501:8501"]
       volumes: ["./data:/app/data", "./reports:/app/reports"]
   ```

8. **CI** `.github/workflows/ci.yml` (optional): checkout → `astral-sh/setup-uv` → `uv sync --frozen` → `make test` → `make smoke` → `docker build .`.

9. **Security tests** `tests/test_security.py`: no banned field names in raw CSV headers or marts; no 13–19 digit runs (PAN-like) in `data/raw` or `reports/`; `query` rejects unknown filters; no unmasked `customer_id` in `reports/` or CLI CSV.

10. **Fresh-clone walk** (S6.3): in a temp dir, `git clone … && make all`; then `uv run recon all`; then `docker compose up`. Fix README for anything that did not work as written.

## Done when
| Command | Expected |
|---|---|
| `make clean && time make all` | exit 0, ~1–2 min |
| idempotency script (step 3) | prints `IDEMPOTENT` |
| `make test` | all green |
| `make smoke` | exit 0 in < 30 s |
| `docker compose up` then `curl -sf localhost:8501 >/dev/null && echo UP` | `UP` after `recon all` finishes |
| CI run on push | green (if built) |

## Serves
Done "reproducibility" · Tech 15 (3 run paths from a fresh clone, idempotent reruns, tests) · constraints "runnable locally", "dashboard on localhost", "Docker available".

## Pitfalls
- **Byte-stable outputs:** no timestamps in `findings.json`, `alerts.jsonl` or the generator CSVs; timestamps only go in `run_manifest.json` (not hashed). PNGs are not byte-stable; never hash them.
- **Row order:** DuckDB with 4 threads returns rows in any order unless you `ORDER BY`.
- **Docker + Streamlit address:** `.streamlit/config.toml` sets `address = "localhost"` (UI plan); inside a container that makes the app unreachable. Always pass `--host 0.0.0.0` in Docker only.
- **Non-root user** needs write access to `/app/dbt/target`, `/app/dbt/logs`, `/app/data`, `/app/reports` (`chown -R app /app`). Host-mounted volumes may need `user: "${UID}:${GID}"` on Linux.
- **kaleido/Chrome** is usually missing in `python:3.12-slim`: figures fall back to HTML; the committed PNGs come from your own run.
- `uv sync --frozen` fails if `uv.lock` is stale: rerun `uv lock` locally and commit.
- The volumes overwrite `reports/` with the container's run; that is expected (same seed → same numbers).
- Do not run tests against `data/casarecon.duckdb`; a dashboard holding it open causes lock errors.

## Hand-off
- File 11 copies the exact 3 commands into README "Quick start".
- Frontend: `tests/conftest.py` fixture DB for Streamlit `AppTest`; `make app` / `recon dashboard` serve `localhost:8501`.
