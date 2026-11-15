"""Forecast-lead GFS steering as a Group 1 input (Decision Log 68).

What the gridded models (Transformer, CNN, GNN, PINN) share when they read
`data.steering`'s features: the window filter that drops a window without
them, the constant channels or columns that carry them, the unfreezing of
the steering path after a stage's own freezing, and the per-stage feed
(zeros on ERA5 years, which have no GFS forecasts, so the zero-initialised
path stays at zero; the cached features on GDAS years, training the path).

Each model's steering path is its own zero-initialised, bias-free layer
beside the layer that reads the input (`models.base.extra_input_conv`,
`extra_input_linear`), named by :data:`STEERING_PARAMS`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from pathlib import Path

import numpy as np

from ..data.sources import Flavor

#: Parameter-name prefixes of each model's steering path: what Stage B
#: trains outside the model's head when it reads steering.
STEERING_PARAMS: dict[str, tuple[str, ...]] = {
    "transformer": ("patch.extra.",),
    "cnn": ("blocks.0.conv1.extra.", "blocks.0.skip.extra."),
    "gnn": ("embed.extra.",),
    "pinn": ("trunk.0.extra.",),
}

#: The models that can read steering: every Group 1 model with gridded
#: inputs. The LSTM reads the track alone.
STEERING_MODELS = tuple(STEERING_PARAMS)

ExtraX = Callable[[object], "np.ndarray | None"]


def n_steering_of(arch_params: dict | None) -> int:
    """How many steering features a version reads: its ``arch_params``'
    ``n_steering`` (0 for every version from before the steering input)."""
    return int((arch_params or {}).get("n_steering", 0))


def with_constant_channels(stack: np.ndarray, vec: np.ndarray | None) -> np.ndarray:
    """``stack`` (C, H, W) with one constant channel per entry of ``vec``
    appended; ``stack`` itself for ``None`` or an empty vector."""
    if vec is None or np.size(vec) == 0:
        return stack
    vec = np.asarray(vec, dtype=np.float64).reshape(-1)
    const = np.broadcast_to(vec[:, None, None], (vec.size, *stack.shape[1:]))
    return np.concatenate([stack, const.astype(stack.dtype)], axis=0)


def with_constant_columns(nodes: np.ndarray, vec: np.ndarray | None) -> np.ndarray:
    """``nodes`` (n_nodes, F) with ``vec`` appended to every row; ``nodes``
    itself for ``None`` or an empty vector."""
    if vec is None or np.size(vec) == 0:
        return nodes
    vec = np.asarray(vec, dtype=np.float64).reshape(-1)
    const = np.broadcast_to(vec[None, :], (nodes.shape[0], vec.size))
    return np.concatenate([nodes, const.astype(nodes.dtype)], axis=1)


def with_trailing(env: np.ndarray, vec: np.ndarray | None) -> np.ndarray:
    """A flat vector ``env`` with ``vec`` appended; ``env`` itself for
    ``None`` or an empty vector."""
    if vec is None or np.size(vec) == 0:
        return env
    return np.concatenate([env, np.asarray(vec, dtype=env.dtype).reshape(-1)])


def keep_with_extra(
    windows: Iterable, extra_x: ExtraX,
) -> tuple[list, dict[tuple[str, datetime], np.ndarray]]:
    """The windows ``extra_x`` has a vector for, and those vectors by
    (storm, valid time). A window it maps to ``None`` is dropped; a
    zero-length vector keeps the window and adds nothing."""
    kept: list = []
    extras: dict[tuple[str, datetime], np.ndarray] = {}
    for sw in windows:
        vec = extra_x(sw)
        if vec is None:
            continue
        extras[(sw.storm_id, sw.current.valid_time)] = np.asarray(vec, dtype=np.float64).reshape(-1)
        kept.append(sw)
    return kept, extras


def unfreeze(model, prefixes: Sequence[str]) -> None:
    """Make the parameters under ``prefixes`` trainable, after a stage's
    own freezing. Raises if none match: a steering path that isn't there
    would otherwise train nothing, silently."""
    if not prefixes:
        return
    matched = False
    for name, param in model.named_parameters():
        if name.startswith(tuple(prefixes)):
            param.requires_grad = True
            matched = True
    if not matched:
        raise ValueError(f"no parameter starts with any of {tuple(prefixes)}")


def steering_n(steering_cache_dir: Path | str | None, *, streaming: bool) -> int:
    """How many steering features a curriculum given ``steering_cache_dir``
    trains its model to read (0 without one). Checks the cache records this
    build's settings, since the version's tag will record them."""
    from ..data.steering import STEERING_DIM, require_meta

    if steering_cache_dir is None:
        return 0
    if not streaming:
        raise ValueError("the steering input needs streaming=True")
    require_meta(steering_cache_dir)
    return STEERING_DIM


def steering_stage_kwargs(
    model_name: str, stage, steering_cache_dir: Path | str | None, n_steering: int,
) -> dict:
    """The ``extra_x``/``trainable`` a model's streaming stage takes for
    one curriculum stage: zeros on ERA5 years (no GFS forecasts there; the
    zero-initialised path then gets no gradient and stays at zero), and on
    GDAS years each window's cached features, dropping a window without
    them, with the steering path trained besides the stage's own policy."""
    from ..data.steering import steering_vector

    if not n_steering:
        return {}
    if stage.flavor is Flavor.ERA5_PRETRAIN:
        zeros = np.zeros(n_steering)
        return {"extra_x": lambda sw: zeros}
    return {
        "extra_x": lambda sw: steering_vector(
            steering_cache_dir, sw.storm_id, sw.current.valid_time,
        ),
        "trainable": STEERING_PARAMS[model_name],
    }
