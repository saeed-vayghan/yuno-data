# Final Solution: CasaMarket Settlement Discrepancies

## 1. System (FR1 pipeline)
- **Stack:** Python 3.12 + uv · DuckDB 1.4.x LTS (one file: `data/casarecon.duckdb`) · dbt-core 1.12 + dbt-duckdb 1.11 · scipy + statsmodels.
- **Flow:** `data/raw` CSV → dbt staging → marts → analysis → reports, dashboard, alerts.
- **Build:** full rebuild from raw on every run. A rerun gives the same output.
- **Reference data (dbt seeds):** currency exponents, PSP fees, VAT rates.
- **Config:** `thresholds.yaml` + `alerts.yaml`.
- **Data quality:** dbt tests; a failed test stops the run (exit 5).
- **Reports:** `reports/FINDINGS.md`, `reports/RECOMMENDATIONS.md` (3–5 actions), `reports/figures/`. Every number comes from data; none are typed by hand.
- **Run (3 ways):** `make all` · `pip install uv && uv run recon all` · `docker compose up`.
- **Scale path (docs only):** PSP files → S3/Iceberg → Airflow → dbt on StarRocks → Superset.

## 2. Detection & root cause (FR1 flag, FR2, FR4)

**Money and FX**
- Both amounts are in local currency, in integer minor units (CLP has 0 decimals).
- Cross-border = `payer_currency = USD`.
- Expected settle (cross-border) = auth × local_per_usd(settle day) / local_per_usd(auth day). Domestic = auth.
- Residual = settled − expected. All cut-offs use the absolute residual.

**Categories** (first match wins; share of approved + settled rows)

| Category | Rule | Share |
|---|---|---|
| `exact` | Δ = 0 | 67% |
| `rounding` | \|Δ\| ≤ 1 minor unit | 1% |
| `fx_tolerance` | ≤ 2% and < $20 | 18% |
| `meaningful` | 2–5% and < $20 | 10% |
| `large` | > 5% or ≥ $20 | 4% |

- **Flag:** `meaningful` + `large` (about 14%).
- **Outlier:** a `large` row.

**Analysis**
- **Segment tests:** rate + Wilson range, lift, chi² (Fisher for small groups), BH-FDR.
- **One logistic GLM:** PSP, country, size, cross-border, weekend, lag, plus PSP × country.
- **Cause labels** on all non-exact rows: fx_timing, psp_rounding, partial_capture, psp_fee, tax_recalc, fraud_hold, psp_adjustment, tip (ruled out), unexplained. They are scored against `data/truth`.
- **Signature table** to tell systematic patterns from random ones (HDBSCAN optional).
- **$ impact:** excess loss = (segment rate − peer rate) × volume × mean loss, with the median beside it; compared with $127k as an estimate.

## 3. Synthetic data (test data spec)
- **Tool:** a custom seeded generator driven by one YAML spec. `recon generate` → `data/raw`, with truth labels in `data/truth`.
- **Shape:**
  - 3 months, 135k rows (`--rows 500` smoke run);
  - MX/CO/AR/CL;
  - PSP_A–E;
  - failed 4%, pending 3%;
  - lag 1–7 days plus outliers;
  - about 20% cross-border.
- **Planted patterns:**
  - P1: PSP_B in AR +3.5 pts;
  - P2: CO orders > $300 settle late;
  - P3: weekend 1.3×;
  - P4: PSP_D rounds cross-border CLP/COP down to 1,000 units;
  - X1–X6: FX, partial capture, fee, tax, fraud hold, PSP adjustment;
  - a PSP_C fee drift in month 3;
  - no tips.
- **Validation:** `recon validate` checks bucket shares and pattern bands. The full run hard-fails; the smoke run only warns.
- **Commit:** script + seed + a 500-row sample.

## 4. CLI (FR3 reports, running)
- **Tool:** Typer, command `recon`, a thin shell over the shared core.
- **Commands:** `generate | build | validate | analyze | alerts | report | query | worst-week | dashboard | all`.
- **`all` order:** generate → build → validate → analyze → alerts → report.
- **Brief questions:**
  - `recon worst-week --month last`
  - `recon query --min-usd 50 --format csv`
- **Exit codes:** 0 ok · 1 error · 2 usage · 5 data-quality or validation failed.

## 5. Dashboard (FR3)
- **Tool:** Streamlit + Plotly at `localhost:8501` (`make app`).
- **Pages:**
  - Overview (KPIs, trend, week-over-week, worst-week card);
  - Drill-down;
  - Outliers (min $50, CSV);
  - Root causes & actions;
  - Alerts.
- **Data access:** short read-only DuckDB connection per query, cached, through the core shared with the CLI.
- **Worst week:**
  - ISO week by auth date; a week belongs to the month of its Thursday;
  - ranked by net USD loss;
  - n < 30 shown greyed.

## 6. Alert system (FR3)
- **Tool:** YAML rules + a small Python evaluator (`recon alerts`) → `alerts.jsonl` + a Markdown report.
- **6 rules:**
  - peer (PSP vs the other PSPs in the same country);
  - change (weekly p-chart);
  - money leak;
  - large-rows summary;
  - pending aging;
  - settle lag.
- **Evaluation:**
  - on the last closed week;
  - n < 50 → "insufficient data";
  - status NEW / ONGOING / RESOLVED vs the last closed week, with no state file.
- **Slack:** optional, off by default.
