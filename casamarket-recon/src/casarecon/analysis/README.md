# analysis
Root-cause analysis for `recon analyze` -> `reports/findings.json`, `reports/analysis/*.csv`, `reports/figures/*`.

Pure functions on pandas DataFrames (no DB, no files); only `run.py` does I/O (core + store + `adapters/files.py`).

| Module | Holds |
|---|---|
| `stats.py` | `wilson`, `lift`, `rate_test` (chi² / Fisher), `bh`, `spearman`, `mann_whitney`, `excess_loss` |
| `segments.py` | `rate_frame`, `segments_from_fct` (pure stand-in for `core.segment_rates`), `compare_to_peers` (peer rule), `two_group`, `top_causes` |
| `rca.py` | one test table per brief question (Q1 geo, Q2 PSP × country, Q3 size, Q4 time + over-$300 lag, Q6 cross-border); `all_tests` runs BH once |
| `causes.py` | Q5 cause share per PSP, fee drift (last month vs earlier), partial capture, fraud hold |
| `signatures.py` | signature table, `systematic` vs `random` |
| `glm.py` | the one logistic GLM; drops PSP × country cells n < 200 and refits on failure |
| `checks.py` | truth precision / recall, threshold sensitivity |
| `findings.py` | summary + `findings.json` (q < 0.05, worse than peers, ranked by `usd_quarter`) |
| `figures.py` | one bar chart per finding (saved by `adapters.files.write_figures`) |
| `analyze.py` | the whole analysis as one pure function |

$ impact per segment = max(rate − peer rate, 0) × n × mean loss (median beside it); the window is one quarter.
Run: `uv run recon analyze`. `CASARECON_FIGURE_FORMAT=html` skips PNG export.
