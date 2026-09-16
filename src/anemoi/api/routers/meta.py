"""Health, model catalog, and data source registry."""

from __future__ import annotations

import importlib.util

from fastapi import APIRouter

from ... import __version__ as anemoi_version
from ...data.sources import REGISTRY
from .. import __api_version__, convert, schemas

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    return schemas.HealthOut(
        status="ok",
        api_version=__api_version__,
        anemoi_version=anemoi_version,
        torch_available=importlib.util.find_spec("torch") is not None,
    )


@router.get("/models", response_model=schemas.ModelCatalog)
def models() -> schemas.ModelCatalog:
    """The six wind gods plus the neutral Fusion colour (Branding Brief §5)."""
    return convert.model_catalog()


@router.get("/sources", response_model=list[schemas.SourceOut])
def sources() -> list[schemas.SourceOut]:
    """The §4.1 data source registry, sorted role then key -- matches
    ``anemoi sources``."""
    rows = sorted(REGISTRY.values(), key=lambda src: (src.role.value, src.key))
    return [convert.source_out(r) for r in rows]
