"""Synthetic GOES storm-relative crops (PLAN.md §4 productionization: Satellite)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from anemoi.data.satellite import (
    CHANNEL_NAMES,
    SatelliteCrop,
    crop_to_cnn_input,
    generate_satellite_crop,
)

T = datetime(2026, 8, 6, 6, tzinfo=UTC)


def test_crop_has_the_declared_channel_count_and_shape():
    crop = generate_satellite_crop("AL092026", T, max_wind_kt=90.0, size=32, seed=0)
    assert crop.channels.shape == (len(CHANNEL_NAMES), 32, 32)
    assert crop.size == 32


def test_as_dict_maps_channel_names_to_arrays():
    crop = generate_satellite_crop("AL092026", T, max_wind_kt=90.0, size=16, seed=0)
    d = crop.as_dict()
    assert set(d) == set(CHANNEL_NAMES)
    assert d["ir_brightness_temp_k"].shape == (16, 16)


def test_wrong_channel_count_is_rejected():
    with pytest.raises(ValueError, match="expected 5 channels"):
        SatelliteCrop("AL092026", T, np.zeros((3, 16, 16)))


def test_non_3d_channels_are_rejected():
    with pytest.raises(ValueError, match="C, H, W"):
        SatelliteCrop("AL092026", T, np.zeros((16, 16)))


def test_stronger_storms_have_colder_cloud_tops_near_the_center():
    """Deeper, better-organized eyewall convection -> colder IR/WV brightness
    temperature near the storm center -- the directionally honest relationship
    this synthetic generator is required to preserve."""
    weak = generate_satellite_crop("AL092026", T, max_wind_kt=35.0, size=64, seed=0)
    strong = generate_satellite_crop("AL092026", T, max_wind_kt=150.0, size=64, seed=0)

    def center_mean(crop, channel):
        arr = crop.as_dict()[channel]
        c = crop.size // 2
        return arr[c - 4 : c + 4, c - 4 : c + 4].mean()

    assert center_mean(strong, "ir_brightness_temp_k") < center_mean(weak, "ir_brightness_temp_k")
    assert center_mean(strong, "water_vapor_brightness_temp_k") < center_mean(
        weak, "water_vapor_brightness_temp_k"
    )
    assert center_mean(strong, "rain_rate_mm_hr") > center_mean(weak, "rain_rate_mm_hr")


def test_visible_reflectance_stays_in_unit_range():
    crop = generate_satellite_crop("AL092026", T, max_wind_kt=160.0, size=32, seed=1)
    vis = crop.as_dict()["visible_reflectance"]
    assert vis.min() >= 0.0
    assert vis.max() <= 1.0


def test_rain_rate_is_never_negative():
    crop = generate_satellite_crop("AL092026", T, max_wind_kt=0.0, size=32, seed=2)
    assert crop.as_dict()["rain_rate_mm_hr"].min() >= 0.0


def test_same_seed_is_reproducible():
    a = generate_satellite_crop("AL092026", T, max_wind_kt=90.0, size=16, seed=42)
    b = generate_satellite_crop("AL092026", T, max_wind_kt=90.0, size=16, seed=42)
    np.testing.assert_array_equal(a.channels, b.channels)


def test_crop_to_cnn_input_adds_a_batch_dimension():
    crop = generate_satellite_crop("AL092026", T, max_wind_kt=90.0, size=32, seed=0)
    batch = crop_to_cnn_input(crop)
    assert batch.shape == (1, len(CHANNEL_NAMES), 32, 32)
    assert batch.dtype == np.float32


@pytest.mark.torch
def test_synthetic_crop_feeds_the_cnn_channel_stack_end_to_end():
    """The whole point: synthetic imagery in the exact shape models.cnn.build_cnn expects."""
    torch = pytest.importorskip("torch")
    from anemoi.models.cnn import build_cnn

    crop = generate_satellite_crop("AL092026", T, max_wind_kt=110.0, size=64, seed=0)
    batch = crop_to_cnn_input(crop)

    model, spec = build_cnn(in_channels=len(CHANNEL_NAMES), base_width=8, depth=3, latent_dim=32)
    out = model(torch.from_numpy(batch))
    assert out.shape == (1, len(spec.lead_hours), spec.outputs_per_lead)
