# 05 · CLI Tool
**Purpose:** Pick the `recon` command-line tool that serves FR3's "command-line tool that generates reports" and runs the whole build with one command.
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Option | What it is | Pros | Cons | Simplicity | Maintainability | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Typer 0.27.x | Type-hint CLI on top of Click | Little code; Rich help; `CliRunner` tests; thin shell over the shared core | One more dependency | High | High | 🥇 Best: fastest, typed |
| 2 | Click 8.5 | Decorator CLI library | Mature; explicit; same test runner | More boilerplate | High | High | 🥈 Runner-up: fallback |
| 3 | Cyclopts 5 | Type-hint CLI library | Clean API | v5.0 is six days old (23 Sep 2026); breaking changes | High | Med | ❌ Reject: too new |
| 4 | argparse (stdlib) | Built-in parser | No dependencies | Hand-written subcommands, help and tests | Med | Med | ❌ Reject: hand work |
| 5 | Makefile only | `make` targets call tools directly | Nothing new | No `--help`, typed flags or exit codes; no `make` on Windows | High | Med | ❌ Reject: kept as wrapper |
| 6 | Go (Cobra) / Rust (clap) | Compiled single binary | Fast start; one file | Second language next to Python + dbt | Low | Low | ❌ Reject: splits the stack |

## Top 2 choices
**🥇 Typer 0.27.x:** `recon` is a thin shell over one core package that the Streamlit dashboard also imports, so metrics stay in the dbt marts. It opens DuckDB read-only (only `build` writes), uses parameterized SQL over a column whitelist, and prints Rich tables on a TTY or CSV/JSON when piped. `make all` = `uv run recon all`; fixed exit codes (0/1/2/3/4/5/10) let the same image run as Airflow (MWAA) tasks on ECS, with query commands reading StarRocks at scale.
`recon generate | build | validate | analyze | report | query | worst-week | alerts check | dashboard | all`
**🥈 Click 8.5:** Typer already runs on Click, so the switch is small and safe. It needs more decorator code for the same commands. Use it if a Typer feature blocks us.

Key sources: [typer on PyPI](https://pypi.org/project/typer/) · [Click 8.5 changelog](https://pallets-click.readthedocs.io/en/latest/changelog/) · [Cyclopts v5.0.0](https://github.com/BrianPugh/cyclopts/releases/tag/v5.0.0) · [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency) · [OWASP CSV injection](https://owasp.org/www-community/attacks/CSV_Injection)
