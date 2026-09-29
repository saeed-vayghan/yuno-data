# 02 · Data-access contract

**Goal:** fix exactly which `casarecon.core` functions the UI calls, with what arguments, and what comes back; plus caching, the read-only connection, masking, money formats and the data guard.

**Time box:** 10 min · **Tag:** Core

## Inputs
- Engineer delivered (S3.1): `core/db.py` (`connect()` read-only, `DbBusy`), `core/queries.py` (`worst_week`, `query_transactions`, `segment_rates`, `cause_summary`, `psp_weekly`, `mask_id`), `core/paths.py` (`CASARECON_DB`).
- IMPLEMENTATION-PLAN S5.3: list of extra read functions the UI needs.
- UI-UX-PLAN: component → core function tables per page.

## Rule
The dashboard reads data **only** through `casarecon.core`. No SQL, no `duckdb`, no `pandas.read_csv` of `data/raw` in `dashboard/`. The same functions serve `recon worst-week` and `recon query`, so CLI and UI agree.

## Contract table

Status legend: **S3.1** = the engineer builds it before the gate · **S5.3** = added page by page (by the frontend dev if the engineer has not, with a pytest) · **ASSUMED** = our guess where the engineer contract is not final; reconcile in the judgment session.

| # | Core function | Args | Returns (key fields) | Reads | Used on | Status |
|---|---|---|---|---|---|---|
| 1 | `core.filters.Filters` | frozen dataclass; tuple fields, empty = all: `date_from, date_to, country, psp, tier, xb, weekday, category, cause` | hashable value passed to every query | — | all | ASSUMED (lives in core so the CLI can use it too) |
| 2 | `core.paths.db_path()` | — | `Path` (honours `CASARECON_DB`) | env | data guard | ASSUMED name |
| 3 | `core.db.DbBusy` | exception | raised when the file is locked by a build | — | all | S3.1 |
| 4 | `status()` | — | dict: `as_of`, `last_closed_week` ("2026-W25"), `last_closed_start`, `last_closed_end`, `open_weeks` (list), `n_rows` | fct | banner (all) | S5.3 |
| 5 | `filter_options()` | — | dict of lists: `country`, `psp`, `tier`, `category`, `cause`, `months` (full months only, "YYYY-MM"), `min_date`, `max_date` | fct | sidebar, page filters | S5.3 |
| 6 | `kpis(filters, week=None)` | `week="last_closed"` or `None` (= filtered range) | dict: `n`, `n_flagged`, `flag_rate`, `net_usd`, `gross_under_usd`, `gross_over_usd`, `n_large`; plus `prev` (same keys, prior closed week) when `week` is set | `mart_psp_weekly` / fct | Overview, Drill-down | S5.3 |
| 7 | `worst_week(month="last")` | `"last"` or `"YYYY-MM"` | DataFrame, ranked: `rank, psp, auth_week, week_start, week_end, week_month, n, n_flagged, rate, gross_under_usd, gross_over_usd, net_usd, low_sample`; low-sample rows ranked last | `mart_psp_weekly` | Overview card | S3.1 (return columns ASSUMED) |
| 8 | `weekly_trend(filters, by="portfolio")` | `by` in `portfolio`, `psp` | DataFrame: `auth_week, week_start, psp` (if by psp), `n, n_flagged, rate, net_usd, gross_under_usd, is_closed, low_sample` | `mart_psp_weekly` | Overview | S5.3 |
| 9 | `week_over_week(filters)` | — | DataFrame: `psp, country, rate_prev, rate_curr, delta_pts, n_prev, n_curr, low_sample`, sorted by `delta_pts` desc | `mart_psp_weekly` | Overview | S5.3 |
| 10 | `segment_rates(dim, filters=None)` | `dim` in mart segment types (`country`, `psp`, `psp_country`, `amount_tier`, `weekday`, `cross_border`, `lag_bucket`…) | DataFrame: `segment_type, segment_value, n, n_flagged, rate, ci_low, ci_high, n_large, gross_under_usd, gross_over_usd, net_usd, mean_loss_usd, median_loss_usd, low_sample` | `mart_segment_rates` (no filters) / fct (filtered) | Drill-down, Root causes | S3.1 is `segment_rates(type)`; `filters` arg + `ci_low/ci_high` ASSUMED |
| 11 | `category_mix(filters)` | — | DataFrame: `auth_week, category, n, share` | fct | Drill-down | S5.3 |
| 12 | `query_transactions(filters, min_usd=None, limit=None)` | `min_usd` set → `mart_outliers` where `abs_residual_usd > min_usd`; `None` → settled rows of fct | DataFrame sorted by `abs_residual_usd` desc: `transaction_id, auth_ts, psp, country, currency, currency_exponent, is_cross_border, amount_tier, customer_id` (already masked), `authorized_amount, expected_settled, settled_amount, diff_local` (int minor units), `residual_usd, abs_residual_usd, residual_pct, direction, category, likely_cause, why_flagged, settle_lag_days` | `mart_outliers` / fct | Outliers, Drill-down, both CSVs | S3.1 (column list ASSUMED) |
| 13 | `outlier_summary(filters, min_usd)` | — | dict: `n, under_usd, over_usd` | `mart_outliers` | Outliers | S5.3 |
| 14 | `transaction_detail(txn_id)` | `str` | dict: row fields of #12 + `amount_usd, settled_usd, fx_move_pct, is_weekend, item_count, risk_score, cause_note` | fct | Outliers detail | S5.3 |
| 15 | `similar_count(txn_id)` | `str` | dict: `n, psp, country, likely_cause` | fct | Outliers detail | S5.3 |
| 16 | `cause_summary(filters=None)` | — | DataFrame: `likely_cause, n, gross_under_usd, gross_over_usd, net_usd, share_of_loss` | `mart_cause_summary` | Root causes | S3.1 |
| 17 | `excess_loss(top=5)` | — | DataFrame: `segment, n, rate, peer_rate, lift, q, excess_usd, median_loss_usd` | `mart_segment_rates` + `findings.json` | Root causes | S5.3 |
| 18 | `load_findings()` | — | `(items, markdown)`: `items` = list of dicts from `findings.json` (`id, headline, segment, n, rate, ci, peer_rate, lift, q, usd_quarter, share_of_loss, likely_cause`); `markdown` = FINDINGS.md text. `None` if missing | `reports/` | Root causes | S5.3 |
| 19 | `load_recommendations()` | — | list of dicts `rank, id, action, evidence, usd_impact, owner, implementation`; `None` if missing | `reports/RECOMMENDATIONS.md` | Root causes | S5.3 (shape ASSUMED) |
| 20 | `load_alerts()` | — | DataFrame from `alerts.jsonl`: `rule_id, segment, psp, country, period, severity, status, message, owner, n, value, threshold`; `None` if the file is missing | `reports/alerts.jsonl` | Overview KPI, Alerts | S5.3 (fields ASSUMED) |
| 21 | `mask_id(customer_id)` | `str` | `cus_••••7f3a` (last 4 kept) | — | called inside core only | S3.1 |

Assumptions to reconcile (short list, also in file 10):
- A1: `Filters` lives in core (`core/filters.py`), not in `dashboard/`. Reason: core cannot import the dashboard, and the CLI builds the same object from its flags.
- A2: `query_transactions` returns `customer_id` already masked and a `currency_exponent` column (joined from the seed). The UI never sees a raw ID and never hard-codes CLP = 0.
- A3: `why_flagged` text ("> 5% and ≥ $20") is built in core (SQL or Python), not in the page.
- A4: counts for "Showing 1,000 of N" come from `outlier_summary` (Outliers) and `kpis(filters)["n"]` (Drill-down), so the UI never loads 135k rows to count them.
- A5: `alerts.jsonl` has `psp` and `country` as separate fields (for "View segment"), and "insufficient data" is a `status` value `INSUFFICIENT_DATA` with severity `Info`.
- A6: `load_recommendations()` parses a fixed block per item in RECOMMENDATIONS.md. Fallback if parsing is not worth it: return the markdown string and the page renders it whole.

**Decision (min_usd is an argument, not a Filters field):** 🎨 Mani wanted everything in `Filters`. 🏛️ Jamshid: `recon query --min-usd` maps 1:1 to `query_transactions(min_usd=…)`, keep that signature. → Separate argument.

## Steps

### 1. `dashboard/data.py`: cached wrappers

```python
import streamlit as st
from casarecon.core import queries          # import the MODULE, so tests can monkeypatch it
from casarecon.core.paths import db_path

TTL = 600   # safety net; the real key is the DB file mtime

def db_mtime() -> float: ...                 # db_path().stat().st_mtime; raises FileNotFoundError

# Careful: a leading underscore (`_mtime`) tells Streamlit NOT to hash that arg.
# The mtime must be hashed, so name it `mtime`.
@st.cache_data(ttl=TTL, show_spinner="Loading…")
def worst_week(month: str, mtime: float) -> pd.DataFrame:
    return queries.worst_week(month)

def get_worst_week(month: str) -> pd.DataFrame:
    return worst_week(month, db_mtime())
```

- One wrapper per contract row. The cache key = function args (`Filters`, `min_usd`, `limit`, `month`…) + `mtime`. A rebuild changes `mtime`, so the cache refreshes on the next run.
- `Filters` must be hashable: frozen dataclass with tuple fields (no lists, no sets). If Streamlit cannot hash it, pass `filters.as_key()` (a tuple) and rebuild the object inside.
- Report loaders (`load_alerts`, `load_findings`, `load_recommendations`) key on the report file's mtime instead.
- Cache DataFrames only (small, pickle-safe). Never cache a connection.

### 2. Connection: short and read-only (engineer side, you just rely on it)
Each core function does `with connect() as con:` → `duckdb.connect(path, read_only=True)`, runs one parameterized query, closes. The dashboard holds **no** open connection, so `make all` can rebuild while the app runs.

### 3. Data guard: one wrapper around every page body

```python
def guarded(render: Callable[[], None]) -> None:
    # FileNotFoundError (no DB)      → st.info("No data yet. Run `make all` first, then reload this page."); st.stop()
    # queries.DbBusy / db.DbBusy     → st.warning("The data is being rebuilt. Retry in a minute."); st.button("Retry")
    # any other Exception            → log traceback; st.error("Something went wrong loading this view. The details are in the terminal.")
```
Every page ends with `guarded(render)`.

### 4. Money and number formats (`format.py`, pure functions)

```python
def usd(x: float) -> str: ...                     # "$1,234.56"
def usd_compact(x: float) -> str: ...             # "$127.4k"
def usd_signed(x: float) -> str: ...              # "−$62.10 under" / "+$4.00 over"
def local(minor: int, currency: str, exponent: int) -> str: ...  # "CLP 12,345", "MXN 1,234.56"
def rate(p: float) -> str: ...                    # "14.2%"
def delta_pts(d: float) -> str: ...               # "▲ +1.1 pts" (worse) / "▼ −0.4 pts" (better)
def rate_range(p, lo, hi) -> str: ...             # "21.3% [19.8–22.9]"
def week_label(iso: str, start: date, end: date) -> str: ...   # "W25 (Jun 15–21)"
```
- Local amount = `minor / 10**exponent`, shown with `exponent` decimals. CLP → 0 decimals. MXN, COP, ARS → 2 (per the `currency_exponents` seed).
- USD values from core are already in dollars (`residual_usd`, `net_usd`…), 2 decimals.
- Use the real minus sign `−` (U+2212) in display text; keep numeric columns numeric in tables (format with `column_config`, not by turning them into strings), so sort still works.
- Never put a bare `$` next to a local amount.

### 5. Masking
- Core masks. The UI only checks: any column named `customer_id` must match `^cus_••••.{4}$` (test 11 in file 09).
- CSV download uses the same DataFrame, so it is masked too.

## Done when
- [ ] `dashboard/data.py` has one cached wrapper per row you use, all keyed on `mtime`.
- [ ] Deleting `data/casarecon.duckdb` → every page shows "Run `make all` first" (no traceback).
- [ ] Running `make all` while the app is open → the app shows "Rebuilding" or fresh data after Retry; never a crash.
- [ ] `grep -rn "duckdb\|read_csv\|SELECT" src/casarecon/dashboard` finds nothing.
- [ ] `format.py` unit tests pass for `CLP 12,345`, `MXN 1,234.56`, `−$62.10 under`, `▲ +1.1 pts`.

## Serves
FR3 (shared core, CLI ↔ UI agree); Tech 15 ("no logic in UI", clean code); privacy (masked IDs); UI-UX build steps 2 and 3.

## Pitfalls
- `_mtime` with an underscore is silently not hashed → stale data after a rebuild.
- `from casarecon.core.queries import worst_week` in a page: tests cannot monkeypatch it. Import the module.
- Formatting numbers into strings inside DataFrames breaks sort. Use `st.column_config.NumberColumn(format=…)`.
- Loading the full fact table to count rows. Ask core for the count.

## Hand-off
Wrappers + guard + formatters ready. Next: `05-page-outliers.md` (build order) or `03-page-overview.md` (reading order). Keep the list of any function you added to core and any assumption A1–A6 that turned out wrong.
