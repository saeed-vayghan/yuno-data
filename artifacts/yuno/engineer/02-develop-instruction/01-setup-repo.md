# 01 · Set up the repo

**Goal:** one locked Python 3.12 env, the repo skeleton, a Makefile and a `recon` CLI with 10 stub commands.

**Time box:** 10 min · **Core**

## Inputs
- IMPLEMENTATION-PLAN S0.1, S0.3, S0.4 (repo layout, contract, CLI skeleton).
- Diagram: `../../architect/03-system-design/01-high-level.svg`, `07-run-and-ci.svg`.

## Steps

1. **Create the project** (repo root = `casamarket-recon/`):
   ```bash
   uv python install 3.12
   uv init --package casarecon --python 3.12
   echo "3.12" > .python-version
   ```

2. **Add pinned dependencies:**
   ```bash
   uv add "duckdb>=1.4,<1.5" "dbt-core>=1.12,<1.13" "dbt-duckdb>=1.11,<1.12" \
          numpy pandas scipy statsmodels "typer>=0.27" "streamlit>=1.40" plotly kaleido \
          pydantic pyyaml jinja2
   uv add --dev pytest
   ```
   | Package | Pin | Why |
   |---|---|---|
   | Python | 3.12 | brief stack |
   | duckdb | 1.4.x LTS | one file DB; LTS support ends 17 Nov 2026 |
   | dbt-core / dbt-duckdb | 1.12.x / 1.11.x | staging → marts + tests |
   | scipy, statsmodels | latest | chi²/Fisher, Wilson, BH, GLM |
   | typer | ≥ 0.27 | `recon` CLI |
   | streamlit | ≥ 1.40 | `st.navigation`, `st.dataframe(on_select=…)` used by the UI plan |
   | plotly + kaleido | latest | figures; PNG is best-effort |
   | pydantic, pyyaml, jinja2 | latest | config models, YAML, report templates |

3. **Pre-flight version check (do not skip):**
   ```bash
   uv sync
   uv run python -c "import duckdb; print('duckdb', duckdb.__version__); duckdb.sql('select 1').fetchall()"
   uv run dbt --version        # must list core 1.12.x and plugin duckdb 1.11.x
   uv run python -c "import scipy, statsmodels, typer, streamlit, plotly; print('ok')"
   ```
   Fallback if it fails:
   | Symptom | Fix |
   |---|---|
   | `uv add` cannot resolve duckdb `<1.5` with dbt-duckdb 1.11 | Remove the duckdb pin, let dbt-duckdb pick its duckdb; write the resolved version in README `### Assumptions` |
   | dbt-core 1.12 not found / incompatible with dbt-duckdb 1.11 | Pin dbt-core to the newest minor that dbt-duckdb 1.11 accepts (`uv add "dbt-core>=1.10,<1.12"`) |
   | `uv python install` blocked | Use a system Python 3.12; `uv venv --python /path/to/python3.12` |
   | kaleido install fails | Drop kaleido; figures write HTML only (see file 07) |
   Record the final versions: `uv pip list | grep -Ei 'duckdb|dbt-|statsmodels|streamlit'`.

4. **Entry point** in `pyproject.toml`:
   ```toml
   [project.scripts]
   recon = "casarecon.cli:app"
   ```

5. **Create the layout** (empty `__init__.py` in each package):
   ```
   config/  contracts/  dbt/  data/sample/  reports/figures/  reports/analysis/  tests/
   src/casarecon/{core,generate,analysis,alerts,report/templates,dashboard/pages}/
   ```
   Full tree: IMPLEMENTATION-PLAN "Repo layout".

6. **`.gitignore`:**
   ```
   .venv/
   __pycache__/
   data/raw/
   data/truth/
   data/*.duckdb
   data/*.duckdb.wal
   data/*.duckdb.tmp
   dbt/target/
   dbt/logs/
   .env
   ```
   Do **not** ignore `reports/` or `data/sample/` (they are committed).

7. **`.env.example`:**
   ```
   CASARECON_DB=data/casarecon.duckdb
   SLACK_WEBHOOK_URL=
   ```

8. **Contract** `contracts/transactions.yaml` (IMPLEMENTATION-PLAN S0.3): one entry per column with `type`, `nullable`, `enum`, `unit`, `pii`; plus `banned_fields: [pan, card_number, cvv, email, name]`. Columns: `transaction_id, customer_id, product_category, country, currency, payer_currency, is_cross_border, psp, status, auth_ts, settle_ts, authorized_amount, settled_amount, item_count, risk_score, card_bin_country`.

9. **CLI skeleton** `src/casarecon/cli.py`: 10 commands (`generate build validate analyze alerts report query worst-week dashboard all`), each a stub that prints "not built yet" and exits 1. Global `--verbose`. Details and exit codes: file 09.

10. **Logging** `src/casarecon/core/log.py`: stdlib `logging` to stderr, one `key=value` line per step, e.g. `step=build layer=staging rows=135000 secs=3.1`.

11. **Makefile:**
    ```make
    .PHONY: all smoke generate build validate analyze alerts report app test clean
    all:      ; uv run recon all
    smoke:    ; uv run recon all --rows 500
    generate: ; uv run recon generate
    build:    ; uv run recon build
    validate: ; uv run recon validate
    analyze:  ; uv run recon analyze
    alerts:   ; uv run recon alerts
    report:   ; uv run recon report
    app:      ; uv run recon dashboard
    test:     ; uv run pytest -q
    clean:    ; rm -rf data/raw data/truth data/*.duckdb data/*.duckdb.wal data/*.duckdb.tmp dbt/target dbt/logs
    ```

12. `git init && git add -A && git commit -m "scaffold"`.

## Done when
| Command | Expected |
|---|---|
| `uv sync --frozen && uv run python -c "import duckdb, dbt, statsmodels"` | exit 0 |
| `uv run dbt --version` | core 1.12.x, duckdb plugin 1.11.x (or the documented fallback) |
| `uv run recon --help` | lists 10 commands |
| `uv run recon build; echo $?` | prints "not built yet", then `1` |
| `uv run python -c "import yaml; yaml.safe_load(open('contracts/transactions.yaml'))"` | exit 0 |

## Serves
Deliverable 1 (working code, run instructions) · Tech 15 (locked deps, reproducible) · constraint "runnable locally".

## Pitfalls
- `uv.lock` must be committed; every later command uses `uv sync --frozen` / `uv run`.
- Do not `pip install` into the venv by hand; the lock file will drift.
- The Makefile needs **tabs** if you use multi-line recipes; the one-line `target: ; cmd` form above avoids that.
- Streamlit < 1.36 has no `st.navigation`; keep `>= 1.40`.
- dbt writes `dbt/target` and `dbt/logs` next to the project; they must stay ignored.

## Hand-off
- File 02 gets an importable `casarecon` package with `core/` ready for modules.
- Every later file wires its own CLI command into the stub.
