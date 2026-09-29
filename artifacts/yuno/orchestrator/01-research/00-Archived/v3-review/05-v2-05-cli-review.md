# Review · v2/05 CLI Tool
**Verdict:** ⚠️ Pass with fixes — **Score:** 6.5/10 (the right tool and the right top 2, but the file never shows how `recon` answers the two brief questions, and the command tree and exit codes are bigger than a 2-hour build needs)

## Fit to brief
| Brief requirement / constraint | Served? (✅/⚠️/❌) | Note |
|---|---|---|
| FR3: "even a command-line tool that generates reports" | ⚠️ | `recon report` is in the tree, but the file does not say what it writes (Markdown? where?). |
| "Which PSP had the worst week last month?" | ⚠️ | `worst-week` is listed, but there are no flags, no example and no definition of "worst week" or "last month". The playbook (§5, §9) and 06 define them; 05 must repeat them. |
| "Show me all transactions with discrepancies over $50" | ⚠️ | `query` is listed, but `--min-usd` is missing and "over $50" (absolute USD diff at the auth-date FX rate) is not defined. |
| "Runnable locally" / "reviewer has Python, Node.js, or Docker" | ⚠️ | `make all` = `uv run recon all` needs `uv` and `make`. The brief only promises Python. The file itself says "no `make` on Windows" but gives no fallback. |
| "Clear setup/run instructions" | ⚠️ | No plain run line for a reviewer without `make` or `uv`. |
| "If you build a dashboard … localhost" | ✅ | `recon dashboard` starts the Streamlit app. |
| "Keep your architecture simple" / 2-hour scope | ⚠️ | 10 commands, 7 exit codes, TTY-based output switching and a StarRocks read path are more than the brief needs. |
| Is a CLI justified at all? | ✅ | Yes. FR3 names it, the user frame asks for it, and it is the engine the Makefile calls. It is cheap (about 100 lines) if it stays a thin shell. |

## Findings
| # | Severity (High/Med/Low) | Location (quote) | Problem | Proposed fix | Jamshid | Status |
|---|---|---|---|---|---|---|
| 1 | High | "`recon generate \| build \| validate \| analyze \| report \| query \| worst-week \| alerts check \| dashboard \| all`" | The two brief questions are the acceptance test for FR3, but the file never shows the commands that answer them. `--min-usd`, `--month last` and `--min-tx` from the playbook and v1 are gone. | Add two example lines and their rules: `recon worst-week --month last` (net USD loss per ISO week by auth date, skip PSP-weeks with < 30 tx, last full calendar month in the data) and `recon query --min-usd 50 --format csv` (\|Δ USD\| > 50 at the auth-date FX rate). Use the same words as 06 and playbook §5. | Accept. This is the whole reason the CLI exists. | Agreed |
| 2 | Med | "fixed exit codes (0/1/2/3/4/5/10)" | Seven codes with no meaning given. The reader cannot use them. Most exist only for Airflow, which is scale path and not built. Over-engineered for a local demo. | Lean build: 0 = ok, 1 = error, 2 = bad usage (Click's default). Add one code only if `recon validate` must stop `all` (e.g. 1 is enough). Keep "10 = alert fired" in the scale-path notes only. | Compromise: keep 0/1/2 now, plus 5 = data checks failed, so `make all` stops clearly. List them in one line in the README. | Agreed |
| 3 | Med | "`recon generate \| build \| validate \| analyze \| report \| query \| worst-week \| alerts check \| dashboard \| all`" | 10 commands is a big surface for a 2-hour build. `alerts check` is a two-word group for one action, while the playbook and 07 say `make alerts`. The order of `all` is not stated; the playbook says generate → build → validate → analyze → alerts → report, but this line and v1 put `report` before alerts. | Keep the tree, but (a) rename `alerts check` to `alerts`, (b) state the order of `all` as in the playbook (alerts before report, so the report includes alerts), (c) in the README, show only the 4 commands a user needs: `all`, `report`, `worst-week`, `query`. | Accept (a) and (b). For (c): the step commands stay, because each make target calls one of them and they help reruns. They are one line each. | Agreed |
| 4 | Med | "`make all` = `uv run recon all`" | The brief says the reviewer has Python, Node.js or Docker. It does not promise `uv` or `make`. Row 5 even says "no `make` on Windows". The one command can fail on a clean machine. | README gives three paths: `make all`; without make: `pip install uv && uv run recon all`; without Python setup: `docker compose up`. The Makefile checks for `uv` and prints the install hint. | Accept. Docker is already in 01 and the playbook; just say it here too. | Agreed |
| 5 | Med | Line 15, the whole 🥇 paragraph | One dense paragraph with many hard terms (TTY, parameterized SQL, column whitelist, MWAA, ECS, StarRocks) and a claim that does not follow ("imports … so metrics stay in the dbt marts": sharing a package does not put metrics in dbt). Hard to read. | Split into 4 short bullets: **Rule:** no metric logic in the CLI; metrics live in dbt marts. **Safety:** opens DuckDB read-only (only `build` writes); `query` uses fixed filters, never raw SQL. **Output:** a table by default, `--format csv\|json` for files. **Scale path (docs only):** the same image runs as Airflow tasks. | Accept. | Agreed |
| 6 | Med | "with query commands reading StarRocks at scale" | A second database backend for the CLI is scale-path design inside a lean decision file. It invites a "connection factory" that nobody will build or test now. | Cut it to the one scale-path line in finding 5. Do not design a StarRocks connector here. | Compromise: keep "same SQL can point at StarRocks later" as one line in 01's reference stack, not here. | Agreed |
| 7 | Low | "prints Rich tables on a TTY or CSV/JSON when piped" | Switching format by guessing TTY is hidden magic. `recon query > x.csv` silently changes format. Also one more thing to test. | Default = table; `--format csv\|json` is explicit. No auto-switch. | Rebut in part: auto-switch is 3 lines and is common CLI practice. But I accept that explicit is easier to explain in the README. | Agreed |
| 8 | Low | "[OWASP CSV injection](...)" in Key sources | A source with no matching text. v1 said "escape cells starting with `=`, `+`, `-`, `@`", which would also break negative amounts like `-12.50`. The data has no free-text fields (04: "no text fields"). | Drop the source, or say: "escape only text columns; numbers are written as numbers". | Accept: drop the source; there are no free-text columns. | Agreed |
| 9 | Low | "It opens DuckDB read-only (only `build` writes)" | If the dashboard is open and holds a read-only connection, a rerun of `recon build` cannot get the write lock and fails with a raw DuckDB error. | Dashboard and CLI open short-lived read-only connections per query. `build` catches the lock error and says "close the dashboard, then rerun". | Accept; one try/except. | Agreed |
| 10 | Low | Table (no row for "No CLI") | v1 had "No CLI (dashboard only)". v2 dropped it, so the table never answers "why a CLI at all?" | Put the row back: "No CLI: one UI less; but no scriptable report and no engine for `make` → reject (FR3 names a CLI; user wants all three)". | Accept. | Agreed |
| 11 | Low | "Cyclopts 5 … v5.0 is six days old (23 Sep 2026); breaking changes" | Facts are right (v5.0.0 on 23 Sep 2026, verified). But "six days old" will age badly, and "breaking changes" vs v4 do not hurt a new project. The real reason is: new major, less known to reviewers. | "v5.0 released 23 Sep 2026: brand-new major; less known than Click/Typer" | Accept. | Agreed |
| 12 | Low | 🥇 paragraph (no test line) | v2 lost v1's test plan. Testability is a scored item (Tech 15). | Add: "`CliRunner` tests for `worst-week` and `query` on a small fixture DuckDB; same answer as the dashboard's core query." | Accept. | Agreed |
| 13 | Low | Kaveh: "Drop the CLI; the dashboard already answers both questions" | Possible scope creep. | Remove 05. | Rebut: FR3 names a CLI, the user frame says build all, and the Makefile needs an engine with `--help` and exit codes. Kept thin, it costs ~100 lines. | Rebutted |

**Version spot-check (WebSearch/PyPI):** Typer latest = 0.27.2 ✅ · Click 8.5.0, released 26 Aug 2026, Python ≥ 3.10 ✅ · Cyclopts 5.0.0, released 23 Sep 2026, drops Python 3.10, removes fuzzy command matching ✅. Pros and cons in the table are accurate. Top 2 (Typer, then Click) are correct: Typer runs on Click, so the fallback is a safe, small switch.

## Debate highlights
⚡ **Kaveh:** The brief's test is two questions. Our CLI file does not show one command that answers them. That is the first fix.
🏛️ **Jamshid:** Agreed. Copy the definitions from 06 word for word: net USD loss, ISO week by auth date, min 30 tx, last full month, \|Δ USD\| > $50 at auth-date FX.
⚡ **Kaveh:** Seven exit codes and a StarRocks read path for a 2-hour demo. That is enterprise design in a lean file.
🏛️ **Jamshid:** The codes help Airflow later, but I accept: 0/1/2 plus 5 for failed data checks now; the rest goes in the scale-path notes.
⚡ **Kaveh:** Ten commands? Is this the tool or the build system?
🏛️ **Jamshid:** Both, on purpose: each make target calls one command. But the README shows only four, and `alerts check` becomes `alerts`.
⚡ **Kaveh:** Should the CLI exist at all?
🏛️ **Jamshid:** Yes. FR3 names it, the user asked for all three, and a thin shell is about 100 lines. Rebutted.

## Must-fix list
1. Show how `recon` answers both brief questions: `recon worst-week --month last` and `recon query --min-usd 50 --format csv`, with the same "worst week", "last month" and "over $50" rules as 06 and playbook §5. (High, #1)
2. Cut exit codes to 0 / 1 / 2 / 5 and list their meaning in one line; move 10 to the scale-path notes. (Med, #2)
3. Rename `alerts check` to `alerts`; state the `all` order as generate → build → validate → analyze → alerts → report (same as playbook); README shows only `all`, `report`, `worst-week`, `query`. (Med, #3)
4. Add run paths for a reviewer without `make` or `uv`: `pip install uv && uv run recon all`, or `docker compose up`. (Med, #4)
5. Rewrite the 🥇 paragraph as 4 short bullets (rule, safety, output, scale path) in plain words; remove the "so metrics stay in the dbt marts" non-sequitur. (Med, #5)
6. Remove "query commands reading StarRocks at scale" from this file. (Med, #6)
