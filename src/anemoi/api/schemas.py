"""Pydantic v2 response/request models for Anemoi-API v1.

Field names in :class:`CyclePayload` intentionally mirror
``CycleOutput.payload()`` (the wire shape documented on the wiki's
Inference Cycle page) exactly, so the API's ``/cycles/{cycle}`` response is
byte-for-byte the same JSON a consumer already reading dissemination output
would recognise. Everything else here is additive.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WindGodOut(BaseModel):
    slug: str
    name: str
    direction: str
    color: str
    architecture: str
    module: str
    persona: str


class ModelCatalog(BaseModel):
    gods: list[WindGodOut]
    fusion_color: str
    structural_colors: dict[str, str]


class SourceOut(BaseModel):
    key: str
    provider: str
    role: str
    is_operational: bool
    typical_latency_minutes: float
    max_latency_minutes: float
    fmt: str
    retention: str
    notes: str = ""


class StageOut(BaseModel):
    stage: str
    start: datetime
    end_target: datetime
    end_max: datetime


class CyclePlanOut(BaseModel):
    """A planned (not yet run) cycle -- what ``anemoi schedule`` prints."""

    label: str
    target_time: datetime
    cycle_start: datetime
    advisory_deadline: datetime
    core_ready_target: datetime
    spread_ready_target: datetime
    spread_ready_max: datetime
    margin_target_minutes: float
    margin_max_minutes: float
    meets_advisory_deadline: bool
    vitals_estimated: bool
    load_shed: bool
    degraded: bool
    stages: list[StageOut]


class ScheduleOut(BaseModel):
    date: str
    worst_case: bool
    plans: list[CyclePlanOut]


class ConeSegmentOut(BaseModel):
    lead_hours: int
    lat: float
    lon: float
    radius_nm: float
    basis: str = Field(description="'ensemble' or 'climatology'")


class CyclePayload(BaseModel):
    """Exact shape of ``CycleOutput.payload()`` -- the dissemination JSON."""

    model_config = ConfigDict(populate_by_name=True)

    cycle: str
    issued_at: datetime
    advisory_deadline: datetime
    nwp_cycle_lag_hours: int
    vitals: str
    ensemble_size: int
    rapid_intensification: bool
    ri_probability: float
    cone: list[ConeSegmentOut]
    flags: list[str]
    #: The real coastal reference point `landfall_probability` was computed
    #: against -- `None` whenever the run_cycle request didn't supply one
    #: (the same condition that leaves `products.landfall_probability` `None`).
    coastline_lat: float | None = None
    coastline_lon: float | None = None


class IntensityPercentiles(BaseModel):
    lead_hours: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class TrackPointOut(BaseModel):
    lead_hours: int
    lat: float
    lon: float
    wind_kt: float


class CycleProducts(BaseModel):
    """Extended products payload -- the parts of ``ForecastProducts`` that
    ``CycleOutput.payload()`` does not disseminate (§6.1 full product suite).
    Proposed v1 addition; see docs/api.md ("The payload is a contract, not a
    convenience") and the wiki's API page for the full shape.
    """

    deterministic_track: list[TrackPointOut]
    contributors: dict[str, float]
    #: Each contributing Group 1 model's own track, keyed by architecture
    #: slug (lstm/cnn/transformer/gnn/pinn) -- same real per-model
    #: prediction `deterministic_track`/`contributors` are fused from, not
    #: derived after the fact. Empty for the synthetic fallback and demo
    #: cycles (neither runs a real per-model forward pass).
    per_model_tracks: dict[str, list[TrackPointOut]]
    #: Why each Group 1 model that *isn't* in `contributors`/`per_model_
    #: tracks` was skipped, keyed the same way (architecture slug). Real,
    #: not derived after the fact -- see `DeterministicForecast.missing_
    #: model_reasons`. Empty for the synthetic fallback and demo cycles.
    missing_model_reasons: dict[str, str]
    intensity_pdf: list[IntensityPercentiles]
    landfall_probability: float | None
    notes: list[str]
    degraded: bool


class CycleResult(BaseModel):
    storm_id: str
    payload: CyclePayload
    products: CycleProducts
    on_time: bool


class FixOut(BaseModel):
    valid_time: datetime
    lat: float
    lon: float
    max_wind_kt: float
    min_pressure_mb: float
    quality: str


class StormSummary(BaseModel):
    storm_id: str
    #: The storm's public name (e.g. "Fay"), when the source carries one --
    #: None for an unnamed archive storm or a fully synthetic demo storm,
    #: never a fabricated placeholder.
    name: str | None = None
    season: int
    active: bool
    latest_fix: FixOut
    peak_wind_kt: float
    last_cycle: str | None = None
    #: Two-letter ATCF basin code, e.g. "AL"/"EP" -- a direct slice of
    #: storm_id (see `data.atcf.storm_basin`), not a new data source.
    basin: str
    #: False for any basin outside `data.atcf.TRAINED_BASINS` -- real storm
    #: data (the live feed and HURDAT2 both cover more than the Atlantic),
    #: but genuinely out-of-distribution for every currently trained model.
    trained_basin: bool


class StormDetail(StormSummary):
    history: list[FixOut]
    cycles: list[str]


class RunCycleRequest(BaseModel):
    cycle: str = Field(description="Cycle label, e.g. '20260806_06Z'")
    lat: float | None = Field(default=None, description="Override fix latitude")
    lon: float | None = Field(default=None, description="Override fix longitude")
    wind_kt: float | None = Field(default=None, description="Override fix max wind (kt)")
    members: int = Field(default=20, ge=1, le=100)
    worst_case: bool = False
    coastline_lat: float | None = None
    coastline_lon: float | None = None


class ModelVersionOut(BaseModel):
    name: str
    version: int
    stage: str
    run_id: str
    metrics: dict[str, float]
    created_at: datetime
    tags: dict[str, str]
    input_flavor: str
    latent_signature: str | None
    checkpoint_uri: str | None


class RegistryEntry(BaseModel):
    model: str
    latest: ModelVersionOut | None
    production: ModelVersionOut | None
    versions: list[ModelVersionOut]


class ActivePin(BaseModel):
    label: str
    latent_signature: str
    members: dict[str, int]


class FeatureDriftOut(BaseModel):
    name: str
    standardized_shift: float
    variance_ratio: float
    drifted: bool


class DriftReportOut(BaseModel):
    """``DriftReport`` plus the API-level context (model, flavor, when) it
    does not itself carry -- drift is reported per model on request, not
    stored on the dataclass."""

    model: str
    flavor: str
    generated_at: datetime
    features: list[FeatureDriftOut]
    n_live: int
    alert: bool
    summary: str


class SkewReportOut(BaseModel):
    lead_hours: int
    n: int
    window_start: datetime
    window_end: datetime
    mean_track_delta_nm: float
    mean_abs_intensity_delta_kt: float
    intensity_bias_kt: float
    alert: bool
    reasons: list[str]


class LeadCalibrationOut(BaseModel):
    """Real served-product calibration for one (lead, product) pair
    (#166's live-monitoring follow-up) -- was the cone/intensity band
    this system actually served right, once the real truth became
    known. ``containment_rate`` is ``None`` (not 0.0) when ``n_cases``
    is too low to report honestly -- see
    ``monitoring.calibration_audit.MIN_CASES``."""

    lead_hours: int
    quantity: str = Field(description="'cone' or 'intensity'")
    n_cases: int
    containment_rate: float | None
    nominal_rate: float
    verdict: str = Field(
        description="'too narrow', 'too wide', 'calibrated', or 'not enough data'"
    )


class RetrainJobOut(BaseModel):
    model: str
    reason: str
    mode: str
    cascaded: bool
    note: str
    trigger_tag: str


class DegradedFlagRef(BaseModel):
    """One entry in the documented flag vocabulary (see docs/api.md)."""

    pattern: str
    meaning: str
    severity: str


class HealthOut(BaseModel):
    status: str
    api_version: str
    anemoi_version: str
    torch_available: bool
    #: "demo" (synthetic storms/models, always available) or "real"
    #: (real HURDAT2 storms + real trained models via #78/#85) -- which
    #: `deps.state_dependency` is currently serving, so a client (the
    #: console frontend) can label data honestly instead of always
    #: saying "demo" even once real state is opted into.
    state_mode: str
