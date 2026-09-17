"""Streaming training infrastructure (training.streaming,
docs/streaming_dataloader.md).

The core claim this file verifies, not just asserts: OnlineMeanStd/
OnlineMaskedLeadMeanStd computed incrementally over batches produce the
same real numbers (to float32 precision) as the existing single-pass
_standardize_x/_standardize_y functions computed over the whole array at
once -- imported directly from the real modules, not reimplemented here,
so a future change to either the real function or this one can't silently
drift apart without a test catching it.
"""

from __future__ import annotations

import numpy as np
import pytest

from anemoi.training.streaming import (
    OnlineMaskedLeadMeanStd,
    OnlineMeanStd,
    WindowDataset,
    filter_windows_with_cache,
    iter_dataset_in_batches,
)


def _batches(arr: np.ndarray, batch_size: int):
    for start in range(0, len(arr), batch_size):
        yield arr[start : start + batch_size]


# --- OnlineMeanStd vs each model's real single-pass function ----------------


def test_online_mean_std_matches_lstm_standardize_x():
    from anemoi.training.real_run import _standardize_x

    rng = np.random.default_rng(1)
    x = rng.normal(loc=5.0, scale=3.0, size=(97, 8, 5))  # (N, SEQ, F), ragged batch count

    _, real_mean, real_std = _standardize_x(x)

    acc = OnlineMeanStd(reduce_axes=(0, 1), keepdims=False)
    for batch in _batches(x, batch_size=13):
        acc.update(batch)
    mean, std = acc.finalize()

    np.testing.assert_allclose(mean, real_mean, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(std, real_std, rtol=1e-5, atol=1e-5)


def test_online_mean_std_matches_cnn_and_transformer_standardize_x():
    from anemoi.training.real_run_cnn import _standardize_cnn_x

    rng = np.random.default_rng(2)
    x = rng.normal(loc=-2.0, scale=4.0, size=(83, 10, 9, 9))  # (N, C, H, W)

    _, real_mean, real_std = _standardize_cnn_x(x)

    acc = OnlineMeanStd(reduce_axes=(0, 2, 3), keepdims=True)
    for batch in _batches(x, batch_size=17):
        acc.update(batch)
    mean, std = acc.finalize()

    assert mean.shape == real_mean.shape == (1, 10, 1, 1)
    np.testing.assert_allclose(mean, real_mean, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(std, real_std, rtol=1e-5, atol=1e-5)


def test_online_mean_std_matches_gnn_standardize_x():
    from anemoi.training.real_run_gnn import _standardize_x

    rng = np.random.default_rng(3)
    x = rng.normal(loc=0.0, scale=2.0, size=(64, 25, 12))  # (N, n_nodes, F)

    _, real_mean, real_std = _standardize_x(x)

    acc = OnlineMeanStd(reduce_axes=(0, 1), keepdims=True)
    for batch in _batches(x, batch_size=9):
        acc.update(batch)
    mean, std = acc.finalize()

    assert mean.shape == real_mean.shape == (1, 1, 12)
    np.testing.assert_allclose(mean, real_mean, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(std, real_std, rtol=1e-5, atol=1e-5)


def test_online_mean_std_single_batch_matches_numpy_directly():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(50, 4))
    acc = OnlineMeanStd(reduce_axes=(0,))
    acc.update(x)
    mean, std = acc.finalize()
    np.testing.assert_allclose(mean, x.mean(axis=0), rtol=1e-6)
    np.testing.assert_allclose(std, x.std(axis=0), rtol=1e-6)


def test_online_mean_std_finalize_without_data_raises():
    with pytest.raises(ValueError, match="no data"):
        OnlineMeanStd(reduce_axes=(0,)).finalize()


# --- OnlineMaskedLeadMeanStd vs _standardize_y -------------------------------


def test_online_masked_lead_mean_std_matches_standardize_y():
    from anemoi.training.real_run import _standardize_y

    rng = np.random.default_rng(5)
    n, n_leads = 120, 7
    y = rng.normal(loc=10.0, scale=6.0, size=(n, n_leads, 3))
    # a real, ragged mask: later leads less often available, like a short track
    mask = np.zeros((n, n_leads), dtype=bool)
    for li in range(n_leads):
        mask[:, li] = rng.random(n) > (li * 0.1)

    real_mean, real_std = _standardize_y(y, mask)

    acc = OnlineMaskedLeadMeanStd(n_leads=n_leads)
    for start in range(0, n, 11):
        sl = slice(start, start + 11)
        acc.update(y[sl], mask[sl])
    mean, std = acc.finalize()

    np.testing.assert_allclose(mean, real_mean, rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(std, real_std, rtol=1e-5, atol=1e-5)


def test_online_masked_lead_mean_std_handles_a_never_valid_lead():
    """A lead nothing in the (batched) data ever has -- must stay the
    identity default (mean 0, std 1), matching _standardize_y's own
    np.zeros/np.ones defaults, not raise or divide by zero."""
    n_leads = 3
    acc = OnlineMaskedLeadMeanStd(n_leads=n_leads)
    y = np.ones((10, n_leads, 3))
    mask = np.zeros((10, n_leads), dtype=bool)
    mask[:, 0] = True  # only lead 0 ever valid
    acc.update(y, mask)
    mean, std = acc.finalize()
    assert mean[1:].tolist() == [[0.0, 0.0, 0.0]] * 2
    assert std[1:].tolist() == [[1.0, 1.0, 1.0]] * 2


# --- WindowDataset / iter_dataset_in_batches --------------------------------


class _FakeWindow:
    def __init__(self, value: float, y, mask) -> None:
        self.value = value
        self.y = y
        self.mask = mask


def test_window_dataset_standardization_must_match_unbatched_item_shape():
    """Real bug caught building CNN's streaming path: a keepdims=True
    OnlineMeanStd fit over BATCHED (N, C, H, W) arrays produces (1, C, 1,
    1) mean/std -- correct for standardizing another batched array, but
    WindowDataset standardizes one UNBATCHED (C, H, W) item at a time, and
    (C, H, W) broadcast against (1, C, 1, 1) silently produces a wrong
    (1, C, H, W) result (numpy left-pads the smaller-rank array) instead
    of raising. Callers must pass the batch axis already squeezed off
    (e.g. `x_mean[0]`, not `x_mean`) -- this pins that contract."""
    x_mean = np.array([[[[2.0]], [[4.0]]]])  # shape (1, 2, 1, 1) -- batched convention
    assert x_mean.shape == (1, 2, 1, 1)

    windows = [_FakeWindow(1.0, y=np.zeros((1, 3)), mask=np.array([True]))]
    ds = WindowDataset(
        windows,
        lambda sw: np.ones((2, 3, 3)),  # one unbatched (C, H, W) item
        x_mean=x_mean[0], x_std=np.ones((2, 1, 1)),  # correctly squeezed
    )
    x, _y, _mask = ds[0]
    assert x.shape == (2, 3, 3)  # not (1, 2, 3, 3)


def test_window_dataset_applies_standardization_lazily():
    windows = [
        _FakeWindow(v, y=np.array([[1.0, 2.0, 3.0]]), mask=np.array([True])) for v in range(5)
    ]
    calls: list[float] = []

    def build_x(sw):
        calls.append(sw.value)
        return np.array([sw.value, sw.value * 2.0])

    ds = WindowDataset(
        windows, build_x,
        x_mean=np.array([2.0, 4.0]), x_std=np.array([1.0, 2.0]),
        y_mean=np.array([[0.0, 0.0, 0.0]]), y_std=np.array([[1.0, 1.0, 1.0]]),
    )
    assert len(ds) == 5
    assert calls == []  # nothing built yet -- lazy

    x, y, mask = ds[3]
    assert calls == [3]  # only the requested item was built
    np.testing.assert_allclose(x, [(3 - 2.0) / 1.0, (6 - 4.0) / 2.0])
    np.testing.assert_allclose(y, [[1.0, 2.0, 3.0]])
    np.testing.assert_allclose(mask, [1.0])


def test_window_dataset_without_standardization_returns_raw_values():
    windows = [_FakeWindow(1.0, y=np.array([[5.0]]), mask=np.array([True]))]
    ds = WindowDataset(windows, lambda sw: np.array([sw.value]))
    x, y, mask = ds[0]
    np.testing.assert_allclose(x, [1.0])
    np.testing.assert_allclose(y, [[5.0]])


def test_iter_dataset_in_batches_covers_every_item_exactly_once():
    windows = [
        _FakeWindow(float(v), y=np.array([[float(v)]]), mask=np.array([True])) for v in range(23)
    ]
    ds = WindowDataset(windows, lambda sw: np.array([sw.value]))

    seen = []
    for xb, yb, mb in iter_dataset_in_batches(ds, batch_size=7):
        assert len(xb) == len(yb) == len(mb)
        seen.extend(xb[:, 0].tolist())

    assert sorted(seen) == [float(v) for v in range(23)]


# --- make_dataloader ----------------------------------------------------------

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


@pytest.mark.torch
def test_make_dataloader_num_workers_zero_covers_every_item_exactly_once():
    from anemoi.training.streaming import make_dataloader

    windows = [
        _FakeWindow(float(v), y=np.array([[float(v)]]), mask=np.array([True])) for v in range(11)
    ]
    ds = WindowDataset(windows, lambda sw: np.array([sw.value]))
    loader = make_dataloader(ds, batch_size=4, shuffle=False, num_workers=0)

    assert loader.num_workers == 0
    seen = []
    for xb, _yb, _mb in loader:
        seen.extend(xb[:, 0].tolist())
    assert sorted(seen) == [float(v) for v in range(11)]


@pytest.mark.torch
def test_make_dataloader_num_workers_positive_forks_real_worker_processes():
    """Real functional check, not just an attribute check -- confirms
    num_workers>0 actually produces correct results through real forked
    worker processes (docs/streaming.make_dataloader's docstring explains
    why `multiprocessing_context="fork"` is forced explicitly), the exact
    path that was all-serial (`num_workers=0`) before this existed."""
    from anemoi.training.streaming import make_dataloader

    windows = [
        _FakeWindow(float(v), y=np.array([[float(v)]]), mask=np.array([True])) for v in range(11)
    ]
    ds = WindowDataset(windows, lambda sw: np.array([sw.value]))
    loader = make_dataloader(ds, batch_size=4, shuffle=False, num_workers=2)

    assert loader.num_workers == 2
    assert loader.persistent_workers is True
    seen = []
    for xb, _yb, _mb in loader:
        seen.extend(xb[:, 0].tolist())
    assert sorted(seen) == [float(v) for v in range(11)]


@pytest.mark.torch
def test_make_dataloader_passes_through_a_custom_collate_fn():
    """GNN's streaming path needs its own collate_fn (block-diagonal batch
    assembly) -- confirms make_dataloader forwards it rather than only
    supporting the default collation `WindowDataset`'s other callers use."""
    from anemoi.training.streaming import make_dataloader

    windows = [
        _FakeWindow(float(v), y=np.array([[float(v)]]), mask=np.array([True])) for v in range(6)
    ]
    ds = WindowDataset(windows, lambda sw: np.array([sw.value]))
    calls = []

    def collate(batch):
        calls.append(len(batch))
        xs, ys, masks = zip(*batch, strict=True)
        return np.stack(xs), np.stack(ys), np.stack(masks)

    loader = make_dataloader(ds, batch_size=3, shuffle=False, num_workers=0, collate_fn=collate)
    batches = list(loader)
    assert calls == [3, 3]
    assert len(batches) == 2


# --- filter_windows_with_cache -----------------------------------------------


def test_filter_windows_with_cache_keeps_only_real_cached_windows(tmp_path):
    from datetime import UTC, datetime

    from anemoi.data.besttrack import Fix, TrackQuality
    from anemoi.data.features import GriddedFields
    from anemoi.data.gridded_cache import FetchTask, cache_path, save_cached_fields
    from anemoi.data.sources import Flavor
    from anemoi.training.real_run import StageWindow

    def make_fix(hour: int) -> Fix:
        return Fix(
            storm_id="AL011985", valid_time=datetime(1985, 8, 1, hour, tzinfo=UTC),
            lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
            quality=TrackQuality.FINAL,
        )

    cached_fix = make_fix(0)
    uncached_fix = make_fix(6)
    grid = lambda v: np.full((5, 5), v)  # noqa: E731
    fields = GriddedFields(
        valid_time=cached_fix.valid_time, flavor=Flavor.ERA5_PRETRAIN,
        u200=grid(1.0), v200=grid(1.0), u850=grid(1.0), v850=grid(1.0), z500=grid(1.0),
        rh700=grid(1.0), t700=grid(1.0), mslp=grid(1.0), sst=grid(1.0), ohc=grid(1.0),
    )
    task = FetchTask(
        storm_id=cached_fix.storm_id, valid_time=cached_fix.valid_time,
        lat=cached_fix.lat, lon=cached_fix.lon,
    )
    save_cached_fields(cache_path(tmp_path, task), fields, task)

    windows = [
        StageWindow(
            storm_id="AL011985", window=(cached_fix,), current=cached_fix,
            y=np.zeros((1, 3)), mask=np.array([True]),
        ),
        StageWindow(
            storm_id="AL011985", window=(uncached_fix,), current=uncached_fix,
            y=np.zeros((1, 3)), mask=np.array([True]),
        ),
    ]

    kept = filter_windows_with_cache(windows, tmp_path)
    assert len(kept) == 1
    assert kept[0].current.valid_time == cached_fix.valid_time


def test_filter_windows_with_cache_empty_when_nothing_cached(tmp_path):
    from datetime import UTC, datetime

    from anemoi.data.besttrack import Fix, TrackQuality
    from anemoi.training.real_run import StageWindow

    fix = Fix(
        storm_id="AL011985", valid_time=datetime(1985, 8, 1, tzinfo=UTC),
        lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    windows = [
        StageWindow(
            storm_id="AL011985", window=(fix,), current=fix,
            y=np.zeros((1, 3)), mask=np.array([True]),
        ),
    ]
    assert filter_windows_with_cache(windows, tmp_path) == []
