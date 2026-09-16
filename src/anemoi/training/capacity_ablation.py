"""Capacity-vs-sample-size ablation (#9; PLAN.md §5 "Sample size").

Whether the transformer -- and the LSTM/GNN/PINN group alongside it -- is
the right capacity for an archive this thin (~1,200 storms) is a question to
measure before committing GPU-months to full Stage A/B training, not one to
assume away. This harness trains the LSTM baseline (the cheapest Group 1
model to iterate on, and architecturally the closest fit to a storm-relative
track sequence) at several hidden-layer widths against several sample-size
fractions of the real HURDAT2 archive, and records whether validation loss
keeps improving as capacity grows at full data. If it stops improving, more
parameters would not help without more data -- the dataset, not the
architecture, is the binding constraint.

Track-only, single 6h-ahead step -- not the transformer's full gridded-field,
multi-lead task. This is a real, honest measurement of the thin-dataset
concern on the model it's cheapest to run the experiment on, not a proxy
result dressed up as a transformer verdict. See docs/capacity_ablation.md for
what this does and does not claim, and PLAN.md §5 for the recorded decision.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise, augment_track
from ..data.splits import DEFAULT_BOUNDARIES, Split, assign_splits, filter_tracks
from ..data.storm_relative import STORM_RELATIVE_COLUMNS, displacement_nm, storm_relative_sequence
from ..models.base import require_torch
from .device import get_device

#: 4 * 6h = 24h of history per input sequence.
SEQUENCE_LENGTH = 4
#: Fixes needed per sample: SEQUENCE_LENGTH + 1 for the input window
#: (storm_relative_sequence drops one row of lookback), + 1 more for the
#: next-step label.
_FIXES_PER_SAMPLE = SEQUENCE_LENGTH + 2

DEFAULT_HIDDEN_DIMS: tuple[int, ...] = (8, 16, 32, 64, 128)
DEFAULT_SAMPLE_FRACTIONS: tuple[float, ...] = (0.1, 0.25, 0.5, 1.0)


def build_samples(
    tracks: list[Track],
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """``(X, y)``: storm-relative input sequences and single-step-ahead targets.

    For each FINAL track and each of ``n_augment`` independently emulated
    working-quality realisations (``besttrack.augment_track`` -- the
    augmentation strategy this issue also calls for), every
    ``SEQUENCE_LENGTH``-fix window becomes one input sequence. The label is
    the east/north displacement (nm) and wind (kt) from the window's last
    *working* fix to the *next* fix's position on the FINAL track -- input is
    always working-quality, the label always final-quality, matching Stage
    B's policy (see the ``besttrack`` module docstring).
    """
    x_rows: list[np.ndarray] = []
    y_rows: list[list[float]] = []
    for final in tracks:
        if len(final.fixes) < _FIXES_PER_SAMPLE:
            continue
        for working in augment_track(final, rng, n_variants=n_augment, noise=noise):
            for i in range(len(working.fixes) - _FIXES_PER_SAMPLE + 1):
                window = working.fixes[i : i + SEQUENCE_LENGTH + 1]
                seq = storm_relative_sequence(window)
                current = window[-1]
                next_final = final.fixes[i + SEQUENCE_LENGTH + 1]
                dx, dy = displacement_nm(current, next_final)
                x_rows.append(seq)
                y_rows.append([dx, dy, next_final.max_wind_kt])
    if not x_rows:
        return (
            np.empty((0, SEQUENCE_LENGTH, len(STORM_RELATIVE_COLUMNS))),
            np.empty((0, 3)),
        )
    return np.stack(x_rows), np.array(y_rows, dtype=float)


def train_cell(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    *,
    hidden_dim: int,
    epochs: int = 30,
    lr: float = 1e-3,
    seed: int = 0,
) -> tuple[float, float]:
    """Train one LSTM capacity cell full-batch; return (train_loss, val_loss).

    Losses are standardised MSE: inputs and targets are z-scored with
    mean/std fit on the training set only, so a cell's loss is comparable
    across sample-size fractions despite the underlying position/wind scale
    never changing.
    """
    if len(x_train) == 0 or len(x_val) == 0:
        raise ValueError("empty train or val sample set -- widen the split or fraction")

    torch = require_torch()
    from ..models.lstm import build_lstm

    torch.manual_seed(seed)
    device = get_device()

    x_mean, x_std = x_train.mean(axis=(0, 1)), x_train.std(axis=(0, 1))
    x_std[x_std < 1e-8] = 1.0
    y_mean, y_std = y_train.mean(axis=0), y_train.std(axis=0)
    y_std[y_std < 1e-8] = 1.0

    def prep(x: np.ndarray, y: np.ndarray) -> tuple:
        return (
            torch.as_tensor((x - x_mean) / x_std, dtype=torch.float32, device=device),
            torch.as_tensor((y - y_mean) / y_std, dtype=torch.float32, device=device),
        )

    xt, yt = prep(x_train, y_train)
    xv, yv = prep(x_val, y_val)

    model, _spec = build_lstm(
        input_dim=x_train.shape[-1], hidden_dim=hidden_dim, num_layers=1, lead_hours=(6,)
    )
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(model(xt).squeeze(1), yt)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        train_loss = float(loss_fn(model(xt).squeeze(1), yt).item())
        val_loss = float(loss_fn(model(xv).squeeze(1), yv).item())
    return train_loss, val_loss


@dataclass(frozen=True, slots=True)
class AblationCell:
    """One (capacity, sample-fraction) trial result."""

    hidden_dim: int
    sample_fraction: float
    n_storms: int
    n_train_samples: int
    n_val_samples: int
    final_train_loss: float
    final_val_loss: float


@dataclass(frozen=True, slots=True)
class AblationReport:
    cells: tuple[AblationCell, ...]

    def at_fraction(self, fraction: float) -> tuple[AblationCell, ...]:
        return tuple(sorted((c for c in self.cells if c.sample_fraction == fraction),
                             key=lambda c: c.hidden_dim))

    def capacity_helps_at_full_data(self, *, improvement_threshold: float = 0.02) -> bool:
        """True if the largest capacity still meaningfully beats the smallest
        at the largest sample fraction present -- i.e. capacity is not yet
        the bottleneck. False means more parameters stopped helping."""
        if not self.cells:
            raise ValueError("no cells recorded")
        full_fraction = max(c.sample_fraction for c in self.cells)
        cells = self.at_fraction(full_fraction)
        if len(cells) < 2:
            raise ValueError("need at least two capacity levels at the full fraction to compare")
        smallest, largest = cells[0], cells[-1]
        if smallest.final_val_loss <= 0:
            return False
        relative_gain = (smallest.final_val_loss - largest.final_val_loss) / smallest.final_val_loss
        return relative_gain > improvement_threshold

    def recommend(self, *, improvement_threshold: float = 0.02) -> str:
        """Human-readable go/no-go statement."""
        if self.capacity_helps_at_full_data(improvement_threshold=improvement_threshold):
            return (
                "GO: validation loss keeps improving with more LSTM capacity at "
                "full training data -- capacity is not yet the binding constraint "
                "for this task. Scaling further (more width/layers, or the "
                "transformer) may still pay off."
            )
        return (
            "NO-GO on scaling capacity alone: additional LSTM capacity stops "
            "reducing validation loss at full training data -- the archive size "
            "is the binding constraint, not model capacity. Scaling the "
            "transformer further without more data is unlikely to help; invest "
            "in more samples (augmentation, more seasons, more basins) before "
            "more parameters."
        )

    def to_markdown(self) -> str:
        lines = [
            "| hidden_dim | sample_fraction | n_storms | n_train | n_val | train_loss | val_loss |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in sorted(self.cells, key=lambda c: (c.sample_fraction, c.hidden_dim)):
            lines.append(
                f"| {c.hidden_dim} | {c.sample_fraction:.2f} | {c.n_storms} | "
                f"{c.n_train_samples} | {c.n_val_samples} | {c.final_train_loss:.4f} | "
                f"{c.final_val_loss:.4f} |"
            )
        return "\n".join(lines)


def run_capacity_ablation(
    tracks: list[Track],
    *,
    hidden_dims: tuple[int, ...] = DEFAULT_HIDDEN_DIMS,
    sample_fractions: tuple[float, ...] = DEFAULT_SAMPLE_FRACTIONS,
    n_augment: int = 3,
    epochs: int = 30,
    seed: int = 20260806,
) -> AblationReport:
    """Run the full (hidden_dim x sample_fraction) grid against real tracks.

    Train/val split uses ``data.splits``' real storm-wise, chronological
    boundaries (train 1980-2019, val 2020-2022, see ``DEFAULT_BOUNDARIES``).
    The test split (2023-2025) is never touched here, matching the project's
    metered test-set policy (``training.promotion.TestSetBudget``).
    """
    rng = np.random.default_rng(seed)
    assignment = assign_splits(tracks, DEFAULT_BOUNDARIES)
    train_tracks_all = filter_tracks(tracks, assignment, Split.TRAIN)
    val_tracks = filter_tracks(tracks, assignment, Split.VAL)
    if not train_tracks_all or not val_tracks:
        raise ValueError("need non-empty train and val storm sets")

    x_val, y_val = build_samples(val_tracks, rng, n_augment=1)

    perm = rng.permutation(len(train_tracks_all))
    shuffled = [train_tracks_all[i] for i in perm]

    cells = []
    for fraction in sample_fractions:
        n_storms = max(1, int(round(len(shuffled) * fraction)))
        subset = shuffled[:n_storms]
        x_train, y_train = build_samples(subset, rng, n_augment=n_augment)
        for hidden_dim in hidden_dims:
            train_loss, val_loss = train_cell(
                x_train, y_train, x_val, y_val, hidden_dim=hidden_dim, epochs=epochs, seed=seed
            )
            cells.append(
                AblationCell(
                    hidden_dim=hidden_dim,
                    sample_fraction=fraction,
                    n_storms=n_storms,
                    n_train_samples=len(x_train),
                    n_val_samples=len(x_val),
                    final_train_loss=train_loss,
                    final_val_loss=val_loss,
                )
            )
    return AblationReport(cells=tuple(cells))
