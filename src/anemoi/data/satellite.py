"""Synthetic GOES-18/19 storm-relative crops -> CNN channel stack.

Scope v2.1 PLAN.md §4 "productionise" table -- Satellite row, listed as "Not
implemented" until this module. Real ingestion now exists --
``data.real_goes.fetch_real_satellite_crop`` (#146) returns a real
``SatelliteCrop`` in this exact shape/channel order, fetched from real GOES
ABI imagery and derived products. This module remains the synthetic
stand-in for offline/test use (matching ``data.synthetic``'s role for
``GriddedFields``), not because real ingestion doesn't exist -- nothing in
this codebase wires the real fetch into a live training/inference path yet,
same "fetch exists, not yet a consumed input" state every #147 source
shipped in.

No torch dependency here -- crops are plain numpy arrays. A caller with the
torch extra installed converts with ``torch.from_numpy(crop_to_cnn_input(...))``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

#: Matches models.cnn.build_cnn's default in_channels=5 and the wiki's
#: Data-Pipeline Stage 4 CNN row: "Multi-channel imagery stacks (IR, WV, VIS,
#: SST, rain rate)".
CHANNEL_NAMES: tuple[str, ...] = (
    "ir_brightness_temp_k",
    "water_vapor_brightness_temp_k",
    "visible_reflectance",
    "sst_c",
    "rain_rate_mm_hr",
)


@dataclass(frozen=True, slots=True)
class SatelliteCrop:
    """A storm-relative multi-channel image stack for one storm at one time."""

    storm_id: str
    valid_time: datetime
    #: (channels, height, width), channel order == CHANNEL_NAMES.
    channels: np.ndarray

    def __post_init__(self) -> None:
        if self.channels.ndim != 3:
            raise ValueError("channels must be (C, H, W)")
        if self.channels.shape[0] != len(CHANNEL_NAMES):
            raise ValueError(
                f"expected {len(CHANNEL_NAMES)} channels, got {self.channels.shape[0]}"
            )

    @property
    def size(self) -> int:
        return self.channels.shape[-1]

    def as_dict(self) -> dict[str, np.ndarray]:
        return dict(zip(CHANNEL_NAMES, self.channels, strict=True))


def generate_satellite_crop(
    storm_id: str,
    valid_time: datetime,
    max_wind_kt: float,
    *,
    size: int = 64,
    seed: int | None = None,
) -> SatelliteCrop:
    """Synthetic storm-relative crop with an intensity-dependent structure.

    Not a simulation of real convection -- a stand-in with the right shape
    and a directionally honest relationship to intensity (colder IR/WV
    brightness temperatures, brighter VIS reflectance, and heavier rain rate
    toward the center for a more intense storm, consistent with deeper,
    better-organized eyewall convection), so CNN-path code has
    realistically-shaped imagery to run against offline. See module
    docstring for what replacing this with real GOES imagery involves.
    """
    rng = np.random.default_rng(seed if seed is not None else int(valid_time.timestamp()))
    y, x = np.mgrid[0:size, 0:size]
    cy, cx = size / 2.0, size / 2.0
    r = np.hypot(y - cy, x - cx) / max(cy, 1.0)  # 0 at center, ~1 at the crop edge

    intensity = float(np.clip(max_wind_kt, 0.0, 200.0)) / 200.0

    ir = 260.0 - 60.0 * intensity * np.exp(-3.0 * r**2) + rng.normal(0.0, 3.0, (size, size))
    wv = 240.0 - 35.0 * intensity * np.exp(-2.0 * r**2) + rng.normal(0.0, 3.0, (size, size))
    vis = np.clip(
        0.3 + 0.6 * intensity * np.exp(-3.0 * r**2) + rng.normal(0.0, 0.05, (size, size)),
        0.0, 1.0,
    )
    sst = 28.0 - 1.5 * intensity + rng.normal(0.0, 0.3, (size, size))
    rain = np.clip(
        5.0 + 40.0 * intensity * np.exp(-2.5 * r**2) + rng.normal(0.0, 2.0, (size, size)),
        0.0, None,
    )

    channels = np.stack([ir, wv, vis, sst, rain], axis=0).astype(float)
    return SatelliteCrop(storm_id=storm_id, valid_time=valid_time, channels=channels)


def crop_to_cnn_input(crop: SatelliteCrop) -> np.ndarray:
    """(1, C, H, W) float32 array shaped for ``models.cnn.build_cnn``'s forward pass."""
    return crop.channels[np.newaxis, ...].astype(np.float32)
