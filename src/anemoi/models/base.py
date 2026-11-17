"""Shared plumbing for the torch-backed model implementations.

Torch is an optional dependency (``pip install anemoi[torch]``). The
operational layers -- scheduling, availability, curriculum, promotion, metrics --
carry the v2.1 policy and must remain importable and testable without it, so the
import is deferred and failure is a clear message rather than a stack trace at
module load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_TORCH_HINT = (
    "torch is required for model construction; install the optional extra:\n"
    "    uv sync --extra torch"
)


def require_torch() -> Any:
    """Import torch or raise a message that says how to get it."""
    try:
        import torch  # noqa: PLC0415
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise ModuleNotFoundError(_TORCH_HINT) from exc
    return torch


def torch_available() -> bool:
    try:
        import torch  # noqa: F401, PLC0415

        return True
    except ModuleNotFoundError:
        return False


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Architecture-independent description of a model's I/O contract.

    Carried alongside every model so the fusion layer and the latent extractor
    can be written against the contract rather than against each architecture.
    """

    name: str
    input_dim: int
    latent_dim: int
    #: Forecast lead times the head emits, in hours.
    lead_hours: tuple[int, ...]
    #: Outputs per lead time: (delta_lat, delta_lon, wind).
    outputs_per_lead: int = 3

    @property
    def output_dim(self) -> int:
        return len(self.lead_hours) * self.outputs_per_lead


DEFAULT_LEADS: tuple[int, ...] = (12, 24, 36, 48, 72, 96, 120)

#: ``arch_params`` keys that record how a version was trained or what its
#: output means, not how its network is built, so they are never passed to
#: ``build_<model>``. ``track_prior``: the forecast technique the version's
#: output is a correction to (`training.track_prior`).
NON_BUILD_ARCH_PARAMS: frozenset[str] = frozenset({"track_prior"})


def build_kwargs(arch_params: dict) -> dict:
    """``arch_params`` without `NON_BUILD_ARCH_PARAMS`: what ``build_<model>`` takes."""
    return {k: v for k, v in arch_params.items() if k not in NON_BUILD_ARCH_PARAMS}


def extra_input_conv(base, n_extra: int):
    """A conv that takes ``n_extra`` more input channels than ``base`` (an
    ``nn.Conv2d``), through a separate zero-initialised, bias-free conv of
    the same geometry (``.extra``: kernel, stride, padding), added to
    ``base``'s output. It computes ``base``'s function until ``.extra``
    trains, so it can sit in a model whose other weights a stage freezes
    (the forecast-lead steering input, Decision Log 68)."""
    torch = require_torch()
    nn = torch.nn

    class _ExtraInputConv(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.base = base
            self.extra = nn.Conv2d(
                n_extra, base.out_channels, kernel_size=base.kernel_size,
                stride=base.stride, padding=base.padding, bias=False,
            )
            nn.init.zeros_(self.extra.weight)
            self.extra.to(base.weight.device)
            self.in_channels = base.in_channels + n_extra
            self.out_channels = base.out_channels

        def forward(self, x):
            c = self.base.in_channels
            return self.base(x[:, :c]) + self.extra(x[:, c:])

    return _ExtraInputConv()


def extra_input_linear(base, n_extra: int):
    """`extra_input_conv` for an ``nn.Linear``: ``n_extra`` more input
    features, read from the end of the input through a zero-initialised,
    bias-free ``.extra``."""
    torch = require_torch()
    nn = torch.nn

    class _ExtraInputLinear(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.base = base
            self.extra = nn.Linear(n_extra, base.out_features, bias=False)
            nn.init.zeros_(self.extra.weight)
            self.extra.to(base.weight.device)
            self.in_features = base.in_features + n_extra
            self.out_features = base.out_features

        def forward(self, x):
            c = self.base.in_features
            return self.base(x[..., :c]) + self.extra(x[..., c:])

    return _ExtraInputLinear()
