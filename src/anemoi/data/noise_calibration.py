"""Calibrate the working-track noise emulator from real pairs (#216).

Stage B's inputs are final best-track fixes plus noise
(`besttrack.emulate_working_track`), with placeholder sizes in
`configs/curriculum.yaml` -- "replace with numbers from
recalibrate_from_pairs() once paired archive data exists". The archive
exists since #213 (`data.atcf_archive`); this pairs it with HURDAT2.
"""

from __future__ import annotations

from .atcf import pair_by_valid_time
from .besttrack import Fix, Track, recalibrate_from_pairs


def as_issued(fixes: list[Fix]) -> list[Fix]:
    """The first bulletin for each valid time, in time order -- what a cycle
    had when it ran (later bulletins for the same time are corrections)."""
    first: dict = {}
    for fix in fixes:  # issue order
        first.setdefault(fix.valid_time, fix)
    return [first[t] for t in sorted(first)]


def calibrate_season(
    working_by_storm: dict[str, list[Fix]], finals: list[Track],
) -> dict[str, object] | None:
    """Pair each storm's as-issued working fixes with its final track and
    measure the RMS differences. ``None`` when nothing pairs."""
    pairs = []
    storms = []
    for final in finals:
        working = as_issued(working_by_storm.get(final.storm_id, []))
        if not working:
            continue
        matched = pair_by_valid_time(Track(storm_id=final.storm_id, fixes=tuple(working)), final)
        if matched:
            pairs.extend(matched)
            storms.append(final.storm_id)
    if not pairs:
        return None
    noise = recalibrate_from_pairs(pairs)
    return {
        "season": finals[0].season,
        "n_pairs": len(pairs),
        "storms": sorted(storms),
        "position_rms_nm": noise.position_rms_nm,
        "intensity_rms_kt": noise.intensity_rms_kt,
        "pressure_rms_mb": noise.pressure_rms_mb,
    }
