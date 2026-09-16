"""Stage B noise-emulator sensitivity (#12; PLAN.md §5 "Noise-emulator
recalibration is a prerequisite, not a refinement").

No trained Stage A checkpoint exists yet (#22), so "Stage B fine-tuning" here
is the same honest substitute #9 used for the capacity question: a
track-only LSTM trained from scratch on storm-relative sequences, reusing
``training.capacity_ablation.build_samples``/``train_cell`` directly rather
than a from-scratch reimplementation. What's varied is the one thing this
issue is about -- which :class:`~anemoi.data.besttrack.WorkingTrackNoise` the
*training* input is emulated with -- while every other run is held fixed
using ``training.capacity_ablation``'s own go/no-go capacity finding
(``docs/capacity_ablation.md``: capacity keeps helping through hidden_dim=128,
so a mid/high capacity is used here rather than risking capacity itself
confounding the noise comparison).

The comparison holds *evaluation* noise fixed at
``WorkingTrackNoise.from_literature()`` for both runs -- the better-evidenced
of the two candidates (Torn and Snyder 2012), standing in for real paired
data until it exists -- and varies only the *training* input noise between
the scope's defaults and the literature values. That isolates the question
the issue asks: does the training-time noise assumption change fine-tuned
performance against the best available estimate of real conditions, not
"which noise level produces a lower loss when train and eval share it."

Known structural gap, not closed here (documented per the issue's own "at
minimum as a follow-up"): both noise candidates are a single scalar RMS.
Torn and Snyder (2012) report intensity-*dependent* error -- position
uncertainty falls with intensity while intensity uncertainty rises -- which
neither candidate can express. A real fix replaces
:class:`~anemoi.data.besttrack.WorkingTrackNoise` with something keyed on
category (e.g. a small table of RMS values by Saffir-Simpson bin, or a
regression against wind speed) rather than one constant; that is a
``besttrack`` module change, not something this sensitivity comparison can
retrofit, and needs real paired data to fit against regardless.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise
from ..data.splits import DEFAULT_BOUNDARIES, Split, assign_splits, filter_tracks
from .capacity_ablation import build_samples, train_cell

#: Informed by docs/capacity_ablation.md: val loss keeps improving through
#: 128 with no sign of flattening, so a capacity where the #9 ablation found
#: headroom is used here -- a smaller capacity risks the *capacity* gap
#: swamping the *noise* gap this comparison is trying to isolate.
DEFAULT_HIDDEN_DIM = 64


@dataclass(frozen=True, slots=True)
class NoiseSensitivityResult:
    noise_label: str
    position_rms_nm: float
    intensity_rms_kt: float
    pressure_rms_mb: float
    final_train_loss: float
    final_val_loss: float


@dataclass(frozen=True, slots=True)
class NoiseSensitivityReport:
    default: NoiseSensitivityResult
    literature: NoiseSensitivityResult

    @property
    def relative_change(self) -> float:
        """Fractional change in val loss, defaults -> literature noise."""
        if self.default.final_val_loss <= 0:
            raise ValueError("default val loss must be positive to compute a relative change")
        return (
            self.literature.final_val_loss - self.default.final_val_loss
        ) / self.default.final_val_loss

    def is_load_bearing(self, *, threshold: float = 0.05) -> bool:
        """True if the noise assumption moves val loss by more than ``threshold``."""
        return abs(self.relative_change) > threshold

    def recommend(self, *, threshold: float = 0.05) -> str:
        if self.is_load_bearing(threshold=threshold):
            return (
                "LOAD-BEARING: switching the training-input noise assumption from "
                "the scope's defaults to the literature (Torn and Snyder 2012) "
                f"values moves validation loss by {self.relative_change:+.1%} -- "
                "recalibration cannot wait for real paired working/final data. "
                "Use WorkingTrackNoise.from_literature() as the interim Stage B "
                "default until recalibrate_from_pairs() has real data to run "
                "against."
            )
        return (
            "NOT LOAD-BEARING at this precision: switching the training-input "
            f"noise assumption moves validation loss by only "
            f"{self.relative_change:+.1%} -- recalibration can reasonably wait "
            "for real paired data without materially changing Stage B "
            "fine-tuned performance in the meantime."
        )


def run_noise_sensitivity(
    tracks: list[Track],
    *,
    hidden_dim: int = DEFAULT_HIDDEN_DIM,
    n_augment: int = 3,
    epochs: int = 30,
    seed: int = 20260806,
) -> NoiseSensitivityReport:
    """Train the same architecture twice, varying only the training-input
    noise assumption; evaluate both against a fixed literature-noise
    validation set. See the module docstring for why evaluation noise is
    held fixed while training noise is the one thing that varies.

    Train/val split uses ``data.splits.DEFAULT_BOUNDARIES`` (storm-wise,
    chronological); the test split is never touched here, matching the
    project's metered test-set policy.
    """
    assignment = assign_splits(tracks, DEFAULT_BOUNDARIES)
    train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
    val_tracks = filter_tracks(tracks, assignment, Split.VAL)
    if not train_tracks or not val_tracks:
        raise ValueError("need non-empty train and val storm sets")

    val_rng = np.random.default_rng(seed)
    x_val, y_val = build_samples(
        val_tracks, val_rng, n_augment=1, noise=WorkingTrackNoise.from_literature()
    )

    candidates = {"default": WorkingTrackNoise(), "literature": WorkingTrackNoise.from_literature()}
    results: dict[str, NoiseSensitivityResult] = {}
    for label, noise in candidates.items():
        train_rng = np.random.default_rng(seed)
        x_train, y_train = build_samples(train_tracks, train_rng, n_augment=n_augment, noise=noise)
        train_loss, val_loss = train_cell(
            x_train, y_train, x_val, y_val, hidden_dim=hidden_dim, epochs=epochs, seed=seed
        )
        results[label] = NoiseSensitivityResult(
            noise_label=label,
            position_rms_nm=noise.position_rms_nm,
            intensity_rms_kt=noise.intensity_rms_kt,
            pressure_rms_mb=noise.pressure_rms_mb,
            final_train_loss=train_loss,
            final_val_loss=val_loss,
        )
    return NoiseSensitivityReport(default=results["default"], literature=results["literature"])
