"""Data source registry.

Scope v2.1 §4.1. Each source carries an explicit real-time latency and a
*role*. The role is load-bearing, not documentation: :func:`operational_sources`
is what the inference scheduler is allowed to read, and
:func:`assert_not_operational` is the guard that keeps reanalysis out of the
production path.

A role is permission, not use. Which models read a source today is a separate
table, :data:`MODEL_INPUTS`, and :func:`used_by` is the per-source answer the
API serves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class Role(str, Enum):
    """What a source is permitted to be used for."""

    #: May be read live during a forecast cycle, and used for Stage B
    #: fine-tuning. Whether anything reads it yet is :func:`used_by`.
    OPERATIONAL = "operational"
    #: Stage A pretraining only. Never read during a forecast cycle.
    PRETRAIN_ONLY = "pretrain_only"
    #: Supervision targets and verification. Never a model *input*.
    LABELS_ONLY = "labels_only"


class Flavor(str, Enum):
    """Input distribution a feature or dataset was computed from (§4.6.1)."""

    ERA5_PRETRAIN = "era5_pretrain"
    GDAS_FINETUNE = "gdas_finetune"


@dataclass(frozen=True, slots=True)
class DataSource:
    key: str
    provider: str
    role: Role
    #: Typical wall-clock delay between valid time and availability.
    typical_latency: timedelta
    #: Worst-case delay used for scheduling budgets.
    max_latency: timedelta
    fmt: str
    retention: str
    notes: str = ""

    @property
    def is_operational(self) -> bool:
        return self.role is Role.OPERATIONAL


_H = timedelta(hours=1)
_M = timedelta(minutes=1)
_D = timedelta(days=1)

#: The §4.1 table, as code.
REGISTRY: dict[str, DataSource] = {
    src.key: src
    for src in (
        DataSource(
            key="besttrack_working",
            provider="NHC ATCF (a-/b-deck, TC-Vitals)",
            role=Role.OPERATIONAL,
            typical_latency=45 * _M,
            max_latency=90 * _M,
            fmt="ATCF text",
            retention=(
                "not kept upstream as issued: the working b-deck is overwritten with "
                "the final best track after the season, and TC-Vitals/CurrentStorms "
                "have no documented retention -- archived verbatim to durable storage "
                "after every cycle (data.atcf_archive, #213)"
            ),
            notes="Gating input for the cycle. Noisy real-time fixes.",
        ),
        DataSource(
            key="besttrack_final",
            provider="NHC / NOAA (HURDAT2)",
            role=Role.LABELS_ONLY,
            typical_latency=180 * _D,
            max_latency=365 * _D,
            fmt="CSV / ATCF",
            retention="permanent",
            notes="Post-season reanalysed. Labels and verification only.",
        ),
        DataSource(
            key="gdas_gfs",
            provider="NOAA NOMADS (live cycle feed); AWS Open Data (bulk archival mirror)",
            role=Role.OPERATIONAL,
            typical_latency=int(3.5 * 60) * _M,
            max_latency=4 * _H,
            fmt="GRIB2",
            retention="2021-01-01-present in noaa-gfs-bdp-pds (verified via direct S3 "
            "listing, 2026-09-16); no documented retention policy for this bucket "
            "either way -- see data.gridded_cache's archive-sync path, which backfills "
            "this into permanent storage rather than depending on NOAA's bucket as the "
            "system of record",
            notes=(
                "Operational gridded input; cycle t consumes the t-6 cycle. "
                "No public pre-converted Zarr exists for GDAS/GFS pressure "
                "levels (verified -- dynamical.org's GFS Icechunk stores are "
                "surface/near-surface only), so GRIB2 remains the most "
                "performant format available for this source. "
                "data.real_gridded.fetch_gdas_grib2_fields() reads it via "
                "per-message byte-range fetch against the AWS Open Data "
                "mirror (anonymous, no NOMADS access-window constraint) "
                "rather than downloading the full ~450 MB file. Do not confuse "
                "this bucket (noaa-gfs-bdp-pds) with the older, Unidata-maintained "
                "noaa-gfs-pds, which documents an explicit rolling 4-week archive -- "
                "that policy does not apply here."
            ),
        ),
        DataSource(
            key="era5",
            provider="Google ARCO-ERA5 (Zarr, anonymous GCS); Copernicus CDS (origin, GRIB/NetCDF)",
            role=Role.PRETRAIN_ONLY,
            typical_latency=5 * _D,
            max_latency=90 * _D,
            fmt="Zarr",
            retention="rolling 10yr + permanent storm-relative extracts",
            notes=(
                "Stage A pretraining and the ERA5T skew audit only. "
                "data.real_gridded.open_era5() reads the pre-converted, "
                "analysis-ready ARCO-ERA5 Zarr store directly -- anonymous, "
                "no CDS account, no rate limit -- rather than requesting "
                "GRIB/NetCDF through CDS, which is the most performant path "
                "for this source now that it exists."
            ),
        ),
        DataSource(
            key="goes",
            provider="NOAA AWS (GOES-18/19) -- implemented, data.real_goes",
            role=Role.OPERATIONAL,
            typical_latency=5 * _M,
            max_latency=20 * _M,
            fmt="NetCDF (real per-product fetch: ABI-L2-CMIPF for IR/WV/VIS, "
            "ABI-L2-SSTF for SST, ABI-L2-RRQPEF for rain rate)",
            retention="rolling 1yr raw; permanent storm-relative crops",
            notes=(
                "Real storm-relative crop via lazy fsspec+h5netcdf partial "
                "reads (confirmed live: ~8 MB transferred per crop from a "
                "real ~430 MB full-disk file, not a full download) and real "
                "pyproj geostationary-projection geolocation (verified "
                "against a real active storm's real position). "
                "DQF-flagged pixels masked to NaN, not presented as good."
            ),
        ),
        DataSource(
            key="ndbc",
            provider="NDBC buoy / C-MAN",
            role=Role.OPERATIONAL,
            typical_latency=15 * _M,
            max_latency=1 * _H,
            fmt="whitespace-separated text (not JSON/NetCDF -- corrected "
            "2026-09-22 against the real realtime2 product; see data.real_ndbc)",
            retention="rolling 45 days in the real-time product this reads "
            "(data.real_ndbc); NDBC's separate historical archive holds "
            "more, not fetched here -- corrected from the registry's "
            "earlier unverified 'rolling 3yr'",
        ),
        DataSource(
            key="dropsonde",
            provider="NOAA / AFRC (implemented, data.real_dropsonde)",
            role=Role.OPERATIONAL,
            typical_latency=1 * _H,
            max_latency=3 * _H,
            fmt="BUFR / NetCDF",
            retention="permanent",
            notes=(
                "Event-driven; absent for most cycles. Real per-level "
                "profile decode via eccodes' BUFR reader -- standard WMO "
                "descriptors (pressure/airTemperature/dewpointTemperature/ "
                "windSpeed/windDirection/nonCoordinateGeopotentialHeight), "
                "no proprietary format to reverse-engineer. Confirmed live: "
                "levels are surface-first (pressure decreases monotonically "
                "through the array)."
            ),
        ),
        DataSource(
            key="microwave",
            provider="RSS (SSMIS, F16/F17/F18)",
            role=Role.OPERATIONAL,
            typical_latency=1 * _H,
            max_latency=4 * _H,
            fmt="gzip'd raw uint8 bytemap (not HDF5 -- corrected 2026-09-22 "
            "against the real, fetched format; see data.real_microwave)",
            retention="rolling 2yr + permanent storm crops",
            notes=(
                "Orbit-dependent; opportunistic. typical_latency/max_latency "
                "above are unverified against the real daily-file upload "
                "cadence (confirmed same-day but not yet precisely timed) -- "
                "left as-is rather than guessed at; a real latency "
                "verification pass is separate future work."
            ),
        ),
        DataSource(
            key="sst_ohc",
            provider="NOAA NCEI OISST v2.1 (SST, implemented) + "
            "NOAA OSPO CoastWatch OHC (not implemented)",
            role=Role.OPERATIONAL,
            typical_latency=1 * _D,
            max_latency=2 * _D,
            fmt="NetCDF",
            retention="rolling 5yr",
            notes=(
                "SST half is real (data.real_sst, OISST v2.1). OHC half "
                "isn't wired yet, but a live feed does exist: NOAA OSPO's "
                "CoastWatch OHC files (na14/np14 QG3, 0.25 deg NetCDF) are "
                "current -- na14/2026/ had day 316 (Nov 12) posted Nov 13, "
                "no gaps since Jul 17. The earlier '~8 months stale, stops "
                "2026-01-26' finding was a different endpoint (AOML's HDB "
                "ERDDAP UOHC_2026/TCHP), not this one. OHC still waits on "
                "the 2021-2022 training archive (docs/skill_gap_plan.md "
                "Phase 0/2b); files post ~36h late, so a live cycle reads "
                "D-2."
            ),
        ),
        DataSource(
            key="ensemble_perturbations",
            provider="GEFS (implemented, data.real_ensemble) / ECMWF EPS (not implemented)",
            role=Role.OPERATIONAL,
            typical_latency=4 * _H,
            max_latency=6 * _H,
            fmt="GRIB2",
            retention="2017-01-01-present in noaa-gefs-pds (verified via direct "
            "S3 listing, 2026-09-22) -- not the unverified 'rolling 1yr' this "
            "entry previously claimed",
            notes="Anemoi-Spread conditioning; t-6 members valid at t. Real "
            "fetch reuses real_gridded's GDAS_LEVEL_MESSAGES/_parse_grib2_index "
            "directly -- confirmed live that GEFS's .idx carries the exact "
            "same messages in the identical format. Fetch only, no Anemoi-"
            "Spread conditioning contract wired in yet (nothing consumes it).",
        ),
    )
}


def get(key: str) -> DataSource:
    try:
        return REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"unknown data source {key!r}") from exc


def operational_sources() -> list[DataSource]:
    """Sources the inference path may read."""
    return [s for s in REGISTRY.values() if s.role is Role.OPERATIONAL]


def pretrain_only_sources() -> list[DataSource]:
    return [s for s in REGISTRY.values() if s.role is Role.PRETRAIN_ONLY]


# --- Who uses each source ----------------------------------------------------
#
# The three tables below are the one place this is written down. The API serves
# them (``GET /v1/sources``, ``used_by``) and the console's Sources page and
# system graph draw from that, so a model gaining an input is one edit here.

#: The registry sources each Group 1 model's input is built from, in training
#: and when serving. Models are in catalogue order
#: (``tracking.registry.GROUP1_MODELS``, held equal by tests/test_sources.py).
#:
#: Read from the code (``training.real_run*`` for training,
#: ``training.real_inference_live`` for a live cycle), not from what a model
#: was designed for:
#:
#: * ``lstm`` reads the storm's working-quality track and nothing gridded.
#: * ``cnn``, ``transformer`` and ``gnn`` read the storm-centred field crop:
#:   ERA5 in Stage A, GDAS/GFS in Stage B and in a live cycle. The crop is
#:   centred on the working fix, but no track value is in what they read.
#: * ``pinn`` reads both: an environment vector from the same crop, and the
#:   forecast of its own candidate LSTM, which reads the track.
#:
#: In training the working-quality track is emulated from HURDAT2
#: (``besttrack.augment_track``). That is still ``besttrack_working``, the
#: quality a model is trained to see; ``besttrack_final`` is the label. The
#: one place final fixes reach a model is flagged rather than listed: a cycle
#: run on an archive storm, whose vitals were never kept, is marked
#: ``input:final_best_track`` (``api.real_state``).
#:
#: ``diffusion`` and ``fusion`` are not here: they read the Group 1 models'
#: latents and forecasts, not a source of their own. Fusion also takes a
#: context vector computed from the working track
#: (``training.real_latents.CONTEXT_FEATURE_NAMES``).
MODEL_INPUTS: dict[str, tuple[str, ...]] = {
    "lstm": ("besttrack_working",),
    "cnn": ("gdas_gfs", "era5"),
    "transformer": ("gdas_gfs", "era5"),
    "gnn": ("gdas_gfs", "era5"),
    "pinn": ("besttrack_working", "gdas_gfs", "era5"),
}

#: Sources whose values are the supervision targets.
LABEL_SOURCES: tuple[str, ...] = ("besttrack_final",)

#: Sources kept for verifying forecasts and never fed to a model.
#:
#: Only ``besttrack_final`` is read by verification code today: validation
#: metrics, the promotion gates and the spread backtest all score forecasts
#: against it. For ``dropsonde`` and ``ndbc`` this is a designation
#: (docs/input_sources_plan.md, "Not model inputs"): they will not become model
#: inputs and are meant for checking intensity near landfall, but no
#: verification code reads them yet. Their adapters fetch and decode, and
#: nothing imports them; tests/test_sources.py fails the day something does.
VERIFICATION_SOURCES: tuple[str, ...] = ("besttrack_final", "dropsonde", "ndbc")

#: The :func:`used_by` entries that are not model names.
LABELS = "labels"
VERIFICATION = "verification"


def used_by(key: str) -> tuple[str, ...]:
    """Who uses source ``key`` today.

    In a fixed order: the models that read it as an input, in
    :data:`MODEL_INPUTS` order; then ``"labels"`` if it supplies supervision
    targets; then ``"verification"`` if it is kept for verifying forecasts and
    is never a model input. Empty means the source is registered, and may be
    read as its role allows, but nothing uses it yet.

    ``"verification"`` marks a source that is not a model input, so it is not
    the whole list of what verification reads: the served-product calibration
    monitor (``monitoring.calibration_audit``) scores a served cone against
    the storm's later working fixes, and ``besttrack_working`` is listed by
    its models only. Nor is every ``"verification"`` read yet: see
    :data:`VERIFICATION_SOURCES`.
    """
    get(key)  # an unknown key is a typo, not a source nothing uses
    users = [model for model, inputs in MODEL_INPUTS.items() if key in inputs]
    if key in LABEL_SOURCES:
        users.append(LABELS)
    if key in VERIFICATION_SOURCES:
        users.append(VERIFICATION)
    return tuple(users)


class OperationalUseError(RuntimeError):
    """A non-operational source was requested inside the inference path."""


def assert_not_operational(key: str) -> None:
    """Guard used by the inference path (Scope v2.1 §3.2 "hard rule").

    Raises :class:`OperationalUseError` when code attempts to read a
    pretrain-only or labels-only source during a forecast cycle. This is the
    mechanical enforcement of the train/serve consistency policy -- without it,
    an ERA5 read is a one-line change that silently reintroduces the skew.
    """
    src = get(key)
    if src.role is Role.OPERATIONAL:
        return
    raise OperationalUseError(
        f"source {key!r} has role {src.role.value!r} and must not be read during "
        "a forecast cycle (Scope v2.1 §4.6). Use the operational equivalent: "
        f"{_operational_substitute(key)}"
    )


def _operational_substitute(key: str) -> str:
    return {
        "era5": "gdas_gfs",
        "besttrack_final": "besttrack_working",
    }.get(key, "see §4.1 role column")
