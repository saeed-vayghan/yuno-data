# 02 · Config and the shared core

**Goal:** put every cut-off in YAML, and build one read-only `casarecon.core` package that the CLI, analysis, alerts and dashboard all call. This file defines the **CORE API CONTRACT** the frontend developer consumes.

**Time box:** part A 5 min (now) · part B 5 min (after file 04) · part C 15 min (after the core checkpoint)
**Tag:** A + B **Core** · C **Stretch**

## Inputs
- File 01 done.
- IMPLEMENTATION-PLAN S0.2, S3.1, S5.3 · UI-UX-PLAN "Pages" tables (source functions) · decision sheet (money, categories, week rules).
- Diagram: `../../architect/03-system-design/06-cli-and-dashboard.svg`.

## Module map

| Module | Holds | Part |
|---|---|---|
| `core/config.py` | pydantic models for the 3 YAML files, `load_config()`, `dbt_vars()` | A |
| `core/paths.py` | repo root, `DB_PATH` (env `CASARECON_DB`), `RAW_DIR`, `TRUTH_DIR`, `REPORTS_DIR`, `SEEDS_DIR` | A |
| `core/errors.py` | `DataQualityError`, `DbMissing`, `DbBusy`, `BadFilter` | A |
| `core/db.py` | `connect()`, `db_version()` | A |
| `core/money.py` | `exponent()`, `to_major()`, `round_half_up()`, `expected_settled()` | A |
| `core/privacy.py` | `mask_id()` | A |
| `core/filters.py` | `Filters` dataclass + `where_sql()` | A |
| `core/queries.py` | all read functions in the contract | B (Core rows), C (Stretch rows) |
| `core/__init__.py` | re-exports everything in the contract | A |

---

## Part A (Core, 5 min)

### A1. `config/thresholds.yaml`
```yaml
# categories (first match wins, see file 04). All cut-offs on ABSOLUTE residual.
rounding_minor_units: 1        # |diff_local| <= 1 minor unit → rounding
fx_tolerance_pct: 2            # |residual_pct| <= 2 and |residual_usd| < large_usd → fx_tolerance
large_pct: 5                   # |residual_pct| > 5 → large
large_usd: 20                  # |residual_usd| >= 20 → large   (brief: "$20 is not" noise)
lag_outlier_days: 7            # settle_lag_days > 7 → is_lag_outlier
sensitivity_pcts: [1, 2, 3]
causes:
  rounding_step_major: 1000    # settled is a multiple of 1,000 MAJOR units (no PSP name here)
  fee_min_usd: 1
  fee_min_repeats: 20          # same residual repeated >= 20 times in one PSP × currency
  high_risk_score: 0.8
  partial_tolerance_pct: 0.5   # settled within 0.5% of expected × (n-1)/n
money_leak: {warn_pct: 1.5, crit_pct: 2.5, weekly_usd: 9800}   # tune after the first full run
min_sample: {alerts: 50, worst_week: 30}
full_run_min_rows: 10000       # below this, validate pattern checks only warn
```

> **Decision (rounding step):** ⚡ Kaveh: IMPLEMENTATION-PLAN keys the step by PSP (`rounding_steps: {PSP_D: …}`), but the cause rules must "never name a PSP". 🏛️ Jamshid: keep one generic `causes.rounding_step_major: 1000`; the PSP_D planting lives only in `generator.yaml`. The analysis then *finds* PSP_D.

### A2. `config/alerts.yaml`
```yaml
slack: {enabled: false}        # posts only if enabled AND env SLACK_WEBHOOK_URL is set
rules:
  - {id: peer,          severity: SEV2, owner: "PSP ops", window_weeks: 4, q_max: 0.05, min_gap_pts: 2}
  - {id: change,        severity: SEV3, owner: "PSP ops", window_weeks: 8, sigma: 3}
  - {id: money_leak,    severity_warn: SEV3, severity_crit: SEV2, owner: "Finance"}   # limits in thresholds.yaml
  - {id: large_rows,    severity: SEV3, owner: "PSP ops", top_n: 3}
  - {id: pending_aging, owner: "PSP ops + Finance", warn_days: 7, crit_days: 14}      # SEV3 / SEV2
  - {id: settle_lag,    severity: SEV3, owner: "PSP ops", window_weeks: 4, late_days: 7, max_late_share: 0.06}
```
`config/generator.yaml` is written in file 03.

### A3. `core/config.py`
```python
class Thresholds(BaseModel):  # one field per key above; validators: pct > 0, fx_tolerance_pct < large_pct
    ...
class AlertsConfig(BaseModel): ...
class GeneratorConfig(BaseModel): ...
class Config(BaseModel):
    thresholds: Thresholds; alerts: AlertsConfig; generator: GeneratorConfig

def load_config(root: Path = REPO_ROOT) -> Config: ...      # raises ValueError with the bad key
def dbt_vars(cfg: Config | None = None) -> str:              # JSON string for dbt --vars
    return json.dumps({"thresholds": cfg.thresholds.model_dump()})
```

### A4. `core/paths.py`
- `REPO_ROOT` = folder that holds `pyproject.toml`.
- `DB_PATH = Path(os.environ.get("CASARECON_DB", REPO_ROOT / "data/casarecon.duckdb")).resolve()` (always absolute).
- `RAW_DIR`, `TRUTH_DIR`, `SAMPLE_DIR`, `REPORTS_DIR`, `FIGURES_DIR`, `SEEDS_DIR = REPO_ROOT/"dbt/seeds"`. `RAW_DIR` and `REPORTS_DIR` honour env `CASARECON_RAW_DIR` / `CASARECON_REPORTS_DIR` (the test fixture points them at a tmp dir).

### A5. `core/errors.py`
| Error | Raised when | CLI maps to | UI shows |
|---|---|---|---|
| `DataQualityError` | failed dbt test or validation gate | exit 5 | — |
| `DbMissing` | `DB_PATH` does not exist (raised by `connect()`) | exit 1, "Run `make all` first" | "No data yet. Run `make all` first" |
| `DbBusy` | DuckDB lock error while `build` writes | exit 1, "rebuilding, retry" | "The data is being rebuilt. Retry in a minute." |
| `BadFilter` | unknown filter value / sort key | exit 2 | drop value + toast |

### A6. `core/db.py`
```python
@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    if not DB_PATH.exists(): raise DbMissing(str(DB_PATH))
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    except duckdb.IOException as e:            # "Could not set lock on file"
        raise DbBusy("rebuilding, retry") from e
    try: yield con
    finally: con.close()

def db_version() -> float:                      # cache key for the dashboard
    return DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0
```
Rule: **only `recon build` opens the DB for writing.** Every other path uses `connect()`.

### A7. `core/money.py` (shared by generator, analysis and UI formatters)
```python
def exponent(currency: str) -> int          # from dbt/seeds/currency_exponents.csv (CLP 0, others 2)
def to_major(amount_minor: int, currency: str) -> Decimal
def round_half_up(x: float) -> int          # MUST match DuckDB round() for positive values
def expected_settled(auth_minor: int, fx_auth: float, fx_settle: float, cross_border: bool) -> int
    # cross-border: round_half_up(auth * fx_settle / fx_auth); domestic: auth
```

### A8. `core/privacy.py`
```python
def mask_id(customer_id: str | None) -> str | None:
    # "cus_8f2a91c07f3a" -> "cus_••••7f3a"; None -> None
```

### A9. `core/filters.py`
```python
@dataclass(frozen=True)                       # frozen + tuples → hashable → st.cache_data works
class Filters:
    country: tuple[str, ...] = ()             # MX CO AR CL
    psp: tuple[str, ...] = ()                 # PSP_A..PSP_E
    tier: tuple[str, ...] = ()                # "10-50" "50-200" "200+"
    xb: Literal["all", "cross", "domestic"] = "all"
    weekday: tuple[str, ...] = ()             # Mon..Sun
    category: tuple[str, ...] = ()            # exact rounding fx_tolerance meaningful large
    cause: tuple[str, ...] = ()               # fx_timing ... unexplained
    week: str | None = None                   # "2026-W25"
    date_from: date | None = None             # auth date, inclusive
    date_to: date | None = None               # auth date, inclusive

    def validate(self) -> None: ...           # raises BadFilter on unknown values
    def where_sql(self) -> tuple[str, list]:  # " and country in (?, ?) ..." + params; never string-formats values
```

> **Decision (Filters home):** UI-UX-PLAN puts `Filters` in `dashboard/filters.py`. 🏛️ Jamshid: core must not import the dashboard. `Filters` lives in `core/filters.py`; `dashboard/filters.py` only maps it to and from `st.query_params`. `min_usd` stays a separate argument (as in `query_transactions`).

---

## Part B (Core, 5 min, after file 04 builds the marts)
Write the **Core** rows of the contract in `core/queries.py`. Each function: open `connect()`, run one parameterized SQL on a mart (or `fct_transaction_discrepancy`), return a DataFrame / dict, close.

## Part C (Stretch, 15 min, after the core checkpoint)
**Owner rule:** the engineer owns `core/` and writes these rows (work-order step 13, right after the CLI brief questions). If a row is still missing when a page needs it, the frontend developer may add it, using exactly the name, args and columns in the contract, the part B pattern (`connect()`, `?` params) and one pytest; the engineer reviews it. Write the **Stretch** rows in the UI build order: Outliers (`outlier_summary`, `transaction_detail`, `similar_count`) → Overview (`kpis`, `weekly_trend`, `week_over_week`) → Drill-down (`category_mix`, `filter_options`) → Alerts (`load_alerts`) → Root causes (`load_recommendations`, `load_findings`). One pytest per function on the 500-row fixture DB.

---

## CORE API CONTRACT

Import: `from casarecon import core`. All functions are **read-only**, take plain Python values, and return a pandas `DataFrame`, `dict`, `str` or `None`. Money in DataFrames: local amounts are **int minor units** (with an `exponent` column); USD amounts are **float, rounded to 2 dp**. Rates are **fractions 0–1**; `*_pts` are percentage points; `residual_pct` is in **percent**. Loss sign: `gross_under_usd ≥ 0`, `gross_over_usd ≥ 0`, `net_usd = gross_under_usd − gross_over_usd` (positive = CasaMarket lost money).

| # | Function | Arguments | Returns | Columns / keys (type) | Used by | Tier |
|---|---|---|---|---|---|---|
| 1 | `connect()` | – | context manager → read-only `DuckDBPyConnection` | raises `DbMissing`, `DbBusy` | every core function | Core |
| 2 | `db_version()` | – | `float` | DB file mtime (0.0 if missing); dashboard cache key | dashboard | Core |
| 3 | `status()` | – | `dict` | `as_of: datetime`, `last_closed_week: str` ("2026-W25"), `last_closed_start: date`, `last_closed_end: date`, `open_weeks: list[str]` (weeks after the last closed one), `last_full_month: str` ("2026-06"), `months: list[str]`, `n_rows: int`. `as_of` = latest timestamp in the data (never wall-clock); closed week = ISO week whose Sunday ≤ `as_of − 7 days`. Full data: as_of 2026-06-30, last closed 2026-W25 (Jun 15–21), last full month 2026-06 | CLI, alerts, UI banner | Core |
| 4 | `psp_weekly(filters=None)` | `Filters \| None` (uses `psp`, `country`, `week`) | `DataFrame` | `psp, country, auth_week: str, week_start: date, week_end: date, week_month: str, n: int, n_flagged: int, rate: float, n_large: int, gross_under_usd, gross_over_usd, net_usd: float, low_sample: bool` | analysis, alerts | Core |
| 5 | `worst_week(month="last")` | `"last"` or `"YYYY-MM"` | `DataFrame`, ranked | `rank: int, psp, auth_week, week_start, week_end, n, n_flagged, rate, n_large, net_usd, gross_under_usd, low_sample` — one row per PSP × week whose Thursday is in `month`; sorted by `low_sample` asc, then `net_usd` desc, then `psp` asc, then `auth_week` asc (deterministic tie-break; the CLI prints this order as is) | `recon worst-week`, Overview card, FINDINGS | Core |
| 6 | `query_transactions(filters=None, min_usd=None, limit=None)` | `Filters \| None`, `float \| None` (strict `abs_residual_usd > min_usd`), `int \| None` | `DataFrame` of **settled** fct rows, sorted `abs_residual_usd` desc, `transaction_id` asc | **TXN_COLUMNS** (below) | `recon query`, Outliers, Drill-down, CSV | Core |
| 7 | `segment_rates(dim, filters=None)` | `dim` ∈ `country, currency, psp, psp_country, amount_tier, country_tier, weekday, is_weekend, lag_bucket, cross_border`; `Filters \| None` (None → read `mart_segment_rates`; else aggregate `fct`) | `DataFrame` | `segment_type, segment_value: str, n, n_flagged: int, rate, ci_low, ci_high (Wilson 95%), peer_rate, lift: float, n_large: int, gross_under_usd, gross_over_usd, net_usd, mean_loss_usd, median_loss_usd: float, low_sample: bool` | analysis, Drill-down, heatmap | Core |
| 8 | `cause_summary(filters=None)` | `Filters \| None` | `DataFrame` sorted `gross_under_usd` desc | `likely_cause, n: int, n_flagged: int, gross_under_usd, gross_over_usd, net_usd, share_of_loss: float` — one row per cause label, `tip` always present (0 rows = "ruled out") | analysis, Root causes | Core |
| 9 | `excess_loss(top=None)` | `int \| None` | `DataFrame` sorted `excess_usd` desc | `psp, country, n: int, rate, peer_rate, lift, excess_usd, mean_loss_usd, median_loss_usd: float` (peer = other PSPs in same country) | analysis, Root causes | Core |
| 10 | `lag_by_country_tier()` | – | `DataFrame` | `country, amount_tier, is_over_300: bool, n: int, median_lag_days, p90_lag_days, late_share: float` | analysis (P2), alerts | Core |
| 11 | `mask_id(customer_id)` | `str \| None` | `str \| None` | `"cus_••••" + last 4` | query, CSV, UI | Core |
| 12 | `exponent(currency)` · `to_major(amount_minor, currency)` | `str` · `int, str` | `int` · `Decimal` | from `currency_exponents` seed (CLP 0) | UI formatters | Core |
| 13 | `kpis(filters=None, week="last_closed")` | `Filters \| None`; `"last_closed"`, `"all"` or ISO week | `dict` | `n, n_flagged, n_large: int, flag_rate, net_usd, gross_under_usd: float`; when `week` is a week also `prev_week: str`, `delta_rate_pts, delta_net_usd: float`, `delta_n_large: int` | Overview, Drill-down | Stretch |
| 14 | `weekly_trend(filters=None, by="portfolio")` | `by` ∈ `portfolio, psp` | `DataFrame` | `auth_week, week_start, series: str ("ALL" or PSP), n, n_flagged, rate, net_usd, gross_under_usd, is_closed: bool, low_sample: bool` | Overview | Stretch |
| 15 | `week_over_week(filters=None)` | `Filters \| None` | `DataFrame` sorted `delta_pts` desc | `psp, country, week_prev, week_last: str, rate_prev, rate_last, delta_pts: float, n_prev, n_last: int, low_sample: bool` (last closed vs the one before) | Overview, alerts.md | Stretch |
| 16 | `category_mix(filters=None)` | `Filters \| None` | `DataFrame` | `auth_week, category: str, n: int, share: float` (order exact → large) | Drill-down | Stretch |
| 17 | `outlier_summary(filters=None, min_usd=50)` | `Filters \| None`, `float` | `dict` | `n: int, gross_under_usd, gross_over_usd: float` (same rows as `query_transactions`) | Outliers | Stretch |
| 18 | `transaction_detail(transaction_id)` | `str` | `dict \| None` | TXN_COLUMNS + `fx_auth, fx_settle, fx_move_pct, amount_usd, settled_usd: float, item_count: int, risk_score: float, is_weekend, is_lag_outlier, rounding_flag: bool` | Outliers detail panel | Stretch |
| 19 | `similar_count(transaction_id)` | `str` | `dict` | `psp, country, likely_cause: str, n: int` | Outliers detail panel | Stretch |
| 20 | `filter_options()` | – | `dict[str, list[str]]` | `country, psp, tier, weekday, category, cause, weeks, months` (full calendar months only), `min_date, max_date` (auth date range, ISO strings) | Drill-down widgets, URL validation | Stretch |
| 21 | `pending()` | – | `DataFrame` | `psp, country, n: int, amount_usd, oldest_age_days: float` (age vs `as_of`) | alerts | Stretch |
| 22 | `load_alerts()` | – | `DataFrame \| None` (None if file missing) | `period, rule_id, segment, key, severity, status, message, owner: str, psp, country: str \| None` (null when not part of the segment), `n: int, value, threshold: float`. `status` ∈ `NEW, ONGOING, RESOLVED, INSUFFICIENT_DATA`; `severity` ∈ `SEV2, SEV3, INFO` (file 08) | Alerts page, Overview KPI | Stretch |
| 23 | `load_findings()` | – | `dict \| None` | `{"markdown": str (FINDINGS.md), "items": list[dict]}` (`items` = `findings.json["findings"]`) | Root causes | Stretch |
| 24 | `load_recommendations()` | – | `list[dict] \| None` | `rank: int, action, evidence, owner, implementation: str, usd_quarter: float` (from `reports/recommendations.json`) | Root causes | Stretch |

**TXN_COLUMNS** (fixed order; also the `recon query --format csv` header):
`transaction_id, auth_date, psp, country, currency, exponent, customer, amount_tier, is_cross_border, category, likely_cause, why_flagged, authorized_amount, expected_settled, settled_amount, diff_local, residual_usd, abs_residual_usd, residual_pct, direction, settle_lag_days`
- `customer` = `mask_id(customer_id)`; the full ID never leaves core.
- `authorized_amount, expected_settled, settled_amount, diff_local` = int minor units; `residual_usd` signed (negative = under); `direction` ∈ `under, over, none`.

**Frontend rules:** wrap every DB-reading call in `st.cache_data` (no TTL), passing `core.db_version()` as a hashed argument (no leading `_`) so a rebuild clears the cache; do not cache the 3 report loaders (`load_*`: small files, read on each run); catch `DbMissing` / `DbBusy`; never write SQL in a page; `Filters` must be built from `filter_options()` values. The Outliers page passes `Filters(category=("large",))` so that "min $0" still shows only `large` rows (every row over $20 is `large` anyway, so "over $50" is unchanged).

---

## Done when
| Command | Expected |
|---|---|
| `uv run python -c "from casarecon.core.config import load_config; load_config()"` | exit 0 |
| edit `large_pct: -1`, rerun | `ValueError` naming `large_pct` |
| `uv run python -c "from casarecon.core.config import dbt_vars; print(dbt_vars())"` | one JSON line with `thresholds` |
| `uv run python -c "from casarecon.core import mask_id; print(mask_id('cus_8f2a91c07f3a'))"` | `cus_••••7f3a` |
| (part B) `uv run pytest -q tests/test_core.py -k core` | Core-row functions pass on the 500-row fixture DB |
| (part C) `uv run pytest -q tests/test_core.py` | every contract function has ≥ 1 passing test |
| `uv run python -c "import inspect, casarecon.core as c; print(all(hasattr(c, n) for n in ['worst_week','query_transactions','mask_id']))"` | `True` |

## Serves
FR1 "define meaningful" (cut-offs in config) · FR3 (one core for CLI + dashboard) · Tech 15 (no logic in UI, typed config) · security (read-only DB, fixed filters, masked IDs).

## Pitfalls
- **DuckDB lock:** `build` writes a `.tmp` file and swaps it in (file 04), so `DbBusy` is rare; keep the handler anyway. Keep connections short (open → query → close). Never keep a global connection in Streamlit.
- **Relative DB path:** dbt runs from `dbt/`, the CLI from the repo root. Always pass an **absolute** `DB_PATH` (file 04 sets `CASARECON_DB` before calling dbt).
- **Rounding mismatch:** Python `round()` is banker's rounding; DuckDB `round()` is half away from zero. Use `round_half_up()` in Python everywhere money is rounded, or generator and dbt will disagree by 1 minor unit.
- **CLP has 0 decimals:** never hard-code `/100`; always use `exponent()`.
- `$` is ambiguous across MXN/COP/ARS/CLP: USD values go in `*_usd` columns; local values always travel with `currency`.
- `Filters` must be `frozen=True` with tuples, not lists, or `st.cache_data` cannot hash it.
- `min_usd` is **strict `>`** ("over $50"). Do not use `>=`.
- Never build SQL with f-strings from user values; use `?` params. Sort keys come from a whitelist.

## Hand-off
- File 03 uses `money.expected_settled`, `round_half_up` and `generator.yaml` models.
- File 04 uses `dbt_vars()` and `DB_PATH`.
- Files 06, 08, 09 call only the contract functions.
- **Frontend developer:** the contract table above, the `Filters` dataclass, the error table, and the "Frontend rules".
