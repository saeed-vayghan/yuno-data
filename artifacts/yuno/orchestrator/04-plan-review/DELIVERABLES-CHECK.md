# Deliverables Check · Implementation Plan + UI/UX Plan
**Verdict:** ⚠️ before → ✅ after: every brief item already had a step, but 8 of 11 lacked a strict "Done when" proof or were out of sync between the plans. All are closed now.

Plan A = `architect/02-implementation-plan/IMPLEMENTATION-PLAN.md` · Plan B = `designer/01-ui-ux/UI-UX-PLAN.md`. Step numbers in the "before" table are the original ones.

## Coverage (before fixes)
| # | Brief item | Plan A | Plan B | Status | Evidence (section/step) |
|---|---|---|---|---|---|
| 1 | Working code + clear README / run instructions | ✅ | n/a | ✅ | A: S0–S3 code; S4.3 README Quick start; Done: `make clean && make all` exits 0 and every README command runs as written |
| 2 | Generated test dataset or script to reproduce | ✅ | n/a | ✅ | A: S1.2–S1.3 seeded generator + committed 500-row sample; Done: same seed → same sha256; S1.4 validation gate |
| 3 | Analysis outputs (tables, charts, stats, report) | ✅ | n/a | ⚠️ | A: S3.3 CSVs, S3.4 findings.json + figures, S4.1 FINDINGS.md. Gap: committing `reports/` + figures only happens in S6.3 (packaging, can be cut); S4.1 Done did not check figures are linked |
| 4 | Docs: approach, key findings, **assumptions** | ⚠️ | n/a | ⚠️ | A: S4.3 lists a "Definitions & assumptions" section, but no explicit Assumptions list and the Done check only ran commands; nothing proved the sections exist |
| 5 | (Stretch) Dashboard / monitoring or recommendations | ⚠️ | ✅ | ⚠️ | A: S5.1–S5.3; B: Build order 1–11. Gaps: B's prerequisite needs ~15 core functions that A never plans (A named 8, with different names: `outliers()`, `transactions()`); S5.2 Done did not check $ impact / implementation per action |
| 6 | Process data, calculate discrepancies accurately | ✅ | n/a | ✅ | A: S2.4 fact model + dbt unit tests (FX row, CLP row, 2¢/$500, $20); S2.6 exit 5 on failure; S3.3 truth check (≥ 0.9) |
| 7 | ≥ 3–4 patterns backed by data | ⚠️ | n/a | ⚠️ | A: S3.3 P1–P4 q < 0.05; S3.4 "≥ 4 findings"; S4.1 grep ≥ 4 `F#`. Gap: counts findings, not their evidence. No check that each has n, CI, lift, q, $; `lift` not in findings.json; non-significant findings could fill the count |
| 8 | Well documented, team can understand and use it | ⚠️ | ⚠️ | ⚠️ | A: README sections + "How to read outputs"; B: tooltips, captions, microcopy. Gap: no check README sections exist; README "Monitoring" (written in Phase 4) never updated for the dashboard |
| 9 | Good engineering practice (clean, reproducible, clear) | ⚠️ | ✅ | ⚠️ | A: dbt tests, pytest, `uv.lock`, contract. Gap: full-pipeline rerun check only in S6.2 (Phase 6, after stretch); core Done does not run `make test` |
| 10 | (Stretch) Interactive exploration or next steps | ⚠️ | ✅ | ⚠️ | B: Pages 1–5, Filters & state, UI tests 1–15. Gaps: B test 4 calls `recon worst-week --format json` (A had no `--format` there); B filtered "≥ $50" vs A `> 50`; A S5.3 said Root causes reads only `findings.json`, B reads marts + both reports |
| 11 | Priority: pipeline + analysis first, then stretch | ⚠️ | ⚠️ | ⚠️ | A: Phases 0–4 core, 5 stretch, 6 packaging. Gap: S4.2 (brief CLI questions = FR3 stretch) came **before** the README (S4.3) and the core checkpoint. B had no "start after core" gate |

## Discussion highlights (🏛️ / ⚡ / 🎨, 6–10 short turns, ending in agreement)
| # | Voice | Point |
|---|---|---|
| 1 | 🏛️ Jamshid | Structure is sound: every deliverable maps to a phase, and the Definition of done walks the brief. Items 1, 2, 6 are fully proven. |
| 2 | ⚡ Kaveh | "Has a step" is not "proven". Item 7: `grep -c F#` ≥ 4 passes with four findings that have no CI or $. The check must look at the evidence, and require q < 0.05. |
| 3 | 🏛️ Jamshid | Agreed. Add `lift` to `findings.json` (the brief's examples are lifts: "3.2x higher"). Done when: every finding has n, rate, CI, peer, lift, q, $, and each F# links a real figure. |
| 4 | 🎨 Mani | Item 4: the brief says "assumptions". A reviewer scanning the README wants a heading called Assumptions, not assumptions buried in a definitions table. And nothing checks the README has its 11 sections. |
| 5 | ⚡ Kaveh | Add one `### Assumptions` list and put it in Done when. Same step: run `make all` twice and compare the `findings.json` hash, plus `make test`. Cheap, and it proves item 9 before stretch starts. |
| 6 | ⚡ Kaveh | Item 11: the brief CLI questions are FR3, a stretch item, yet they sat before the README. Swap them: README is S4.2, the core checkpoint follows, brief questions become S4.3, "first stretch step". The checkpoint must also commit `reports/` so item 3 survives if Phase 6 is cut. |
| 7 | 🎨 Mani | Items 5 and 10: my plan assumes `kpis`, `weekly_trend`, `load_recommendations` and more, but the Implementation Plan never builds them, and it calls the outliers query something else. And "over $50" is `>` in one plan and `≥` in the other. |
| 8 | 🏛️ Jamshid | One name: `query_transactions` + `mask_id` in S3.1. The rest are added in S5.3, page by page, each with a pytest. Add `--format json` to `worst-week`. Use "over $50" (`> 50`) everywhere, as the brief says. |
| 9 | 🎨 Mani | Last one, item 8: after the dashboard exists, the README must tell the team how to use it. Build step 11 now writes the README "Monitoring" section, and "done" means a newcomer answers both questions using only the README. |
| 10 | All | Agreed. Minimal edits, no new tools, formats kept. Both plans now agree with each other and with FINAL-SOLUTION. |

## Fixes applied
| # | Gap | File | Change made |
|---|---|---|---|
| 3 | Outputs could stay uncommitted if Phase 6 is cut; figures not checked | Plan A | Core checkpoint now commits `reports/FINDINGS.md`, `findings.json`, `analysis/*.csv`, `figures/*`. S4.1 Done when: each F# links a figure file that exists |
| 4 | No explicit Assumptions list; no check | Plan A | S4.2 (README) Do: `### Assumptions` list (synthetic data, auth-day USD, FX removal, `thresholds.yaml`, local time, Thursday rule, no tips, $ estimates, reduction %). Done when: all 11 sections + `### Assumptions` heading present |
| 5 | FR4 check weak; dashboard core functions not planned | Plan A | S5.2 Done when: each action shows $ impact, owner, implementation. S5.3 Do: add the UI plan's core read functions; Done when: each has a pytest |
| 7 | Pattern count not tied to evidence | Plan A | S3.4: `lift` added to `findings.json`; Done when: ≥ 4 findings with q < 0.05 and non-null n, rate, CI, peer_rate, lift, q, usd_quarter. S4.1: finding format adds lift; Done when: each F# shows n, CI, lift, q and $ |
| 8 | README not checked; Monitoring section never updated for the dashboard | Plan A, Plan B | A S4.2 Done when checks all 11 sections. B Build order step 11: write README "Monitoring" (open the app, page purposes, both brief questions); done = newcomer answers both using only the README |
| 9 | Reproducibility only proven in Phase 6 | Plan A | S4.2 Done when: `make all` twice → same `sha256sum reports/findings.json`; `make test` passes |
| 10 | Names, `--format`, `>` vs `≥`, Root-causes source out of sync | Plan A, Plan B | A S3.1: `query_transactions(filters, min_usd, limit)` + `mask_id` (replaces `outliers()`/`transactions()`). A S4.3: `worst-week --format table|json`; `query` masks IDs. A S5.3: Root causes reads `mart_cause_summary`, `findings.json`, FINDINGS.md, RECOMMENDATIONS.md. B: Flow B, Outliers note and UI test 6 use "over $50" (`> 50`) |
| 11 | Stretch step before README / checkpoint; Plan B had no gate | Plan A, Plan B | A: README is now S4.2; core checkpoint moved before brief questions (now S4.3, "first stretch step"); phase table and DoD (`S0–S4.2`) updated. B Build order prerequisite: start only after Plan A's core checkpoint |

## Coverage (after fixes)
| # | Brief item | Status | Where |
|---|---|---|---|
| 1 | Working code + README / run instructions | ✅ | A S0–S3; S4.2 README + `make all` Done when |
| 2 | Test dataset or generator script | ✅ | A S1.2–S1.4 (seeded, same hash, sample committed, validation gate) |
| 3 | Analysis outputs | ✅ | A S3.3–S3.4, S4.1 (figures linked); core checkpoint commits `reports/` |
| 4 | Docs: approach, findings, assumptions | ✅ | A S4.2: 11 README sections incl. `### Assumptions`, checked in Done when |
| 5 | (Stretch) Dashboard / recommendations | ✅ | A S5.1–S5.3 (core functions + pytest; FR4 $ / owner / implementation); B Build order 1–11 |
| 6 | Accurate discrepancy calculation | ✅ | A S2.4 unit tests, S2.6 exit 5, S3.3 truth check |
| 7 | ≥ 3–4 patterns backed by data | ✅ | A S3.4 (≥ 4, q < 0.05, n/CI/lift/q/$ non-null), S4.1 (each F# shows them + figure) |
| 8 | Well documented and usable | ✅ | A S4.2 README check; B step 11 README Monitoring + newcomer test; B microcopy/tooltips |
| 9 | Clean, reproducible engineering | ✅ | A S4.2 (rerun hash + `make test` before stretch); S6.2 CI/e2e |
| 10 | (Stretch) Interactive exploration / next steps | ✅ | B Pages 1–5 + UI tests; A S4.3/S5.3 consistent names, formats and `> 50` rule; A S5.2 recommendations |
| 11 | Pipeline + analysis before stretch | ✅ | A: core checkpoint after S4.2 README; S4.3+ and Phase 5 are stretch; B gated on core checkpoint |
