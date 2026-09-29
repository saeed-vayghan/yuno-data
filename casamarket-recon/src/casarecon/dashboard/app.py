"""Streamlit entry: page config, 5-page navigation, global sidebar filters. Owner: FRONTEND.

Run with `recon dashboard` (or `make app`) -> http://localhost:8501.
"""

import logging

import streamlit as st

from casarecon.dashboard import filters

st.set_page_config(page_title="CasaMarket settlement monitor", page_icon="📊", layout="wide")
logging.basicConfig(level=logging.INFO)

PAGES = {
    "overview": st.Page("views/overview.py", title="Overview", icon="📊", default=True),
    "drill_down": st.Page("views/drill_down.py", title="Drill-down", icon="🔎",
                          url_path="drill-down"),
    "outliers": st.Page("views/outliers.py", title="Outliers", icon="🚩", url_path="outliers"),
    "root_causes": st.Page("views/root_causes.py", title="Root causes & actions", icon="🧭",
                           url_path="root-causes"),
    "alerts": st.Page("views/alerts.py", title="Alerts", icon="🔔", url_path="alerts"),
}
st.session_state["PAGES"] = PAGES

nav = st.navigation(list(PAGES.values()))
filters.render_global_sidebar()  # before nav.run(): widgets survive page switches
nav.run()
