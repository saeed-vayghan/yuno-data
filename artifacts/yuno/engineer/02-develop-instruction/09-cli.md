# 09 · CLI (`recon`)

**Goal:** one Typer app, `recon`, a thin shell over `casarecon.core` and the step modules: 10 commands, fixed exit codes, and both brief questions answerable from the terminal.

**Time box:** part A 5 min · part B 10 min
**Tag:** A (`all`, exit codes) **Core** · B (`worst-week`, `query`, `dashboard`) **Stretch** (first stretch step)

## Inputs
- File 01 (stub CLI), files 02–08 (each step function).
- Research 05 · decision sheet "Run and tools" · IMPLEMENTATION-PLAN S0.4, S4.2, S4.3 · DELIVERABLES-CHECK fix #10 (`--format json`, `> 50`).
- Diagram: `../../architect/03-system-design/06-cli-and-dashboard.svg`.

## Commands

| Command | Calls | Options | Writes DB? |
|---|---|---|---|
| `recon generate` | `generate.writer.run()` | `--rows N`, `--seed S` | no |
| `recon build` | `core.build.run_build()` | – | **yes (only one)** |
| `recon validate` | `generate.validate.run_validate()` | – | no |
| `recon analyze` | `analysis.findings.run()` | – | no |
| `recon alerts` | `alerts.evaluate.run()` | – | no |
| `recon report` | `report.render.run()` | – | no |
| `recon query` | `core.query_transactions()` | `--min-usd 50`, `--psp`, `--country` (repeatable), `--limit`, `--format table\|csv\|json` | no |
| `recon worst-week` | `core.worst_week()` | `--month last\|YYYY-MM`, `--format table\|json` | no |
| `recon dashboard` | `streamlit run src/casarecon/dashboard/app.py` | `--port 8501`, `--host localhost` | no |
| `recon all` | generate → build → validate → analyze → alerts → report | `--rows N`, `--seed S` | via build |

Global: `--verbose` (DEBUG logs).

## Steps

### Part A (Core)

1. **Exit codes** in one place:
   ```python
   EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_DQ = 0, 1, 2, 5

   def run_step(fn, *a, **kw):
       try:
           return fn(*a, **kw)
       except DataQualityError as e: log.error("step failed: %s", e); raise typer.Exit(EXIT_DQ)
       except BadFilter as e:        typer.echo(str(e), err=True);   raise typer.Exit(EXIT_USAGE)
       except DbMissing:             typer.echo("No data yet. Run `make all` first.", err=True); raise typer.Exit(EXIT_ERROR)
       except DbBusy:                typer.echo("rebuilding, retry", err=True); raise typer.Exit(EXIT_ERROR)
       except Exception:             log.exception("unexpected error"); raise typer.Exit(EXIT_ERROR)
   ```
   Typer/Click already exits 2 on bad options.

2. **`recon all`**: call the 6 steps in order through `run_step`; stop at the first non-zero exit; pass `--rows/--seed` to `generate`. Log one line per step with seconds. Until file 08 exists, `alerts` logs "skipped".

### Part B (Stretch, right after the core checkpoint)

3. **`recon worst-week --month last [--format table|json]`** → `core.worst_week(month)`.
   - Table: rank, PSP, ISO week + dates, net USD loss, gross under, flag rate, n; low-sample rows greyed ("low sample") and ranked last.
   - JSON (used by the UI consistency test):
     ```json
     {"month": "2026-06", "worst": {"psp": "PSP_B", "auth_week": "2026-W24", "week_start": "2026-06-08",
      "week_end": "2026-06-14", "n": 2410, "rate": 0.162, "net_usd": 4210.55, "gross_under_usd": 4902.10,
      "low_sample": false}, "ranking": [ ... same keys + "rank" ... ]}
     ```

4. **`recon query --min-usd 50 [--psp PSP_B] [--country AR] [--limit N] [--format table|csv|json]`** → `core.query_transactions(Filters(...), min_usd, limit)`.
   - Filter `abs_residual_usd > min_usd` (strict), sorted desc.
   - CSV header = TXN_COLUMNS (core contract); customer IDs already masked by core.
   - Table mode prints the first 50 rows + "N rows; use --format csv for all".
   - Unknown PSP/country → `BadFilter` → exit 2.

5. **`recon dashboard`**: `subprocess.run(["streamlit", "run", APP, "--server.port", port, "--server.address", host])`; default host `localhost` (Docker passes `0.0.0.0`, file 10).

6. **`tests/test_cli.py`** (Typer `CliRunner` on the 500-row fixture DB): `--help` lists 10 commands; `worst-week --format json` parses and its `worst` equals `core.worst_week().iloc[0]`; `query --min-usd 50 --format csv` rows all have `abs_residual_usd > 50` and no unmasked `cus_` IDs; bad `--psp PSP_Z` exits 2; missing DB exits 1 with "Run `make all` first".

## Done when
| Command | Expected |
|---|---|
| `uv run recon --help` | 10 commands |
| `uv run recon all --rows 500; echo $?` | 6 step lines, `0` |
| `recon generate --rows 500`, edit one row so settle < auth, then `uv run recon build; echo $?` | `5` (and `recon all` stops at the first non-zero step) |
| `uv run recon query --psp PSP_Z; echo $?` | `2` |
| `uv run recon worst-week --month last` | one ranked table |
| `uv run recon worst-week --month last --format json \| python -m json.tool` | valid JSON with `worst` |
| `uv run recon query --min-usd 50 --format csv \| head -3` | header = TXN_COLUMNS, then rows, `customer` like `cus_••••7f3a` |
| `uv run pytest -q tests/test_cli.py` | passes |

## Serves
FR3 acceptance: "Which PSP had the worst week last month?" and "Show me all transactions with discrepancies over $50" · Stretch 10 · Deliverable 1 (run instructions) · Tech 15 (exit codes).

## Pitfalls
- **No metric logic in the CLI.** It formats what core returns. If a number differs from the dashboard, the bug is in core.
- **"Over $50" is `> 50`,** on the FX-adjusted residual in USD, not the raw difference.
- **"Last month"** = the last full calendar month in the data, not the wall-clock month; weeks belong to the month of their Thursday.
- Only `build` opens DuckDB for writing; running `recon query` during a build gets `DbBusy` → "rebuilding, retry".
- Typer prints a traceback on unhandled errors; route everything through `run_step`.
- Write CSV to stdout with `newline=""` and UTF-8 so the `••••` mask survives.

## Hand-off
- File 10 calls `recon all` from `make all` and Docker.
- File 11 README shows `all`, `report`, `worst-week`, `query`.
- Frontend: UI test 4 uses `recon worst-week --month last --format json`; UI test 5 uses `recon query --min-usd 50 --format csv`.
