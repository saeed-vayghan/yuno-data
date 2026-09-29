# core
Shared primitives + the read-only CORE API (`from casarecon import core`). Pure code; no duckdb/streamlit/typer imports.
Stores come from `deps.py` (`get_store()`, `get_store_at(path)`); tests pass `store=`.
Files: config, paths (env overrides), errors, filters, money, privacy, weeks (ISO week / Thursday / closed-week rules), log, deps, queries/.
