# 03 · Synthetic data generator

**Goal:** `recon generate` writes a seeded, reproducible dataset (135k rows, 3 months, MX/CO/AR/CL, PSP_A–E) with planted patterns P1–P4, X1–X6, the PSP_C fee drift, and truth labels kept apart.

**Time box:** 20 min · **Core**

## Inputs
- Files 01, 02 part A (`money.py`, config models).
- Brief "Test Data Specification" · decision sheet "Planted patterns" · IMPLEMENTATION-PLAN S1.1–S1.3.
- Diagram: `../../architect/03-system-design/02-data-generation.svg`.

## Steps

1. **Write `config/generator.yaml`:**
   ```yaml
   seed: 42
   rows: 135000
   start: 2026-04-01
   months: 3                              # 3 full calendar months; window end = 2026-06-30 23:59:59
   countries: {MX: 0.40, CO: 0.25, AR: 0.20, CL: 0.15}
   currency: {MX: MXN, CO: COP, AR: ARS, CL: CLP}
   psps: {PSP_A: 0.30, PSP_B: 0.25, PSP_C: 0.20, PSP_D: 0.15, PSP_E: 0.10}
   status: {settled: 0.93, failed: 0.04, pending: 0.03}
   cross_border_share: 0.20
   tiers_usd: {"10-50": 0.45, "50-200": 0.40, "200+": 0.15}   # ~40% of 200+ above $300 → ~6% over $300
   item_count: {1: 0.55, 2: 0.25, 3: 0.12, 4: 0.08}           # max 4 (see pitfalls)
   lag_days: {min: 1, max: 7, mode: 2, outlier_share: 0.02, outlier_range: [8, 15]}
   fx_base: {MXN: 18.0, COP: 4000.0, ARS: 1000.0, CLP: 950.0}
   buckets: {exact: 0.67, rounding: 0.01, fx_tolerance: 0.18, meaningful: 0.10, large: 0.04}
   patterns:
     P1: {psp: PSP_B, country: AR, meaningful_boost_pts: 3.5}
     P2: {country: CO, min_usd: 300, extra_lag_days: [2, 4], outlier_share: 0.10}
     P3: {weekend_meaningful_ratio: 1.3}
     P4: {psp: PSP_D, currencies: [CLP, COP], cross_border_only: true, step_major: 1000}
     X3: {psp: PSP_C, fee_local: {MXN: 3000, COP: 600000, ARS: 150000, CLP: 1400}, months: [3]}  # ≈ $1.5, minor units
     X4: {countries: [MX, CO], pct_range: [0.2, 1.9], domestic_only: true, both_signs: true}
     X5: {min_risk: 0.8, withheld_pct: [10, 20], single_item_only: true}
     X6: {pct_range: [2, 5]}
   tips: none
   ```

2. **`generate/fx.py`** → `fx_rates_daily(rate_date, currency, local_per_usd)`:
   - Daily random walk per currency from `fx_base`, every calendar day (weekends too), covering window + 15 days.
   - Cap so any 15-day move stays < 2%. Round rates to 6 decimals (both Python and DuckDB then read the same number).

3. **`generate/rows.py` (base rows)**, all randomness from one `rng = numpy.random.default_rng(seed)`:
   - `auth_ts` uniform over the window (merchant local time, no timezone), `country` → `currency`, `psp`, `is_cross_border` (20%) → `payer_currency` = `USD` if cross-border else local.
   - `transaction_id` = `txn_` + 12 hex from `rng`; `customer_id` = `cus_` + 12 hex token (no names, no emails).
   - `product_category` (e.g. furniture, kitchen, decor, bedding, lighting), `item_count`, `risk_score` (beta, ~3% ≥ 0.8), `card_bin_country` (ISO-2).
   - Tier first, then `amount_usd` inside the tier (≥ $10); `authorized_amount = round_half_up(amount_usd × fx_auth × 10^exp)`.
   - `status`; lag from the lag spec; `settle_ts = auth_ts + lag`.
   - **As-of rule:** if `settle_ts` > window end, the row becomes `pending` (`settle_ts`, `settled_amount` null). Failed rows: both null.

4. **`generate/patterns.py`**, in this exact order:
   | Step | What |
   |---|---|
   | 1 | **P2:** CO rows with `amount_usd > 300` get lag + U(2,4) days and 10% lag outliers (re-apply the as-of rule). |
   | 2 | **P4 first:** PSP_D, cross-border, CLP/COP: `settled = floor(expected / step) × step`, `step = 1000 × 10^exp` minor units. The row keeps whatever bucket its diff lands in. |
   | 3 | **Buckets** for other settled rows: counts so the **total** (incl. P4 rows) hits 67/1/18/10/4. Weights: P1 (PSP_B × AR) +3.5 pts on `meaningful`; P3 weekend `meaningful` × 1.3. |
   | 4 | **Cause per bucket** (must fit the row): `exact` → none · `rounding` → ±1 minor unit, domestic · `fx_tolerance` → X1 (cross-border, residual 0) or X4 (MX/CO domestic, ±0.2–1.9%) or X3 (PSP_C, month 3, order big enough to stay < 2%) · `meaningful` → X6 (−2 to −5%, < $20) or X3 (PSP_C month 3, small order) · `large` → X2 (`item_count` ≥ 2, settle = expected × (n−1)/n) or X5 (risk ≥ 0.8, single item, 10–20% withheld) or X6 on big orders (≥ $20). |
   | 5 | **Size** the diff inside the bucket limits; recheck: `meaningful` rows must stay < $20 and 2–5%; `large` must be > 5% or ≥ $20. |
   | 6 | `settled_amount = expected_settled + delta` where `expected_settled` comes from `core.money.expected_settled()` (same formula as dbt). |
   - **Drift:** X3 is only drawn in month 3 (June), so PSP_C's rate jumps there.
   - **Tips:** none. No positive residual except X4 (+), `rounding` (+1) and FX rounding (±1).

5. **`generate/writer.py`** writes:
   | File | Content |
   |---|---|
   | `data/raw/transactions.csv` | contract columns only, sorted by `transaction_id` |
   | `data/raw/fx_rates_daily.csv` | sorted by `rate_date, currency` |
   | `data/truth/labels.parquet` | `transaction_id, true_bucket, true_cause, pattern_ids` (e.g. `"P1;X6"`) |
   | `data/raw/generation_manifest.json` | seed, rows, window, realized bucket mix, package versions (no wall-clock time) |
   - Write parquet with DuckDB (`COPY (SELECT * FROM df) TO '…' (FORMAT parquet)`) or pandas + pyarrow (already pulled in by Streamlit).
   - Truth cause names = the `likely_cause` labels: `fx_timing, psp_rounding, partial_capture, psp_fee, tax_recalc, fraud_hold, psp_adjustment` (+ `psp_rounding` for the `rounding` bucket, see Decision).

6. **Wire `recon generate [--rows N] [--seed S]`** (overrides YAML). Log `step=generate rows=… secs=…`.

7. **Commit a sample:** `uv run recon generate --rows 500 && cp data/raw/transactions.csv data/sample/transactions_500.csv`.

8. **Tests `tests/test_generator.py`:** same seed → same bytes; no column outside the contract and no banned field; P4 rows: settled multiple of the step and ≤ expected; `meaningful` rows < $20; FX 15-day move < 2%; `settle_ts ≤ window end` for all settled rows.

> **Decision (rounding bucket cause):** ⚡ Kaveh: the ±1-minor-unit `rounding` rows need a cause label, and the label list is fixed. 🏛️ Jamshid: label them `psp_rounding` (the PSP rounded the amount) in both truth and SQL; P4 is the large-step case of the same cause.

## Done when
| Command | Expected |
|---|---|
| `time uv run recon generate --rows 500` | exit 0, < 5 s |
| run it twice, `shasum -a 256 data/raw/transactions.csv` | same hash both times |
| `uv run recon generate` (full) | 135,000 rows, < 60 s |
| `uv run python -c "import pandas as p; d=p.read_csv('data/raw/transactions.csv'); print(d.country.nunique(), d.psp.nunique(), d.status.value_counts(normalize=True).round(2).to_dict())"` | `4 5 {'settled': ~0.93, 'failed': ~0.04, 'pending': ~0.03}` |
| `uv run pytest -q tests/test_generator.py` | passes |

## Serves
Deliverable 2 (dataset + script) · Test data 10 (realistic mix, planted patterns) · brief test-data bullets (≥ 500 rows, 3–4 months, 4 countries/currencies, 3–5 PSPs, statuses, lag 1–7 + outliers, customer ID, category, tiers, cross-border).

## Pitfalls
- **One RNG only.** No `random`, no `np.random.seed`, no `uuid4()`, no `datetime.now()` in outputs; they break the byte-identical rerun.
- **Cross-border rows can never be `exact`** (FX moves every day). With 20% cross-border, `exact` 67% must come from domestic rows, and X1 fills most of `fx_tolerance` (18%). Keep X4 small.
- **P4 "1,000 units" = major units.** CLP step = 1,000 minor; COP step = 100,000 minor. `settled` for COP ends in `00000`, not `000`.
- **Partial capture vs fraud hold overlap:** (n−1)/n with n ≥ 5 is ≤ 20% under, which looks like X5. Hence `item_count` ≤ 4 (partial ≥ 25% under) and X5 only on single-item orders.
- **X3 fee must be fixed in local minor units** (not USD converted daily), or the "same amount repeated" rule in file 04 cannot see it.
- **X6 in `meaningful` must stay < $20**; on a $900 order, 3% = $27 → it is `large`. Draw X6 `meaningful` on smaller orders.
- **$20 boundary:** a row at exactly $20.00 residual is `large`. Keep the generator's own bucket check on the same rule (`≥ 20`).
- **Pending placement:** pending rows must come from the as-of rule (auth in the last days), not a random 3% everywhere.
- Money columns must be **integers** in the CSV (no `1234.0`). Cast before writing.

## Hand-off
- File 04 reads `data/raw/*.csv` as dbt sources. dbt never reads `data/truth`.
- File 05 compares realized shares/patterns; file 06 scores `likely_cause` against `data/truth/labels.parquet`.
