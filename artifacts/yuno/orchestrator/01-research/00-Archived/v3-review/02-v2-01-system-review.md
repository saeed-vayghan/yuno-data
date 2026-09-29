# Review · v2/01 Discrepancy Analysis System
**Verdict:** ⚠️ Pass with fixes — **Score:** 7/10 (the right core pick, but the incremental-merge design is heavier than the brief needs, and some rows are missing or hard to read)

Reviewed file: `orchestrator/01-research/v2/01-discrepancy-analysis-system.md`. Brief: `architect/00-scenario/scenario.md`.

## Fit to brief
| Brief requirement / constraint | Served? (✅/⚠️/❌) | Note |
|---|---|---|
| FR1: ingest auth + settlement records | ⚠️ | There is no "Ingest" row. The doc never says how the CSV gets into DuckDB (v1 had this row). |
| FR1: calculate diffs, flag meaningful ones, enrich | ✅ | Money/FX row + dbt marts cover it. The flag rule itself lives in 02. |
| FR1 acceptance: "run your pipeline … get a clean, enriched dataset" | ✅ | `make all` → dbt marts with tests. |
| FR2: root-cause analysis outputs | ⚠️ | Stats row names the libraries, but no row says where the outputs go (FINDINGS.md, charts). |
| FR3: dashboard or alerts, on localhost | ✅ | Streamlit read-only + YAML evaluator. |
| FR4: recommendations | ⚠️ | The user's frame says to build it, but no row in the stack mentions it. |
| Test data (≥ 500 rows, reproducible) | ✅ | Fixed seed, `--rows 500` smoke run, 135k by default. |
| "Runnable locally" (reviewer has Python, Node.js **or** Docker) | ⚠️ | Needs `uv` and `make`. The reviewer is only promised Python or Docker. Docker is listed as "optional". |
| "Keep your architecture simple … not an enterprise data warehouse" | ⚠️ | Rejecting the lakehouse is right. But append-only raw + incremental merge + re-open window + parity test is warehouse-style work for a 1-second full rebuild. |
| "Focus on … a working prototype, not a production-grade system" | ⚠️ | Same issue as above; pydantic config and contracts on marts add more. |
| Clear README / run instructions | ✅ | Implied by the Makefile + CLI; see F7 for one line to add. |

## Findings
| # | Severity (High/Med/Low) | Location (quote) | Problem | Proposed fix | Jamshid | Status |
|---|---|---|---|---|---|---|
| 1 | High | "Append-only raw (`batch_id`); latest row per `transaction_id`; merge + re-open window for pending" and "incremental = full-refresh parity test" | Too complex for the brief. A full rebuild of 135k rows takes about a second. Incremental merge, a re-open window and a parity test add code and bugs, and earn no points. It also clashes with the playbook: "Idempotency: Full rebuild from raw". | Lean build: full rebuild from raw every run (`dbt build --full-refresh` is the default). Tests check that a rerun gives the same output. Move incremental merge to the scale column only. | Accepts. The merge story belongs to Iceberg/StarRocks, where late settlements are real. Locally, a full rebuild is simpler and is idempotent by design. | Agreed |
| 2 | Med | Row "Docker": "Optional Dockerfile for a machine without Python/make"; Row "Runtime": "Python 3.12 + uv" | The brief says the reviewer has "Python, Node.js, or Docker". It does not promise `uv` or `make` (no `make` on Windows). The Docker path is "optional" here, but the playbook says `docker compose up` runs the same steps. | Name three ways to run it in the README and in this row: (a) `make all`; (b) `pip install uv && uv run recon all`; (c) `docker compose up`. Make Docker a supported path, not optional. Use the same compose wording as the playbook. | Accepts. Docker is the safest path for a reviewer we have never met. | Agreed |
| 3 | Med | (missing row) | No "Ingest" row. FR1 starts with "Ingests transaction records". The reader cannot see how the raw CSV becomes a typed table, or what checks the input. | Add a row. Lean: "generator writes CSV to `data/raw`; dbt source reads it with explicit column types; contract check on load". Scale: "PSP files → S3 → Iceberg". | Accepts. It was in v1 and was lost when the file was cut down. | Agreed |
| 4 | Med | (missing rows) | The frame says to build RCA outputs and recommendations, but the stack has no row for reports, charts or recommendations. FR2 acceptance is about "analysis outputs". | Add one row "Reports": `reports/FINDINGS.md` + `reports/figures/` + `reports/RECOMMENDATIONS.md`, built from a findings table (no hand-typed numbers). | Accepts. | Agreed |
| 5 | Med | "DuckDB read-only; no logic in UI" (Dashboard) vs Option 6 con "holds the file lock and blocks writes" | Streamlit has the same lock problem that the doc uses to reject BI tools. If the dashboard is open, a read-only process holds the file, so `recon build` cannot write. | Dashboard opens a short-lived read-only connection per query (or the build writes a new file and swaps it in). Add a one-line note: "close or restart the app before `make all`", or handle it in code. | Partly rebuts: a take-home reviewer runs build first, then the app. Accepts adding the short-lived connection; it is one line of code. | Agreed (compromise) |
| 6 | Med | (missing option) Trade-off table | The simplest real rival is missing: **DuckDB + plain SQL files run by Python (no dbt)**. It keeps DuckDB and SQL but drops dbt setup. It is a fairer runner-up than polars + Parquet, which drops SQL and DuckDB together. | Add the option. Pros: fewest moving parts, same SQL. Cons: tests, order and docs by hand. Make it the 🥈, or say clearly why polars beats it. | Rebuts in part: dbt tests and contracts are the point for the "good data engineering" score. Accepts adding the row and making it 🥈; polars moves to ❌ or stays as a note. | Agreed |
| 7 | Med | Option 1 "Simplicity: High" | dbt adds a project, profiles, a second DAG and a pinning rule. It is not as simple as "plain scripts" or "notebook", which also get High. The rating hides the real trade. | Set Option 1 Simplicity to **Med**. The verdict still holds on Maintainability and Scales later. | Accepts. An honest Med makes the pick more credible. | Agreed |
| 8 | Med | "DuckDB 1.4.x LTS" | Community support for DuckDB 1.4 LTS ends on 17 Nov 2026, about 7 weeks from now (DuckDB release calendar). v1 picked 1.5.x. The reader is not told either fact. | Keep 1.4.x LTS for stability, but add "(community support to 17 Nov 2026; move to 1.5.x/2.0 on the scale path)". Or pin 1.5.x. Say which one, in one place. | Rebuts the switch: LTS gets fewer breaking changes, and a take-home is a snapshot. Accepts the note. | Agreed (compromise) |
| 9 | Med | "`make all` runs on a reviewer's laptop in seconds" | Doubtful at 135k rows. dbt start-up alone takes several seconds; generation, logit, bootstrap and HDBSCAN add more. The claim can be checked by the reviewer and may fail. | Say "in about a minute (the 500-row smoke run takes seconds)". Measure it before the interview and put the real number in the README. | Accepts. | Agreed |
| 10 | Med | Cells in "Money / FX", "Idempotency / pending", "Alerts" | Hard to read. Very long cells mix many ideas: "seeds only for exponents, PSP fees, VAT; diff = FX-explained + residual". "failed/pending out of the rate" is a definition, not idempotency. | Keep one idea per cell, ≤ 12 words. Move definitions (status, denominator, FX split) to 02's Definitions table and link it. Example: Money/FX → "Integer minor units (CLP 0 decimals); daily FX table in `data/raw`. Rules: see 02." | Accepts. | Agreed |
| 11 | Low | "thresholds from `thresholds.yaml` (pydantic) as dbt vars" | pydantic is an extra layer just to load one YAML file into dbt vars. | Load the YAML and pass it with `--vars`; check it with a small pytest. Drop pydantic unless the CLI needs typed config anyway. | Rebuts: the CLI and the alert evaluator share the same config, and pydantic gives clear errors for free. Kaveh accepts if it stays a single small model class. | Rebutted |
| 12 | Low | `casa.duckdb` | The playbook uses `data/casarecon.duckdb`. Two names for one file. | Use `data/casarecon.duckdb` everywhere. | Accepts. | Agreed |
| 13 | Low | "Makefile targets → `uv run recon …`" | The doc does not list the key targets. Siblings use `make app` (06), `make alerts` (07), `make data` (04), but the CLI has `generate`, not `data`. | Add one line: "`make all` · `make app` · `make alerts` · `make test`". Tell 04 to use `make generate` or `make all`. | Accepts. | Agreed |
| 14 | Low | Option 7 "Maintainability: High" | A lakehouse in Compose on a laptop (Iceberg + StarRocks + Airflow) is not highly maintainable for this team or this job. | Set it to Low (lean) / High (at scale), or just Low. | Rebuts: at scale it is maintainable, and that is what the column means. Compromise: write "High (at scale)", as v1 did. | Agreed (compromise) |
| 15 | Low | "SQL ports to Yuno's dbt" / "Same dbt project on `dbt-starrocks`" | This oversells it. The DuckDB and StarRocks SQL dialects differ (functions, `read_csv`, types). Model structure and tests port; some SQL needs edits. | Say "model structure and tests port; dialect edits expected". | Accepts. | Agreed |
| 16 | Low | "seeds only for exponents, PSP fees, VAT" | The generator plants the PSP_C fee from the same seed that the detector reads. That could look circular ("found what we told it"). | Add a note: fees are contract reference data that a real merchant has. The analysis must still find them from the data, and it is scored against truth labels. | Accepts the note. | Agreed |
| 17 | Low | Option 4 cons "Weak analytics SQL" | Only half true. SQLite has had window functions since 3.25. The real weak spots are types (money, time) and the lack of a first-class dbt adapter. | Change it to "no decimal/time types; community dbt adapter only". | Accepts. | Agreed |

## Debate highlights
⚡ **Kaveh:** The brief says "not an enterprise data warehouse". Why do we have append-only raw, `batch_id`, a merge with a re-open window, and a parity test to prove it works? A full rebuild takes a second.

🏛️ **Jamshid:** Late settlements are the real problem in production, and I want to show we know that. But you are right that the lean build does not need it. Full rebuild locally; merge goes in the scale column.

⚡ **Kaveh:** You reject Metabase because it "holds the file lock". Streamlit read-only holds the same lock. Open the dashboard, run `make all`, and the build fails.

🏛️ **Jamshid:** Fair point. A short-lived connection per query fixes it in one line. The BI rejection still stands for its other reasons: a JVM container and a third-party plugin.

⚡ **Kaveh:** The runner-up is wrong. The real simpler rival is DuckDB + plain SQL files with no dbt. Polars drops SQL too, so it is a weaker comparison.

🏛️ **Jamshid:** Agreed on the row. dbt still wins: tests, contracts and lineage are exactly what "thoughtful data engineering practices" rewards. But I will rate our own pick's simplicity as Med, not High.

⚡ **Kaveh:** The brief promises the reviewer Python or Docker, not `uv` and not `make`. Docker cannot be "optional".

🏛️ **Jamshid:** Accepted. There will be three ways to run it, each in one line of the README, and `docker compose up` is fully supported.

## Must-fix list
1. **(High, F1)** Drop incremental merge, the re-open window and the parity test from the lean build. Use a full rebuild from raw, matching the playbook. Keep the merge in the scale column only.
2. **(Med, F2)** Make Docker a supported path, and give three one-line ways to run (`make all` · `uv run recon all` · `docker compose up`), with the same compose wording as the playbook.
3. **(Med, F3)** Add an "Ingest" row: CSV in `data/raw` → typed dbt source + contract check.
4. **(Med, F4)** Add a "Reports" row: FINDINGS.md, figures, RECOMMENDATIONS.md, built from a findings table.
5. **(Med, F5)** Dashboard uses short-lived read-only connections so `make all` can run while the app is open.
6. **(Med, F6)** Add the option "DuckDB + plain SQL files (no dbt)" and make it the 🥈 (or say clearly why polars beats it).
7. **(Med, F7)** Rate Option 1 Simplicity as Med.
8. **(Med, F8)** State the DuckDB 1.4 LTS support end date (17 Nov 2026) and the upgrade plan, and use one version wording across all files.
9. **(Med, F9)** Replace "runs … in seconds" with a measured time (about a minute at 135k; seconds for the 500-row smoke run).
10. **(Med, F10)** Shorten the long cells to one idea each, ≤ 12 words, and move definitions to 02.

Sources checked: [DuckDB release calendar](https://duckdb.org/release_calendar) · [endoflife.date: DuckDB](https://endoflife.date/duckdb) · [dbt-duckdb on PyPI](https://pypi.org/project/dbt-duckdb/) (1.11.0 needs dbt-core ≥ 1.11.12, < 2, so 1.12 is allowed).
