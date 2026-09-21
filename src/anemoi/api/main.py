"""Anemoi-API application factory.

Run it with:

    uv sync --extra api
    uv run python -m anemoi.api            # http://127.0.0.1:8000
    uv run python -m anemoi.api --reload

Or directly with uvicorn: ``uvicorn anemoi.api.main:app --reload``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__ as anemoi_version
from . import __api_version__
from .routers import meta, monitoring, registry, retraining, schedule, storms
from .stream import router as stream_router

TAGS_METADATA = [
    {"name": "meta", "description": "Health, the model/god catalog, and the data source registry."},
    {"name": "schedule", "description": "Cycle timing -- the HTTP equivalent of `anemoi schedule`."},
    {"name": "storms", "description": "Storms, and running or retrieving forecast cycles."},
    {"name": "registry", "description": "Model versions, stages, and the active model-set pin."},
    {"name": "monitoring", "description": "Train/serve drift and skew audits."},
    {"name": "retraining", "description": "Pending retrain triggers."},
    {"name": "stream", "description": "WebSocket push of cycle completions."},
]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Anemoi-API",
        description="Many winds. One forecast. Developer interface over the Anemoi reference implementation.",
        version=__api_version__,
        openapi_tags=TAGS_METADATA,
        # Starlette's own debug mode: an unhandled exception returns its
        # real traceback in the response body instead of a bare "Internal
        # Server Error". Off by default (never leak internals in normal
        # operation) -- opt in only to debug a deployment where the
        # container's own stdout/stderr isn't easily reachable (e.g.
        # Cloudflare Containers without SSH access configured).
        debug=bool(os.environ.get("ANEMOI_API_DEBUG")),
    )

    origins = os.environ.get("ANEMOI_API_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LookupError)
    def _not_found(request: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def _bad_request(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    app.include_router(meta.router, prefix="/v1")
    app.include_router(schedule.router, prefix="/v1")
    app.include_router(storms.router, prefix="/v1")
    app.include_router(registry.router, prefix="/v1")
    app.include_router(monitoring.router, prefix="/v1")
    app.include_router(retraining.router, prefix="/v1")
    app.include_router(stream_router, prefix="/v1")

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "product": "Anemoi-API",
            "tagline": "Many winds. One forecast.",
            "anemoi_version": anemoi_version,
            "api_version": __api_version__,
            "docs": "/docs",
        }

    return app


app = create_app()
