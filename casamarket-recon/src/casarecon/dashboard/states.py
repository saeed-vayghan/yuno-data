"""Page states: no DB, rebuilding, not built yet, error, empty. One place for the microcopy.

`guarded(render)` wraps a whole page body; `section(label, render)` wraps one block so a
missing core function degrades only that block ("not available yet"), not the whole page.
"""

import logging
from collections.abc import Callable

import streamlit as st

from casarecon.dashboard import data

log = logging.getLogger("casarecon.dashboard")

NO_DATA = "No data yet. Run `make all` first, then reload this page."
BUSY = "The data is being rebuilt. Retry in a minute."
ERROR = "Something went wrong loading this view. The details are in the terminal."
EMPTY = "No transactions match these filters."


def no_data() -> None:
    st.info(NO_DATA, icon="ℹ️")
    st.stop()


def busy(key: str) -> None:
    st.warning(BUSY, icon="⏳")
    if st.button("Retry", key=f"retry_{key}"):
        st.rerun()


def not_built(label: str, detail: str = "") -> None:
    note = f" ({detail})" if detail else ""
    st.info(f"**{label}** is not available yet: the core function is still being built{note}.",
            icon="🚧")


def error(label: str) -> None:
    log.exception("dashboard view failed: %s", label)
    st.error(ERROR, icon="⚠️")


def empty(text: str = EMPTY) -> None:
    st.info(text, icon="ℹ️")


def section(label: str, render: Callable[[], None]) -> None:
    """Wrap one block; other blocks keep working when this one is not built yet."""
    try:
        render()
    except data.DbMissing:
        no_data()
    except data.DbBusy:
        busy(label)
    except NotImplementedError as e:
        not_built(label, str(e))
    except data.BadFilter as e:
        st.warning(f"Ignored a bad filter: {e}", icon="⚠️")
    except Exception:  # noqa: BLE001 - friendly message; traceback goes to the log
        error(label)  # st.stop / st.rerun raise BaseException, so they pass through


def guarded(render: Callable[[], None], label: str = "This page") -> None:
    """Wrap a whole page body."""
    section(label, render)
