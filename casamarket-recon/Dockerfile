FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev && useradd -m app && chown -R app /app
USER app
ENV PATH="/app/.venv/bin:$PATH" CASARECON_DB=/app/data/casarecon.duckdb
EXPOSE 8501
CMD ["sh", "-c", "recon all && recon dashboard --host 0.0.0.0"]
