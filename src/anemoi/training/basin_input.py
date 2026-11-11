"""The storm's basin as a model input (docs/multi_basin.md).

One model per architecture is trained on every basin. Their inputs are
deliberately position-free -- storm-relative motion, a storm-centred patch
of fields -- so nothing in them says which basin a storm is in, and what
differs between basins (the usual steering, the land, the climatology)
would have to be averaged over. Each Group 1 model therefore also takes a
one-hot of the basins it is trained on, appended to whatever it already
reads:

* a track sequence or a graph's node features: extra columns
  (`with_basin_columns`);
* a channel stack: extra constant channels (`with_basin_channels`);
* an environment vector: extra entries (`with_basin_vector`).

The fusion layer needs none: its context already carries the storm's
latitude and longitude.

``basins`` is always the tuple of basins a model's columns stand for, in
order. It is recorded on every registered version (`BASIN_INPUTS_TAG`) and
the same builders are used to train and to serve, so the two can't drift
apart. An empty tuple adds nothing: that is every version from before this
existed, whose inputs are built exactly as they always were. A storm from
a basin not in the tuple gets all zeros, never an error.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from ..data.atcf import storm_basin
from ..data.basins import TRAINING_BASINS

#: The basins a newly trained model's basin columns stand for: the ones
#: training reads (``curriculum.yaml`` ``data.basins``).
DEFAULT_BASIN_INPUTS: tuple[str, ...] = TRAINING_BASINS


def basin_one_hot(storm_id: str, basins: Sequence[str]) -> np.ndarray:
    """``(len(basins),)``: 1 where ``storm_id``'s basin is, else 0. A basin
    that isn't one of ``basins`` is all zeros."""
    basin = storm_basin(storm_id)
    return np.array([1.0 if b == basin else 0.0 for b in basins])


def with_basin_columns(x: np.ndarray, storm_id: str, basins: Sequence[str]) -> np.ndarray:
    """``x`` is ``(rows, features)`` -- a track sequence's steps, or a
    graph's nodes. Returns ``(rows, features + len(basins))``: the basin's
    one-hot repeated on every row."""
    if not basins:
        return x
    one_hot = basin_one_hot(storm_id, basins).astype(x.dtype)
    return np.concatenate([x, np.broadcast_to(one_hot, (x.shape[0], len(one_hot)))], axis=1)


def with_basin_channels(stack: np.ndarray, storm_id: str, basins: Sequence[str]) -> np.ndarray:
    """``stack`` is ``(channels, height, width)``. Returns ``(channels +
    len(basins), height, width)``: one constant channel per basin."""
    if not basins:
        return stack
    one_hot = basin_one_hot(storm_id, basins).astype(stack.dtype)
    planes = np.broadcast_to(one_hot[:, None, None], (len(one_hot), *stack.shape[1:]))
    return np.concatenate([stack, planes], axis=0)


def with_basin_vector(vector: np.ndarray, storm_id: str, basins: Sequence[str]) -> np.ndarray:
    """``vector`` is ``(features,)``. Returns ``(features + len(basins),)``."""
    if not basins:
        return vector
    return np.concatenate([vector, basin_one_hot(storm_id, basins).astype(vector.dtype)])
