"""Per-basin scores (docs/multi_basin.md).

One model per architecture is trained on every basin, so one overall
number can hide a basin it is poor in, and a number over a different mix of
basins isn't comparable with the last one. Every validation run therefore
also records, for each basin it has storms from:

* ``{basin}/track_error_{lead}h_nm`` and ``{basin}/intensity_error_{lead}h_kt``
  -- the same errors as the overall metrics, over that basin's storms only;
* ``{basin}/train_samples`` and ``{basin}/val_samples`` -- how many windows
  it trained and validated on there. A gridded model skips a window with no
  cached field, so a basin whose cache hasn't been fetched has none, and the
  model has not seen that basin whatever the storm archive holds;
* ``{basin}/persistence_track_error_{lead}h_nm`` (and intensity) -- what
  holding the storm's last motion and wind scores on the same storms
  (`training.basin_gates.persistence_baseline`).

A basin is **verified** for a model when it beats persistence there on the
primary metric (`verified_basins`). The keys use ``/`` so MLflow groups a
basin's metrics together, and so no overall metric name can collide with one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

from ..data.atcf import storm_basin
from .track import ForecastPoint, VerificationPair, verify

_SEP = "/"
PERSISTENCE_PREFIX = "persistence_"


def basin_key(basin: str, metric: str) -> str:
    """The metric name of ``metric`` over ``basin``'s storms alone."""
    return f"{basin}{_SEP}{metric}"


def is_basin_key(key: str) -> bool:
    return _SEP in key


def key_basin(key: str) -> str | None:
    """The basin a per-basin metric name is for; None for an overall one."""
    return key.split(_SEP, 1)[0] if is_basin_key(key) else None


def scored_basins(values: Mapping[str, float]) -> tuple[str, ...]:
    """The basins ``values`` holds any per-basin metric for, sorted."""
    return tuple(sorted({b for k in values if (b := key_basin(k)) is not None}))


def basin_value(values: Mapping[str, float], basin: str, metric: str) -> float | None:
    """``metric`` over ``basin`` alone, or None if it wasn't recorded."""
    return values.get(basin_key(basin, metric))


def absolute_pairs(
    pred_abs: np.ndarray,
    obs_abs: np.ndarray,
    mask: np.ndarray,
    lead_hours: Sequence[int],
) -> list[VerificationPair]:
    """One `VerificationPair` per unmasked (sample, lead): ``pred_abs`` and
    ``obs_abs`` are ``(n, n_leads, 3)`` absolute (lat, lon, wind_kt),
    ``mask`` is ``(n, n_leads)``."""
    pairs: list[VerificationPair] = []
    for si, li in zip(*np.nonzero(np.asarray(mask, dtype=bool)), strict=True):
        plat, plon, pwind = pred_abs[si, li]
        olat, olon, owind = obs_abs[si, li]
        pairs.append(
            VerificationPair(
                forecast=ForecastPoint(
                    lead_hours=lead_hours[li], lat=float(plat), lon=float(plon),
                    max_wind_kt=float(pwind),
                ),
                obs_lat=float(olat),
                obs_lon=float(olon),
                obs_wind_kt=float(owind),
            )
        )
    return pairs


def per_basin_scores(
    pred_abs: np.ndarray,
    obs_abs: np.ndarray,
    mask: np.ndarray,
    storm_ids: Sequence[str],
    lead_hours: Sequence[int],
    *,
    prefix: str = "",
) -> dict[str, float]:
    """Track and intensity error at each lead, for each basin ``storm_ids``
    (one per sample) come from. ``prefix`` names what was scored
    (`PERSISTENCE_PREFIX` for the baseline; nothing for the model)."""
    if len(storm_ids) != len(mask):
        raise ValueError(f"{len(storm_ids)} storm ids for {len(mask)} samples")
    basins = np.array([storm_basin(s) for s in storm_ids])
    out: dict[str, float] = {}
    for basin in sorted(set(basins.tolist())):
        sel = basins == basin
        stats = verify(absolute_pairs(pred_abs[sel], obs_abs[sel], mask[sel], lead_hours))
        for lead, s in stats.items():
            out[basin_key(basin, f"{prefix}track_error_{lead}h_nm")] = s.track_mae_nm
            out[basin_key(basin, f"{prefix}intensity_error_{lead}h_kt")] = s.intensity_mae_kt
    return out


def sample_counts(storm_ids: Sequence[str], split: str) -> dict[str, float]:
    """``{basin}/{split}_samples`` for each basin ``storm_ids`` come from."""
    counts: dict[str, float] = {}
    for storm_id in storm_ids:
        key = basin_key(storm_basin(storm_id), f"{split}_samples")
        counts[key] = counts.get(key, 0.0) + 1.0
    return counts


def trained_basins(values: Mapping[str, float]) -> tuple[str, ...] | None:
    """The basins a run had training samples from, sorted -- or None when
    it recorded no counts at all (a run from before they existed)."""
    counted = [
        b for b in scored_basins(values) if basin_value(values, b, "train_samples") is not None
    ]
    if not counted:
        return None
    return tuple(b for b in counted if (basin_value(values, b, "train_samples") or 0.0) > 0.0)


def verified_basins(values: Mapping[str, float], metric: str) -> tuple[str, ...]:
    """The basins where the model beats persistence on ``metric``, sorted.

    Both numbers must have been recorded and be finite: a basin with no
    validation storms, or no baseline, has shown nothing.
    """
    out = []
    for basin in scored_basins(values):
        model = basin_value(values, basin, metric)
        baseline = basin_value(values, basin, PERSISTENCE_PREFIX + metric)
        if model is None or baseline is None:
            continue
        if math.isfinite(model) and math.isfinite(baseline) and model < baseline:
            out.append(basin)
    return tuple(out)
