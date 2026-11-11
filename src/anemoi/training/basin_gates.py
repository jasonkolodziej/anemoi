"""What a model has to show in each basin (docs/multi_basin.md).

One model per architecture is trained on every configured basin. Before a
basin's storms are treated as in distribution, the model has to beat
**persistence** there: the forecast that holds the storm's last 6-hour
motion and its current wind. It is the weakest forecast with any skill in
it, needs no fitting, and is computed here from the same validation storms
the model was scored on -- so "better than persistence" means the model
learnt something about that basin, not that the basin is easy.

`with_basin_baseline` adds the baseline to a run's validation metrics;
`basin_tags` turns them into the two registry tags the serving side reads
(`tracking.registry.ModelRegistry.verified_basins`):

* ``trained_basins`` -- the basins the run had training samples from. For
  a gridded model that is the basins whose fields were cached, not every
  basin in the storm archive.
* ``verified_basins`` -- of those, the ones where it beat persistence on
  the promotion metric (`training.promotion.PRIMARY_METRIC`).
"""

from __future__ import annotations

import numpy as np

from ..data.besttrack import Track
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..data.storm_relative import displacement_nm
from ..metrics.basin import (
    PERSISTENCE_PREFIX,
    key_basin,
    per_basin_scores,
    scored_basins,
    trained_basins,
    verified_basins,
)
from ..models.base import DEFAULT_LEADS
from ..tracking.experiment_tracking import TRAINED_BASINS_TAG, VERIFIED_BASINS_TAG
from .capacity_ablation import SEQUENCE_LENGTH
from .promotion import PRIMARY_METRIC, MetricSet
from .real_run import LEAD_STEPS, boundaries_for_tracks, displacements_to_absolute


def persistence_baseline(tracks: list[Track]) -> dict[str, float]:
    """Persistence's track and intensity error at each lead, for each basin
    in ``tracks``: ``{basin}/persistence_track_error_{lead}h_nm`` and
    ``{basin}/persistence_intensity_error_{lead}h_kt``.

    Scored on the windows `real_run.iter_stage_windows` gives a model --
    the same current fixes, the same targets -- but from the final track
    itself, with no working-track noise: the baseline gets slightly cleaner
    inputs than the model does, so it is, if anything, harder to beat.
    """
    n_leads = len(LEAD_STEPS)
    pred_rows: list[np.ndarray] = []
    obs_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat: list[float] = []
    base_lon: list[float] = []
    storm_ids: list[str] = []
    for track in tracks:
        fixes = track.fixes
        if len(fixes) < SEQUENCE_LENGTH + 1 + LEAD_STEPS[0]:
            continue
        for current_idx in range(SEQUENCE_LENGTH, len(fixes)):
            prev, current = fixes[current_idx - 1], fixes[current_idx]
            step_dx, step_dy = displacement_nm(prev, current)
            pred = np.zeros((n_leads, 3))
            obs = np.zeros((n_leads, 3))
            mask = np.zeros(n_leads, dtype=bool)
            for li, step in enumerate(LEAD_STEPS):
                target_idx = current_idx + step
                if target_idx >= len(fixes):
                    continue
                target = fixes[target_idx]
                dx, dy = displacement_nm(current, target)
                obs[li] = [dx, dy, target.max_wind_kt]
                pred[li] = [step_dx * step, step_dy * step, current.max_wind_kt]
                mask[li] = True
            if not mask.any():
                continue
            pred_rows.append(pred)
            obs_rows.append(obs)
            mask_rows.append(mask)
            base_lat.append(current.lat)
            base_lon.append(current.lon)
            storm_ids.append(track.storm_id)
    if not pred_rows:
        return {}
    lat = np.array(base_lat)[:, None]
    lon = np.array(base_lon)[:, None]
    return per_basin_scores(
        displacements_to_absolute(np.stack(pred_rows), lat, lon),
        displacements_to_absolute(np.stack(obs_rows), lat, lon),
        np.stack(mask_rows),
        storm_ids,
        DEFAULT_LEADS,
        prefix=PERSISTENCE_PREFIX,
    )


def validation_tracks(tracks: list[Track]) -> list[Track]:
    """The storms a promotion is decided on: the operational (Stage B)
    validation split of ``tracks`` -- the split every real runner's final
    stage validates on (`real_run.boundaries_for_tracks`)."""
    boundaries = boundaries_for_tracks(Flavor.GDAS_FINETUNE, tracks)
    return filter_tracks(tracks, assign_splits(tracks, boundaries), Split.VAL)


def with_basin_baseline(val_metrics: MetricSet, tracks: list[Track]) -> MetricSet:
    """``val_metrics`` plus the persistence baseline for every basin it
    scored, from the validation storms of ``tracks`` (the archive the run
    trained on). A run that scored no basin on its own is returned as is."""
    scored = scored_basins(val_metrics.values)
    if not scored:
        return val_metrics
    baseline = {
        key: value
        for key, value in persistence_baseline(validation_tracks(tracks)).items()
        if key_basin(key) in scored
    }
    return MetricSet(
        split=val_metrics.split, flavor=val_metrics.flavor,
        values={**val_metrics.values, **baseline},
    )


def basin_tags(val_metrics: MetricSet) -> dict[str, str]:
    """The registry tags saying which basins a version trained on and which
    it is verified in, from its validation metrics (after
    `with_basin_baseline`). Empty for a run that recorded no per-basin
    sample counts -- its tags are left to whatever else sets them."""
    trained = trained_basins(val_metrics.values)
    if trained is None:
        return {}
    verified = [b for b in verified_basins(val_metrics.values, PRIMARY_METRIC) if b in trained]
    return {
        TRAINED_BASINS_TAG: ",".join(trained),
        VERIFIED_BASINS_TAG: ",".join(verified),
    }
