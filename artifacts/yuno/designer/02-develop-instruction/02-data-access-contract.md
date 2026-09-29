# 02 · Data-access contract

**Goal:** fix exactly which `casarecon.core` functions the UI calls, with what arguments, and what comes back; plus caching, the read-only connection, masking, money formats and the data guard.

**Time box:** 10 min · **Tag:** Core

## Inputs
- **The single source:** [engineer 02 · CORE API CONTRACT](../../engineer/02-develop-instruction/02-config-and-core.md#core-api-contract): names, args, return columns, keys and tiers (Core / Stretch), `Filters`, TXN_COLUMNS, the error table and the "Frontend rules". This file only says which rows each page uses. If this file and the contract disagree, the contract wins.
- UI-UX-PLAN: component → function tables per page.

## Rule
The dashboard reads data **only** through `casarecon.core`. No SQL, no `duckdb`, no `pandas.read_csv` of `data/raw` in `dashboard/`. The same functions serve `recon worst-week` and `recon query`, so CLI and UI agree.

## Which contract rows each page uses

Row # = the row in the engineer contract. Tier is the engineer's: **Core** exists at the start gate; **Stretch** is written by the engineer in work-order step 13 (owner rule in [00](00-README.md)).

| Row | Function (as in the contract) | Tier | Used on |
|---|---|---|---|
| 1–2 | `connect()` (inside core only), `db_version()` | Core | `data.py` cache key |
| 3 | `status()` → `as_of`, `last_closed_week`, `last_closed_start/end`, `open_weeks`, `last_full_month`, `months`, `n_rows` | Core | as-of banner (all pages), Alerts header |
| 5 | `worst_week(month="last")` | Core | Overview card |
| 6 | `query_transactions(filters, min_usd, limit)` → TXN_COLUMNS | Core | Outliers, Drill-down, both CSVs |
| 7 | `segment_rates(dim, filters)` (`dim` e.g. `country, psp, psp_country, amount_tier, weekday, cross_border, lag_bucket`) | Core | Drill-down chart, Root-causes heatmap |
| 8 | `cause_summary(filters)` | Core | Root causes |
| 9 | `excess_loss(top=5)` → `psp, country, n, rate, peer_rate, lift, excess_usd, mean_loss_usd, median_loss_usd` | Core | Root causes |
| 11–12 | `mask_id` (core only), `exponent`, `to_major` | Core | formatters |
| 13 | `kpis(filters, week)` → `n, n_flagged, n_large, flag_rate, net_usd, gross_under_usd` + `prev_week, delta_rate_pts, delta_net_usd, delta_n_large` when `week` is a week | Stretch | Overview (`week="last_closed"`), Drill-down (`week="all"`) |
| 14 | `weekly_trend(filters, by)` → `series` = `"ALL"` or PSP | Stretch | Overview |
| 15 | `week_over_week(filters)` → `week_prev, week_last, rate_prev, rate_last, delta_pts, n_prev, n_last, low_sample` | Stretch | Overview |
| 16 | `category_mix(filters)` | Stretch | Drill-down chart |
| 17 | `outlier_summary(filters, min_usd)` → `n, gross_under_usd, gross_over_usd` | Stretch | Outliers |
| 18 | `transaction_detail(transaction_id)` | Stretch | Outliers detail |
| 19 | `similar_count(transaction_id)` | Stretch | Outliers detail |
| 20 | `filter_options()` → lists + `months` (full months), `min_date`, `max_date` | Stretch | sidebar, page filters, URL check |
| 22 | `load_alerts()` → incl. `psp`, `country`; `status` NEW/ONGOING/RESOLVED/INSUFFICIENT_DATA; `severity` SEV2/SEV3/INFO | Stretch | Overview KPI, Alerts |
| 23 | `load_findings()` → `{"markdown", "items"}` | Stretch | Root causes |
| 24 | `load_recommendations()` → `rank, action, evidence, owner, implementation, usd_quarter` (from `reports/recommendations.json`) | Stretch | Root causes |

Names you must use (from TXN_COLUMNS): `auth_date` (not `auth_ts`), `exponent` (not `currency_exponent`), `customer` (already masked; the full `customer_id` never leaves core). `Filters` lives in `core/filters.py` with fields `country, psp, tier, xb, weekday, category, cause, week, date_from, date_to`; the UI sends a week as `date_from`/`date_to` and leaves `week` unset. Outliers passes `Filters(category=("large",))`.

**Decision (min_usd is an argument, not a Filters field):** 🎨 Mani wanted everything in `Filters`. 🏛️ Jamshid: `recon query --min-usd` maps 1:1 to `query_transactions(min_usd=…)`, keep that signature. → Separate argument.

## Steps

### 1. `dashboard/data.py`: cached wrappers

```python
import streamlit as st
from casarecon import core
from casarecon.core import queries          # import the MODULE, so tests can monkeypatch it

# Careful: a leading underscore (`_version`) tells Streamlit NOT to hash that arg.
# The DB version must be hashed, so name it `version`. No TTL.
@st.cache_data(show_spinner="Loading…")
def worst_week(month: str, version: float) -> pd.DataFrame:
    return queries.worst_week(month)

def get_worst_week(month: str) -> pd.DataFrame:
    return worst_week(month, core.db_version())
```

- One wrapper per contract row you use. Cache key = function args (`Filters`, `min_usd`, `limit`, `month`…) + `core.db_version()` (DB file mtime). A rebuild changes it, so the cache refreshes on the next run.
- `Filters` must be hashable: frozen dataclass with tuple fields (no lists, no sets). If Streamlit cannot hash it, pass `filters.as_key()` (a tuple) and rebuild the object inside.
- Report loaders (`load_alerts`, `load_findings`, `load_recommendations`) are **not** cached (small files; read on each run). Same rule as the engineer's "Frontend rules".
- Cache DataFrames only (small, pickle-safe). Never cache a connection.

### 2. Connection: short and read-only (engineer side, you just rely on it)
Each core function does `with connect() as con:` → `duckdb.connect(path, read_only=True)`, runs one parameterized query, closes. The dashboard holds **no** open connection, so `make all` can rebuild while the app runs.

### 3. Data guard: one wrapper around every page body

```python
def guarded(render: Callable[[], None]) -> None:
    # core.DbMissing                 → st.info("No data yet. Run `make all` first, then reload this page."); st.stop()
    # core.DbBusy                    → st.warning("The data is being rebuilt. Retry in a minute."); st.button("Retry")
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
- Core masks. The UI only checks: the `customer` column must match `^cus_••••.{4}$` (test 11 in file 09).
- CSV download uses the same DataFrame, so it is masked too.

## Done when
- [ ] `dashboard/data.py` has one cached wrapper per DB-reading row you use, all keyed on `core.db_version()`; no TTL; report loaders uncached.
- [ ] Deleting `data/casarecon.duckdb` → every page shows "Run `make all` first" (no traceback).
- [ ] Running `make all` while the app is open → the app shows "Rebuilding" or fresh data after Retry; never a crash.
- [ ] `grep -rn "duckdb\|read_csv\|SELECT" src/casarecon/dashboard` finds nothing.
- [ ] `format.py` unit tests pass for `CLP 12,345`, `MXN 1,234.56`, `−$62.10 under`, `▲ +1.1 pts`.

## Serves
FR3 (shared core, CLI ↔ UI agree); Tech 15 ("no logic in UI", clean code); privacy (masked IDs); UI-UX build steps 2 and 3.

## Pitfalls
- `_version` with an underscore is silently not hashed → stale data after a rebuild.
- `from casarecon.core.queries import worst_week` in a page: tests cannot monkeypatch it. Import the module.
- Formatting numbers into strings inside DataFrames breaks sort. Use `st.column_config.NumberColumn(format=…)`.
- Loading the full fact table to count rows. Ask core for the count.

## Hand-off
Wrappers + guard + formatters ready. Next: `05-page-outliers.md` (build order) or `03-page-overview.md` (reading order). Keep the list of any Stretch core function you added (owner rule, file 00).
