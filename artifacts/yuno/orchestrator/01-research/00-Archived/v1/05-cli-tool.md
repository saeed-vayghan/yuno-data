# CLI Tool: Decision Brief (v1)

## Question
Should CasaMarket's tool have a real command-line tool next to the Streamlit dashboard and the alert system? If yes, which library, and what shape? FR3 says monitoring "could be … even a command-line tool that generates reports". The reviewer must be able to answer "Which PSP had the worst week last month?" and "Show me all transactions with discrepancies over $50". The whole thing must run with one command. (A) What to build now (lean local build). (B) The documented scale path on Yuno's AWS stack. It is not built.

## Debate (🏛️ Jamshid (Architect) vs ⚡ Kaveh (Engineer))

1. 🏛️ **Jamshid:** We already have a dashboard and an alert evaluator. A CLI is a third front door. The Makefile can call dbt, the generator and Streamlit directly. Fewer moving parts.
2. ⚡ **Kaveh:** A Makefile is not a tool. It has no `--help`, no typed flags and no exit codes a script can trust. Windows reviewers may not have `make`. And scenario.md names a CLI as a valid FR3 answer. One `recon` command gives a reviewer both answers in the terminal, with no browser.
3. 🏛️ **Jamshid:** Fine, but only under one rule. **The CLI owns no logic.** Every metric lives in the dbt marts. The CLI and the dashboard import one shared core package (`recon.core`) for connections, queries and config. If `worst-week` in the CLI and on the dashboard ever disagree, the design failed.
4. ⚡ **Kaveh:** Agreed. Then the Makefile shrinks too: `make all` = `uv run recon all`. One code path, many entry points. For the library I want Typer 0.27. It uses type hints, it has Click underneath, and its `CliRunner` makes tests easy. Rich tables show only on a TTY. When output is piped, we print CSV or JSON.
5. 🏛️ **Jamshid:** Why not Cyclopts? It fixes some Typer pain points.
6. ⚡ **Kaveh:** Cyclopts 5.0 came out on 23 Sep 2026, six days ago, with breaking changes. Too new for a graded demo. Click 8.5 is the fallback if Typer blocks us. argparse is too much hand work. Go or Rust would split the stack from Python and dbt.
7. 🏛️ **Jamshid:** Next, safety. `query` takes filters from the user. That is an injection risk, and a DuckDB write lock risk.
8. ⚡ **Kaveh:** Three guards. (1) Every command opens DuckDB `read_only=True`. Only `build` writes. (2) `query` filters use parameterized SQL over a whitelist of columns. No raw SQL from the user. (3) CSV output escapes cells that start with `=`, `+`, `-` or `@`, so a spreadsheet never runs them as formulas.
9. 🏛️ **Jamshid:** And the exit codes must be fixed, because at scale Airflow reads them. 0 ok, 1 unexpected, 2 usage, 3 bad input or config, 4 warehouse missing, 5 DQ failed, 10 alert fired with `--fail-on`.
10. ⚡ **Kaveh:** **Agreed:** a thin Typer `recon` CLI over the shared core, called by the Makefile, read-only by default. At scale, the same image is the task entrypoint in Airflow. 🏛️ **Jamshid:** Agreed.

## Trade-off table

| Option | Pros | Cons | Simplicity | Maintainability | Testability | Verdict |
|---|---|---|---|---|---|---|
| **Typer 0.27.x** | Type hints = flags; Click underneath; Rich help; `CliRunner` | Extra dependency; some magic in defaults | ✅ High | ✅ High | ✅ High | **Pick for (A)** |
| Click 8.5 | Mature; explicit decorators; PowerShell completion | More boilerplate than Typer | ✅ High | ✅ High | ✅ High | Fallback |
| Cyclopts 5 | Clean type-hint API; good docs | v5.0 released 23 Sep 2026; breaking changes | ✅ High | ⚠️ Churn risk | ✅ High | Reject for now |
| argparse (stdlib) | Zero dependencies | Hand-written subcommands, help and tests | ⚠️ Medium | ⚠️ Medium | ⚠️ Medium | Reject |
| Makefile only | Nothing new to learn | No `--help`, typed flags or exit codes; no `make` on Windows | ✅ High | ⚠️ Medium | ❌ Low | Reject (kept as wrapper) |
| Go (Cobra) / Rust (clap) | Single binary; fast start | Second language; must re-read DuckDB and dbt outputs | ❌ Low | ❌ Low | ⚠️ Medium | Reject |
| No CLI (dashboard only) | One UI less | No scriptable answer; no task entrypoint for Airflow | ✅ High | ✅ High | ⚠️ Medium | Reject (user wants all three) |

## Recommendation

**(A) Lean build**
- Libraries: `typer==0.27.*`, `rich`, `pydantic`. Python 3.12 + uv, DuckDB 1.4.x LTS, dbt-core 1.12 + dbt-duckdb 1.11.
- Layout: `recon/cli.py` (commands only), `recon/core/` (connection, queries, config) shared with `dashboard/`. Metric logic stays in the dbt marts.
- Config: `thresholds.yaml` is checked by pydantic and passed to dbt as vars. `alerts.yaml` feeds the Python evaluator.
- One command: `make all` = `uv run recon all` (generate → build → validate → analyze → report → alerts check).

```
recon
├── generate      [--rows 135000] [--seed 42]   synthetic data into data/raw
├── build                                       dbt build (the only writer)
├── validate                                    dbt tests + checks → exit 5 on failure
├── analyze                                     segment stats, root causes
├── report        [--out reports/]              Markdown report of findings
├── query         [--min-usd] [--psp] [--country] [--format table|csv|json]
├── worst-week    [--month last] [--min-tx 30]
├── alerts check  [--fail-on SEV2]              writes alerts.jsonl → exit 10 if fired
├── dashboard                                   streamlit run (read-only)
└── all                                         the full run, one command
```

The two brief questions:
```
uv run recon worst-week --month last
# PSP_B · 2026-W31 · net loss $4,120 · 312 tx   (last full month, net USD loss, min 30 tx)

uv run recon query --min-usd 50 --format csv > over_50.csv
# every tx with |Δ USD| > $50 at the auth-date FX rate
```

**(B) Scale path (documented, not built)**
- The same CLI image is the entrypoint of Airflow (MWAA) tasks on ECS, for example `recon build`, `recon validate`, `recon alerts check --fail-on SEV2`.
- Airflow reads the exit codes: 5 stops the publish, 10 routes the alert through SNS to Slack.
- Query commands (`query`, `worst-week`) read StarRocks through a small connection factory. The SQL and whitelist stay the same.

## Key practices
- **No logic in the CLI.** It parses flags, calls `recon.core`, and prints. Metrics live in dbt.
- **Output by context.** Rich tables on a TTY. CSV or JSON when piped (`--format` overrides).
- **Read-only by default.** Only `build` opens DuckDB for writing.
- **Safe queries.** Parameterized SQL over a column whitelist. No raw SQL from users.
- **Safe CSV.** Escape cells starting with `=`, `+`, `-`, `@`.
- **Fixed exit codes.** 0, 1, 2, 3, 4, 5, 10, documented in `--help` and the README.
- **Clear errors.** A missing warehouse says "run `recon build` first" and exits 4. No stack traces.
- **Tests.** `CliRunner` for each command on a small fixture DuckDB, plus an output-parity test with the dashboard.

## Open disagreements

| Point | 🏛️ Jamshid | ⚡ Kaveh | Tie-breaker |
|---|---|---|---|
| `recon report` format | HTML (Quarto) for the CFO | Markdown is enough | Markdown now; HTML only if time remains |
| Shell completion | Ship it | Not worth the docs | Leave Typer's default `--install-completion` on, no extra work |

## Sources
- [typer on PyPI (0.27.2, 28 Aug 2026)](https://pypi.org/project/typer/) · [Typer 0.27.0 release](https://newreleases.io/project/pypi/typer/release/0.27.0)
- [Click 8.5 changelog](https://pallets-click.readthedocs.io/en/latest/changelog/)
- [Cyclopts v5.0.0 release (23 Sep 2026)](https://github.com/BrianPugh/cyclopts/releases/tag/v5.0.0)
- [DuckDB concurrency (read-only access)](https://duckdb.org/docs/current/connect/concurrency)
- [OWASP CSV injection](https://owasp.org/www-community/attacks/CSV_Injection)
