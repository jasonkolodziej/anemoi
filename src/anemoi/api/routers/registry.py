"""Model registry: versions, stages, and the active model-set pin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...tracking.registry import ALL_MODELS
from .. import convert, schemas
from ..deps import require_api_key, state_dependency

router = APIRouter(prefix="/registry", tags=["registry"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[schemas.RegistryEntry])
def list_registry(state=Depends(state_dependency)) -> list[schemas.RegistryEntry]:
    state.refresh_registry_if_stale()
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
    state.refresh_registry_if_stale()
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


@router.get("/{model}/architecture", response_model=schemas.ArchitectureOut)
def get_model_architecture(
    model: str, version: int | None = None, state=Depends(state_dependency)
) -> schemas.ArchitectureOut:
    """What ``model`` is made of, read from the model itself: the console's
    system view. ``version`` defaults to the one the active pin serves,
    else production, else the newest. A version registered before
    ``arch_params`` (or none at all) is described from the builder's
    defaults, and says so (``defaults``)."""
    import json

    from ...models.architecture import DESCRIBABLE_MODELS, describe_cached
    from ...models.base import torch_available

    if model not in DESCRIBABLE_MODELS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown model {model!r}")
    if not torch_available():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "torch is not installed")
    state.refresh_registry_if_stale()
    versions = state.registry.versions(model)
    if version is not None:
        chosen = next((v for v in versions if v.version == version), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model} has no version {version}")
    else:
        pin = state.registry.active_pin()
        pinned = (pin or {}).get("members", {}).get(model)
        chosen = (
            next((v for v in versions if v.version == pinned), None)
            or state.registry.production(model)
            or state.registry.latest(model)
        )
    raw = chosen.tags.get("arch_params") if chosen else None
    arch_params = json.loads(raw) if raw else None
    arch = describe_cached(model, arch_params)
    return schemas.ArchitectureOut(
        model=model,
        version=chosen.version if chosen else None,
        stage=chosen.stage.value if chosen else None,
        arch_params=arch.arch_params,
        defaults=arch.defaults,
        batched=arch.batched,
        input_dim=arch.input_dim,
        latent_dim=arch.latent_dim,
        lead_hours=arch.lead_hours,
        output_dim=arch.output_dim,
        inputs=[schemas.TensorOut(name=t.name, shape=t.shape) for t in arch.inputs],
        outputs=[schemas.TensorOut(name=t.name, shape=t.shape) for t in arch.outputs],
        layers=[
            schemas.LayerOut(
                path=layer.path, type=layer.type, depth=layer.depth,
                output_shape=layer.output_shape, own_params=layer.own_params,
                total_params=layer.total_params,
            )
            for layer in arch.layers
        ],
        total_params=arch.total_params,
        trainable_params=arch.trainable_params,
    )


@router.get("/pins/active", response_model=schemas.ActivePin | None)
def get_active_pin(state=Depends(state_dependency)) -> schemas.ActivePin | None:
    state.refresh_registry_if_stale()
    pin = state.registry.active_pin()
    if pin is None:
        return None
    return schemas.ActivePin(
        label=pin["label"], latent_signature=pin["latent_signature"], members=pin["members"]
    )
