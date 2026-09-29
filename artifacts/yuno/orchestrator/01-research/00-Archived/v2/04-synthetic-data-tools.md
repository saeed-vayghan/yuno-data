# 04 · Synthetic Settlement Data
**Purpose:** Choose how to generate CasaMarket's seeded auth-vs-settlement dataset that meets the Test Data Specification and ships as Deliverable 2 (dataset + script).
**Frame:** lean local build (one command) + documented AWS scale path; scenario.md is the source of truth.

| # | Tool / approach | What it is | License / status | Pros | Cons | Pattern control | Simplicity | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Custom seeded generator + YAML spec | NumPy/pandas script; one YAML sets shares, patterns, seed | Own code on BSD libs | Exact bucket quotas; FX-driven causes; same output every run; ~250 LOC | We write it; realism depends on our priors | High | High | 🥇 Best: full control, one command |
| 2 | Same generator on Polars | Swap pandas for Polars | MIT; active | Faster at 10M+ rows | No gain at 135k; less familiar to reviewers | High | Med | 🥈 Runner-up: scale path only |
| 3 | Faker / Mimesis | Fake field values (names, IDs) | MIT; active | Seedable; LatAm locales | No joint logic; extra seed stream; invites PII; no field needs it | Low | High | ❌ Reject: RNG IDs are enough |
| 4 | SDV (+SDMetrics) | Learned tabular synthesizers | BSL 1.1 (non-prod OK); SDMetrics MIT | Constraints, quality reports | Needs real seed data; fitting on our own output is circular | Low | Low | ❌ Reject: no real data |
| 5 | MOSTLY AI SDK | Learned synthesis with privacy | Apache 2.0; vendor stopped Mar 2026, brand sold Jun 2026 | Privacy-safe copies of real data | Needs real data; stewardship risk | Low | Low | ❌ Reject: no real data |
| 6 | NeMo Data Designer | Samplers + LLM columns | Apache 2.0; active | Good for free text | Needs LLM endpoint; not bit-reproducible | Med | Low | ❌ Reject: no text fields |
| 7 | Mockaroo | Web GUI mock data | Freemium: 1,000 rows/file free | Fast to click | Can't make 135k rows; no conditional logic; logic not in repo | Low | Med | ❌ Reject: too small |
| 8 | LLM-written CSV | Ask a model for rows | n/a | No code | Not seeded; wrong counts and FX math; can't audit | Low | High (fake) | ❌ Reject: LLM writes the code instead |

## Top 2 choices
**🥇 Custom seeded generator + YAML spec:** `make data` builds a daily FX table into `data/raw`, then 135k rows (45k × 3 months; `--rows 500` is a smoke run), with money in integer minor units (CLP 0 dp). Exclusive buckets over settled rows hit exact quotas (exact 65%, small 18%, meaningful 13%, large 4%): FX-timing and rounding rows are pinned first, then weighted sampling fills the rest. Truth labels go to `data/truth` (never a dbt source), and `make validate` fails the run if a bucket share or pattern lift misses its band.
**🥈 Polars variant:** Same spec and logic, only a faster engine. Use it on the AWS path (ECS/Batch task from MWAA, `SeedSequence.spawn()` per partition, Parquet/Iceberg to S3, then StarRocks) once volume passes ~10M rows.

## Planted patterns
| # | Pattern (brief) | Injection rule | Expected finding |
|---|---|---|---|
| P1 | PSP_B has higher discrepancy rate in Argentina | Sampling weight: PSP_B × AR >2% rate = base + 3.5 pp | ~20.5% vs 17%, significant (χ², 95% CI) |
| P2 | Large (>$300) Colombia txns have timing issues | Lag + 3–5 days, 20% over 7 days; more fraud holds | Median lag ~6 d vs 2 d (Mann-Whitney) |
| P3 | Weekend auths have higher discrepancy rate | Weekend (local tz) uses Friday's FX rate + 1.3× weight | Rate ratio ~1.3 (χ², CI) |
| P4 | One PSP rounds certain currency pairs | PSP_D floors ARS→USD and CLP→USD settles to whole USD | All end in .00, always negative, mean −$0.50 |
| X1 | FX timing (cross-border) | settle = auth × FX(settle day) / FX(auth day) | Cross-border ~3× domestic rate; ARS worst |
| X2 | Partial capture | −10% to −40% on furniture/appliances | Large bucket; clean fractions |
| X3 | PSP fee | PSP_C withholds 0.8% (fee seed) | Diff ≈ fee rate; tight cluster |
| X4 | Tax recalculation | ± VAT delta (MX 16%, CO 19%) on some categories | Small bucket; both signs |
| X5 | Fraud hold | 10–30% withheld on high-value rows | Large bucket; CO >$300 |

Key sources: [SDV BSL license](https://datacebo.com/blog/sdv-bsl-license/) · [Mockaroo pricing](https://www.mockaroo.com/pricing) · [LLM tabular generation limits](https://arxiv.org/abs/2505.02659) · [Currency minor units](https://docs.adyen.com/development-resources/currency-codes) · [BCRA ARS band regime](https://www.bcra.gob.ar/en/exchange-rate-band-regime/)
