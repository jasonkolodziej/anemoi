"""Real inference: reconstruct a trained model from its registered
checkpoint (#78).

Checkpoints only ever save ``model.state_dict()`` (every
``run_*_curriculum``'s upload step) -- never the architecture that
produced it. A real inference process needs to rebuild an identical,
untrained skeleton (``build_<model>(...)`` called with the exact same
kwargs training used) before ``load_state_dict`` can put real weights
into it. `tracking.registry.ModelVersion.tags["arch_params"]` (added
#78, JSON-encoded by `tracking.experiment_tracking.arch_params_tag`) is
the only real record of what those kwargs were; `ModelVersion
.checkpoint_uri` is the only real record of where the weights are.

A version registered before #78 has neither -- ``load_trained_model``
raises rather than guessing at defaults that might not match what that
specific version was actually trained with.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.base import require_torch

if TYPE_CHECKING:
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelVersion

#: Every real architecture with a real training path (#22, #78).
MODEL_NAMES: tuple[str, ...] = (
    "lstm", "cnn", "transformer", "gnn", "pinn", "diffusion", "fusion",
)

#: Arch_params keys whose JSON round-trip (list) needs to become the real
#: tuple `build_<model>(...)` expects.
_TUPLE_PARAMS: tuple[str, ...] = ("lead_hours", "grid_size")


class InferenceLoadError(RuntimeError):
    pass


def _builder(name: str):
    """The real `build_<model>` function for ``name`` -- deferred imports,
    same pattern every `real_run_*.py` module already uses, so importing
    this module doesn't require every model's dependencies to be
    installed just to look one builder up."""
    if name == "lstm":
        from ..models.lstm import build_lstm

        return build_lstm
    if name == "cnn":
        from ..models.cnn import build_cnn

        return build_cnn
    if name == "transformer":
        from ..models.transformer import build_transformer

        return build_transformer
    if name == "gnn":
        from ..models.gnn import build_gnn

        return build_gnn
    if name == "pinn":
        from ..models.pinn import build_pinn

        return build_pinn
    if name == "diffusion":
        from ..models.diffusion import build_diffusion

        return build_diffusion
    if name == "fusion":
        from ..models.fusion import build_fusion

        return build_fusion
    raise InferenceLoadError(f"no real architecture for {name!r}; expected one of {MODEL_NAMES}")


def _decode_arch_params(version: ModelVersion, tag_key: str) -> dict:
    raw = version.tags.get(tag_key)
    if raw is None:
        raise InferenceLoadError(
            f"{version.name} v{version.version} has no {tag_key!r} tag -- either "
            "registered before #78, or trained via a path that doesn't set it"
        )
    params = json.loads(raw)
    for key in _TUPLE_PARAMS:
        if key in params:
            params[key] = tuple(params[key])
    return params


def _download_state_dict(
    checkpoint_uri: str | None, checkpoint_store: CheckpointStore, torch, *, label: str,
):
    if not checkpoint_uri:
        raise InferenceLoadError(f"{label} has no checkpoint_uri to load real weights from")
    with tempfile.TemporaryDirectory() as tmpdir:
        local_path = Path(tmpdir) / "checkpoint.pt"
        checkpoint_store.download(checkpoint_uri, local_path)
        # weights_only=True (unpickles only tensors/plain containers, never
        # arbitrary objects) -- every save site here is `torch.save(model
        # .state_dict(), ...)`, nothing else, so this is a pure hardening,
        # not a behaviour change: a checkpoint_uri traces back to this
        # repo's own S3/R2 bucket, but there is no reason to trust its
        # contents any more than that.
        return torch.load(local_path, map_location="cpu", weights_only=True)


def load_trained_model(name: str, version: ModelVersion, checkpoint_store: CheckpointStore):
    """Reconstruct ``name``'s real trained model from ``version``'s
    ``arch_params`` tag and ``checkpoint_uri`` -- a real, eval-mode
    ``nn.Module`` with real trained weights, ready for inference.

    Returns ``(model, spec)``, the same shape every ``build_<model>``
    itself returns. Works for all seven real architectures (Group 1 plus
    diffusion/fusion) via one shared path, since ``arch_params`` was
    deliberately recorded as exactly the kwargs each model's own
    ``build_<model>(...)`` call needs (#79) -- there is no per-model
    special-casing here, only the builder lookup itself.
    """
    torch = require_torch()
    builder = _builder(name)
    arch_params = _decode_arch_params(version, "arch_params")
    model, spec = builder(**arch_params)
    state_dict = _download_state_dict(
        version.checkpoint_uri, checkpoint_store, torch, label=f"{name} v{version.version}",
    )
    model.load_state_dict(state_dict)
    model.eval()
    return model, spec


def load_standardization_stats(version: ModelVersion) -> dict:
    """Real standardisation stats (`tracking.experiment_tracking
    .STANDARDIZATION_STAT_FIELDS`, whichever ``version`` actually
    carries) decoded back into real numpy arrays -- a real inference
    process needs the EXACT same mean/std training fit its inputs/
    targets with, to standardise a live input correctly and un-
    standardise a prediction back to real units. Empty dict for a
    version that predates this being persisted, or one (fusion) whose
    inputs/outputs are already absolute and were never standardised.
    """
    import numpy as np

    from ..tracking.experiment_tracking import STANDARDIZATION_STAT_FIELDS

    stats: dict[str, object] = {}
    for field_name in STANDARDIZATION_STAT_FIELDS:
        raw = version.tags.get(field_name)
        if raw is not None:
            stats[field_name] = np.array(json.loads(raw))
    return stats


def load_trained_pinn_candidate(version: ModelVersion, checkpoint_store: CheckpointStore):
    """PINN only: its candidate-generator LSTM, from the
    ``candidate_arch_params``/``candidate_checkpoint_uri`` tags (#80) --
    the second real model `models.pinn.PhysicsCorrector.encode` needs
    (``encode(environment, candidate)``), never persisted under its own
    registry entry since it isn't itself a registrable model."""
    torch = require_torch()
    from ..models.lstm import build_lstm

    arch_params = _decode_arch_params(version, "candidate_arch_params")
    model, spec = build_lstm(**arch_params)
    checkpoint_uri = version.tags.get("candidate_checkpoint_uri")
    state_dict = _download_state_dict(
        checkpoint_uri, checkpoint_store, torch, label=f"pinn v{version.version} candidate",
    )
    model.load_state_dict(state_dict)
    model.eval()
    return model, spec
