FROM python:3.14-slim AS backend

RUN groupadd -g 1001 -r appgroup && \
    useradd -u 1001 -r -g appgroup appuser && \
    mkdir -p /home/appuser && chown appuser:appgroup /home/appuser

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_PYTHON_INSTALL_DIR=/usr/local/share/uv/python

COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-project && \
    rm -rf /root/.cache/uv && \
    chown -R appuser:appgroup /app/.venv && \
    uv run python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL spatial'); con.close()" && \
    cp -r /root/.duckdb /home/appuser/ && \
    chown -R appuser:appgroup /home/appuser/.duckdb

COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup data/processed/ ./data/processed/
COPY --chown=appuser:appgroup data/geojson/ ./data/geojson/

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

USER appuser

CMD ["uvicorn", "srag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
