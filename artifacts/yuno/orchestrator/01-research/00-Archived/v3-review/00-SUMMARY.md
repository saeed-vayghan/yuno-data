# Review Summary: Kaveh ⚡ vs Jamshid 🏛️

Every doc was judged against [scenario.md](../../../../architect/00-scenario/scenario.md). No doc was edited.

## Verdicts

| Doc | Verdict | Score | Main issue |
|---|---|---|---|
| [PLAYBOOK](01-playbook-review.md) | ⚠️ Pass with fixes | 7/10 | FX formula direction; rounding floor; validation gate fails by design |
| [v2/01 System](02-v2-01-system-review.md) | ⚠️ Pass with fixes | 7/10 | Over-built incremental merge; missing Ingest and Reports rows |
| [v2/02 Detection](03-v2-02-detection-review.md) | ⚠️ Pass with fixes | 7/10 | Cause labels miss sub-flag patterns; rounding rule; MAD = 0 |
| [v2/04 Synthetic data](04-v2-04-synthetic-data-review.md) | ⚠️ Pass with fixes | 7/10 | No cause for the 2–5% bucket; rounding not in quotas; exact-share denominator |
| [v2/05 CLI](05-v2-05-cli-review.md) | ⚠️ Pass with fixes | 6.5/10 | Doesn't show the 2 brief answers; too many exit codes |
| [v2/06 Dashboard](06-v2-06-dashboard-review.md) | ⚠️ Pass with fixes | 7/10 | Open app blocks `make all` (DuckDB lock); no Outliers page |
| [v2/07 Alerts](07-v2-07-alerts-review.md) | ⚠️ Pass with fixes | 7/10 | Wrong peer group; open-week testing; dedupe; too many rules |

**Coverage:** the playbook covers every brief item. Its quotes and numbers match the brief, and nothing is invented.

## Cross-cutting fixes (same problem in several docs)

| # | Problem | Fix | Docs |
|---|---|---|---|
| 1 | Rounding rule `\|Δ USD\| < $0.50` hides real patterns (fee, P4, small orders) | Rounding = ≤ 1 minor unit (or the PSP rounding step); give it its own share; fee ≥ $1 | Playbook, 02, 04 |
| 2 | P4 is described two ways | Pick one P4 version and use it everywhere | Playbook, 04 |
| 3 | 2–5% bucket has no planted cause | Add "PSP adjustment −2% to −5%" (raised by P1, P3) + a cause rule | 04, 02 |
| 4 | Validation gate (1.5× lift) fails P1 and P3 by design, and always fails the 500-row run | Per-pattern bands; hard-fail only on the full run | Playbook, 04 |
| 5 | Exact share can fall below 60% | Denominator = approved + settled; failed + pending ≤ 7% | Playbook, 04 |
| 6 | FX formula direction / currency model undefined | Define payer vs settle currency; one formula with a unit test worked by hand; all cut-offs on the absolute FX-adjusted residual | Playbook, 02 |
| 7 | Cause labels only run on flagged rows | Run on all non-exact rows | 02 |
| 8 | Robust z divides by 0 (most rows exact) | Use it on non-exact rows only, or just "large and > $50" | 02, 07 |
| 9 | An open dashboard locks DuckDB, so `make all` fails | Short read-only connection per query + cache keyed on file time | 01, 06 |
| 10 | Reviewer may not have `make`/`uv` | Three run paths: `make all` · `pip install uv && uv run recon all` · `docker compose up` | Playbook, 01, 05 |
| 11 | Worst-week edge cases | ISO week belongs to the month of its Thursday; low-sample weeks shown greyed; label net vs gross | Playbook, 05, 06 |
| 12 | Small mismatches | min n 50 everywhere (30 only for the worst-week card); `alerts.yaml`; one command order: generate → build → validate → analyze → alerts → report | Playbook, 05, 06, 07 |

## Over-engineering to cut

| Cut | Doc |
|---|---|
| Incremental merge, reopen window, parity test → full rebuild each run | 01 |
| Depth-3 decision tree → scale path; HDBSCAN → optional | 02, Playbook |
| Two-phase "pin then fill" generator → bucket → cause → size | 04 |
| AWS generator path → one line | 04 |
| Exit codes → 0 / 1 / 2 / 5 | 05 |
| Worst-week page → a card on Overview (5 pages) | 06 |
| Alert rules → 6; data quality = the dbt build fails; no alert-state file; Slack optional or cut | 07, Playbook |

## Readability
Split dense table cells and paragraphs into short bullets (one rule per line), and add a small glossary for terms like residual, peer rule and p-chart. This applies to all docs.
