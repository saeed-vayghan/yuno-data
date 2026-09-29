# 05 · CLI Tool
**Purpose:** Pick the `recon` command-line tool. It serves FR3's "command-line tool that generates reports" and runs the whole build with one command.
**Frame:** lean local build (one command) + AWS scale path, documented only. [scenario.md](../../../architect/00-scenario/scenario.md) is the source of truth; the [decision sheet](00-SUMMARY.md) overrides this file.

| # | Option | What it is | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Typer 0.27.x | Type-hint CLI built on Click | Little code | One more dependency | High | High | 🥇 Best: fastest to write |
| 2 | Click 8.5 | Decorator CLI library | Mature and explicit | More boilerplate | High | High | 🥈 Runner-up: safe fallback |
| 3 | Cyclopts 5 | Type-hint CLI library | Clean API | v5.0 released 23 Sep 2026: brand-new major | High | Med | ❌ Reject: less known |
| 4 | argparse (stdlib) | Built-in parser | No dependencies | Subcommands and help written by hand | Med | Med | ❌ Reject: hand work |
| 5 | No CLI (Makefile only) | `make` targets call tools directly | Nothing new to learn | No `--help`, typed flags or exit codes | High | Med | ❌ Reject: FR3 names a CLI |
| 6 | Go (Cobra) / Rust (clap) | Compiled single binary | Fast start | Second language next to Python | Low | Low | ❌ Reject: splits the stack |

## The brief's two questions

| Brief question | Command | Rule (from the decision sheet) |
|---|---|---|
| "Which PSP had the worst week last month?" | `recon worst-week --month last` | Week = ISO week (Mon–Sun) by auth date |
| | | A week belongs to the month that holds its Thursday |
| | | "Last month" = last full calendar month in the data |
| | | Ranked by net USD loss (under − over) |
| | | Gross under-settlement shown beside it |
| | | PSP-weeks with n < 30 shown as "low sample" |
| "Show me all transactions with discrepancies over $50" | `recon query --min-usd 50 --format csv` | Filter: `\|residual_usd\| > 50` |
| | | `residual_usd` uses the auth-day FX rate |

## Commands
- **Tree:** `recon generate | build | validate | analyze | alerts | report | query | worst-week | dashboard | all`
- **Order of `all`:** generate → build → validate → analyze → alerts → report.
- **`report`:** writes the Markdown findings report (it includes the alerts, so alerts run first).
- **README shows 4:** `all`, `report`, `worst-week`, `query`. Each `make` target calls one step command.

## Exit codes
0 ok · 1 error · 2 usage · 5 data-quality or validation failed (stops `all`).

## Run paths (all in the README)
- `make all`
- No `make`: `pip install uv && uv run recon all`
- No Python setup: `docker compose up`

## Top 2 choices
**🥇 Typer 0.27.x**
- **Rule:** no metric logic in the CLI; metrics live in the dbt marts.
- **Safety:** short read-only DuckDB connections (only `build` writes); `query` uses fixed filters, never raw SQL.
- **Output:** a table by default; `--format csv|json` for files.
- **Scale path (docs only):** the same image runs as Airflow tasks.

**Testing:** `CliRunner` tests for `worst-week` and `query` on a small fixture DuckDB; they must match the dashboard's answer.

**🥈 Click 8.5:** Typer runs on Click, so the switch is small and safe. It needs more decorator code. Use it only if a Typer feature blocks us.

Key sources: [typer on PyPI](https://pypi.org/project/typer/) · [Click 8.5 changelog](https://pallets-click.readthedocs.io/en/latest/changelog/) · [Cyclopts v5.0.0](https://github.com/BrianPugh/cyclopts/releases/tag/v5.0.0) · [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency)
