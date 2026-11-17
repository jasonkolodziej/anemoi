"""GFS's own forecast track as a prior the Group 1 models correct.

AVNI (NHC's interpolated GFS track: the previous run, shifted 6 h to the
cycle's own position) is available at every cycle the models serve, from
the same t−6 GFS run their steering features come from. Fusion trails it
by 100+ nm at 48 h (Decision Log 66, 68). So instead of predicting the
track from scratch, a model trained with a prior predicts its *correction*
to AVNI's track: its training target is the observed displacement minus
AVNI's, and its forecast is AVNI's displacement plus what it predicts.

Only the track is a prior. The wind column is left as the model's own
(the prior's wind entry is 0), so intensity is learnt as before.

A lead AVNI doesn't reach (it stops early for a storm it dissipates)
falls back to persistence for that lead, so every lead has a prior. A
window whose cycle has no AVNI row at all, or no AVNI position at the
first lead, has no prior and is dropped from training, and a live cycle
without one is skipped, as with the steering input. The prior applies in
Stage B only: Stage A's ERA5 years predate most a-decks, and Stage B
re-fits the output standardisation anyway.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

from ..data.atcf import Adeck
from ..geo import bearing_deg, haversine_nm
from ..models.base import DEFAULT_LEADS

#: The a-deck technique the prior is read from.
TRACK_PRIOR_TECHNIQUE = "AVNI"

PriorFn = Callable[[object], "np.ndarray | None"]


def _offset_nm(lat0: float, lon0: float, lat1: float, lon1: float) -> tuple[float, float]:
    distance = haversine_nm(lat0, lon0, lat1, lon1)
    theta = np.radians(bearing_deg(lat0, lon0, lat1, lon1))
    return float(distance * np.sin(theta)), float(distance * np.cos(theta))


def prior_from_adeck(
    adeck: Adeck | None,
    init_time: datetime,
    base_lat: float,
    base_lon: float,
    persistence: np.ndarray,
    lead_hours: Sequence[int] = DEFAULT_LEADS,
    technique: str = TRACK_PRIOR_TECHNIQUE,
) -> np.ndarray | None:
    """``(n_leads, 3)``: ``technique``'s displacement (dx east, dy north,
    nm) from ``(base_lat, base_lon)`` at each lead, a wind of 0, and
    ``persistence``'s displacement for a lead it has no position for.
    None when it has no position at the first lead of ``init_time``."""
    if adeck is None:
        return None
    first = adeck.get(technique, init_time, int(lead_hours[0]))
    if first is None or not first.has_position:
        return None
    prior = np.zeros((len(lead_hours), 3))
    for i, lead in enumerate(lead_hours):
        point = adeck.get(technique, init_time, int(lead))
        if point is not None and point.has_position:
            prior[i, 0], prior[i, 1] = _offset_nm(base_lat, base_lon, point.lat, point.lon)
        else:
            prior[i, 0], prior[i, 1] = persistence[i, 0], persistence[i, 1]
    return prior


def window_prior_fn(adecks: Mapping[str, Adeck]) -> PriorFn:
    """A `StageWindow` -> prior map over ``adecks`` (storm id -> a-deck)."""

    def prior(sw) -> np.ndarray | None:
        return prior_from_adeck(
            adecks.get(sw.storm_id), sw.current.valid_time,
            sw.current.lat, sw.current.lon, sw.persistence,
        )

    return prior


def load_adecks(adeck_dir: Path | str, storm_ids: Iterable[str]) -> dict[str, Adeck]:
    """The cached a-decks (`anemoi adeck-fetch`) of ``storm_ids``, AVNI only."""
    from ..data.adeck_source import read_cached_adecks

    return read_cached_adecks(adeck_dir, storm_ids, techniques=[TRACK_PRIOR_TECHNIQUE]).adecks


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
    """The technique a version's forecasts are corrections to (its
    ``arch_params``' ``track_prior``), or None for a version without one."""
    return (arch_params or {}).get("track_prior")


def curriculum_adecks(
    adeck_dir: Path | str | None, tracks: Iterable, *, streaming: bool,
) -> dict[str, Adeck] | None:
    """The a-decks a curriculum given ``adeck_dir`` reads its prior from
    (None without one): every storm in ``tracks`` the cache has."""
    if adeck_dir is None:
        return None
    if not streaming:
        raise ValueError("the track prior needs streaming=True")
    adecks = load_adecks(adeck_dir, [t.storm_id for t in tracks])
    if not adecks:
        raise ValueError(f"no a-deck for any storm in {adeck_dir}")
    return adecks


def prior_stage_kwargs(stage, adecks: Mapping[str, Adeck] | None) -> dict:
    """The ``prior_fn`` a model's streaming stage takes for one curriculum
    stage: Stage B's, from ``adecks``; nothing for Stage A (see the module
    docstring) or without a-decks."""
    from ..data.sources import Flavor

    if adecks is None or stage.flavor is Flavor.ERA5_PRETRAIN:
        return {}
    return {"prior_fn": window_prior_fn(adecks)}
