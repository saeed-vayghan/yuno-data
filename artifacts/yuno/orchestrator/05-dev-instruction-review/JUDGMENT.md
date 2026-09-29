# Judgment · Dev instructions (engineer 00–11, designer 00–10)

Chair 🏛️ Jamshid · ⚡ Kaveh (data engineer) · 🎨 Mani (designer / frontend). Rule: the engineer's **CORE API CONTRACT** (`engineer/02-develop-instruction/02-config-and-core.md`) is the single source for core names. Designer 02 now points to it.

## Verdict
| Set | Before | After | Why |
|---|---|---|---|
| Engineer | 8/10 | 9/10 | Solid and checkable. Gaps: `open_week` (should be a list), no tie-break, no `min_date/max_date`, alerts had no `psp/country`, report dirs not redirectable for tests, part C came too late for the UI. |
| Designer | 6/10 | 8.5/10 | Good pages and states, but its own contract used different names (TXN columns, `prev`, `psp`, `rate_curr`, tuple `load_findings`, `usd_impact`, `Info`), had a TTL, and used a second Docker fix. |

## Decisions
| # | Issue | Decision | Who argued what | Files changed |
|---|---|---|---|---|
| 1 | TXN columns | Engineer TXN_COLUMNS: `auth_date`, `exponent`, `customer` (masked) | 🎨 wanted `customer_id` shown masked; ⚡ the full ID never leaves core → column `customer` | D02, D05, D09 |
| 2 | Outliers source | `query_transactions(Filters(category=("large",)), min_usd)` on fct, not `mart_outliers` | ⚡ one code path for CLI + UI; 🎨 fine, same rows over $50 | D05, D09 |
| 3 | `kpis` | `prev_week, delta_rate_pts, delta_net_usd, delta_n_large`; Drill-down uses `week="all"` | 🎨 wanted a `prev` dict; 🏛️ deltas in core = no maths in the UI | D02, D03, D04 |
| 4 | `weekly_trend` / `week_over_week` | `series`; `week_prev, week_last, rate_last, n_last` | no dispute | D02, D03 |
| 5 | `worst_week` tie-break | `low_sample` asc, `net_usd` desc, `psp` asc, `auth_week` asc; CLI prints core order | 🎨 raised ties on the 500-row DB; ⚡ added it to the contract | E02, E06, D09 |
| 6 | `load_findings` / `load_recommendations` | dict `{markdown, items}`; JSON rows with `rank`, `usd_quarter` (UI shows `R{rank}`) | 🎨 had a Markdown-parse fallback; 🏛️ dropped: JSON only | D02, D06, D09, E06 |
| 7 | Alerts record | Status `NEW/ONGOING/RESOLVED/INSUFFICIENT_DATA`, severity `SEV2/SEV3/INFO` (as engineer 08 emits). **Added** `psp`, `country` (nullable) to the JSONL and `load_alerts()` | 🎨 "View segment" needs them; ⚡ the evaluator knows them, parsing `segment` is fragile | E02, E08, D01, D02, D07 |
| 8 | Tiers + ownership | Engineer Core/Stretch tiers only. Gate lists every Core row. One rule: engineer owns `core/`, writes Stretch rows at step 13; frontend dev may add a missing one exactly as in the contract + a pytest, engineer reviews | 🏛️ wanted engineer-only; 🎨 did not want to wait → fallback rule | E00, E02, D00, D02, D09, D10 |
| 9 | `Filters` | `core/filters.py`, engineer fields; UI sends a week as `date_from/date_to` | agreed | D02 |
| 10 | Cache | `st.cache_data` keyed on `core.db_version()` (hashed arg, no TTL); report loaders not cached | 🎨 wanted TTL 600 as a safety net; ⚡ the mtime key is enough, and caching reports on DB mtime goes stale during `make all` | E02, D02 |
| 11 | Exceptions | `core.DbMissing`, `core.DbBusy` (from `connect()`); no `FileNotFoundError` path | agreed | D02 |
| 12 | Docker bind | Dockerfile `CMD recon dashboard --host 0.0.0.0`; `config.toml` stays `localhost`; no env var | 🎨 had proposed an env var; 🏛️ one fix only | E10, D01, D10 |
| 13 | As-of dates | as_of = latest data timestamp → 2026-06-30, last full month 2026-06, last closed 2026-W25; closed-week rule in contract; `open_weeks` is a list | ⚡ with the −7-day rule W26 and W27 are both open, so a single `open_week` was wrong | E02, D00, D03, D09 |
| 14 | Time budget | Combined timeline + one cut order in both 00s; part C moved to step 13 | ⚡ UI would wait for part C; 🏛️ core checkpoint stays the hard line | E00, D00 |
| 15 | Engineer source conflicts | Checked: stated once and consistent (AR 20/CL 15, lag 8–15, p-chart, generic rounding step, tax both signs, 13 nodes, tmp swap, placeholder limits) | no change. The `DbBusy` pitfall was reworded because the tmp swap makes it rare | E02 |
| 16 | Test isolation | `RAW_DIR`/`REPORTS_DIR` honour `CASARECON_RAW_DIR`/`CASARECON_REPORTS_DIR`; fixture sets them | ⚡ otherwise tests overwrite committed `reports/` | E02, E10, D09 |

## Coverage (brief → where → Done-when check)
| Brief item | Engineer | Designer | Done-when check |
|---|---|---|---|
| D1 Working code + README/run steps | 01, 09A, 10A, 11A | 01, 10 | `make clean && make all` exit 0; every README command runs |
| D2 Dataset / generator | 03, 05 | — | same seed → same sha256; `recon validate` all PASS |
| D3 Analysis outputs | 06, 07A | 06 (in UI) | ≥ 4 findings q < 0.05 with n/CI/lift/q/$; figures exist |
| D4 Docs incl. assumptions | 11A | 10 | `grep -c '^## '` ≥ 11; `### Assumptions` = 1 |
| D5 (Stretch) dashboard / recommendations | 07B, 08, 09B | 00–10 | 3–5 R# rows with $/owner/impl; UI tests 4, 5 pass |
| Done: accurate discrepancies | 04 | — | dbt unit tests (FX, CLP, 2¢/$500, $20) pass; truth ≥ 0.9 |
| Done: ≥ 3–4 patterns | 06, 07A | 06 | findings.json check ≥ 4; each F# shows n, CI, lift, q, $ |
| Done: well documented | 11 | 10 | README sections + newcomer answers both questions |
| Done: good engineering | 10 | 09 | `make test` green; `IDEMPOTENT`; no PAN |
| Done: (Stretch) interactive / next steps | 09B, 07B | 03, 05 | worst-week card = CLI JSON; Outliers set = `recon query --min-usd 50` |

## Combined timeline
| t (min) | Engineer | UI | Tier |
|---|---|---|---|
| 0–135 | steps 1–11 → core checkpoint | — | Core |
| 135–160 | CLI questions, core part C | shell, wrappers | Stretch |
| 160–205 | recommendations, alerts, Docker/CI | Outliers, Overview, Drill-down table, README draft, core tests (UI core path done at 200) | Stretch |
| 205–245 | review, then README Monitoring + final DoD | Alerts, Root causes, charts, polish | Stretch |

One builder: ~320 min; stop after recommendations (t = 170) if the brief's 2 h matters.

## Remaining open risks
1. Plan is well over the brief's ~2 h (core alone is 135 min). The cut order is the only guard.
2. `money_leak` / `settle_lag` limits are placeholders until the first full run.
3. dbt-core 1.12 + dbt-duckdb 1.11 + duckdb 1.4 pins are not proven yet (file 01 has the fallback).
4. kaleido/Chrome may fail, so figures fall back to HTML in Docker/CI.
5. The fallback rule (frontend adds a Stretch core function) can cause merge conflicts in `core/queries.py`.
