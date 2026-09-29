# 01 · Setup and app shell

**Goal:** `make app` opens a 5-page Streamlit app on `localhost:8501`, with the theme, the Okabe-Ito colours, shared layout helpers and one set of sidebar filters that follow the user from page to page.

**Time box:** 12 min · **Tag:** Core

## Inputs
- Engineer delivered: repo layout from IMPLEMENTATION-PLAN (`src/casarecon/…`), `pyproject.toml` with `streamlit` and `plotly`, `recon dashboard` stub in `cli.py`, Makefile.
- UI-UX-PLAN: Information architecture, Filters & state, Visual system (theme + colours).

## Steps

### 1. Files to create

```
casamarket-recon/
├── .streamlit/config.toml                 # theme + server (repo root: Streamlit reads it from the working dir)
└── src/casarecon/dashboard/
    ├── app.py                             # entry: page config, sidebar filters, st.navigation
    ├── theme.py                           # Okabe-Ito constants + Plotly template
    ├── format.py                          # pure formatters (file 02 / 08)
    ├── filters.py                         # widgets ↔ session_state ↔ query_params
    ├── layout.py                          # page header, as-of banner, active-filter line
    ├── data.py                            # cached wrappers over casarecon.core (file 02)
    └── pages/
        ├── overview.py  drill_down.py  outliers.py  root_causes.py  alerts.py
```

Note: when `st.navigation` is used, Streamlit ignores the automatic `pages/` folder discovery. The folder name is only for order.

### 2. Run command and Makefile

- `recon dashboard` runs:
  `streamlit run src/casarecon/dashboard/app.py --server.port 8501 --server.address localhost`
- Makefile: `app: ; uv run recon dashboard`
- Docker override (one fix, owned by engineer file 10): the Dockerfile `CMD` runs `recon dashboard --host 0.0.0.0`. The CLI flag beats `config.toml`, so `config.toml` keeps `address = "localhost"`. No `STREAMLIT_SERVER_ADDRESS` env.

**Decision (bind address):** 🏛️ Jamshid: bind to `localhost` by default (no auth, private data). 🎨 Mani: Docker users will see a dead page. → Default `localhost`; only the Docker `CMD` passes `--host 0.0.0.0` (engineer file 10).

### 3. `.streamlit/config.toml`
Copy it from UI-UX-PLAN "Theme" as is: light base, `primaryColor = "#0072B2"`, `headless = true`, `gatherUsageStats = false`, `toolbarMode = "minimal"`, `showErrorDetails = false`. No custom CSS.

### 4. `theme.py`: colours in one place

```python
# Okabe-Ito. Colour is never the only signal: always pair with a word or icon.
CATEGORY_COLORS = {"exact": "#8C8C8C", "rounding": "#56B4E9", "fx_tolerance": "#0072B2",
                   "meaningful": "#E69F00", "large": "#D55E00"}
CATEGORY_LABELS = {"exact": "Exact", "rounding": "Rounding", "fx_tolerance": "FX noise",
                   "meaningful": "Meaningful", "large": "Large"}
CATEGORY_ORDER = ["exact", "rounding", "fx_tolerance", "meaningful", "large"]
PSP_COLORS = {"PSP_A": "#0072B2", "PSP_B": "#E69F00", "PSP_C": "#009E73",
              "PSP_D": "#CC79A7", "PSP_E": "#56B4E9"}
SEVERITY = {"SEV2": ("#D55E00", "▲ SEV2 · same day"), "SEV3": ("#E69F00", "● SEV3 · weekly"),
            "INFO": ("#0072B2", "ℹ Info")}   # keys = severity values in alerts.jsonl
RESOLVED = ("#009E73", "✓ Resolved")
UNDER, OVER = "#D55E00", "#0072B2"
LOW_SAMPLE_OPACITY = 0.4
TEXT_ON_ORANGE = "#1F2328"

def plotly_template() -> "plotly.graph_objects.layout.Template": ...
    # font, light grid, hover format, height ≤ 400, no title case
```

### 5. `app.py`: the shell

```python
import streamlit as st
from casarecon.dashboard import filters, layout

st.set_page_config(page_title="CasaMarket settlement monitor", page_icon="📊", layout="wide")

PAGES = {
    "overview":    st.Page("pages/overview.py",    title="Overview", icon="📊", default=True),
    "drill_down":  st.Page("pages/drill_down.py",  title="Drill-down", icon="🔎", url_path="drill-down"),
    "outliers":    st.Page("pages/outliers.py",    title="Outliers", icon="🚩", url_path="outliers"),
    "root_causes": st.Page("pages/root_causes.py", title="Root causes & actions", icon="🧭", url_path="root-causes"),
    "alerts":      st.Page("pages/alerts.py",      title="Alerts", icon="🔔", url_path="alerts"),
}
st.session_state["PAGES"] = PAGES          # pages use it for st.switch_page / st.page_link
nav = st.navigation(list(PAGES.values()))
filters.render_global_sidebar()            # rendered in the entry file → widgets survive page switches
nav.run()
```

### 6. Sidebar global filters

Three global filters, in the sidebar, rendered once in `app.py`:

| Filter | Widget | Default | Values from |
|---|---|---|---|
| Auth date range | `st.date_input(value=(min, max))` | full data range | `core.filter_options()` `min_date`, `max_date` |
| Country | `st.multiselect` | empty = all | `MX, CO, AR, CL` |
| PSP | `st.multiselect` | empty = all | `PSP_A … PSP_E` |

Page-only filters (tier, cross-border, weekday, category, cause, min $, month, severity, status) sit at the top of their page, not in the global sidebar.

**Decision (global vs page filters):** 🎨 Mani wanted all filters in the sidebar. 🏛️ Jamshid: a sidebar with 12 widgets hides which ones apply. → 3 global in the sidebar; the rest on the page that uses them. Each page says which global filters it ignores.

### 7. How filters pass between pages (`filters.py`)

One source of truth: `st.session_state["filters"]`, a `Filters` value (the frozen dataclass defined in core, see file 02).

```python
def render_global_sidebar() -> None: ...
    # 1. first run of a session: read st.query_params, validate, st.toast unknown values
    # 2. widgets with key="w_country" etc.; on_change=_sync
def _sync() -> None: ...
    # copy widget values → st.session_state["filters"]; write non-default values to st.query_params
def current() -> Filters: ...
def set_handoff(**values) -> None: ...     # e.g. psp=("PSP_B",), date_from=…, date_to=…
def apply_handoff() -> list[str]: ...       # target page: pop "handoff", merge into filters, return what was set
def clear() -> None: ...                    # "Clear filters" button
```

Order of truth: handoff (one-shot) > `st.session_state["filters"]` > `st.query_params` (first load only) > defaults.

A cross-page link does:
```python
filters.set_handoff(psp=("PSP_B",), date_from=week_start, date_to=week_end)
st.switch_page(st.session_state["PAGES"]["drill_down"])
```

**Fallback if the handoff fails** (new tab, browser refresh, or a Streamlit version that drops state on switch):
1. On first load the target page reads `st.query_params` (the source page wrote them before switching).
2. If both are empty, the page still loads with all data and shows in the active-filter line: "No filters carried over. Set PSP / dates in the sidebar." The link label on the source page already shows the values ("Open PSP_B · W25 in Drill-down"), so the user can set them by hand.

Page-only filters are stored in plain keys (`st.session_state["f_min_usd"]`), not only in widget keys, because Streamlit deletes a widget's key when that widget is not drawn on the current page.

### 8. `layout.py`: shared helpers

```python
def page_header(title: str, uses: set[str]) -> None: ...
    # st.title(title); as-of banner; active-filter line; "Clear filters" button
def as_of_banner() -> None: ...
    # "Data as of 2026-06-30 · Last closed week W25 (Jun 15–21)"  ← core.status()
def active_filters_line(uses: set[str]) -> None: ...
    # "Active: PSP_B · AR · Jun 15–21. Tier filter not used here."
```

Wireframe of the frame every page shares:
```
┌ Sidebar ─────────────┐┌──────────────────────────────────────────────────────┐
│ 📊 Overview          ││ <Page title>                                         │
│ 🔎 Drill-down        ││ Data as of 2026-06-30 · Last closed week W25 (Jun 15–21)
│ 🚩 Outliers          ││ Active: PSP_B · AR · Apr 1–Jun 30   [Clear filters]  │
│ 🧭 Root causes & act.│├──────────────────────────────────────────────────────┤
│ 🔔 Alerts            ││ page body                                            │
│ ── Filters ───────── ││                                                      │
│ Auth dates [..–..]   ││                                                      │
│ Country   [ … ]      ││                                                      │
│ PSP       [ … ]      ││                                                      │
└──────────────────────┘└──────────────────────────────────────────────────────┘
```

## Done when
- [ ] `make app` opens `http://localhost:8501` with 5 pages in the sidebar, in the order above, each with a stable URL (`/drill-down`, `/outliers`, `/root-causes`, `/alerts`).
- [ ] Server binds to localhost (check the terminal line "Local URL").
- [ ] Setting PSP = PSP_B on Overview and clicking Outliers keeps PSP_B selected.
- [ ] Opening `localhost:8501/drill-down?psp=PSP_B` preselects PSP_B; `?psp=PSP_Z` shows a toast "Ignored unknown PSP 'PSP_Z'".
- [ ] No page imports `duckdb`.

## Serves
FR3 (dashboard on localhost); constraint "runs on localhost"; UI-UX build step 1 and 4; Flows A, C, D, E (cross-page links).

## Pitfalls
- Rendering filter widgets inside a page file: they reset when you switch pages. Render them in `app.py`.
- `st.set_page_config` must be the first Streamlit call, and only in `app.py`.
- Writing every filter to the URL: keep only non-default values, links stay short.
- Hard-coding the country/PSP lists in the page: take them from `core.filter_options()`.

## Hand-off
Shell and filters work with empty pages. Next: `02-data-access-contract.md` fills `data.py`.
