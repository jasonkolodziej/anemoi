"""Device selection for local (non-cloud) training runs.

MPS on Apple Silicon, then CUDA, then CPU. Exists because #9's capacity
ablation and #12's noise-sensitivity comparison (PLAN.md §5 "Sample size") are
small enough -- a few million parameters, ~10-15k samples -- to run entirely
on a local machine rather than rented GPU compute; see the "Checkpoint store"
section of the Storage and Versioning wiki page for the split between what
needs real GPU-hours (#22's full Stage A/B run) and what doesn't.

Torch is an optional dependency project-wide (``models.base.require_torch``),
so this module must stay importable without it -- the import is deferred into
each function rather than done at module scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import torch as _torch


def get_device() -> _torch.device:
    """Return the best available torch device: MPS, then CUDA, then CPU."""
    from ..models.base import require_torch

    torch = require_torch()
    if torch.backends.mps.is_available():
        print("Using MPS (Apple Silicon GPU).")
        return torch.device("mps")
    if torch.cuda.is_available():
        print("Using CUDA GPU.")
        return torch.device("cuda")
    print("Using CPU.")
    return torch.device("cpu")


def compile_model(model: Any, device: _torch.device) -> Any:
    """Wrap ``model`` in ``torch.compile`` where that's supported.

    ``torch.compile``'s default (Inductor) backend does not support the MPS
    device as of torch 2.14 -- compilation is skipped outright there rather
    than attempted and left to fail or silently fall back, so a slow first
    batch on a Mac doesn't look like a hang.
    """
    from ..models.base import require_torch

    torch = require_torch()
    if not isinstance(model, torch.nn.Module):
        raise TypeError(f"expected an nn.Module, got {type(model).__name__}")
    if device.type == "mps":
        print("torch.compile skipped: not supported on the MPS backend (torch 2.14)")
        return model
    if not hasattr(torch, "compile"):
        return model
    try:
        compiled = torch.compile(model, mode="reduce-overhead")
        print("torch.compile enabled (reduce-overhead mode)")
        return compiled
    except Exception as exc:  # noqa: BLE001 - compilation is an optimisation, never load-bearing
        print(f"torch.compile skipped: {exc}")
        return model
