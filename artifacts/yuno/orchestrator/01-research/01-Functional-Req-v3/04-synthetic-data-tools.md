# 04 · Synthetic Settlement Data
**Purpose:** Choose how to make CasaMarket's seeded auth-vs-settlement dataset. It must meet the brief's Test Data Specification and ship as Deliverable 2 (dataset or script).
**Frame:** lean local build (one command) + AWS scale path, documented only. [scenario.md](../../../architect/00-scenario/scenario.md) is the source of truth; the [decision sheet](00-SUMMARY.md) overrides this file.

## Tool trade-offs

| # | Tool / approach | What it is | License / status | Pros | Cons | Pattern control | Simplicity | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Custom seeded generator + YAML spec | NumPy/pandas script | Own code; BSD libs | Exact bucket shares | We write it (~250 LOC) | High | High | 🥇 Best |
| 2 | DuckDB SQL generator | `setseed()` + `random()` in SQL | MIT; active | No new tool; same DB as the build | Same output only with `threads = 1` | Med | Med | 🥈 Runner-up |
| 3 | Polars version of #1 | Same script, other engine | MIT; active | Fast at 10M+ rows | No gain at 135k rows | High | Med | ❌ Not needed |
| 4 | Faker / Mimesis | Fake names and IDs | MIT; active | Seedable | No field needs it | Low | High | ❌ Random IDs are enough |
| 5 | SDV (+ SDMetrics) | Learned table synthesizer | BSL 1.1; SDMetrics MIT | Quality reports | Needs real data to learn from | Low | Low | ❌ No real data |
| 6 | MOSTLY AI SDK | Learned synthesis with privacy | Apache 2.0; vendor stopped Mar 2026 | Privacy-safe copies | Needs real data | Low | Low | ❌ No real data |
| 7 | NeMo Data Designer | Samplers + LLM columns | Apache 2.0; active | Good for free text | Needs an LLM; not repeatable | Med | Low | ❌ No text fields |
| 8 | Mockaroo | Web GUI mock data | Free: 1,000 rows/file; paid for more | Has formula fields | Logic lives in a web UI, not the repo | Low | Med | ❌ Not in the repo |
| 9 | PaySim / AMLSim | Fraud and AML simulators | GPL-3.0 / Apache 2.0 | Real payment flows | No auth-vs-settle; Java | Low | Low | ❌ Wrong problem |
| 10 | LLM-written CSV | Ask a model for rows | n/a | No code | Not seeded; wrong FX math | Low | High (fake) | ❌ LLM writes the code instead |

## Top 2 choices
**🥇 Custom seeded generator + YAML spec**
- `recon generate` writes the FX table and the transactions to `data/raw`, and truth labels to `data/truth`.
- One YAML file holds the seed, the shares and the pattern settings.
- Same seed → same output, byte for byte.
- `recon validate` checks shares and patterns (see Validation).

**🥈 DuckDB SQL generator**
- Same rules, written as SQL on the DuckDB we already use.
- It needs `SET threads = 1` to repeat exactly.
- Branching rules (bucket → cause → size) get long in SQL, so Python is easier to read.

**AWS path:** at scale, real PSP settlement files replace this generator; it stays a test fixture.

## Dataset shape

| Item | Value |
|---|---|
| Window | 3 full calendar months |
| Rows | 135k by default (45k per month) |
| Smoke run | `recon generate --rows 500` |
| Countries (weight) | MX 40% · CO 25% · AR 20% · CL 15% |
| Currencies | MXN, COP, ARS (2 decimals) · CLP (0 decimals) |
| Money type | Integer minor units, in local currency |
| PSPs (weight) | PSP_A 30% · PSP_B 25% · PSP_C 20% · PSP_D 15% · PSP_E 10% |
| Status mix | approved + settled 93% · failed 4% · pending 3% |
| Pending rows | Mostly in the last 7 days of data |
| Settle lag | 1–7 days, mode 2 days |
| Lag outliers | About 2% at 8–15 days |
| Cross-border share | About 20% of rows |
| Cross-border meaning | `payer_currency = USD`; the PSP converts to local |
| Amount tiers (USD) | $10–50: 45% · $50–200: 40% · $200+: 15% |
| Orders > $300 | About 6% (so P2 has rows) |
| FX table | `fx_rates_daily(date, currency, local_per_usd)` |
| FX moves | Capped so auth → settle stays < 2% |

**Columns**
- `transaction_id`, `customer_id`, `product_category`
- `country`, `currency`, `payer_currency`, `is_cross_border`
- `psp`, `status`, `auth_ts`, `settle_ts`
- `authorized_amount`, `settled_amount` (minor units)
- `item_count` (for partial capture), `risk_score` (for fraud hold)
- The amount tier is computed in the build, not stored.

## Buckets

**Denominator:** approved + settled rows. Failed + pending stay ≤ 7%, so every brief range also holds over all rows.

| Category | Rule | Brief tier | Target share | Share of all rows |
|---|---|---|---|---|
| `exact` | Δ = 0 | match 60–70% | 67% | 62.3% (with rounding: 63.2%) |
| `rounding` | \|Δ\| ≤ 1 minor unit | match | 1% | 0.9% |
| `fx_tolerance` | residual ≤ 2% and < $20 | small: 15–20% | 18% | 16.7% |
| `meaningful` | residual 2–5% and < $20 | > 2%: 10–18% (with large) | 10% | 9.3% |
| `large` | residual > 5% or ≥ $20 | 3–5% | 4% | 3.7% |

**Bucket rules**
- Δ = `settled − authorized` (raw). It is used for `exact` and `rounding`.
- `expected` = auth for domestic rows.
- `expected` = auth × FX(settle day) / FX(auth day) for cross-border rows.
- `residual` = `settled − expected`. It is used for the other three buckets.
- All cut-offs use absolute values (`|residual_pct|`, `|residual_usd|`).
- Check the rules in table order; the first match wins.
- Flag: `is_meaningful` = `meaningful` or `large` (about 14%).

**CFO's 18%:** the README says our data follows the brief's spec ranges. The flagged share is about 14%, and the non-exact share is about 33%.

## Planted patterns

| # | Pattern | Injection rule | Expected finding |
|---|---|---|---|
| P1 | PSP_B in Argentina | Higher weight for the `meaningful` bucket (X6 rows) | Meaningful rate about +3.5 pts vs other PSPs in AR |
| P2 | Colombia orders > $300 | Lag +2–4 days; more lag outliers | Median lag higher by ≥ 2 days |
| P3 | Weekend authorizations | Weight 1.3× for the `meaningful` bucket | Rate ratio about 1.3 vs weekday |
| P4 | PSP_D rounding | Cross-border CLP and COP: settle rounded **down** to a multiple of 1,000 units | Settled ends in 000; always ≤ expected |
| X1 | FX timing | Cross-border only; move < 2% | Raw Δ ≠ 0 but residual ≈ 0; not flagged |
| X2 | Partial capture | Settle = (n−1)/n of auth; needs `item_count` ≥ 2 | Mostly `large`; clean fractions |
| X3 | PSP fee | PSP_C deducts a fixed fee ≥ $1 | Tight cluster at the fee amount |
| X4 | Tax recalculation | MX/CO only; tax on part of the order: ±0.2–1.9% | `fx_tolerance` bucket; both signs |
| X5 | Fraud hold | High `risk_score` rows: 10–20% withheld | `large` bucket |
| X6 | PSP adjustment | −2% to −5% | Fills `meaningful` |
| Drift | PSP_C fee starts in month 3 | X3 rows only in month 3 | Change alert fires in the demo |
| — | Tips | None planted (home goods) | Report says "ruled out" |

**Weekend note:** the README tells the real-world story (weekend auths use Friday's FX rate). In our data, only the 1.3× weight plants P3, because the pipeline's FX step removes the Friday-rate effect.

## Generation order
1. Build the daily FX table (capped moves).
2. Draw base rows: date, country, PSP, currency, cross-border, customer, category, `item_count`, `risk_score`, amount, status, lag.
3. Apply P2 lag and put pending rows mostly in the last 7 days.
4. **Fix P4 rows first.** Round PSP_D cross-border CLP/COP settles down to 1,000 units. Each row counts in whatever bucket its diff lands in.
5. **Bucket:** give each other settled row a bucket, so totals hit the target shares. P1 and P3 raise the `meaningful` weight.
6. **Cause:** pick a cause that fits the bucket and the row.
   - `fx_tolerance`: X1 (cross-border), X4 (MX/CO), X3 (PSP_C, month 3, large order).
   - `meaningful`: X6, or X3 on small orders.
   - `large`: X2 (multi-item), X5 (high risk), or X6 on big orders.
   - `rounding`: ±1 minor unit.
7. **Size:** draw the diff inside the bucket limits (for example, X6 in `meaningful` must stay < $20).
8. Write CSVs to `data/raw` and truth labels to `data/truth`.

## Validation (`recon validate`)
- **Bucket shares:** always checked, on both denominators.
- **Pattern bands:**
  - P1: gap ≥ 2.5 pts vs other PSPs in AR;
  - P2: median lag + ≥ 2 days;
  - P3: weekend / weekday ratio ≥ 1.2;
  - P4: ≥ 90% of rows have the round-down signature.
- **Full run:** a missed band is a hard fail (exit code 5).
- **`--rows 500` smoke run:** pattern bands only warn (too few rows).

## What we commit
- The generator script and the YAML spec (with the seed).
- A 500-row sample CSV.
- Not the 135k CSV (about 20 MB); `recon generate` rebuilds it in seconds.

## Commands
- `recon generate` (add `--rows 500` for a smoke run)
- `recon validate`
- Both run inside `make all` / `recon all`.

Key sources: [SDV BSL license](https://datacebo.com/blog/sdv-bsl-license/) · [Syntho acquires MOSTLY AI brand](https://www.syntho.ai/syntho-acquires-mostly-ai-trademark-and-related-assets/) · [Mockaroo pricing](https://www.mockaroo.com/pricing) · [DuckDB random functions (`setseed`)](https://duckdb.org/docs/stable/sql/functions/numeric) · [PaySim](https://github.com/EdgarLopezPhD/PaySim) · [AMLSim](https://github.com/IBM/AMLSim) · [LLM tabular generation limits](https://arxiv.org/abs/2505.02659) · [Currency minor units](https://docs.adyen.com/development-resources/currency-codes)
