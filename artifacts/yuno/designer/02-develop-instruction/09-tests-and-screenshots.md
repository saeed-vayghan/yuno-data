# 09 · Tests and screenshots

**Goal:** turn the 15 UI tests from the UI-UX plan into concrete pytest checks (Streamlit `AppTest` + plain pytest), run them in `make test`, and make the 2 README screenshots.

**Time box:** 12 min (core tests 7 min, rest 5 min) · **Tag:** Core (tests 1, 2, 4, 5, 6, 11, 15) + Stretch (rest, screenshots by script)

## Inputs
- Engineer: `tests/conftest.py` session fixture = 500-row DuckDB in a tmp dir (sets `CASARECON_DB`); `recon worst-week --format json`, `recon query --format csv`.
- Pages 03, 05 at least; files 02 (data wrappers), 08 (states).
- A small extra fixture for alerts: `tests/fixtures/alerts_sample.jsonl` (3–5 hand-written rows, one per severity + one `INSUFFICIENT_DATA`).

## Steps

### 1. Test file and helpers — `tests/test_dashboard.py`

```python
import os, pytest
from streamlit.testing.v1 import AppTest
APP = "src/casarecon/dashboard/app.py"

@pytest.fixture
def app(fixture_db, monkeypatch):           # fixture_db from conftest (500-row DB path)
    monkeypatch.setenv("CASARECON_DB", str(fixture_db))
    import streamlit as st; st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    return at

def open_page(at, page: str) -> AppTest:      # page = "pages/outliers.py"
    at.run(); at.switch_page(page); at.run(); return at
```
Tip: keep CSV building and formatting in plain functions (`data.transactions_csv`, `format.*`) and test them directly. `AppTest` has no simple way to click a download button.

### 2. The 15 tests

| # | Test | How (concrete) | Tag |
|---|---|---|---|
| 1 | Smoke | For each of the 5 page files: `open_page(at, p)`; `assert not at.exception` | Core |
| 2 | No DB | `CASARECON_DB=tmp/missing.duckdb`; run; `assert "Run `make all` first" in " ".join(i.value for i in at.info)` | Core |
| 3 | Locked DB | `monkeypatch.setattr(queries, "worst_week", raise_(DbBusy("rebuilding, retry")))`; Overview; assert warning contains "being rebuilt" and a button labelled "Retry" exists | Stretch |
| 4 | Worst week CLI ↔ UI | `CliRunner().invoke(app, ["worst-week","--month","last","--format","json"])` → top row `psp, auth_week, net_usd`; equals `queries.worst_week("last").iloc[0]`; and the Overview card markdown contains the PSP and `W##` text | Core |
| 5 | Over $50 CLI ↔ UI | `recon query --min-usd 50 --format csv` → set of `transaction_id`; equals set from `queries.query_transactions(Filters(), min_usd=50)` **and** from `data.transactions_csv(Filters(), 50)`; and Outliers `at.dataframe[0].value["Transaction"]` ⊆ that set (table is capped at 1,000) | Core |
| 6 | Default filter | Outliers: `at.number_input[0].value == 50`; `(df["Discrepancy after FX (USD)"].abs() > 50).all()` | Core |
| 7 | Filter change | `at.number_input[0].set_value(100).run()`; set PSP multiselect to `["PSP_B"]`; all rows > 100 and PSP_B | Stretch |
| 8 | URL params | `at.query_params["psp"] = "PSP_B"` before first run → Drill-down PSP multiselect value `["PSP_B"]`; `"PSP_Z"` → dropped + toast text "Ignored unknown PSP" | Stretch |
| 9 | Empty state | Filters that match nothing (e.g. `min_usd = 10_000_000`) → info "No transactions over…" (Outliers) / "No transactions match these filters." (Drill-down) | Stretch |
| 10 | Low sample | On the 500-row DB every PSP-week has n < 30 → card text contains "low sample"; `queries.worst_week("last")` has low-sample rows last | Stretch |
| 11 | Masking | For every `at.dataframe` on all pages and the CSV bytes: no value in `customer_id` / "Customer" fails `^cus_••••.{4}$`; no raw `cus_` token from `data/raw` appears | Core |
| 12 | Currency format | `format.local(12345, "CLP", 0) == "CLP 12,345"`; Outliers CLP rows' raw-diff text has no `.`; USD columns configured with 2 dp | Stretch |
| 13 | Alerts | Point core at `alerts_sample.jsonl` → metric values per severity equal counts in the file; point at an all-`INSUFFICIENT_DATA` file → "Not enough data for alerts" | Stretch |
| 14 | Recommendations | With a sample RECOMMENDATIONS.md → 3–5 items (count `at.expander` labelled "How to implement"); missing file → "not built yet" | Stretch |
| 15 | Formatters | `@pytest.mark.parametrize` over every row of the number-format table (`$1,234.56`, `$127.4k`, `−$62.10 under`, `+$4.00 over`, `MXN 1,234.56`, `COP 123,456.78`, `ARS 9,870.00`, `CLP 12,345`, `14.2%`, `▲ +1.1 pts`, `▼ −0.4 pts`, `21.3% [19.8–22.9]`, `12,345`, `W29 (Jul 13–19)`) | Core |

Also add, one each, the pytest for any core function you added (S5.3 rule): call it on the fixture DB, check columns and one known value.

### 3. Wire into `make test`
`make test` = `uv run pytest -q` already collects `tests/test_dashboard.py`. Keep each AppTest under ~5 s; the whole UI suite under 60 s.

**Decision (AppTest vs browser tests):** 🎨 Mani wanted a Playwright click-through. 🏛️ Jamshid: new tool, needs a browser in CI, breaks the "no other tools" stack. → `AppTest` only; the click-through is a manual check (step 5).

### 4. Screenshots for the README (2 PNGs)

| File | Shows | How |
|---|---|---|
| `docs/screenshots/overview-worst-week.png` | Overview with the worst-week card (brief Q1) | Manual: run `make all && make app`, full dataset, browser at 1280 px, OS screenshot |
| `docs/screenshots/outliers-over-50.png` | Outliers at min $50 with one row selected (brief Q2) | Same |

- Chart PNGs (not app screenshots): the engineer's `reports/figures/*.png` already come from `fig.write_image(...)` via **kaleido**. If you want a chart PNG from a page, reuse the same helper: `try: fig.write_image(path) except Exception: fig.write_html(path.with_suffix(".html")); log.warning(...)`. kaleido needs a Chrome/Chromium install; in Docker/CI it often fails → HTML fallback, and commit the PNGs from your own machine.
- Do not add a headless-browser tool just for screenshots.
- Take screenshots from the **full** run (135k rows), not the 500-row smoke run (everything would be "low sample").

### 5. Manual checks before hand-in (5 min)
- Timed newcomer run: using only the README, answer both brief questions in ≤ 2 clicks each.
- Keyboard-only pass over Outliers (Tab to min $, table, Download CSV).
- (Stretch) CVD simulator on Overview + Root causes; 200% zoom.

## Done when
- [ ] Core tests 1, 2, 4, 5, 6, 11, 15 pass in `make test` on the fixture DB.
- [ ] (Stretch) all 15 pass.
- [ ] Both screenshots exist in `docs/screenshots/` and are linked from the README (file 10).
- [ ] Manual newcomer run done and noted.

## Serves
Rubric Tech 15 (tested, reproducible); DoD "demonstrate thoughtful data engineering practices"; FR3 acceptance proven by tests 4 and 5; UI-UX build step 10; DELIVERABLES-CHECK item 10.

## Pitfalls
- Cache leaks between tests: call `st.cache_data.clear()` in the fixture.
- Monkeypatching a function that the page imported by name: patch has no effect. Pages import `queries` as a module (file 02).
- Comparing the capped UI table (1,000 rows) with the full CLI set: compare the CSV/core set for equality, the table for subset.
- Test 4 on the 500-row DB: all rows are low sample, so ties are possible. Break ties in core (net USD desc, then PSP name) and in the CLI the same way.
- Committing screenshots from the smoke run.

## Hand-off
Tests green, screenshots taken. Next: `10-readme-monitoring-and-handoff.md`.
