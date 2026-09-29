# Synthetic Settlement Data: Decision Brief (v1)

## Question
Which tool and approach should generate CasaMarket's auth-vs-settlement dataset? It must follow the brief's "Test Data Specification" exactly: ≥500 transactions over 3–4 months, MX/CO/AR/CL, 3–5 PSPs, the four discrepancy buckets and the four planted patterns. It must be seeded, runnable with one command, checked against a ground truth, and safe for PCI. Frame: a lean local build (uv + DuckDB + dbt), plus a documented scale path on AWS that we do not build.

## Debate (🏛️ Jamshid vs ⚡ Kaveh)
1. 🏛️ **Jamshid:** We have no real data, so learned generators (SDV, MOSTLY AI) have nothing to learn from. I propose a seeded NumPy/pandas generator driven by one YAML spec. It writes a daily FX table, the transactions, and a separate ground-truth label file. dbt seeds hold the static reference data.
2. ⚡ **Kaveh:** Agreed on the direction. Four objections. (1) The buckets overlap: a 1.5% diff on a $2,000 order is "small" by percent but "large" by the >$20 rule. Random draws will not hit the shares. (2) At 500 rows, PSP_B in Argentina is about 35 rows. A +3.5 pp lift on 35 rows is noise, so the "statistical evidence" (25 pts) would be fake. (3) Floats for money are wrong, and CLP has 0 decimals. (4) The FX series is generated data. It is not reference data, so it should not be a dbt seed.
3. 🏛️ **Jamshid:** (1) Accepted. We use mutually exclusive generation buckets, allocate them with exact quotas (largest-remainder rounding), and validate the brief's overlapping views after generation (see Dataset design). (2) Accepted, and I have the numbers. A two-proportion test (α=0.05, power 0.8) of 17% vs 20.5% needs about 1,950 rows per group. The default run is therefore **realistic scale: 45k/month × 3 = 135k rows**, which takes seconds in NumPy and DuckDB. `--rows 500` stays as a smoke mode, and the report shows CIs so small-n results are honestly labelled "not significant". (3) Accepted. Amounts are integer minor units plus an ISO 4217 exponent (CLP 0; MXN/COP/ARS 2), and dbt uses DECIMAL. (4) Accepted. `fx_rates_daily.csv` goes to `data/raw/` as a source. Seeds hold only hand-kept tables: currencies, PSP fee schedule, country/timezone.
4. ⚡ **Kaveh:** Do we need Faker or Mimesis? The metadata is customer ID, category, tier and a cross-border flag. There are no names or addresses.
5. 🏛️ **Jamshid:** No. The RNG gives opaque IDs (`cus_` + hex). Faker would add a second seed stream and a dependency, and could invite PII. Categories are a fixed list in the YAML. Could an LLM write the CSV directly, since the brief says "AI-first"?
6. ⚡ **Kaveh:** No. It is not seeded, the counts drift, and the arithmetic (auth × FX → settle) goes wrong. Research on LLM tabular synthesis still flags weak constraint and arithmetic fidelity. The AI-first move is to have the AI write the generator and the validator, and then the validator proves it. Mockaroo caps free use at 1,000 rows/file and has no conditional logic. NeMo Data Designer needs an LLM endpoint. SDV is BSL and needs real seed data.
7. 🏛️ **Jamshid:** Agreed. One realism point: FX timing must come from the rate table, not a random noise term. ARS crawls (BCRA band indexed to inflation) and gets one step shock. Weekend auths use Friday's stale rate. These are the real mechanisms behind P3 and the cross-border finding.
8. ⚡ **Kaveh:** Then those rows have *computed* diffs (FX drift, PSP_D rounding), so they cannot be forced into a bucket. How do the quotas stay exact?
9. 🏛️ **Jamshid:** Two phases. Phase 1 "pins" the mechanism rows: compute their diff, classify it, and subtract from the quotas. Phase 2 fills the remaining quotas by weighted sampling without replacement. The weights encode P1–P3, and magnitudes are drawn inside each bucket's bounds. The validator fails the run if any quota goes negative or any lift misses its band.
10. ⚡ **Kaveh:** **Explicit agreement:** a custom seeded generator from a YAML spec; two-phase exact quotas; 135k rows by default and 500 as smoke; minor-unit money; FX in raw and static references as dbt seeds; truth labels kept out of dbt; a validation report that gates the run.

## Trade-off table
| Tool | License/status (Sep 2026) | Pros | Cons | Pattern control | Simplicity | Verdict |
|---|---|---|---|---|---|---|
| Custom NumPy/pandas + YAML spec | BSD; active | Exact quotas; FX-driven mechanisms; seeded; about 250 LOC | We write it; realism depends on our priors | Full | High | **Use** |
| Polars instead of pandas | MIT; active | Faster at 10M+ rows | No gain at 135k; less familiar to reviewers | Full | Med | Scale path only |
| Faker | MIT; active (release Sep 2026) | Locales es_MX/es_CO/es_AR/es_CL | Separate seed stream; invites PII; not needed | None | High | Skip |
| Mimesis | MIT; active (per earlier check) | Fast, schema API | Same as Faker | None | High | Skip |
| SDV (+SDMetrics) | SDV BSL 1.1 (non-prod OK), 1.38.x; SDMetrics MIT | Constraints, quality reports | Needs real seed; fitting it on our own output is circular | Weak | Low | Skip |
| MOSTLY AI SDK | Apache 2.0; vendor stopped operating Mar 2026, Syntho bought the brand Jun 2026 | TabularARGN, differential privacy | Needs real data; stewardship risk | Weak | Low | Skip (see open disagreement) |
| NeMo Data Designer | Apache 2.0; active 2026 | Sampler + LLM columns | Needs an LLM endpoint; not bit-reproducible | Medium | Low | Skip (text fields only, later) |
| Mockaroo | Freemium: 1,000 rows/file, 200 API calls/day | Fast GUI | Cannot make 135k rows; logic not in the repo | Low | Med | Skip |
| LLM-written CSV | n/a | No code | Not seeded; wrong counts and FX arithmetic; cannot be audited | Low | High (fake) | Skip: let the LLM write the *code* |
| dbt seeds (reference) | Part of dbt; dbt-duckdb 1.x; dbt v2 ships DuckDB built in (Sep 2026) | Versioned, tested, visible in lineage | Wrong fit for large or generated data | n/a | High | **Use** for currencies, PSP fees, countries |

## Dataset design
**Files.** `data/raw/transactions.csv`, `data/raw/fx_rates_daily.csv` (generated), `data/truth/labels.csv` (never a dbt source; a CI grep checks this). Seeds: `currencies.csv` (code, minor_unit), `psp_fees.csv`, `countries.csv` (IANA timezone).

| Table | Columns |
|---|---|
| transactions | transaction_id, merchant_id, customer_id (opaque), country, psp, product_category, is_cross_border, auth_ts_utc, auth_status (approved/declined), auth_currency, auth_amount_minor, settlement_status (settled/pending/null), settle_ts_utc, settle_currency (local or USD), settle_amount_minor, psp_reference |
| fx_rates_daily | rate_date, currency, usd_per_unit. Random walk: MXN/COP/CLP σ≈0.5%/day; ARS crawl ≈2%/month + σ≈0.8% + one 4–6% step; weekends carry Friday's rate |
| labels (truth) | transaction_id, target_bucket, injected_cause (none/fx_timing/rounding/psp_fee/tax_adj/partial_capture/fraud_hold/processing_error), pattern_ids |

The window is **2026-04-01 → 2026-06-30** (the "last quarter"), with an export cutoff of 2026-07-02. Status mix: declined 6%, pending 4% (the cutoff creates some; "stuck" rows add the rest), settled 90%. Order value is lognormal in USD: $10–50 45%, $50–200 40%, $200+ 15% (about 7% over $300). Countries: MX 35 / CO 25 / AR 25 / CL 15. PSPs: PSP_A–PSP_D. Cross-border ≈20%. Settlement lag: 1–7 days (mode 2), with 2% outliers at 8–15 days. The pipeline derives the amount tier, day of week (local time zone) and lag. The generator does not write them.

**Bucket allocation** uses exclusive generation buckets over *settled* rows, rounded by largest remainder.
| Gen bucket | Rule | Share | n @135k (121,500 settled) | n @500 (450) |
|---|---|---|---|---|
| exact | diff = 0 | 65% | 78,975 | 293 |
| small | 0.1–2% and ≤ $20 | 18% | 21,870 | 81 |
| meaningful | 2–5% and ≤ $20 | 13% | 15,795 | 58 |
| large | > 5%, or 2–5% and > $20 | 4% | 4,860 | 18 |

Brief views, checked after generation: exact 65% (60–70 ✓), small 18% (15–20 ✓), **>2% = 13 + 4 = 17%** (10–18 ✓, and close to the CFO's "18%"), large 4% (3–5 ✓). No row falls in 0–0.1%. At 135k, net leakage is tuned to about $127k/quarter, as in the story. Sign: about 85% negative (merchant loses).

| Pattern | Injection rule | Expected finding (test) |
|---|---|---|
| P1 PSP_B × AR | Phase-2 weight so the >2% rate is base + 3.5 pp | 20.5% vs 17% (two-proportion z / χ², 95% CI) |
| P2 CO × >$300 | Lag + U(3,5) days, 20% over 7 days; fraud_hold weight in large | Median lag ≈6 d vs 2 d (Mann-Whitney); higher large share |
| P3 Weekend auth (local tz) | Friday-rate staleness on cross-border + weight 1.3× | Rate ratio ≈1.3 (χ², CI) |
| P4 PSP_D rounding | ARS→USD and CLP→USD settlements floored to whole USD (pinned) | 100% end in .00, always negative, mean −$0.50 |
| X1 FX timing (cross-border) | settle = auth × FX(settle_date)/FX(auth_date) (pinned) | Cross-border ≈3× domestic rate; ARS worst; correlates with lag |
| X2 Partial capture | −10% to −40%, furniture/appliances | Large bucket, round fractions |
| X3 PSP fee | PSP_C withholds 0.8% per `psp_fees` seed | Diff/auth ≈ fee rate, tight cluster |
| X4 Tax adjustment | ± IVA delta (MX 16%, CO 19%) on a category subset | Small bucket, both signs |
| X5 Fraud hold | 10–30% withheld on high-value rows | Large bucket, CO > $300 |

## Recommendation
**(A) Lean build.** `src/gen/generate.py` plus `spec.yaml` (pydantic-validated), run by `make data`:
1. `rng = np.random.default_rng(spec.seed)`. Build the FX table, then the base rows (country, PSP, category, USD value → local minor units at the auth-date rate, timestamps, status).
2. Phase 1 (pin): compute FX-timing and PSP_D rounding diffs, classify them, and subtract from the quotas.
3. Phase 2 (fill): for large → meaningful → small, run `rng.choice(idx, k, replace=False, p=w/w.sum())` with pattern weights. Pick a cause valid for each bucket, and draw the magnitude inside the bucket bounds.
4. Round to minor units (CLP 0 dp) with `Decimal`/integers. Write the raw data and the truth separately.
5. `make validate` writes `reports/data_validation.md`: bucket shares vs targets, each pattern's lift with CI and p-value, and a determinism hash from two runs. A miss exits non-zero. `make all` = data → dbt build → validate → report.

**(B) Scale path (not built).** Package the generator (versioned; specs in Git) and run it as an ECS/Batch task from MWAA. It writes Parquet/Iceberg to non-prod S3, which loads into StarRocks via dbt. It also replays auth and settle events into MSK/Flink to test late-arriving settlements with event-time watermarks. Partition with `SeedSequence.spawn()`, and use Polars above about 10M rows. Calibrate priors from *aggregate* StarRocks stats (rates by PSP × country), never row copies.

## Key practices
- One YAML spec drives the generator, the quotas, the validator and the README numbers.
- Exact quotas plus weighted sampling without replacement; never tune intercepts toward a target.
- Money as integer minor units + ISO 4217 exponent; FX applied from the table; no floats in raw.
- The weekend is computed in local time (IANA timezone per country); store UTC.
- Truth labels live outside dbt; they are used only for validation and recall checks.
- Default to realistic volume for statistical power; report CIs, and label anything at n=500 honestly.
- No PAN, BIN, names or emails; IDs are opaque RNG tokens (PCI-DSS data minimization).
- The README states: "synthetic, patterns planted"; seed, spec version, and known limits.

## Open disagreements
- **FX series source.** 🏛️ Jamshid: commit real published daily rates for Q2 2026 (BCRA, Banxico) as a seed, so ARS drift is real. ⚡ Kaveh: licensing and fetch work add risk for no scoring gain; a random walk calibrated to real drift is enough. *Options:* (1) synthetic walk (default); (2) a real-rate CSV behind `--fx real`.
- **Learned synthesis in production.** Jamshid: DP-trained copies of tokenized data inside the PCI zone help analysts. Kaveh: memorization risk, and the MOSTLY AI vendor situation changed in 2026. Use the simulator plus aggregate calibration. Still open from the earlier brief.

## Sources
1. SDV on PyPI (1.38.x, BUSL-1.1): https://pypi.org/project/sdv/ ; license post: https://datacebo.com/blog/sdv-bsl-license/
2. MOSTLY AI SDK (Apache 2.0) and the 2026 vendor status: https://github.com/mostly-ai/mostlyai ; https://www.beri.net/article/best-synthetic-data-platforms-real-data-cannot-leave-2026
3. NVIDIA NeMo Data Designer (Apache 2.0): https://github.com/NVIDIA-NeMo/DataDesigner
4. Mockaroo pricing (1,000 rows/file free): https://www.mockaroo.com/pricing
5. Faker on PyPI (MIT, Sep 2026): https://pypi.org/project/Faker/
6. DuckDB ships inside dbt v2 (Sep 2026): https://duckdb.org/2026/09/22/dbt-fusion ; dbt-duckdb: https://pypi.org/project/dbt-duckdb/
7. BCRA exchange-rate band regime (ARS crawl): https://www.bcra.gob.ar/en/exchange-rate-band-regime/
8. Currency minor units (CLP 0, COP 2): https://docs.adyen.com/development-resources/currency-codes
9. Statistically accurate tabular generation with LLMs (limits): https://arxiv.org/abs/2505.02659
10. Synthetic generators lose behavioral fraud patterns (2026): https://arxiv.org/abs/2604.13125
