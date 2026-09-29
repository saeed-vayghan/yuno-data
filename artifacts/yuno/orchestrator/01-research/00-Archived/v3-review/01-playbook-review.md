# Review · PLAYBOOK.md
**Verdict:** ⚠️ Pass with fixes — **Score:** 7/10 (covers every brief item with correct quotes, but three rules are wrong and would break the build, some parts are over-built, and some text is hard to read)

## Coverage vs brief
| Brief item | Covered? (✅/⚠️/❌) | Where | Note |
|---|---|---|---|
| FR1 ingest auth + settlement records | ✅ | §5, §10 dbt models | Raw → staging → int → fct |
| FR1 calculate discrepancies | ⚠️ | §5 "Discrepancy", §6 | Cross-border currency model unclear; FX formula direction wrong (F1) |
| FR1 flag "meaningful" (2 cents / $20 hint) | ⚠️ | §4 buckets, §5 | $0.50 rounding floor hides brief-meaningful rows (F2); "$20" boundary uses `> $20` (F7) |
| FR1 enrich (%, amount, auth→settle time) | ⚠️ | §6 | No `expected_settled` / `residual_pct` field, even though the category depends on them (F1) |
| FR1 acceptance criterion | ✅ | §2 row 1, §10 `make all` | Quoted verbatim |
| FR2 countries/currencies rates | ✅ | §7 row 1 | Wilson CI + chi-square |
| FR2 most problematic PSPs | ✅ | §7 row 2 | PSP×country heatmap |
| FR2 transaction size vs likelihood/magnitude | ✅ | §7 row 3 | |
| FR2 time patterns (weekday, settle delay) | ✅ | §7 row 4 | |
| FR2 clusters: systematic vs random | ✅ | §7 row 5 | Rule signatures + HDBSCAN cross-check |
| FR2 acceptance criterion | ✅ | §2 row 2, §7 findings format | Verbatim |
| FR3 trends over time | ✅ | §9 | |
| FR3 drill-down by segment | ✅ | §9 | |
| FR3 outlier transactions | ✅ | §9 | |
| FR3 week-over-week | ⚠️ | §9 | "↑ > X pts" left as placeholder; n ≥ 30 vs v2 min sample 50 (F9) |
| FR3 AC "worst week last month" | ⚠️ | §9 | Weeks that cross a month edge not defined; net vs gross loss mixed (F10) |
| FR3 AC "transactions over $50" | ✅ | §9 | Dashboard + `recon query --min-usd 50` |
| FR4 3–5 prioritized actions | ✅ | §8 | |
| FR4 reference findings / $ impact / implementation | ✅ | §8 | Owner column is a nice extra |
| FR4 acceptance criterion | ✅ | §2 row 4 | Verbatim |
| Data ≥ 500 transactions | ✅ | §4 Shape | Default 135k, `--rows 500` smoke |
| Data 3–4 months | ✅ | §4 | 4 full months |
| Data 4 countries + ISO codes | ✅ | §4 | |
| Data 3–5 PSPs | ✅ | §4 | PSP_A–D |
| Data status mix (failed auths, pending) | ✅ | §4, §5 | |
| Data exact 60–70% | ✅ | §4 buckets | 65% |
| Data small 0.1–2% for 15–20% | ⚠️ | §4 buckets | 18% target, but `rounding` rows (P4, fee) have 0% budget, so the realized mix drifts (F2) |
| Data meaningful > 2% for 10–18% | ⚠️ | §4 buckets | 17% target sits 1 pt under the ceiling; flaky at small n (F4) |
| Data large > 5% or > $20 for 3–5% | ⚠️ | §4 buckets | 4% target; ±0.9 pt SE at 500 rows (F4) |
| Data timestamps, lag 1–7 days + outliers | ✅ | §4 | |
| Data metadata (customer ID, category, tiers, cross-border) | ⚠️ | §4 | Cause rules need `item_count` and `risk_score`; not in the contract list (F5) |
| Data amount tiers $10–50 / 50–200 / 200+ | ✅ | §4, §6 | Plus > $300 flag for P2 |
| Pattern: PSP +3–4% in Argentina | ⚠️ | §4 P1 | Embedded right; verification gate would fail it (F3) |
| Pattern: > $300 Colombia settle timing | ✅ | §4 P2 | |
| Pattern: weekend auths higher rate | ⚠️ | §4 P3 | ~1.5× target equals the 1.5× gate, fails about half the time (F3) |
| Pattern: PSP rounding for currency pairs | ✅ | §4 P4 | `rounding_flag` definition vague (F13) |
| Deliverable: code + README + run steps | ⚠️ | §10, §12 | Needs `make` + `uv`; brief only promises Python/Node/Docker (F8) |
| Deliverable: dataset or script | ✅ | §4, §10 | |
| Deliverable: analysis outputs | ✅ | §7, `reports/` | |
| Deliverable: docs (approach, findings, assumptions, how to interpret) | ⚠️ | §12 README template | No "how to read the outputs" section (F16) |
| Deliverable: (stretch) dashboard OR recommendations | ✅ | §8, §9 | Both built |
| Done: accurate discrepancies | ⚠️ | §5 | Depends on F1 fix |
| Done: ≥ 3–4 patterns with data | ✅ | §7, checklist | |
| Done: well-documented | ✅ | §12 | |
| Done: good DE practice | ✅ | §10 standards | |
| Done: (stretch) explore / next steps | ✅ | §8, §9 | |
| Constraint: runnable locally | ⚠️ | §10 | Same as F8 |
| Constraint: README setup/run | ✅ | §12 | |
| Constraint: dashboard on localhost | ✅ | §9 | |
| Scope: 2 h, prototype, keep it simple | ⚠️ | header, §9, §10 | Some extras (Slack webhook, alert state machine, YAML-generated dbt tests) (F12) |
| Time budget | ✅ | §2 | Numbers exact |
| Rubric: Pipeline 20 | ✅ | §3 | |
| Rubric: Test data realism 10 | ⚠️ | §3, §4 | Gate + bucket issues (F2–F4) |
| Rubric: RCA depth 25 | ⚠️ | §3, §7 | No multiple-testing correction; no scoring vs planted truth (F6) |
| Rubric: Insight quality 20 | ✅ | §3, §7 | Fixed findings format, $ reconciles |
| Rubric: Technical execution 15 | ⚠️ | §3, §10 | F8 |
| Rubric: Stretch & polish 10 | ✅ | §3 | Points match the brief |

Faithfulness check: all story numbers (45k/month, 18%, $127k, 1–5 days, < 2%), the four acceptance quotes, the "keep your architecture simple" quote, the "2 cents" hint, the bucket ranges, rubric points and time budget match the brief word for word. VAT rates (MX 16, CO 19, AR 21, CL 19) are right. No invented requirement.

## Findings
| # | Severity (High/Med/Low) | Location (quote) | Problem | Proposed fix | Jamshid | Status |
|---|---|---|---|---|---|---|
| 1 | High | §5 "expected settle = auth × fx(settle day) / fx(auth day)" + "Synthetic daily rates per currency→USD" + §5 "same currency" | Formula is inverted. If `fx` is currency→USD (USD per CLP), the ratio moves the wrong way and every cross-border residual gets the wrong sign. Also, which currency are auth and settle amounts in? No `auth_currency` / `settle_currency` / `payer_currency` columns, and no `expected_settled` / `residual_pct` in §6 even though the category uses them. | State the model: payer pays in `payer_currency`; both `authorized_amount_minor` and `settled_amount_minor` are in the merchant `settle_currency`. `expected_settled = authorized × rate(payer→settle, settle day) / rate(payer→settle, auth day)`. Add `expected_settled_minor`, `fx_residual_minor`, `fx_residual_pct` to §6. Unit test with one hand-worked row. | Accepts. The intent was right; the rate direction was not written down. | Agreed |
| 2 | High | §4 "`rounding` \| \|Δ\| ≤ 1 minor unit or \|Δ USD\| < $0.50 \| not in brief \| label only" and §4 "PSP_C deducts a fixed fee (e.g. ~$0.35)" | The $0.50 floor swallows the PSP_C fee pattern (all fee rows become `rounding`) and brief-meaningful rows on small orders ($0.45 on $10 = 4.5%). Generator targets sum to 100% (65/18/13/4) with 0% for `rounding`, but P4 and the fee create rounding rows, so the realized mix drifts. | `rounding` = \|Δ\| ≤ 1 minor unit **or** Δ is below one PSP rounding step (P4 residue). Drop the $0.50 floor (or use `abs_pct < 0.1%`, which matches the brief's 0.1% lower edge). Budget rounding explicitly (e.g. exact 63%, rounding 2%). Make the PSP_C fee ≥ $1 so it shows up as a pattern. | Accepts the floor change. Keeps a small rounding budget taken from `exact`. | Agreed |
| 3 | High | §4 "verification step fails if a pattern's lift is < 1.5× or p ≥ 0.01" | P1 is +3.5 pts on a ~17% base, a lift of about 1.2×, so the gate fails P1 by design. P3 targets "~1.5×" and fails about half the runs. At `--rows 500` the PSP_B×AR cell has ~17 rows, so p < 0.01 is impossible and the smoke run always fails. P2 is a lag effect, not a lift. | Per-pattern checks in `generator.yaml`: P1 = rate difference 3–4 pts ± 1, CI excludes 0; P2 = median lag shift ≥ 2 days, Mann-Whitney p < 0.01; P3 = lift ≥ 1.3×; P4 = residue share in PSP_D pairs vs others. Hard-fail only at the default size; at `--rows < 10k` print a warning. | Accepts. Adds a `strict` flag tied to row count. | Agreed |
| 4 | Med | §4 "A test asserts each realized share is inside the brief range" + targets 17% / 4% | Meaningful + large = 17% vs an 18% ceiling; large 4% in a 3–5% band. At 500 rows the SE is ~1.7 pts and ~0.9 pts, so the test fails about 1 in 4 smoke runs. Denominator is also not stated (all rows vs approved+settled). | Aim for the middle: meaningful+large ≈ 14%. Use n-aware bounds (range ± 3 SE). State that shares are over approved+settled rows, the same denominator as §5. | Accepts mid-range targets. Rebuts moving off the CFO 18% story. Compromise: document that the brief's 60–70% exact already implies 30–40% differ, so the 18% maps loosely. | Agreed |
| 5 | Med | §4 "Metadata \| Plus: PSP, payer currency, card BIN country (no PAN), risk score (suggestion)" | The cause rules in §7 need `item_count` ((n−1)/n partial capture) and `risk_score` (fraud hold), but one is missing and the other is only a "suggestion". Without them `likely_cause` cannot be computed. | Make `item_count`, `risk_score` and `payer_currency` required fields in `contracts/transactions.yaml`. | Accepts. | Agreed |
| 6 | Med | §7 "Rate per country with Wilson 95% CI; chi-square" and §4 "How the analysis should find it" | The v2 picks include Fisher for small cells, BH-FDR across many segment tests, truth labels kept separate, and scoring cause labels against the planted truth. The playbook drops all four. With 4 PSPs × 4 countries × 7 weekdays × tiers, false positives are likely. | Add: Fisher when an expected cell < 5; BH-FDR q-values in every findings table; write `data/truth/labels.parquet` that dbt never reads; report the precision/recall of `likely_cause` against the truth in FINDINGS. | Accepts. It is cheap and strengthens the RCA 25 pts. | Agreed |
| 7 | Med | §4 "`large` \| residual > 5% **or** \|Δ USD\| > $20" + "a 1.5% diff on a $2,000 order is > $20, so it is `large`" | The example uses the raw diff. A 1.5% FX move is legit noise by the brief (< 2%), yet it becomes an outlier "to investigate". Also `> $20` puts exactly $20 in noise, while the hint says "$20 is not" noise. | Apply the $ rule to the FX-adjusted residual in USD. Use `≥ $20`. Fix the example text. | Accepts. | Agreed |
| 8 | Med | §10 "Make targets (each calls `uv run recon …`)" + §2 "Constraint \| Runnable locally (reviewer has Python, Node.js or Docker)" | The brief only promises Python, Node or Docker. `make` and `uv` may not be there (Windows reviewers). Docker is "optional". | Make `docker compose up` a first-class path that is tested. Add a no-make fallback in the README: `pip install . && recon all`. Keep `make all` as the main path. | Accepts. Docker is promoted from optional to supported. | Agreed |
| 9 | Med | §9 "flag if rate ↑ > X pts with n ≥ 30" vs v2 "minimum sample 50" | "X" is a placeholder, and the minimum n disagrees with the v2 alert pick (50). The dashboard's 30 is right for the worst-week card, but the alert rule is a different thing. | Set the values in `alerts.yaml`: change rule = +2 pts WoW and n ≥ 50, else "insufficient data". Keep min 30 for the worst-week card only, and say so. | Accepts. | Agreed |
| 10 | Med | §5 "ISO week (Mon–Sun), assigned by auth date. 'Last month' = last full calendar month" + §9 "net USD loss per ISO week" | ISO weeks cross month edges, so which weeks are "last month" is not defined. The worst week uses **net** loss while the Pareto and $127k use **gross** under-settlement. | A week belongs to the month holding its Thursday (ISO rule). Show both net and gross in the card, rank by net, and label it. | Accepts the Thursday rule. Rebuts using one metric everywhere: net is the right "worst week" measure and gross is the right loss total. Label both. | Agreed |
| 11 | Low | §10 "Make targets … `make all` · `make app` · `make alerts` · `make test` · `make clean`" vs v2 "`make validate` gate" and `recon generate \| build \| validate \| analyze \| report \| query \| worst-week \| alerts check \| dashboard \| all` | No `make validate` target. `make test` / `make clean` do not call `recon`, so "each calls" is wrong. The `recon` command list is not written down in the playbook. | Add `make validate`. Copy the v2 `recon` command list into §10. Say "make targets call `recon` (test/clean call pytest/dbt directly)". | Accepts. | Agreed |
| 12 | Med | §9 "new/ongoing/resolved dedupe; optional Slack webhook" + §10 "One YAML drives generator, dbt tests and input checks" | Too much for "keep your architecture simple" and 2 hours. Making dbt tests from YAML is a small project of its own. | Drop the Slack webhook and the alert states and move them to §11. Write dbt `schema.yml` by hand, and add one pytest that checks it matches the contract. | Partly rebuts: the user asked for an alert system. Compromise: keep the rules and `alerts.jsonl`, drop the webhook and the states. | Agreed |
| 13 | Low | §6 "`rounding_flag`, `rounding_residue` \| Diff < 1 rounding step of the currency" | "Rounding step" is not defined, and it differs from the `rounding` category rule. P4 rounds to 100 CLP, so its diffs are larger than 1 minor unit. | Define `rounding_step` per PSP×currency pair in `thresholds.yaml`. Use one rule for both the flag and the category. | Accepts. | Agreed |
| 14 | Low | §4 "`fx_tolerance` \| residual ≤ 2% and ≤ $20" | Domestic rows get an "fx" label even though they have no FX. | Rename it to `small` (the brief's word) and keep `fx_move_pct` for the reason. | Accepts. | Agreed |
| 15 | Low | Stack line "raw → staging → marts" and §10 "Layers \| raw → staging → marts" vs §10 models `int_transactions_usd` | The layer names do not match the model list. | Write "raw → staging → intermediate → marts" in both places. | Accepts. | Agreed |
| 16 | Low | §12 README template (10 rows) | The brief deliverable says "how to interpret the results". There is no such section. | Add a row: "How to read the outputs" (buckets, CIs, q-values, $ columns). | Accepts. | Agreed |
| 17 | Low | Header "Topics: 01 … 02 … 04 … 06 … 07" | Topic 05 (CLI, a v2 pick) is missing. | Add "05 CLI tool (FR3, one-command run)". | Accepts. | Agreed |
| 18 | Low | §4 P1 "meaningful rate +3.5 pts" | The brief's "3–4% higher" could mean points or relative. The choice is fine but not stated. | Add a one-line assumption: "read as percentage points". | Accepts. | Agreed |
| 19 | Low | §7 "Multivariable check: logistic regression … country, PSP, tier, weekend, cross-border, lag" vs §4 P1 "logistic regression interaction" | The main model has no PSP×country term, so P1 cannot show up in it. | Add a `psp × country` term (or at least PSP_B×AR). | Accepts. | Agreed |
| 20 | Low | §5 "Pending … (> 7 days pending = outlier)" and §6 "`settle_lag_days`" | No "as of" date for pending age. The lag unit (whole days or fractional) is not given. | As-of = max timestamp in the data. Lag = fractional days from timestamps; the bucket uses floor. | Accepts. | Agreed |
| 21 | Low | §4 "Default 135k (45k × 3 months…)" | Kaveh: too big for "keep it simple"; HDBSCAN on 135k rows is slow. | Keep 500 as the default. | Rebuts: DuckDB handles 135k in seconds, and P1 needs about 5k rows in the PSP_B×AR cell for power. Concedes HDBSCAN runs on flagged rows only (~20k). | Rebutted |
| 22 | Low | Header "Do not cut quality because of time." | Kaveh: this clashes with the brief ("insights and a working prototype, not a production-grade system"). | Soften it to "core first, then stretch". | Rebuts: this is the user's chosen frame, and "lean" plus "keep it simple" are already in the same block. | Rebutted |
| 23 | Low | §4 "Tax recalculation \| A few MX/CO rows move by a VAT-rate share" | A full 16–19% move is not a realistic tax recalculation. Removing VAT gives auth/1.16 (a 13.8% diff), and real corrections are usually smaller. | Embed `settle = auth / (1+VAT)` or a small VAT-base correction. | Wants to keep the simple signature for detectability; will check with a quick test. | Open |
| 24 | Low | §11 "dbt on StarRocks (same models, adapter swap)" | Overclaims: DuckDB-specific SQL (e.g. `date_trunc` variants, list functions) will need edits. | "Same models, minor SQL edits via dbt macros". | Accepts. | Agreed |
| 25 | Low | §7 "then HDBSCAN (scikit-learn) on (pct, sign, lag, residue, cross-border) as a cross-check only" | Over-engineered. The brief asks for "clusters of similar discrepancies". A GROUP BY on the rule signature already gives them. HDBSCAN adds a dependency, tuning and results that are hard to explain. | Drop HDBSCAN. Make a cluster table by grouping on (`likely_cause`, PSP, currency pair, sign). | Accepts. It was a "cross-check only" anyway. | Agreed |
| 26 | Low | §6 "`is_outlier` \| Robust z-score of `diff_usd` within PSP×country" + §9 "Table of `large` + `is_outlier` rows" | That gives two ideas of "outlier". `large` already matches the brief's "outliers CasaMarket needs to investigate". | Drop `is_outlier`. The outlier view shows `large` rows sorted by `abs_diff_usd`. | Rebuts a little: z-score catches odd rows inside a PSP. Accepts dropping it for the brief's scope. | Agreed |
| 27 | Low | §6 "`likely_cause`, `cause_confidence`" | `cause_confidence` has no rule behind it, so it adds work and no clear meaning. | Keep only `likely_cause` (with `unexplained`). | Accepts. | Agreed |
| 28 | Low | §3 "short ADR notes" + §10 "Observability \| Run log with row counts per layer" | These are extra documents for a 2-hour tool. | Put the "why" in the README "Approach" section (a few lines). Print row counts to the console from `recon build`. | Accepts. | Agreed |
| 29 | Low | §4 "Hidden patterns" (5 embedded causes) on top of P1–P4 | Nine planted effects make the generator heavy, and the brief asks for 3–4 patterns. | Keep P1–P4 plus FX timing and PSP fee. Keep partial capture, fraud and tax as optional config flags that are off by default. | Rebuts: the extra causes feed "clusters" and "cause labels" (RCA 25 pts), and each one is a single line in the config. Compromise: keep them, one simple rule each, no extra fields beyond F5. | Rebutted |
| 30 | Med | §4 bucket table and notes, §5 "FX reference rates" row, §9 "Which PSP had the worst week" row | Hard to read. Key rules are packed into long cells full of symbols. Example: "`mart_psp_weekly` ranked by $ lost (and by rate, min n); Dashboard "Worst week" card (net USD loss per ISO week, min 30 txns; last full month in the data); CLI …". A reader cannot find the rule quickly. | Split each into short bullets: one rule per line. Move the "how we got here" notes under the table. Keep cells to one short sentence. | Accepts. | Agreed |
| 31 | Low | Terms used with no explanation: "residue", "signature", "peer rule", "Pareto", "Wilson CI", "robust z-score", "rate ratio" | The CasaMarket ops team (the brief's audience) will not know these words. | Add a 6–8 line glossary, or use plain words ("leftover after rounding", "pattern", "compare to other PSPs", "top segments by $ lost"). | Accepts. | Agreed |
| 32 | Low | Stack line "Python 3.12 + uv · DuckDB 1.4.x LTS · dbt-core 1.12 + dbt-duckdb 1.11 (raw → staging → marts, with tests) · … · optional Docker Compose." and §3 "`make all` from a fresh clone; locked deps; contract; idempotent reruns; unit + dbt tests; short ADR notes; clean README" | Long run-on lines that are hard to scan. | Turn them into a short bullet list, one tool or one point per line. | Accepts. | Agreed |

## Debate highlights
- ⚡ Kaveh: The FX formula divides by a currency→USD rate. For a USD payer settling in CLP, that flips the adjustment. Every cross-border category is then wrong.
- 🏛️ Jamshid: Agreed. The model was in my head, not on the page. I will write down payer vs settle currency and add `expected_settled_minor` and `fx_residual_pct` as real columns.
- ⚡ Kaveh: The gate says lift ≥ 1.5×, but your own P1 is +3.5 pts on 17%, which is 1.2×. `make all` fails on the first run.
- 🏛️ Jamshid: Fair. Each pattern gets its own check in `generator.yaml`, and small smoke runs warn instead of failing.
- ⚡ Kaveh: The $0.50 rounding floor eats your PSP_C $0.35 fee. The fee cause can never be found.
- 🏛️ Jamshid: Accepted. Rounding means ≤ 1 minor unit or the PSP rounding step, nothing else. Fees go to ≥ $1.
- ⚡ Kaveh: 135k rows and an alert state machine don't fit "keep your architecture simple".
- 🏛️ Jamshid: 135k stays, because DuckDB is fast and P1 needs the power. The Slack webhook and the new/ongoing/resolved states move to the scale path.
- ⚡ Kaveh: Also HDBSCAN, a z-score outlier, `cause_confidence` and ADR notes. None of these is asked for, and a GROUP BY on the pattern already gives the clusters.
- 🏛️ Jamshid: Agreed, cut all four. I keep the extra planted causes, though, because they are one config line each and they feed the RCA points.
- ⚡ Kaveh: The worst-week cell and the bucket notes read like a wall of symbols. The ops team won't get past them.
- 🏛️ Jamshid: Fair. One rule per line, and a short glossary for words like "residue" and "Wilson CI".

## Must-fix list
1. **(High, F1)** Fix the FX rate direction and write down the cross-border currency model. Add `expected_settled_minor`, `fx_residual_minor` and `fx_residual_pct` to the enriched fields, with a hand-worked unit test.
2. **(High, F2)** Remove the `|Δ USD| < $0.50` rounding floor. Rounding = ≤ 1 minor unit or the PSP rounding step. Give `rounding` an explicit share. Make the PSP_C fee ≥ $1.
3. **(High, F3)** Replace the global "lift ≥ 1.5×, p < 0.01" gate with per-pattern checks (P1 in points, P2 lag shift, P3 ≥ 1.3×, P4 residue). Hard-fail only at the default size.
4. **(Med, F4)** Target meaningful+large at about 14%. Use n-aware share bounds. State the denominator (approved + settled).
5. **(Med, F5)** Make `item_count`, `risk_score` and `payer_currency` required contract fields.
6. **(Med, F6)** Add Fisher for small cells and BH-FDR q-values. Keep truth labels in a separate file and score `likely_cause` against them.
7. **(Med, F7)** Apply the `large` $ rule to the FX-adjusted residual, use `≥ $20`, and fix the $2,000 example.
8. **(Med, F8)** Make Docker a supported path and add a no-make fallback (`pip install . && recon all`) in the README.
9. **(Med, F9)** Set the alert values: WoW +2 pts, min n 50 (v2). Keep min 30 only for the worst-week card.
10. **(Med, F10)** Assign ISO weeks to a month by their Thursday. Show net and gross loss in the worst-week card, labeled.
11. **(Med, F12)** Cut the Slack webhook and the alert states. Write dbt tests by hand, and add one pytest that checks them against the contract.
12. **(Med, F30)** Rewrite the bucket table, the FX row and the worst-week row as short bullets, one rule per line.
