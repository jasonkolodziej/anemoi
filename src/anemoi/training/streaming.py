"""Streaming training infrastructure (#22, `docs/streaming_dataloader.md`).

The durable fix for the real CUDA OOM `train_transformer_stage` hit on the
training VM (2026-09-17): every ``train_*_stage`` function trains
full-batch -- the whole cached dataset as one GPU tensor, so per-step VRAM
scales with how much real data is cached, not with batch size. This module
is the shared infrastructure the per-model streaming training loops build
on, so each model doesn't reinvent its own online statistics or dataset
wrapper:

- ``OnlineMeanStd``: streaming mean/std via Chan's parallel-batch
  generalisation of Welford's algorithm -- numerically equivalent (to
  float32 precision) to a single ``.mean()``/``.std()`` call over the
  whole array, without ever holding the whole array in memory. Verified
  directly against the existing single-pass ``_standardize_x`` functions
  in ``tests/test_streaming.py``, not just assumed correct.
- ``OnlineMaskedLeadMeanStd``: the same, but for the masked,
  per-lead-time target statistics ``_standardize_y`` already computes
  (displacement scale at 12h and 120h differ by roughly an order of
  magnitude, so each lead needs its own scale factor, fit only over that
  lead's masked-valid entries).
- ``WindowDataset``: a real ``torch.utils.data.Dataset`` over a list of
  `real_run.StageWindow` -- cheap to hold in memory in full (each window
  is a handful of `Fix` objects plus small `(n_leads, 3)` arrays, not the
  heavy per-window field data), with a per-model ``build_x`` callable
  that loads *that one window's* real cached field data (or track
  sequence, for LSTM) on demand. This is what actually keeps the CPU-side
  materialization bounded -- see `docs/streaming_dataloader.md`'s
  "CPU-side" vs "GPU-side" distinction for why fixing only the GPU tensor
  isn't the whole story.

Deliberately additive, not a replacement: every existing
``build_*_samples``/``train_*_stage`` function is untouched and still the
default, tested, full-batch path (fine for small real runs and for CI).
The streaming path is opt-in per `docs/streaming_dataloader.md` §7's own
guidance.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .real_run import StageWindow


class OnlineMeanStd:
    """Streaming mean/std over ``reduce_axes`` of successive batches,
    matching ``batch.mean(axis=reduce_axes, keepdims=keepdims)``'s
    semantics exactly (both the value and the shape), just computed
    incrementally instead of over one fully-materialized array.

    Chan et al. 1979's parallel-batch generalisation of Welford's online
    algorithm: combines each batch's own (count, mean, M2) into a running
    aggregate, which is mathematically equivalent to Welford's original
    one-sample-at-a-time update applied sample by sample, and to a plain
    two-pass mean/variance over the concatenation of every batch seen.
    """

    def __init__(self, reduce_axes: tuple[int, ...], *, keepdims: bool = False) -> None:
        self.reduce_axes = reduce_axes
        self.keepdims = keepdims
        self.count = 0
        self.mean: np.ndarray | None = None
        self.m2: np.ndarray | None = None

    def update(self, batch: np.ndarray) -> None:
        batch = np.asarray(batch, dtype=np.float64)
        count_b = 1
        for ax in self.reduce_axes:
            count_b *= batch.shape[ax]
        if count_b == 0:
            return

        mean_b = batch.mean(axis=self.reduce_axes, keepdims=True)
        m2_b = ((batch - mean_b) ** 2).sum(axis=self.reduce_axes, keepdims=True)
        if not self.keepdims:
            mean_b = mean_b.squeeze(axis=self.reduce_axes)
            m2_b = m2_b.squeeze(axis=self.reduce_axes)

        if self.count == 0:
            self.mean = mean_b
            self.m2 = m2_b
        else:
            new_count = self.count + count_b
            delta = mean_b - self.mean
            self.mean = self.mean + delta * (count_b / new_count)
            self.m2 = self.m2 + m2_b + delta**2 * (self.count * count_b / new_count)
        self.count += count_b

    def finalize(self) -> tuple[np.ndarray, np.ndarray]:
        if self.count == 0 or self.mean is None:
            raise ValueError("OnlineMeanStd.finalize() called with no data seen")
        variance = self.m2 / self.count
        std = np.sqrt(np.clip(variance, 0.0, None))
        std = np.where(std < 1e-8, 1.0, std)
        return self.mean.astype(np.float32), std.astype(np.float32)


class OnlineMaskedLeadMeanStd:
    """Streaming version of `real_run._standardize_y`: per-lead,
    per-channel mean/std, fit only over that lead's masked-valid entries.
    """

    def __init__(self, n_leads: int, n_channels: int = 3) -> None:
        self._leads = [OnlineMeanStd(reduce_axes=(0,)) for _ in range(n_leads)]
        self.n_leads = n_leads
        self.n_channels = n_channels

    def update(self, y_batch: np.ndarray, mask_batch: np.ndarray) -> None:
        """``y_batch`` is ``(batch, n_leads, n_channels)``, ``mask_batch``
        is ``(batch, n_leads)``."""
        for li in range(self.n_leads):
            valid = mask_batch[:, li]
            if valid.any():
                self._leads[li].update(y_batch[valid, li, :])

    def finalize(self) -> tuple[np.ndarray, np.ndarray]:
        mean = np.zeros((self.n_leads, self.n_channels), dtype=np.float32)
        std = np.ones((self.n_leads, self.n_channels), dtype=np.float32)
        for li, acc in enumerate(self._leads):
            if acc.count > 0:
                mean[li], std[li] = acc.finalize()
        return mean, std


class WindowDataset:
    """Real ``torch.utils.data.Dataset`` over a list of real
    `real_run.StageWindow` -- the list itself is cheap to hold in full
    (small per-item arrays, not field data); ``build_x`` loads *that one
    window's* real per-model input on demand, keeping the actual heavy
    data (cached `GriddedFields`, track sequences) un-materialized until
    the item is actually requested by a `DataLoader` worker.

    ``build_x`` must return a real array for every window in ``windows`` --
    a window with no cached field file yet (the same case
    `real_run_cnn.build_cnn_samples` etc. skip) must be filtered out of
    ``windows`` by the caller *before* constructing this dataset, not
    signalled some other way from inside ``build_x``: `DataLoader`
    workers pull items by a fixed-length index (`__len__`), so there's no
    well-defined place to drop an item once construction has already
    committed to a length.
    """

    def __init__(
        self,
        windows: list[StageWindow],
        build_x: Callable[[StageWindow], np.ndarray],
        *,
        x_mean: np.ndarray | None = None,
        x_std: np.ndarray | None = None,
        y_mean: np.ndarray | None = None,
        y_std: np.ndarray | None = None,
    ) -> None:
        self._windows = windows
        self._build_x = build_x
        self.x_mean = x_mean
        self.x_std = x_std
        self.y_mean = y_mean
        self.y_std = y_std

    def __len__(self) -> int:
        return len(self._windows)

    def __getitem__(self, idx: int):
        sw = self._windows[idx]
        x = self._build_x(sw)
        if self.x_mean is not None:
            x = (x - self.x_mean) / self.x_std
        y = sw.y
        if self.y_mean is not None:
            y = (y - self.y_mean) / self.y_std
        return x.astype(np.float32), y.astype(np.float32), sw.mask.astype(np.float32)


def iter_dataset_in_batches(dataset: WindowDataset, batch_size: int):
    """Plain-numpy batching over a `WindowDataset`, no `torch.utils.data
    .DataLoader`/multi-worker overhead -- used for the online
    standardization fitting pass (a single sequential sweep, not worth
    parallelizing) and by tests that want to check batching behaviour
    without a real torch install. Real training loops use a real
    `DataLoader` instead, for shuffling and worker parallelism.
    """
    n = len(dataset)
    for start in range(0, n, batch_size):
        idx = range(start, min(start + batch_size, n))
        xs, ys, masks = zip(*(dataset[i] for i in idx), strict=True)
        yield np.stack(xs), np.stack(ys), np.stack(masks)


def filter_windows_with_cache(windows: list[StageWindow], cache_dir) -> list[StageWindow]:
    """Real windows filtered down to the ones with an actual cached
    `GriddedFields` file on disk -- the same "skip, don't error" contract
    `real_run_cnn.build_cnn_samples`/`real_run_transformer
    .build_transformer_samples`/`real_run_gnn.build_gnn_samples`/
    `real_run_pinn.build_pinn_samples` already use for a fix the cache
    jobs haven't reached yet, applied up front so `WindowDataset`'s
    fixed-length index only ever contains windows `build_x` can actually
    build from (see that class's own docstring for why the filtering has
    to happen here and not inside `build_x`)."""
    from pathlib import Path

    from ..data.gridded_cache import FetchTask, cache_path

    cache_dir = Path(cache_dir)
    kept = []
    for sw in windows:
        task = FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )
        if cache_path(cache_dir, task).exists():
            kept.append(sw)
    return kept
