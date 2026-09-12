from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def register_routes(app: FastAPI) -> None:
    """Register the API endpoints on the FastAPI app."""
    from srag.api.routers_auth import router as auth_router
    from srag.api.routers_clinical import router as clinical_router
    from srag.api.routers_core import router as core_router
    from srag.api.routers_ingest import router as ingest_router
    from srag.api.routers_manage import router as manage_router
    from srag.api.routers_reports import router as reports_router
    from srag.api.routers_territory import router as territory_router

    # Register routes under both "" and "/api" for flexibility and backwards compatibility.
    # The empty prefix "" is used when requests bypass Nginx or Nginx strips the "/api" prefix.
    # The "/api" prefix is used for explicit versioning/routing structures.
    for prefix in ["", "/api"]:
        app.include_router(auth_router, prefix=prefix)
        app.include_router(core_router, prefix=prefix)
        app.include_router(territory_router, prefix=prefix)
        app.include_router(clinical_router, prefix=prefix)
        app.include_router(ingest_router, prefix=prefix)
        app.include_router(manage_router, prefix=prefix)
        app.include_router(reports_router, prefix=prefix)
