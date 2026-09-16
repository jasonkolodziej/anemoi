"""Storm-relative coordinate transform for track-sequence model inputs.

PLAN.md §5 "Sample size" (#9): raw absolute lat/lon in a training sequence
ties a sample's meaning to *where on Earth* a storm happened to be, which the
archive (~1,200 storms, a few tens of thousands of synoptic fixes) is too
thin to marginalise out by brute force -- two storms with identical motion
and intensity histories look unrelated to the model if one recurved off Cuba
and the other off Japan. Recasting position history as step-to-step
displacement -- how far and which way the storm moved -- removes that
dependency, and matches the model output convention already in place
(``models.base.ModelSpec``: outputs are ``(delta_lat, delta_lon, wind)`` per
lead, relative to the current fix, not absolute coordinates).

Latitude itself is not dropped: Coriolis-driven beta drift is a real,
latitude-dependent effect on storm motion, so the current fix's absolute
latitude is retained as a conditioning feature.
"""

from __future__ import annotations

import numpy as np

from ..geo import bearing_deg, haversine_nm
from .besttrack import Fix

#: Columns produced by :func:`storm_relative_sequence`, in order.
STORM_RELATIVE_COLUMNS: tuple[str, ...] = (
    "dx_east_nm",
    "dy_north_nm",
    "max_wind_kt",
    "min_pressure_mb",
    "latitude_deg",
)


def displacement_nm(prev: Fix, cur: Fix) -> tuple[float, float]:
    """East/north displacement (nm) from ``prev`` to ``cur``, bearing decomposed
    into Cartesian components (positive east, positive north)."""
    distance_nm = haversine_nm(prev.lat, prev.lon, cur.lat, cur.lon)
    theta = np.radians(bearing_deg(prev.lat, prev.lon, cur.lat, cur.lon))
    return float(distance_nm * np.sin(theta)), float(distance_nm * np.cos(theta))


def storm_relative_sequence(fixes: tuple[Fix, ...]) -> np.ndarray:
    """``(len(fixes) - 1, 5)`` storm-relative sequence from a window of fixes.

    Row ``i`` describes ``fixes[i + 1]`` relative to ``fixes[i]``: east/north
    displacement in nautical miles from the *previous* fix (bearing decomposed
    into Cartesian components, positive east / positive north), the current
    fix's wind and pressure, and its absolute latitude.

    Needs one extra fix of lookback versus the desired sequence length -- e.g.
    ``track.window_ending(ts, length + 1)`` -- so every output row carries a
    real motion vector rather than a zero-padded first step.
    ``besttrack.Track.window_ending`` already follows a return-None-rather-
    than-pad convention for the same reason: a fabricated "no motion" step
    for a storm that in fact had a predecessor would misrepresent its
    history, not just leave it incomplete.
    """
    if len(fixes) < 2:
        raise ValueError(
            f"need at least 2 fixes (1 lookback + >=1 sequence step), got {len(fixes)}"
        )
    storm_ids = {f.storm_id for f in fixes}
    if len(storm_ids) > 1:
        raise ValueError(f"fixes span multiple storms: {sorted(storm_ids)}")

    rows = []
    for prev, cur in zip(fixes, fixes[1:], strict=False):
        dx_east_nm, dy_north_nm = displacement_nm(prev, cur)
        rows.append([dx_east_nm, dy_north_nm, cur.max_wind_kt, cur.min_pressure_mb, cur.lat])
    return np.array(rows, dtype=float)
