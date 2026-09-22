"""Real NOAA GEFS ensemble perturbation members (the ``ensemble_perturbations``
source, #147) -- Anemoi-Spread's real conditioning input once something
consumes it (nothing does yet -- see the module-level note near the bottom).

Format reference: NOAA GEFS on AWS Open Data (``noaa-gefs-pds``), plain
anonymous S3, real archive since 2017-01-01 (confirmed live 2026-09-22).
Same GRIB2 + ``.idx`` byte-range-fetch shape as ``real_gridded``'s GDAS
fetch -- verified live that GEFS's ``.idx`` carries the *exact* messages
(``UGRD``/``VGRD``/``HGT``/``TMP``/``RH`` at the same pressure levels,
plus ``PRMSL``) that :data:`real_gridded.GDAS_LEVEL_MESSAGES` already
selects for GDAS, in the identical colon-separated index format -- so
this module reuses those constants and :func:`real_gridded._parse_grib2_index`
directly rather than redefining them.

The registry's own note ("t-6 members valid at t") means: a real cycle
targeting valid time ``t`` reads the GEFS cycle that started 6 hours
earlier, at forecast hour 6 -- this module's ``target_valid_time``
parameter does that subtraction so callers pass the time they actually
care about, not a pre-computed cycle/lead pair.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .real_gridded import (
    GDAS_LEVEL_MESSAGES,
    GDAS_MSLP_KEY,
    _parse_grib2_index,
    require_gdas_deps,
)

GEFS_BUCKET_URL = "https://noaa-gefs-pds.s3.amazonaws.com"

#: Real GEFS perturbation members -- confirmed live: gep01..gep30 (30
#: perturbed members), plus gec00 (control, unperturbed).
GEFS_PERTURBED_MEMBERS: tuple[int, ...] = tuple(range(1, 31))

#: Lead hour used for "conditioning at target_valid_time" -- see module
#: docstring's "t-6 members valid at t" note. Real GEFS also archives
#: f000 (its own analysis-equivalent), but f006 is what the registry's
#: latency semantics describe.
_TARGET_LEAD_HOURS = 6


def _gefs_member_url(cycle_time: datetime, member: int, lead_hours: int) -> str:
    if member not in range(0, 31):
        raise ValueError(f"member must be 0 (control) or 1-30 (perturbed), got {member}")
    name = "gec00" if member == 0 else f"gep{member:02d}"
    return (
        f"{GEFS_BUCKET_URL}/gefs.{cycle_time:%Y%m%d}/{cycle_time:%H}/atmos/pgrb2ap5/"
        f"{name}.t{cycle_time:%H}z.pgrb2a.0p50.f{lead_hours:03d}"
    )


def fetch_gefs_member_grib2_fields(
    cycle_time: datetime, member: int, *, lead_hours: int = _TARGET_LEAD_HOURS,
    timeout: float = 60.0, session: Any = None,
) -> dict[tuple[str, int | str], np.ndarray]:
    """Byte-range fetch one real GEFS member's fields at ``cycle_time`` +
    ``lead_hours`` -- same messages, same return shape as
    :func:`real_gridded.fetch_gdas_grib2_fields`, so a caller already
    handling GDAS's field dict can handle one ensemble member's the same
    way. ``member=0`` fetches the unperturbed control run.
    """
    require_gdas_deps()
    import eccodes  # noqa: PLC0415
    import requests  # noqa: PLC0415

    http = session if session is not None else requests

    url = _gefs_member_url(cycle_time, member, lead_hours)
    idx_resp = http.get(f"{url}.idx", timeout=timeout)
    idx_resp.raise_for_status()
    byte_ranges = _parse_grib2_index(idx_resp.text)

    targets = [(sn, f"{lvl} mb", (sn, lvl)) for sn, lvl in GDAS_LEVEL_MESSAGES]
    targets.append((*GDAS_MSLP_KEY, GDAS_MSLP_KEY))

    fields: dict[tuple[str, int | str], np.ndarray] = {}
    for short_name, level_label, out_key in targets:
        start, end = byte_ranges.get((short_name, level_label), (None, None))
        if start is None:
            raise KeyError(f"{short_name}:{level_label} not found in {url}.idx")
        range_header = f"bytes={start}-{end - 1}" if end is not None else f"bytes={start}-"
        msg_resp = http.get(url, headers={"Range": range_header}, timeout=timeout)
        msg_resp.raise_for_status()

        gid = eccodes.codes_new_from_message(msg_resp.content)
        try:
            values = eccodes.codes_get_values(gid)
            nlat = eccodes.codes_get(gid, "Nj")
            nlon = eccodes.codes_get(gid, "Ni")
        finally:
            eccodes.codes_release(gid)
        fields[out_key] = values.reshape(nlat, nlon)

    return fields


def fetch_gefs_ensemble_grib2_fields(
    target_valid_time: datetime, members: tuple[int, ...], *,
    timeout: float = 60.0, session: Any = None,
) -> dict[int, dict[tuple[str, int | str], np.ndarray]]:
    """Real per-member fields for every member in ``members``, all valid
    at ``target_valid_time`` (each fetched from the GEFS cycle 6 hours
    earlier, per the registry's "t-6 members valid at t" convention).

    No default for ``members`` deliberately -- a full 30-member ensemble
    is ~240 real HTTP requests (30 members x ~8 messages each); callers
    must choose how many they actually need rather than silently paying
    for all 30.
    """
    cycle_time = target_valid_time - timedelta(hours=_TARGET_LEAD_HOURS)
    return {
        member: fetch_gefs_member_grib2_fields(
            cycle_time, member, lead_hours=_TARGET_LEAD_HOURS, timeout=timeout, session=session,
        )
        for member in members
    }


#: Nothing in this codebase consumes ensemble_perturbations as a real
#: model input yet (same situation data.real_microwave's SSMIS fetch
#: was in before this module) -- this is real fetch only, no Anemoi-
#: Spread conditioning contract invented here. `models.diffusion`'s
#: real conditioning path is unchanged; wiring this in is separate,
#: real future work once something is designed to consume it.
