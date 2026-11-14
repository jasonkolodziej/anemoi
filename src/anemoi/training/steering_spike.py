"""The steering-along-track spike (docs/skill_gap_plan.md Phase 1, step 2).

Question: does the transformer's Atlantic 48 h track error move toward the
70 nm gate when it also sees how the GFS steering flow evolves over the next
48 h (`data.steering`)? Answered as a controlled comparison, not against a
registered version:

* **One Stage A.** ERA5 pretraining runs once, as in
  `real_run_transformer.run_transformer_curriculum`.
* **Two Stage B arms from the same weights.** ``baseline`` fine-tunes on the
  usual channels; ``steering`` adds `data.steering`'s features as constant
  channels (`train_transformer_stage_streaming`'s ``extra_x``) through their
  own zero-initialised conv (`expand_patch_channels`), so both arms start as
  the same function. Stage B's freezing (everything outside ``head.``)
  applies to both; the steering conv is the one addition left trainable.
  Both see the same windows (those with steering), the same window draw and,
  reseeded after the model is built, the same batch order.
* **Replicates.** Each seed in ``seeds`` runs both arms; the baseline's
  spread across seeds is the run-to-run noise a difference has to clear.
* **Nothing is registered.** No registry is touched and checkpoints aren't
  uploaded: a spike must not change what is served.

The report gives, per basin and replicate, both arms' mean 48 h track error
on the validation windows and the paired difference (steering minus
baseline) with a storm-block bootstrap interval (`metrics.homogeneous`).
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..data.besttrack import Track
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..data.steering import STEERING_DIM, steering_vector
from ..geo import haversine_nm
from ..metrics.homogeneous import storm_block_interval
from ..models.base import DEFAULT_LEADS, require_torch
from ..models.transformer import STEERING_PARAM_PREFIX
from .basin_input import DEFAULT_BASIN_INPUTS
from .curriculum import Curriculum
from .real_run import StageWindow, boundaries_for_tracks, displacements_to_absolute
from .real_run_transformer import (
    GRID_SIZE,
    TRANSFORMER_FIELD_NAMES,
    train_transformer_stage_streaming,
)

#: The lead the exit rule judges (the 70 nm gate).
GATE_LEAD_H = 48
#: Fewer storms than this in a basin's validation set: means only, as in
#: `metrics.homogeneous`.
MIN_STORMS_FOR_INTERVAL = 8


#: Parameter prefix of the steering input path (`expand_patch_channels`),
#: trained in Stage B while the stage's freezing policy holds elsewhere.
STEERING_PARAMS = STEERING_PARAM_PREFIX


def expand_patch_channels(model, n_extra: int):
    """Replace ``model.patch`` (the transformer's patch embedding) with one
    that takes ``n_extra`` more input channels through a separate,
    zero-initialised, bias-free conv (``patch.extra``), added to the
    original's output. The model computes the same function until
    ``patch.extra`` trains, and Stage B's freezing of the original weights
    (everything outside ``head.``) is untouched: the caller unfreezes
    :data:`STEERING_PARAMS` alone."""
    from ..models.transformer import extra_channel_patch

    model.patch = extra_channel_patch(model.patch, n_extra)
    return model


def track_errors_nm(
    windows: Sequence[StageWindow], pred: np.ndarray, lead_h: int = GATE_LEAD_H,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-window great-circle track error at ``lead_h`` (NaN where the window
    has no target there), and the windows' storm ids."""
    li = DEFAULT_LEADS.index(lead_h)
    base_lat = np.array([sw.current.lat for sw in windows])
    base_lon = np.array([sw.current.lon for sw in windows])
    obs = np.stack([sw.y for sw in windows])
    mask = np.stack([sw.mask for sw in windows])[:, li]
    p = displacements_to_absolute(pred[:, li], base_lat, base_lon)
    o = displacements_to_absolute(obs[:, li], base_lat, base_lon)
    err = np.asarray(haversine_nm(p[:, 0], p[:, 1], o[:, 0], o[:, 1]), dtype=float)
    err[~mask] = np.nan
    return err, np.array([sw.storm_id for sw in windows])


@dataclass
class ArmResult:
    arm: str
    seed: int
    keys: list[tuple[str, str]]  # (storm_id, valid time) per validation window
    errors: np.ndarray
    storm_ids: np.ndarray
    val_loss: float


def compare(
    base: ArmResult, other: ArmResult, *, basins: Sequence[str] = ("AL", "EP", "CP"),
) -> dict:
    """Per basin: both arms' mean error and the paired difference (other
    minus base) on the windows both have a 48 h target for."""
    if base.keys != other.keys:
        raise ValueError("the two arms were validated on different windows")
    out: dict[str, dict] = {}
    for basin in basins:
        sel = (np.char.startswith(base.storm_ids.astype(str), basin)
               & np.isfinite(base.errors) & np.isfinite(other.errors))
        n = int(sel.sum())
        storms = base.storm_ids[sel]
        n_storms = len(set(storms.tolist()))
        if n == 0:
            out[basin] = {"n_cases": 0, "n_storms": 0}
            continue
        diff = other.errors[sel] - base.errors[sel]
        ci = (list(storm_block_interval(storms, diff))
              if n_storms >= MIN_STORMS_FOR_INTERVAL else None)
        out[basin] = {
            "n_cases": n,
            "n_storms": n_storms,
            f"{base.arm}_mean_nm": float(base.errors[sel].mean()),
            f"{other.arm}_mean_nm": float(other.errors[sel].mean()),
            "mean_diff_nm": float(diff.mean()),
            "ci95": ci,
            "beat_rate": float((diff < 0).mean()),
        }
    return out


def run_steering_spike(
    tracks: list[Track],
    era5_cache_dir: Path | str,
    gdas_cache_dir: Path | str,
    steering_cache_dir: Path | str,
    *,
    seeds: Sequence[int] = (20260806,),
    n_augment: int = 3,
    batch_size: int = 16,
    num_workers: int = 0,
    d_model: int = 256,
    dropout: float = 0.1,
    basins: Sequence[str] | None = None,
    curriculum_kwargs: dict | None = None,
    device=None,
    log=print,
) -> dict:
    """Stage A once (from ``seeds[0]``), then both Stage B arms per seed. See
    the module docstring."""
    from ..models.transformer import build_transformer

    torch = require_torch()
    if not seeds:
        raise ValueError("at least one seed")
    basins = DEFAULT_BASIN_INPUTS if basins is None else tuple(basins)
    curriculum = Curriculum.standard("transformer", **(curriculum_kwargs or {}))
    stage_a, stage_b = curriculum.stages
    if stage_a.flavor is not Flavor.ERA5_PRETRAIN or stage_b.flavor is not Flavor.GDAS_FINETUNE:
        raise ValueError("expected the standard ERA5 -> GDAS curriculum")

    def split(stage):
        assignment = assign_splits(tracks, boundaries_for_tracks(stage.flavor, tracks))
        return (filter_tracks(tracks, assignment, Split.TRAIN),
                filter_tracks(tracks, assignment, Split.VAL))

    rng = np.random.default_rng(seeds[0])
    torch.manual_seed(seeds[0])
    model, _spec = build_transformer(
        n_variables=len(TRANSFORMER_FIELD_NAMES) + len(basins), grid_size=GRID_SIZE,
        d_model=d_model, dropout=dropout, lead_hours=DEFAULT_LEADS,
    )
    a_train, a_val = split(stage_a)
    log(f"stage A: {len(a_train)} train / {len(a_val)} val storms")
    model, _tl, a_val_loss, _m, _stats = train_transformer_stage_streaming(
        model, stage_a, a_train, a_val, era5_cache_dir, rng,
        n_augment=n_augment, batch_size=batch_size, num_workers=num_workers,
        device=device, basins=basins,
    )
    log(f"stage A done: val loss {a_val_loss:.4f}")
    after_a = copy.deepcopy(model.state_dict())

    b_train, b_val = split(stage_b)

    def has_steering(sw):
        return steering_vector(steering_cache_dir, sw.storm_id, sw.current.valid_time)

    arms = {
        "baseline": lambda sw: None if has_steering(sw) is None else np.zeros(0),
        "steering": has_steering,
    }

    results: list[ArmResult] = []
    for seed in seeds:
        for arm, extra in arms.items():
            rng_b = np.random.default_rng(seed)
            torch.manual_seed(seed)
            arm_model, _ = build_transformer(
                n_variables=len(TRANSFORMER_FIELD_NAMES) + len(basins), grid_size=GRID_SIZE,
                d_model=d_model, dropout=dropout, lead_hours=DEFAULT_LEADS,
            )
            arm_model.load_state_dict(after_a)
            if arm == "steering":
                expand_patch_channels(arm_model, STEERING_DIM)
            # Building the steering conv draws from torch's global RNG, which
            # the DataLoader shuffles with: reseed so both arms see the same
            # batch order.
            torch.manual_seed(seed)
            captured: dict = {}

            def keep(windows, pred, captured=captured):
                captured["windows"], captured["pred"] = windows, pred

            arm_model, _tl, val_loss, _m, _stats = train_transformer_stage_streaming(
                arm_model, stage_b, b_train, b_val, gdas_cache_dir, rng_b,
                n_augment=n_augment, batch_size=batch_size, num_workers=num_workers,
                device=device, basins=basins, extra_x=extra, on_validation=keep,
                trainable=(STEERING_PARAMS,) if arm == "steering" else (),
            )
            if arm == "steering":
                moved = float(arm_model.patch.extra.weight.detach().abs().sum())
                log(f"seed {seed} steering: |patch.extra| = {moved:.4g} after Stage B")
            errors, storm_ids = track_errors_nm(captured["windows"], captured["pred"])
            keys = [(sw.storm_id, sw.current.valid_time.isoformat()) for sw in captured["windows"]]
            results.append(ArmResult(arm, seed, keys, errors, storm_ids, float(val_loss)))
            log(f"seed {seed} {arm}: val loss {val_loss:.4f}, "
                f"48 h mean {np.nanmean(errors):.1f} nm on {np.isfinite(errors).sum()} windows")

    by = {(r.arm, r.seed): r for r in results}
    report = {
        "kind": "steering_spike",
        "question": "does forecast-lead GFS steering along an advected track move 48 h error "
                    "toward the 70 nm gate (docs/skill_gap_plan.md Phase 1, step 2)",
        "gate_lead_h": GATE_LEAD_H,
        "seeds": list(seeds),
        "n_augment": n_augment,
        "steering_dim": STEERING_DIM,
        "stage_a_val_loss": float(a_val_loss),
        "arms": [{"arm": r.arm, "seed": r.seed, "val_loss": r.val_loss,
                  "n_val_windows": len(r.keys),
                  "mean_48h_nm": float(np.nanmean(r.errors))} for r in results],
        "steering_minus_baseline": {
            str(seed): compare(by[("baseline", seed)], by[("steering", seed)]) for seed in seeds
        },
    }
    if len(seeds) > 1:
        report["baseline_seed_noise"] = {
            f"{seeds[i + 1]}_minus_{seeds[0]}": compare(
                by[("baseline", seeds[0])],
                _renamed(by[("baseline", seeds[i + 1])], "baseline_other_seed"),
            )
            for i in range(len(seeds) - 1)
        }
    return report


def _renamed(result: ArmResult, arm: str) -> ArmResult:
    return ArmResult(arm, result.seed, result.keys, result.errors, result.storm_ids,
                     result.val_loss)
