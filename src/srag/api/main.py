from __future__ import annotations

import contextlib
import logging
from pathlib import Path

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from srag.api import core as _core
from srag.api.routes import register_routes

logger = logging.getLogger(__name__)

_cache = _core._cache

app = FastAPI(title="SRAG Mossoró API")

# Configure Logfire (Optional for local development)
try:
    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_fastapi(app)
    logfire.instrument_pydantic()
except Exception as e:
    logger.warning("Logfire not configured: %s", e)

# Use singleton engine from core.py to avoid duplicates
with contextlib.suppress(Exception):
    logfire.instrument_sqlalchemy(_core.engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://localhost:8001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)


register_routes(app)

static_dir = Path("/app/frontend/dist")
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
