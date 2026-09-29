# 05 · Validation gate (`recon validate`)

**Goal:** prove the built data matches the brief's test-data ranges and that P1–P4 really exist. Full run: any miss → exit 5. Smoke run: pattern misses only warn.

**Time box:** 5 min · **Core**

## Inputs
- File 04 (built `marts.fct_transaction_discrepancy`), file 02 (`connect()`, `thresholds.yaml: full_run_min_rows`).
- Brief "Test Data Specification" · decision sheet "Validation gate" · IMPLEMENTATION-PLAN S1.4.

## Steps

1. **`generate/validate.py`**, reading the fact table through `core.connect()` (read-only):
   ```python
   @dataclass
   class Check: name: str; target: str; realized: float; low: float; high: float; status: Literal["PASS","WARN","FAIL"]

   def run_validate(cfg: Config) -> list[Check]: ...
   ```

2. **Brief spec checks (always hard):**
   | Check | Rule |
   |---|---|
   | Rows | ≥ 500 |
   | Months | 3–4 distinct `auth_month` |
   | Countries / currencies | exactly MX, CO, AR, CL / MXN, COP, ARS, CLP |
   | PSPs | 3–5 |
   | Status mix | failed > 0 and pending > 0; settled is the majority |
   | Lag | median of settled lag in 1–7 days; lag outliers (> 7 d) > 0 |
   | Metadata | `customer_id`, `product_category`, `amount_tier`, `is_cross_border` not null |

3. **Bucket shares (always hard)**, on **both** denominators (settled rows, and all rows), with n-aware bounds `[brief_low − 3·SE, brief_high + 3·SE]`, `SE = sqrt(p(1−p)/n)`:
   | Brief tier | Categories | Brief range |
   |---|---|---|
   | Match exactly | `exact` + `rounding` | 60–70% |
   | Small 0.1–2% | `fx_tolerance` | 15–20% |
   | Meaningful > 2% | `meaningful` + `large` | 10–18% |
   | Large > 5% or > $20 | `large` | 3–5% |

4. **Pattern bands** (hard if `rows ≥ full_run_min_rows`, else WARN):
   | Pattern | Check | Band |
   |---|---|---|
   | P1 | flag rate PSP_B × AR − rate of other PSPs in AR | ≥ 2.5 pts |
   | P2 | median lag CO `is_over_300` − median lag other CO rows | ≥ 2 days |
   | P3 | weekend flag rate ÷ weekday flag rate | ≥ 1.2 |
   | P4 | share of PSP_D cross-border CLP/COP settled rows with `rounding_flag` | ≥ 90% |
   The validator may name PSPs (it checks the planted spec); the dbt cause rules may not.

5. **Output:**
   - Print one table: `check | target | realized | bounds | PASS/WARN/FAIL`.
   - Write the result under `"validate"` in `reports/run_manifest.json` (merge, do not overwrite the build part).
   - Any FAIL → raise `DataQualityError` → exit 5.

6. **Wire `recon validate`**. Mode is set by the row count of the fact table, not by a flag.

7. **`tests/test_validate.py`:** 500-row fixture → exit 0 with pattern WARNs allowed; a doctored fixture (e.g. set 30% of rows to `large`) → exit 5.

## Done when
| Command | Expected |
|---|---|
| `uv run recon generate --rows 500 && uv run recon build && uv run recon validate; echo $?` | table printed; bucket rows PASS; pattern rows PASS or WARN; `0` |
| `uv run recon generate && uv run recon build && uv run recon validate; echo $?` | every row PASS; `0` |
| `uv run pytest -q tests/test_validate.py` | passes (incl. the exit-5 case) |
| `uv run python -c "import json; print(json.load(open('reports/run_manifest.json'))['validate']['status'])"` | `PASS` |

## Serves
Test data 10 (distributions + deliberate anomalies proven) · Deliverable 2 · Tech 15 (data quality gate, exit 5).

## Pitfalls
- A 500-row run has ~465 settled rows: the brief ranges alone would fail by chance. Use the ±3 SE bounds.
- `large` must be in both "Meaningful > 2%" and "Large" tiers (the brief tiers overlap).
- P3 compares **flag rates**, not counts (weekends have fewer rows).
- P4 on COP: the step is 100,000 minor units (1,000 pesos). Use `rounding_flag` from the fact table; do not re-derive with `% 1000`.
- If the full run fails a band, tune `config/generator.yaml` weights, not the check.

## Hand-off
- File 09 puts `validate` between `build` and `analyze` in `recon all`.
- File 11 quotes the realized mix (from `run_manifest.json`) in README "Data".
