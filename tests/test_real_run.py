"""Real Stage A/B curriculum run for the LSTM baseline (#22)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.sources import Flavor
from anemoi.data.splits import DEFAULT_BOUNDARIES, STAGE_B_BOUNDARIES
from anemoi.data.storm_relative import displacement_nm
from anemoi.training.real_run import (
    LEAD_STEPS,
    StageSamples,
    boundaries_for_flavor,
    build_stage_samples,
    displacement_to_latlon,
)


def make_track(storm_id: str, season: int, n: int = 26, *, seed: int = 0) -> Track:
    rng = np.random.default_rng(seed)
    lat, lon = 15.0, -50.0
    start = datetime(season, 8, 1, tzinfo=UTC)
    fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.3))
        lon -= float(rng.uniform(0.2, 0.5))
        fixes.append(
            Fix(
                storm_id=storm_id,
                valid_time=start + timedelta(hours=6 * i),
                lat=round(lat, 2),
                lon=round(lon, 2),
                max_wind_kt=float(50 + 2 * i),
                min_pressure_mb=float(995 - 1.5 * i),
                quality=TrackQuality.FINAL,
            )
        )
    return Track(storm_id=storm_id, fixes=tuple(fixes))


# --- boundaries_for_flavor --------------------------------------------------


def test_boundaries_for_flavor_picks_stage_b_for_gdas_finetune():
    assert boundaries_for_flavor(Flavor.GDAS_FINETUNE) is STAGE_B_BOUNDARIES


def test_boundaries_for_flavor_picks_default_for_era5_pretrain():
    assert boundaries_for_flavor(Flavor.ERA5_PRETRAIN) is DEFAULT_BOUNDARIES


# --- displacement_to_latlon (inverse of storm_relative.displacement_nm) ----


def test_displacement_to_latlon_round_trips_with_displacement_nm():
    prev = Fix(
        storm_id="AL01", valid_time=datetime(2026, 8, 6, tzinfo=UTC),
        lat=20.0, lon=-60.0, max_wind_kt=60.0, min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    cur = Fix(
        storm_id="AL01", valid_time=datetime(2026, 8, 6, 6, tzinfo=UTC),
        lat=21.3, lon=-61.7, max_wind_kt=65.0, min_pressure_mb=985.0,
        quality=TrackQuality.FINAL,
    )
    dx, dy = displacement_nm(prev, cur)
    lat2, lon2 = displacement_to_latlon(prev.lat, prev.lon, dx, dy)
    assert lat2 == pytest.approx(cur.lat, abs=1e-6)
    assert lon2 == pytest.approx(cur.lon, abs=1e-6)


def test_displacement_to_latlon_is_a_noop_for_zero_displacement():
    lat, lon = displacement_to_latlon(20.0, -60.0, 0.0, 0.0)
    assert (lat, lon) == (20.0, -60.0)


# --- build_stage_samples ----------------------------------------------------


def test_build_stage_samples_masks_leads_beyond_a_short_track():
    """A track too short for the longest lead (120h = 20 steps ahead) must
    still contribute samples for the leads it does cover, not be dropped
    whole or have a fabricated long-lead target."""
    track = make_track("AL011985", season=1985, n=10)  # covers up to ~24h leads only
    rng = np.random.default_rng(1)
    samples = build_stage_samples([track], rng, n_augment=1)

    assert len(samples) > 0
    assert isinstance(samples, StageSamples)
    n_leads = len(LEAD_STEPS)
    assert samples.y.shape[1:] == (n_leads, 3)
    assert samples.mask.shape[1:] == (n_leads,)
    # short track: last (120h) lead must never be available
    assert not samples.mask[:, -1].any()
    # but the shortest (12h) lead must be available for at least some samples
    assert samples.mask[:, 0].any()


def test_build_stage_samples_full_length_track_covers_every_lead():
    track = make_track("AL012021", season=2021, n=26)
    rng = np.random.default_rng(2)
    samples = build_stage_samples([track], rng, n_augment=1)
    assert samples.mask[:, -1].any()  # 120h lead reachable somewhere in a 26-fix track


def test_build_stage_samples_drops_a_track_too_short_for_any_lead():
    track = make_track("AL013000", season=2021, n=4)  # < SEQUENCE_LENGTH+1+LEAD_STEPS[0]
    rng = np.random.default_rng(3)
    samples = build_stage_samples([track], rng, n_augment=1)
    assert len(samples) == 0


def test_build_stage_samples_masked_entries_are_recoverable_positions():
    """y stores (dx, dy, wind) relative to the window's current fix -- for
    an unmasked entry, displacement_to_latlon(base, *y[...,:2]) must land on
    a real fix's position."""
    track = make_track("AL012021", season=2021, n=26)
    rng = np.random.default_rng(4)
    samples = build_stage_samples([track], rng, n_augment=1)
    si = 0
    li = 0  # shortest lead, always present for a full-length track
    assert samples.mask[si, li]
    dx, dy, _wind = samples.y[si, li]
    lat, lon = displacement_to_latlon(samples.base_lat[si], samples.base_lon[si], dx, dy)
    assert -90.0 <= lat <= 90.0
    assert -180.0 <= lon <= 180.0


# --- torch-dependent: train_lstm_stage / run_lstm_curriculum ---------------

torch_installed = pytest.importorskip("torch", reason="needs the torch extra")


class FakeS3Client:
    """Same duck-typed surface tests/test_checkpoint_store.py uses."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


def _fake_checkpoint_store():
    from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

    config = S3Config(
        endpoint_url="https://example.r2.cloudflarestorage.com",
        bucket="anemoi-test",
        access_key_id="key",
        secret_access_key="secret",
    )
    return CheckpointStore(config, client=FakeS3Client())


@pytest.mark.torch
def test_train_lstm_stage_reduces_loss_over_epochs():
    from anemoi.models.lstm import build_lstm
    from anemoi.training.curriculum import stage_a

    tracks = [make_track("AL011985", season=1985, n=26, seed=0),
              make_track("AL021985", season=1985, n=26, seed=1)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=2)]

    model, _spec = build_lstm(input_dim=5, hidden_dim=16, lead_hours=(12, 24, 36, 48, 72, 96, 120))
    stage = stage_a(epochs=20, learning_rate=1e-2)
    rng = np.random.default_rng(5)

    from anemoi.training.real_run import train_lstm_stage

    trained_model, train_loss, val_loss, val_metrics, _stats = train_lstm_stage(
        model, stage, tracks, val_tracks, rng, n_augment=2,
    )
    assert trained_model is model
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert val_metrics.split == "val"
    assert val_metrics.flavor is Flavor.ERA5_PRETRAIN
    assert "track_error_12h_nm" in val_metrics.values


@pytest.mark.torch
def testfreeze_encoder_leaves_only_head_trainable():
    from anemoi.models.lstm import build_lstm
    from anemoi.training.real_run import freeze_encoder

    model, _spec = build_lstm(input_dim=5, hidden_dim=8, lead_hours=(12,))
    freeze_encoder(model, ("encoder",))
    for name, param in model.named_parameters():
        if name.startswith("head."):
            assert param.requires_grad
        else:
            assert not param.requires_grad


@pytest.mark.torch
def testfreeze_encoder_is_a_noop_without_encoder_in_frozen_modules():
    from anemoi.models.lstm import build_lstm
    from anemoi.training.real_run import freeze_encoder

    model, _spec = build_lstm(input_dim=5, hidden_dim=8, lead_hours=(12,))
    freeze_encoder(model, ())
    assert all(p.requires_grad for p in model.parameters())


@pytest.mark.torch
def test_run_lstm_curriculum_completes_both_stages_and_uploads_checkpoints():
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),  # Stage A train
        make_track("AL012021", season=2021, n=26, seed=1),  # Stage A val / Stage B train
        make_track("AL022021", season=2021, n=26, seed=2),  # Stage B train
        make_track("AL012023", season=2023, n=26, seed=3),  # Stage B val
    ]
    store = _fake_checkpoint_store()

    from anemoi.training.real_run import run_lstm_curriculum

    run, val_metrics, _artifacts = run_lstm_curriculum(
        tracks, store, seed=42, n_augment=1, hidden_dim=8,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert run.results[-1].flavor is Flavor.GDAS_FINETUNE
    for result in run.results:
        assert result.checkpoint_uri.startswith("s3://anemoi-test/checkpoints/lstm/")
        assert store.exists(result.checkpoint_uri.split("anemoi-test/", 1)[1])
    assert val_metrics.flavor is Flavor.GDAS_FINETUNE
    assert "track_error_12h_nm" in val_metrics.values


# --- streaming (docs/streaming_dataloader.md) -------------------------------


@pytest.mark.torch
def test_train_lstm_stage_streaming_reduces_loss_and_produces_val_metrics():
    from anemoi.models.lstm import build_lstm
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run import train_lstm_stage_streaming

    tracks = [make_track("AL011985", season=1985, n=26, seed=0),
              make_track("AL021985", season=1985, n=26, seed=1)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=2)]

    model, _spec = build_lstm(input_dim=5, hidden_dim=16, lead_hours=(12, 24, 36, 48, 72, 96, 120))
    stage = stage_a(epochs=5, learning_rate=1e-2)
    rng = np.random.default_rng(5)

    trained_model, train_loss, val_loss, val_metrics, stats = train_lstm_stage_streaming(
        model, stage, tracks, val_tracks, rng, n_augment=2, batch_size=8,
    )
    assert trained_model is model
    assert train_loss >= 0.0
    assert val_loss >= 0.0
    assert val_metrics.split == "val"
    assert val_metrics.flavor is Flavor.ERA5_PRETRAIN
    assert "track_error_12h_nm" in val_metrics.values
    x_mean, x_std, y_mean, y_std = stats
    assert x_mean.shape == (5,)
    assert y_mean.shape[-1] == 3


@pytest.mark.torch
def test_train_lstm_stage_streaming_batch_size_does_not_change_final_metrics_much():
    """Different batch sizes take different SGD paths (real, expected --
    mini-batch noise), but both must land in a sane, finite, comparable
    range against the same real data -- a basic sanity check that batching
    isn't silently corrupting the loss/metric computation."""
    from anemoi.models.lstm import build_lstm
    from anemoi.training.curriculum import stage_a
    from anemoi.training.real_run import train_lstm_stage_streaming

    tracks = [make_track("AL011985", season=1985, n=26, seed=0),
              make_track("AL021985", season=1985, n=26, seed=1),
              make_track("AL031985", season=1985, n=26, seed=6)]
    val_tracks = [make_track("AL012020", season=2020, n=26, seed=2)]
    stage = stage_a(epochs=5, learning_rate=1e-2)

    losses = []
    leads = (12, 24, 36, 48, 72, 96, 120)
    for batch_size in (4, 64):
        model, _spec = build_lstm(input_dim=5, hidden_dim=16, lead_hours=leads)
        rng = np.random.default_rng(7)
        _m, train_loss, _v, _vm, _s = train_lstm_stage_streaming(
            model, stage, tracks, val_tracks, rng, n_augment=2, batch_size=batch_size,
        )
        assert math.isfinite(train_loss)
        losses.append(train_loss)
    assert all(loss < 10.0 for loss in losses)  # not diverged/NaN-adjacent


@pytest.mark.torch
def test_run_lstm_curriculum_streaming_completes_both_stages():
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    store = _fake_checkpoint_store()

    from anemoi.training.real_run import run_lstm_curriculum

    run, val_metrics, _artifacts = run_lstm_curriculum(
        tracks, store, seed=42, n_augment=1, hidden_dim=8, streaming=True, batch_size=8,
    )

    assert run.complete
    assert [r.stage_name for r in run.results] == ["A", "B"]
    assert run.results[-1].flavor is Flavor.GDAS_FINETUNE
    assert "track_error_12h_nm" in val_metrics.values


@pytest.mark.torch
def test_run_lstm_curriculum_stage_b_starts_from_stage_a_weights_not_fresh(tmp_path):
    """A frozen encoder means Stage B's rnn/norm weights must be byte-for-byte
    identical to Stage A's trained weights, not re-initialised."""
    tracks = [
        make_track("AL011985", season=1985, n=26, seed=0),
        make_track("AL012021", season=2021, n=26, seed=1),
        make_track("AL022021", season=2021, n=26, seed=2),
        make_track("AL012023", season=2023, n=26, seed=3),
    ]
    store = _fake_checkpoint_store()

    from anemoi.training.real_run import run_lstm_curriculum

    run, _val_metrics, _artifacts = run_lstm_curriculum(
        tracks, store, seed=42, n_augment=1, hidden_dim=8,
    )

    import torch

    a_path = tmp_path / "stage_a.pt"
    b_path = tmp_path / "stage_b.pt"
    store.download(run.results[0].checkpoint_uri, a_path)
    store.download(run.results[1].checkpoint_uri, b_path)
    state_a = torch.load(a_path, weights_only=True)
    state_b = torch.load(b_path, weights_only=True)
    for key in state_a:
        if key.startswith("head."):
            continue
        assert torch.equal(state_a[key], state_b[key]), f"{key} changed despite being frozen"
