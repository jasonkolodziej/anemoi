"""NHC's own verification of its official forecast, one row per forecast.

NHC publishes the error of every official forecast it verified, since 1989,
as fixed-width text: one file for the Atlantic and one for the East Pacific
(`OFFICIAL_ERRORS_FILES`; there is none for the Central Pacific, whose
forecasts are CPHC's). Each row is one initial time of one storm, with the
track error in n mi and the signed intensity error in kt at each lead, and
``-9999`` where NHC did not verify that lead.

`training.baseline_backtest.reconcile_official_errors` scores the same
forecasts from the a-deck and HURDAT2 under NHC's rules and compares case by
case with this file. That is the check that the a-deck join (initial time,
lead, sign of the longitude, which advisory) is right: without it a silent
off-by-one-cycle would bias every baseline number built on the join.

The header states the rules NHC applied, and they are read from it rather
than assumed: the stages verified, and the initial-position domain (the
East Pacific file stops at 140W, where CPHC's area begins).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

#: basin -> the file NHC publishes its per-forecast official errors in.
OFFICIAL_ERRORS_FILES: dict[str, str] = {
    "AL": "1989-present_OFCL_v_BCD5_ind_ATL_TI_errors.txt",
    "EP": "1989-present_OFCL_v_BCD5_ind_EPAC_TI_errors.txt",
}
OFFICIAL_ERRORS_URL = "https://www.nhc.noaa.gov/verification/errors/{name}"

#: The file's sentinel for a lead NHC did not verify is -9999.
_MISSING_BELOW = -9000.0

_DOMAIN_RE = re.compile(
    r"Initial position domain:\s+(\d+)([NS])-(\d+)([NS])\s+(\d+)([EW])-(\d+)([EW])"
)
_COLUMN_RE = re.compile(r"(\d{3})h([TI])01")


class OfficialErrorsError(ValueError):
    """Not one of NHC's per-forecast official error files."""


@dataclass(frozen=True, slots=True)
class OfficialErrors:
    """NHC's verified official forecasts, by ``(storm_id, initial time,
    lead in hours)``: the track error in n mi, and the signed intensity
    error in kt (positive: forecast too strong)."""

    track_nm: dict[tuple[str, datetime, int], float]
    intensity_kt: dict[tuple[str, datetime, int], float]
    #: The initial-position domain the header states, in degrees (north and
    #: east positive): south, north, west, east. None when it states none.
    domain: tuple[float, float, float, float] | None

    def in_domain(self, lat: float, lon: float) -> bool:
        """Whether an initial position is one NHC's file covers."""
        if self.domain is None:
            return True
        south, north, west, east = self.domain
        return south <= lat <= north and west <= lon <= east


def _signed(value: str, hemisphere: str) -> float:
    return float(value) * (1.0 if hemisphere in "NE" else -1.0)


def parse_official_errors(text: str) -> OfficialErrors:
    """Parse one of NHC's per-forecast official error files.

    The columns are found by name in the file's own header row
    (``048hT01`` is the 48 h track error of model 1, the official forecast;
    ``048hI01`` its intensity error), so a lead NHC adds or drops does not
    shift the others. Rows that are not data are skipped.
    """
    domain = None
    columns: dict[int, tuple[str, int]] = {}  # field index -> (quantity, lead)
    track: dict[tuple[str, datetime, int], float] = {}
    intensity: dict[tuple[str, datetime, int], float] = {}
    for line in text.splitlines():
        if not columns:
            match = _DOMAIN_RE.search(line)
            if match:
                g = match.groups()
                south, north = sorted((_signed(g[0], g[1]), _signed(g[2], g[3])))
                west, east = sorted((_signed(g[4], g[5]), _signed(g[6], g[7])))
                domain = (south, north, west, east)
            if line.startswith("Date/Time"):
                for index, name in enumerate(line.split()):
                    column = _COLUMN_RE.fullmatch(name)
                    if column:
                        columns[index] = (column.group(2), int(column.group(1)))
            continue
        fields = line.split()
        if len(fields) <= max(columns):
            continue
        try:
            init_time = datetime.strptime(fields[0], "%d-%m-%Y/%H:%M:%S").replace(tzinfo=UTC)
        except ValueError:
            continue
        storm_id = fields[1]
        for index, (quantity, lead) in columns.items():
            try:
                value = float(fields[index])
            except ValueError:
                continue
            if value < _MISSING_BELOW:
                continue
            (track if quantity == "T" else intensity)[(storm_id, init_time, lead)] = value
    if not columns:
        raise OfficialErrorsError("no 'Date/Time' column header: not an official error file")
    return OfficialErrors(track_nm=track, intensity_kt=intensity, domain=domain)
