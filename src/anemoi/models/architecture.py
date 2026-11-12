"""What a model is made of, read from the model itself.

`describe` builds a model the way serving does -- ``build_<model>(**arch_params)``,
the registry's ``arch_params`` tag (#79) -- runs one input of the shape it is
really fed through it, and records every module: its type, its output shape,
its own and total parameter counts. The console's system view (`/models/system`)
draws from it, so the diagram is whatever the served version actually is, not a
drawing someone has to keep in step.

The input shapes follow training (`training.real_run*`): a ``SEQUENCE_LENGTH``
fix history for the track models, the 41x41 storm-centred crop (10 degrees at
0.25 degrees) for the gridded ones, that crop as a lattice of every
``GNN_STRIDE``-th cell for the GNN. Weights are left untrained -- shapes and
parameter counts don't depend on them.
"""

from __future__ import annotations

import importlib
import inspect
import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .base import require_torch

#: Models `describe` can build, in the order the system runs them.
DESCRIBABLE_MODELS: tuple[str, ...] = (
    "lstm", "cnn", "transformer", "gnn", "pinn", "fusion", "diffusion",
)

#: Fixes of storm history a track model sees (`training.capacity_ablation`).
SEQUENCE_LENGTH = 4
#: Side of the storm-centred gridded crop: 10 degrees at 0.25 degrees, inclusive.
GRID_CELLS = 41
#: Every this-many grid cells becomes a GNN node (`training.real_run_gnn`).
GNN_STRIDE = 4


@dataclass(slots=True)
class TensorInfo:
    name: str
    shape: list[int]


@dataclass(slots=True)
class LayerInfo:
    #: Dotted module path from the model's root ("" is the model itself).
    path: str
    type: str
    depth: int
    #: Shape of the first tensor the module returned; None if it never ran.
    output_shape: list[int] | None
    #: Parameters held directly by this module, and by it and everything in it.
    own_params: int
    total_params: int


@dataclass(slots=True)
class Architecture:
    model: str
    #: The kwargs the model was built with, after builder defaults are applied.
    arch_params: dict[str, Any]
    #: True when arch_params came from the builder's defaults, not a
    #: registered version (one registered before arch_params, or none).
    defaults: bool
    #: False for the GNN, whose leading dimension is graph nodes, not a batch.
    batched: bool
    input_dim: int
    latent_dim: int
    lead_hours: list[int]
    output_dim: int
    inputs: list[TensorInfo]
    outputs: list[TensorInfo]
    layers: list[LayerInfo]
    total_params: int
    trainable_params: int = field(default=0)


def _builder(name: str):
    if name not in DESCRIBABLE_MODELS:
        raise ValueError(f"unknown model {name!r}; expected one of {DESCRIBABLE_MODELS}")
    module = importlib.import_module(f"{__package__}.{name}")
    return getattr(module, f"build_{name}")


def resolved_params(name: str, arch_params: dict[str, Any] | None) -> dict[str, Any]:
    """``arch_params`` over the builder's own defaults: everything the model
    was built with, so the view can show values a version didn't record
    because they were the defaults."""
    params = {
        p.name: p.default
        for p in inspect.signature(_builder(name)).parameters.values()
        if p.default is not inspect.Parameter.empty
    }
    params.update(arch_params or {})
    return {k: list(v) if isinstance(v, tuple) else v for k, v in params.items()}


def _lattice(torch, rows: int, cols: int, node_features: int, edge_features: int):
    """The GNN's real input topology: 4-connected lattice, both directions,
    edge features (d_row, d_col, distance) -- `real_run_gnn`'s layout."""
    src, dst, attrs = [], [], []
    for r in range(rows):
        for c in range(cols):
            for dr, dc in ((0, 1), (1, 0)):
                r2, c2 = r + dr, c + dc
                if r2 < rows and c2 < cols:
                    a, b = r * cols + c, r2 * cols + c2
                    src += [a, b]
                    dst += [b, a]
                    attrs += [[dr, dc, 1.0], [-dr, -dc, 1.0]]
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    edge_attr = torch.tensor(attrs, dtype=torch.float32)[:, :edge_features]
    if edge_features > 3:
        edge_attr = torch.nn.functional.pad(edge_attr, (0, edge_features - 3))
    x = torch.randn(rows * cols, node_features)
    center = (rows // 2) * cols + cols // 2
    return x, edge_index, edge_attr, center


def _example_inputs(
    torch, name: str, params: dict[str, Any], spec
) -> tuple[list, dict, list[TensorInfo]]:
    """Positional args, keyword args, and their description, for one forward."""
    n_leads = len(spec.lead_hours)
    if name == "lstm":
        x = torch.randn(1, SEQUENCE_LENGTH, params["input_dim"])
        return [x], {}, [TensorInfo("track history", list(x.shape))]
    if name == "cnn":
        x = torch.randn(1, params["in_channels"], GRID_CELLS, GRID_CELLS)
        return [x], {}, [TensorInfo("gridded fields", list(x.shape))]
    if name == "transformer":
        rows, cols = params["grid_size"]
        x = torch.randn(1, params["n_variables"], rows, cols)
        return [x], {}, [TensorInfo("gridded fields", list(x.shape))]
    if name == "gnn":
        side = (GRID_CELLS - 1) // GNN_STRIDE + 1
        x, edge_index, edge_attr, center = _lattice(
            torch, side, side, params["node_features"], params["edge_features"]
        )
        return [x, edge_index, edge_attr], {"center_index": center}, [
            TensorInfo("node features", list(x.shape)),
            TensorInfo("edge index", list(edge_index.shape)),
            TensorInfo("edge features", list(edge_attr.shape)),
        ]
    if name == "pinn":
        env = torch.randn(1, params["input_dim"])
        candidate = torch.randn(1, n_leads, 3)
        return [env, candidate], {}, [
            TensorInfo("environment", list(env.shape)),
            TensorInfo("candidate forecast", list(candidate.shape)),
        ]
    if name == "fusion":
        preds = torch.randn(1, params["n_models"], n_leads, 3)
        context = torch.randn(1, params["context_dim"])
        return [preds, context], {}, [
            TensorInfo("member forecasts", list(preds.shape)),
            TensorInfo("context", list(context.shape)),
        ]
    if name == "diffusion":
        noisy = torch.randn(1, n_leads, 3)
        t = torch.zeros(1, dtype=torch.long)
        cond = torch.randn(1, spec.input_dim)
        return [noisy, t, cond], {}, [
            TensorInfo("noisy trajectory", list(noisy.shape)),
            TensorInfo("diffusion step", list(t.shape)),
            TensorInfo("conditioning", list(cond.shape)),
        ]
    raise ValueError(f"no example input for {name!r}")


def _first_tensor(torch, value):
    if isinstance(value, torch.Tensor):
        return value
    if isinstance(value, (tuple, list)):
        for item in value:
            found = _first_tensor(torch, item)
            if found is not None:
                return found
    return None


def _all_tensors(torch, value) -> list:
    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, (tuple, list)):
        return [t for item in value for t in _all_tensors(torch, item)]
    return []


def describe(name: str, arch_params: dict[str, Any] | None = None) -> Architecture:
    """Build ``name`` from ``arch_params`` (builder defaults when None or
    empty), run one example input through it, and describe every module."""
    torch = require_torch()
    params = resolved_params(name, arch_params)
    build_kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in params.items()}
    model, spec = _builder(name)(**build_kwargs)
    model.eval()

    shapes: dict[str, list[int]] = {}
    hooks = []
    for path, module in model.named_modules():
        def hook(_module, _inputs, output, path=path):
            tensor = _first_tensor(torch, output)
            if tensor is not None and path not in shapes:
                shapes[path] = list(tensor.shape)

        hooks.append(module.register_forward_hook(hook))

    args, kwargs, inputs = _example_inputs(torch, name, params, spec)
    try:
        with torch.no_grad():
            output = model(*args, **kwargs)
    finally:
        for h in hooks:
            h.remove()

    layers = []
    for path, module in model.named_modules():
        own = sum(p.numel() for p in module.parameters(recurse=False))
        total = sum(p.numel() for p in module.parameters())
        layers.append(
            LayerInfo(
                path=path,
                type=type(module).__name__,
                depth=0 if path == "" else path.count(".") + 1,
                output_shape=shapes.get(path),
                own_params=own,
                total_params=total,
            )
        )

    outputs = [TensorInfo(f"output {i}" if i else "output", list(t.shape))
               for i, t in enumerate(_all_tensors(torch, output))]
    return Architecture(
        model=name,
        arch_params=params,
        defaults=not arch_params,
        batched=name != "gnn",
        input_dim=spec.input_dim,
        latent_dim=spec.latent_dim,
        lead_hours=list(spec.lead_hours),
        output_dim=spec.output_dim,
        inputs=inputs,
        outputs=outputs,
        layers=layers,
        total_params=sum(p.numel() for p in model.parameters()),
        trainable_params=sum(p.numel() for p in model.parameters() if p.requires_grad),
    )


@lru_cache(maxsize=64)
def _describe_cached(name: str, arch_params_json: str) -> Architecture:
    return describe(name, json.loads(arch_params_json) or None)


def describe_cached(name: str, arch_params: dict[str, Any] | None) -> Architecture:
    """`describe`, memoised on the model and its exact params: a registered
    version never changes, and building the model costs up to a second."""
    return _describe_cached(name, json.dumps(arch_params or {}, sort_keys=True))
