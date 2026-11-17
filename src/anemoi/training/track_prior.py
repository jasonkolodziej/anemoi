"""GFS's own forecast track as a prior the Group 1 models correct.

A cycle reads the GFS run of 6 h before. `data.gfs_track` follows the storm
through that run's forecast fields; shifted so it starts at the cycle's
current fix (what NHC's interpolator does to make AVNI from the same run),
that track is the prior. A model trained with it predicts its *correction*:
its training target is the observed displacement minus the prior's, and its
forecast is the prior's displacement plus what it predicts.

The prior is computed from fields Anemoi fetches itself, the same way in
training (the ``anemoi gfs-track-cache`` cache) and in serving
(`real_inference_live.fetch_live_track_prior`). The first version of this
module read AVNI from NHC's a-decks instead. Those rows are written after
the cycle and are verification only (Decision Log 66), so a version trained
that way (``track_prior: "AVNI"``) is refused everywhere a forecast is made
from it (`unservable_reason`).

Only the track is a prior. The wind column is left as the model's own (the
prior's wind entry is 0), so intensity is learnt as before.

A lead GFS has lost the storm by falls back to persistence for that lead,
so every lead has a prior. A window whose cycle has no tracked position at
the valid time or at the first lead has no prior and is dropped from
training, and a live cycle without one skips the model, as with the
steering input. The prior applies in Stage B only: Stage A's ERA5 years
have no GFS forecasts, and Stage B re-fits the output standardisation
anyway.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

from ..data.gfs_track import TRACK_LEADS_H, cached_track, gfs_track_meta, require_meta
from ..geo import bearing_deg, haversine_nm
from ..models.base import DEFAULT_LEADS

#: ``arch_params["track_prior"]`` of a version trained on this prior.
TRACK_PRIOR_NAME = "gfs_track"
#: ``arch_params`` key holding `data.gfs_track.gfs_track_meta` as trained.
TRACK_PRIOR_INPUTS = "track_prior_inputs"

PriorFn = Callable[[object], "np.ndarray | None"]


def _offset_nm(lat0: float, lon0: float, lat1: float, lon1: float) -> tuple[float, float]:
    distance = haversine_nm(lat0, lon0, lat1, lon1)
    theta = np.radians(bearing_deg(lat0, lon0, lat1, lon1))
    return float(distance * np.sin(theta)), float(distance * np.cos(theta))


def prior_from_track(
    positions: np.ndarray | None,
    base_lat: float,
    base_lon: float,
    persistence: np.ndarray,
    lead_hours: Sequence[int] = DEFAULT_LEADS,
) -> np.ndarray | None:
    """``(n_leads, 3)``: the tracked storm's displacement (dx east, dy
    north, nm) at each lead, as from ``(base_lat, base_lon)``; a wind of 0;
    and ``persistence``'s displacement for a lead the track doesn't reach.

    ``positions`` is `data.gfs_track`'s ``(len(TRACK_LEADS_H), 2)`` (lat,
    lon). The track is shifted so its position at the cycle's valid time is
    the base fix. None when it has no position then or at the first lead.
    """
    if positions is None:
        return None
    at = {lead: i for i, lead in enumerate(TRACK_LEADS_H)}
    start = positions[at[0]]
    first = positions[at[int(lead_hours[0])]]
    if not (np.isfinite(start).all() and np.isfinite(first).all()):
        return None
    prior = np.zeros((len(lead_hours), 3))
    for i, lead in enumerate(lead_hours):
        pos = positions[at[int(lead)]]
        if np.isfinite(pos).all():
            prior[i, 0], prior[i, 1] = _offset_nm(
                base_lat, base_lon,
                base_lat + (pos[0] - start[0]), base_lon + (pos[1] - start[1]),
            )
        else:
            prior[i, 0], prior[i, 1] = persistence[i, 0], persistence[i, 1]
    return prior


def window_prior_fn(gfs_track_dir: Path | str) -> PriorFn:
    """A `StageWindow` -> prior map over the GFS track cache."""

    def prior(sw) -> np.ndarray | None:
        return prior_from_track(
            cached_track(gfs_track_dir, sw.storm_id, sw.current.valid_time),
            sw.current.lat, sw.current.lon, sw.persistence,
        )

    return prior


def split_by_prior(
    windows: Iterable, prior_fn: PriorFn,
) -> tuple[list, list, dict[tuple[str, datetime], np.ndarray]]:
    """The windows ``prior_fn`` has a prior for, those same windows with the
    prior subtracted from their targets (what the model trains on), and the
    priors by (storm, valid time). A window without a prior is dropped."""
    kept: list = []
    residual: list = []
    priors: dict[tuple[str, datetime], np.ndarray] = {}
    for sw in windows:
        prior = prior_fn(sw)
        if prior is None:
            continue
        priors[(sw.storm_id, sw.current.valid_time)] = prior
        kept.append(sw)
        residual.append(replace(sw, y=sw.y - prior))
    return kept, residual, priors


def add_priors(
    pred: np.ndarray, windows: Sequence, priors: Mapping[tuple[str, datetime], np.ndarray],
) -> np.ndarray:
    """``pred`` ``(n, n_leads, 3)``, a model's corrections for ``windows`` in
    order, as forecasts: each window's prior added back."""
    if not len(windows):
        return pred
    stacked = np.stack([priors[(sw.storm_id, sw.current.valid_time)] for sw in windows])
    return pred + stacked


def prior_name(arch_params: dict | None) -> str | None:
    """What a version's forecasts are corrections to (its ``arch_params``'
    ``track_prior``), or None for a version without a prior."""
    return (arch_params or {}).get("track_prior")


def prior_arch_params() -> dict:
    """The ``arch_params`` entries a version trained on the prior records."""
    return {"track_prior": TRACK_PRIOR_NAME, TRACK_PRIOR_INPUTS: gfs_track_meta()}


def unservable_reason(arch_params: dict | None) -> str | None:
    """Why a version's forecast can't be made, or None when it can: it has
    no prior, or its prior is this build's GFS track with the settings it
    was trained on."""
    name = prior_name(arch_params)
    if name is None:
        return None
    if name != TRACK_PRIOR_NAME:
        return (
            f"trained to correct {name!r} read from NHC's a-decks, which are written after "
            "the cycle and are verification only (Decision Log 66); retrain on the GFS "
            "track prior (anemoi train --gfs-track-dir)"
        )
    if (arch_params or {}).get(TRACK_PRIOR_INPUTS) != gfs_track_meta():
        return (
            "trained on a GFS track computed with other settings than this build's "
            "(data.gfs_track.gfs_track_meta); retrain or serve a matching build"
        )
    return None


def curriculum_prior(gfs_track_dir: Path | str | None, *, streaming: bool) -> Path | None:
    """The GFS track cache a curriculum given ``gfs_track_dir`` reads its
    prior from (None without one). Checks the cache records this build's
    tracker settings, since the version's ``arch_params`` will record them."""
    if gfs_track_dir is None:
        return None
    if not streaming:
        raise ValueError("the track prior needs streaming=True")
    require_meta(gfs_track_dir)
    return Path(gfs_track_dir)


def prior_stage_kwargs(stage, gfs_track_dir: Path | str | None) -> dict:
    """The ``prior_fn`` a model's streaming stage takes for one curriculum
    stage: Stage B's, from the cache; nothing for Stage A (see the module
    docstring) or without a cache."""
    from ..data.sources import Flavor

    if gfs_track_dir is None or stage.flavor is Flavor.ERA5_PRETRAIN:
        return {}
    return {"prior_fn": window_prior_fn(gfs_track_dir)}
