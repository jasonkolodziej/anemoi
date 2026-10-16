"""Geodesy helpers.

Track errors in this system are reported in nautical miles because that is the
unit NHC verification uses and the unit Scope v2.1 Appendix B states targets in.
Internally everything is great-circle on a spherical Earth, which is accurate to
well under a nautical mile at hurricane-track distances -- far below the ~50 nm
error scale we are trying to measure.
"""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0088
KM_PER_NM = 1.852
NM_PER_DEG_LAT = 60.0


def km_to_nm(km: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(km) / KM_PER_NM if isinstance(km, np.ndarray) else km / KM_PER_NM


def nm_to_km(nm: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(nm) * KM_PER_NM if isinstance(nm, np.ndarray) else nm * KM_PER_NM


def haversine_nm(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> float | np.ndarray:
    """Great-circle distance in nautical miles. Broadcasts over arrays."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    dist_km = 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    out = dist_km / KM_PER_NM
    # Scalar only when the *result* is: a scalar first point against an
    # array of second points is an array of distances. Judging by `lat1`
    # alone called `float()` on that array (#218).
    return float(out) if np.ndim(out) == 0 else out


# The scalar helpers below each delegate to an array form that broadcasts,
# so there is one formula per quantity. Use the array forms for anything
# per-member or per-lead: a Python loop of scalar calls costs ~10 us a point
# in NumPy call overhead, which was most of a training run's verification
# time and of a cycle's product building (#218).


def bearings_deg(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> np.ndarray:
    """Initial great-circle bearing from point 1 to point 2, degrees clockwise
    from north. Broadcasts over arrays."""
    phi1 = np.radians(np.asarray(lat1, dtype=float))
    phi2 = np.radians(np.asarray(lat2, dtype=float))
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    y = np.sin(dlon) * np.cos(phi2)
    x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlon)
    return (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2, degrees clockwise from north."""
    return float(bearings_deg(lat1, lon1, lat2, lon2))


def offset_positions(
    lat: float | np.ndarray,
    lon: float | np.ndarray,
    distance_nm: float | np.ndarray,
    bearing: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Displace positions by ``distance_nm`` along ``bearing`` (deg from
    north). Broadcasts over arrays; returns ``(lat, lon)`` arrays."""
    ang = np.asarray(distance_nm, dtype=float) * KM_PER_NM / EARTH_RADIUS_KM
    phi1 = np.radians(np.asarray(lat, dtype=float))
    lam1 = np.radians(np.asarray(lon, dtype=float))
    theta = np.radians(np.asarray(bearing, dtype=float))
    phi2 = np.arcsin(np.sin(phi1) * np.cos(ang) + np.cos(phi1) * np.sin(ang) * np.cos(theta))
    lam2 = lam1 + np.arctan2(
        np.sin(theta) * np.sin(ang) * np.cos(phi1),
        np.cos(ang) - np.sin(phi1) * np.sin(phi2),
    )
    return np.degrees(phi2), wrap_longitude(np.degrees(lam2))


def offset_position(lat: float, lon: float, distance_nm: float, bearing: float) -> tuple[float, float]:
    """Displace a position by ``distance_nm`` along ``bearing`` (deg from north)."""
    lat2, lon2 = offset_positions(lat, lon, distance_nm, bearing)
    return float(lat2), float(lon2)


def wrap_longitude(lon: float | np.ndarray) -> float | np.ndarray:
    """Wrap longitude into [-180, 180)."""
    return (np.asarray(lon, dtype=float) + 180.0) % 360.0 - 180.0


def cross_along_track_nm(
    fcst_lat: float,
    fcst_lon: float,
    obs_lat: float,
    obs_lon: float,
    motion_bearing: float,
) -> tuple[float, float]:
    """Decompose a track error into (cross-track, along-track) nm.

    Positive cross-track means the forecast lies to the right of the observed
    storm motion; positive along-track means the forecast is ahead of it. This
    decomposition is what makes a bias diagnosable (a fast bias and a rightward
    bias have completely different causes).
    """
    cross, along = cross_along_track_nms(fcst_lat, fcst_lon, obs_lat, obs_lon, motion_bearing)
    return float(cross), float(along)


def cross_along_track_nms(
    fcst_lat: float | np.ndarray,
    fcst_lon: float | np.ndarray,
    obs_lat: float | np.ndarray,
    obs_lon: float | np.ndarray,
    motion_bearing: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Array form of `cross_along_track_nm`: broadcasts over arrays and
    returns ``(cross, along)`` arrays."""
    dist = np.asarray(haversine_nm(obs_lat, obs_lon, fcst_lat, fcst_lon), dtype=float)
    brg = bearings_deg(obs_lat, obs_lon, fcst_lat, fcst_lon)
    delta = np.radians(brg - np.asarray(motion_bearing, dtype=float))
    return dist * np.sin(delta), dist * np.cos(delta)
