"""Real served-product calibration monitor (monitoring.calibration_audit,
#166's live-monitoring follow-up)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from anemoi.api.schemas import (
    ConeSegmentOut,
    CyclePayload,
    CycleProducts,
    CycleResult,
    IntensityPercentiles,
)
from anemoi.data.besttrack import Fix, TrackQuality
from anemoi.monitoring.calibration_audit import (
    CALIBRATION_SAMPLES_KEY,
    CONE_NOMINAL_RATE,
    INTENSITY_NOMINAL_RATE,
    MIN_CASES,
    CalibrationSample,
    audit_cycle,
    audit_due,
    audit_storm,
    calibrate_products,
    load_calibration_samples,
    save_calibration_samples,
)
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

_TARGET = datetime(2026, 9, 1, 0, tzinfo=UTC)
_CONFIG = S3Config(
    endpoint_url="https://example.r2.cloudflarestorage.com",
    bucket="anemoi-checkpoints", access_key_id="key", secret_access_key="secret",
)


class _FakeClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = local_path.read_bytes()

    def get(self, key, local_path):
        local_path.write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def _fix(valid_time: datetime, lat: float, lon: float, wind_kt: float = 60.0) -> Fix:
    return Fix(
        storm_id="AL012026", valid_time=valid_time, lat=lat, lon=lon,
        max_wind_kt=wind_kt, min_pressure_mb=985.0, quality=TrackQuality.WORKING,
    )


def _result(
    lead_hours=(12, 24),
    cone=None,
    pdf=None,
    label="20260901_00Z",
) -> CycleResult:
    cone = cone if cone is not None else [
        ConeSegmentOut(lead_hours=h, lat=20.0, lon=-60.0, radius_nm=50.0, basis="ensemble")
        for h in lead_hours
    ]
    pdf = pdf if pdf is not None else [
        IntensityPercentiles(lead_hours=h, p10=50.0, p25=55.0, p50=60.0, p75=65.0, p90=70.0)
        for h in lead_hours
    ]
    return CycleResult(
        storm_id="AL012026",
        payload=CyclePayload(
            cycle=label, issued_at=_TARGET, advisory_deadline=_TARGET + timedelta(hours=3),
            nwp_cycle_lag_hours=6, vitals="observed", ensemble_size=20,
            rapid_intensification=False, ri_probability=0.0, cone=cone, flags=[],
        ),
        products=CycleProducts(
            deterministic_track=[], contributors={"lstm": 1.0}, per_model_tracks={},
            missing_model_reasons={}, intensity_pdf=pdf, landfall_probability=None,
            notes=[], degraded=False,
        ),
        on_time=True,
    )


def test_audit_due_exactly_at_the_leads_own_real_valid_time():
    assert not audit_due(_TARGET, 12, _TARGET + timedelta(hours=11, minutes=59))
    assert audit_due(_TARGET, 12, _TARGET + timedelta(hours=12))
    assert audit_due(_TARGET, 12, _TARGET + timedelta(hours=13))


def test_audit_cycle_scores_a_real_cone_hit_and_a_real_intensity_hit():
    """Truth lands inside both the served cone radius and the served
    p10-p90 band -- both real real product checks should read as hits."""
    result = _result(lead_hours=(12,))
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.05, lon=-60.05, wind_kt=62.0)
    samples = audit_cycle(
        "AL012026", result, {truth.valid_time: truth},
        now=_TARGET + timedelta(hours=12), already_audited=set(),
    )
    assert len(samples) == 1
    s = samples[0]
    assert s.lead_hours == 12
    assert s.cone_basis == "ensemble"
    assert s.cone_hit is True
    assert s.intensity_hit is True


def test_audit_cycle_scores_a_real_cone_miss_and_a_real_intensity_miss():
    """Truth lands well outside both the served cone radius and the
    served p10-p90 band -- both should read as real misses."""
    result = _result(lead_hours=(12,))
    truth = _fix(_TARGET + timedelta(hours=12), lat=25.0, lon=-65.0, wind_kt=120.0)
    samples = audit_cycle(
        "AL012026", result, {truth.valid_time: truth},
        now=_TARGET + timedelta(hours=12), already_audited=set(),
    )
    assert len(samples) == 1
    assert samples[0].cone_hit is False
    assert samples[0].intensity_hit is False


def test_audit_cycle_skips_a_lead_not_yet_due():
    result = _result(lead_hours=(12, 120))
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.0, lon=-60.0)
    samples = audit_cycle(
        "AL012026", result, {truth.valid_time: truth},
        now=_TARGET + timedelta(hours=12), already_audited=set(),
    )
    # Only the 12h lead is due at now=+12h; 120h isn't, and has no real
    # truth fix anyway.
    assert [s.lead_hours for s in samples] == [12]


def test_audit_cycle_skips_a_due_lead_with_no_real_truth_fix_yet():
    """Due by wall-clock time, but this storm's live feed hasn't produced
    a real fix at this exact synoptic time (yet, or ever) -- must not
    fabricate a sample from a nearby-but-wrong fix."""
    result = _result(lead_hours=(12,))
    samples = audit_cycle(
        "AL012026", result, {}, now=_TARGET + timedelta(hours=12), already_audited=set(),
    )
    assert samples == []


def test_audit_cycle_never_re_scores_an_already_audited_lead():
    result = _result(lead_hours=(12,))
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.0, lon=-60.0)
    already = {"AL012026:20260901_00Z:12"}
    samples = audit_cycle(
        "AL012026", result, {truth.valid_time: truth},
        now=_TARGET + timedelta(hours=12), already_audited=already,
    )
    assert samples == []


def test_audit_cycle_leaves_cone_hit_none_when_a_lead_has_no_cone_segment():
    """A real absence (e.g. a worst-case plan that skipped the cone for
    this lead) must read as `None`, never fabricated as a hit or a miss."""
    result = _result(
        lead_hours=(12,),
        cone=[],  # no cone segment for this lead at all
        pdf=[IntensityPercentiles(lead_hours=12, p10=50.0, p25=55.0, p50=60.0, p75=65.0, p90=70.0)],
    )
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.0, lon=-60.0, wind_kt=62.0)
    samples = audit_cycle(
        "AL012026", result, {truth.valid_time: truth},
        now=_TARGET + timedelta(hours=12), already_audited=set(),
    )
    assert len(samples) == 1
    assert samples[0].cone_hit is None
    assert samples[0].cone_basis is None
    assert samples[0].intensity_hit is True


def test_calibration_samples_round_trip_through_save_and_load(tmp_path):
    samples = [
        CalibrationSample(
            storm_id="AL012026", label="20260901_00Z", lead_hours=12,
            cone_basis="ensemble", cone_hit=True, intensity_hit=False,
            audited_at=_TARGET,
        ),
    ]
    path = tmp_path / "calibration_samples.json"
    save_calibration_samples(samples, path)
    restored = load_calibration_samples(path)
    assert restored == samples


def test_calibration_samples_push_and_pull_through_a_real_durable_store(tmp_path):
    store = CheckpointStore(_CONFIG, client=_FakeClient())
    samples = [
        CalibrationSample(
            storm_id="AL012026", label="20260901_00Z", lead_hours=12,
            cone_basis="ensemble", cone_hit=True, intensity_hit=True,
            audited_at=_TARGET,
        ),
    ]
    save_calibration_samples(samples, tmp_path / "a.json", store)
    assert store.exists(CALIBRATION_SAMPLES_KEY)

    fresh_root = tmp_path / "fresh"
    restored = load_calibration_samples(fresh_root / "b.json", store)
    assert restored == samples


def test_audit_storm_persists_new_samples_and_skips_them_on_a_second_pass(tmp_path):
    store = CheckpointStore(_CONFIG, client=_FakeClient())
    from anemoi.api.cycle_store import save_cycle_result

    result = _result(lead_hours=(12,))
    save_cycle_result(store, result)
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.0, lon=-60.0, wind_kt=62.0)

    first = audit_storm(
        "AL012026", ["20260901_00Z"], (truth,), store, tmp_path,
        now=_TARGET + timedelta(hours=12),
    )
    assert len(first) == 1

    second = audit_storm(
        "AL012026", ["20260901_00Z"], (truth,), store, tmp_path,
        now=_TARGET + timedelta(hours=13),
    )
    assert second == []  # already audited -- not re-scored


def test_audit_storm_degrades_past_an_unreadable_stored_cycle(tmp_path):
    """A corrupted/missing stored cycle for one label must not sink the
    whole storm's audit pass -- the same per-record degrade contract
    `monitoring.skew_audit.list_operational_records` already uses."""
    store = CheckpointStore(_CONFIG, client=_FakeClient())
    truth = _fix(_TARGET + timedelta(hours=12), lat=20.0, lon=-60.0)
    samples = audit_storm(
        "AL012026", ["does-not-exist"], (truth,), store, tmp_path,
        now=_TARGET + timedelta(hours=12),
    )
    assert samples == []


@pytest.mark.parametrize(
    ("hits", "quantity", "expected"),
    [
        ([True] * MIN_CASES, "cone", "too wide"),
        ([False] * MIN_CASES, "cone", "too narrow"),
        # 4/5 hits == 0.8 == INTENSITY_NOMINAL_RATE exactly.
        ([True, True, True, True, False], "intensity", "calibrated"),
    ],
)
def test_calibrate_products_real_verdicts(hits, quantity, expected):
    nominal = CONE_NOMINAL_RATE if quantity == "cone" else INTENSITY_NOMINAL_RATE
    samples = [
        CalibrationSample(
            storm_id="AL012026", label=f"c{i}", lead_hours=12,
            cone_basis="ensemble" if quantity == "cone" else None,
            cone_hit=hit if quantity == "cone" else None,
            intensity_hit=hit if quantity == "intensity" else None,
            audited_at=_TARGET,
        )
        for i, hit in enumerate(hits)
    ]
    reports = calibrate_products(samples)
    report = next(r for r in reports if r.quantity == quantity)
    assert report.n_cases == MIN_CASES
    assert report.nominal_rate == nominal
    assert report.verdict == expected


def test_calibrate_products_reports_not_enough_data_below_min_cases():
    samples = [
        CalibrationSample(
            storm_id="AL012026", label="c0", lead_hours=12,
            cone_basis="ensemble", cone_hit=True, intensity_hit=None,
            audited_at=_TARGET,
        ),
    ]
    reports = calibrate_products(samples)
    cone_report = next(r for r in reports if r.quantity == "cone")
    assert cone_report.n_cases == 1
    assert cone_report.verdict == "not enough data"
    intensity_report = next(r for r in reports if r.quantity == "intensity")
    assert intensity_report.n_cases == 0
    assert intensity_report.containment_rate is None
    assert intensity_report.verdict == "not enough data"


def test_calibrate_products_returns_nothing_for_an_empty_corpus():
    assert calibrate_products([]) == []
