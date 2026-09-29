# report
`recon report`: renders `reports/FINDINGS.md`, `reports/RECOMMENDATIONS.md` and `reports/recommendations.json`
from `reports/findings.json` + `reports/analysis/*.csv` (+ `reports/alerts.jsonl` if present). No hand-typed numbers:
every number goes through a filter in `fmt.py` (`usd`, `pct`, `pts`, `q`, `ci`, `ratio`, `count`, `table`).

| Module | Holds |
|---|---|
| `fmt.py` | Jinja filters + Markdown table |
| `recommend.py` | action catalogue (keyed by finding kind / cause), ranking by saving = excess loss × reduction % |
| `render.py` | Jinja env (`StrictUndefined`), table shaping, context builders |
| `templates/` | `FINDINGS.md.j2`, `RECOMMENDATIONS.md.j2` |
| `run.py` | shell: read files, render, write |

Run: `uv run recon report` (after `recon analyze`).
