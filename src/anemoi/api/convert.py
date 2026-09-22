"""Dataclass -> Pydantic conversion. Kept separate from the routers so a
router's job stays "parse request, call the domain layer, convert result" --
never re-deriving a field the dataclass already computed.
"""

from __future__ import annotations

from ..branding import FUSION_COLOR, GODS, STRUCTURAL_COLORS, WindGod
from ..data.sources import DataSource
from ..inference.cycle import CycleOutput
from ..inference.scheduler import CyclePlan
from ..monitoring.drift import DriftReport
from ..monitoring.skew import SkewReport
from ..tracking.registry import ModelVersion
from ..training.triggers import RetrainJob
from . import schemas as s


def god_out(g: WindGod) -> s.WindGodOut:
    return s.WindGodOut(
        slug=g.slug,
        name=g.name,
        direction=g.direction,
        color=g.color,
        architecture=g.architecture,
        module=g.module.value,
        persona=g.persona,
    )


def model_catalog() -> s.ModelCatalog:
    return s.ModelCatalog(
        gods=[god_out(g) for g in GODS],
        fusion_color=FUSION_COLOR,
        structural_colors=dict(STRUCTURAL_COLORS),
    )


def source_out(src: DataSource) -> s.SourceOut:
    return s.SourceOut(
        key=src.key,
        provider=src.provider,
        role=src.role.value,
        is_operational=src.is_operational,
        typical_latency_minutes=src.typical_latency.total_seconds() / 60.0,
        max_latency_minutes=src.max_latency.total_seconds() / 60.0,
        fmt=src.fmt,
        retention=src.retention,
        notes=src.notes,
    )


def cycle_plan_out(plan: CyclePlan) -> s.CyclePlanOut:
    return s.CyclePlanOut(
        label=plan.label,
        target_time=plan.target_time,
        cycle_start=plan.cycle_start,
        advisory_deadline=plan.advisory_deadline,
        core_ready_target=plan.core_ready_target,
        spread_ready_target=plan.spread_ready_target,
        spread_ready_max=plan.spread_ready_max,
        margin_target_minutes=plan.margin_target.total_seconds() / 60.0,
        margin_max_minutes=plan.margin_max.total_seconds() / 60.0,
        meets_advisory_deadline=plan.meets_advisory_deadline,
        vitals_estimated=plan.vitals_estimated,
        load_shed=plan.load_shed,
        degraded=plan.degraded,
        stages=[
            s.StageOut(stage=st.stage.value, start=st.start, end_target=st.end_target, end_max=st.end_max)
            for st in plan.stages
        ],
    )


def cycle_payload_out(output: CycleOutput) -> s.CyclePayload:
    return s.CyclePayload.model_validate(output.payload())


def cycle_products_out(output: CycleOutput) -> s.CycleProducts:
    det = output.deterministic
    track = [
        s.TrackPointOut(lead_hours=lh, lat=round(float(lat), 3), lon=round(float(lon), 3), wind_kt=round(float(w), 1))
        for lh, lat, lon, w in zip(det.lead_hours, det.lats, det.lons, det.winds_kt, strict=True)
    ]
    per_model_tracks = {
        name: [
            s.TrackPointOut(
                lead_hours=lh, lat=round(float(row[0]), 3), lon=round(float(row[1]), 3),
                wind_kt=round(float(row[2]), 1),
            )
            for lh, row in zip(det.lead_hours, abs_pred, strict=True)
        ]
        for name, abs_pred in det.per_model_tracks.items()
    }
    pdf = [
        s.IntensityPercentiles(
            lead_hours=lead,
            p10=round(pct[10], 1),
            p25=round(pct[25], 1),
            p50=round(pct[50], 1),
            p75=round(pct[75], 1),
            p90=round(pct[90], 1),
        )
        for lead, pct in output.products.intensity_pdf.items()
    ]
    return s.CycleProducts(
        deterministic_track=track,
        contributors=dict(det.contributors),
        per_model_tracks=per_model_tracks,
        missing_model_reasons=dict(det.missing_model_reasons),
        intensity_pdf=pdf,
        landfall_probability=output.products.landfall_probability,
        notes=list(output.products.notes),
        degraded=output.products.degraded,
    )


def cycle_result_out(storm_id: str, output: CycleOutput) -> s.CycleResult:
    return s.CycleResult(
        storm_id=storm_id,
        payload=cycle_payload_out(output),
        products=cycle_products_out(output),
        on_time=output.on_time,
    )


def model_version_out(v: ModelVersion) -> s.ModelVersionOut:
    return s.ModelVersionOut(
        name=v.name,
        version=v.version,
        stage=v.stage.value,
        run_id=v.run_id,
        metrics=dict(v.metrics),
        created_at=v.created_at,
        tags=dict(v.tags),
        input_flavor=v.input_flavor.value,
        latent_signature=v.latent_signature,
        checkpoint_uri=v.checkpoint_uri,
    )


def drift_report_out(model: str, flavor: str, report: DriftReport) -> s.DriftReportOut:
    from datetime import UTC, datetime

    return s.DriftReportOut(
        model=model,
        flavor=flavor,
        generated_at=datetime.now(UTC),
        features=[
            s.FeatureDriftOut(
                name=f.name,
                standardized_shift=round(f.standardized_shift, 3),
                variance_ratio=round(f.variance_ratio, 3),
                drifted=f.drifted,
            )
            for f in report.features
        ],
        n_live=report.n_live,
        alert=report.alert,
        summary=report.summary(),
    )


def skew_report_out(report: SkewReport) -> s.SkewReportOut:
    return s.SkewReportOut(
        lead_hours=report.lead_hours,
        n=report.n,
        window_start=report.window_start,
        window_end=report.window_end,
        mean_track_delta_nm=round(report.mean_track_delta_nm, 2),
        mean_abs_intensity_delta_kt=round(report.mean_abs_intensity_delta_kt, 2),
        intensity_bias_kt=round(report.intensity_bias_kt, 2),
        alert=report.alert,
        reasons=list(report.reasons),
    )


def retrain_job_out(job: RetrainJob) -> s.RetrainJobOut:
    return s.RetrainJobOut(
        model=job.model,
        reason=job.reason.value,
        mode=job.mode.value,
        cascaded=job.cascaded,
        note=job.note,
        trigger_tag=job.trigger_tag.value,
    )
