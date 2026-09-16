"""Model registry: versions, stages, and the active model-set pin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...tracking.registry import ALL_MODELS
from .. import convert, schemas
from ..deps import require_api_key, state_dependency

router = APIRouter(prefix="/registry", tags=["registry"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[schemas.RegistryEntry])
def list_registry(state=Depends(state_dependency)) -> list[schemas.RegistryEntry]:
    out = []
    for name in ALL_MODELS:
        versions = state.registry.versions(name)
        if not versions:
            continue
        latest = state.registry.latest(name)
        production = state.registry.production(name)
        out.append(
            schemas.RegistryEntry(
                model=name,
                latest=convert.model_version_out(latest) if latest else None,
                production=convert.model_version_out(production) if production else None,
                versions=[convert.model_version_out(v) for v in versions],
            )
        )
    return out


@router.get("/{model}", response_model=schemas.RegistryEntry)
def get_model_registry(model: str, state=Depends(state_dependency)) -> schemas.RegistryEntry:
    versions = state.registry.versions(model)
    if not versions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no registered versions for {model!r}")
    latest = state.registry.latest(model)
    production = state.registry.production(model)
    return schemas.RegistryEntry(
        model=model,
        latest=convert.model_version_out(latest) if latest else None,
        production=convert.model_version_out(production) if production else None,
        versions=[convert.model_version_out(v) for v in versions],
    )


@router.get("/pins/active", response_model=schemas.ActivePin | None)
def get_active_pin(state=Depends(state_dependency)) -> schemas.ActivePin | None:
    pin = state.registry.active_pin()
    if pin is None:
        return None
    return schemas.ActivePin(
        label=pin["label"], latent_signature=pin["latent_signature"], members=pin["members"]
    )
