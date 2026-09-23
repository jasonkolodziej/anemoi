"""The real Anemoi-Spread calibration backtest (GitHub #10).

Does the real diffusion ensemble underdisperse -- especially for recurving
storms, where the distribution is bimodal -- and is that evidence enough to
turn on `models.diffusion.build_diffusion(extra_conditioning_dim=...)`?
`train_diffusion_stage`'s own validation only ever scored the ensemble
*mean*; nothing measured spread against real outcomes until this.

What's measured is exactly what production serves:

* **The champions.** Group 1 latents come from the current staging/
  production champions (`real_inference.load_run_artifacts`), and the
  diffusion champion must record their `latent_signature` -- refused
  otherwise, the same rule `real_inference_ensemble.build_real_ensemble_fn`
  applies to a live cycle (§5.7). Measuring a desynced pipeline would
  measure something no real cycle can run.
* **The validation split, never test.** The 2023-2025 test split is a
  rate-limited resource (§4.4, `promotion.TestSetBudget`: every look spends
  some of its power). `real_latents.extract_joint_latents`' storm-disjoint
  val split, with the orchestrator's own seed, reproduces the exact windows
  diffusion was validated on.
* **The same sampling and conversions as production and training.**
  `model.sample(...)` with its own defaults (as `build_real_ensemble_fn`
  calls it), un-standardised with the version's real stats, converted to
  absolute positions with `real_run.displacement_to_latlon` -- observed
  positions derived from the displacement targets the way
  `train_diffusion_stage`'s own validation does, so this agrees with the
  version's registered track-error metric rather than re-deriving truth
  differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from ..metrics.ensemble_calibration import LeadCalibration, calibrate, recurving_cases

if TYPE_CHECKING:
    from ..data.besttrack import Track
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelRegistry

#: Leads where recurvature-driven bimodality matters most (#10's own
#: motivation): a recurving storm's "out to sea or not" split opens up
#: days out, not at 12-24h.
LONG_LEADS: tuple[int, ...] = (72, 96, 120)


class SpreadBacktestError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ConeOutcome:
    """What the real served cone (`inference.postprocess.build_cone`) did on
    these cases: how often it used the ensemble's own spread rather than
    falling back to climatology, and how often the truth then fell outside
    the radius actually served at the longest lead. The cone is a 2/3
    probability circle, so a calibrated cone misses about a third."""

    lead_hours: int
    n_cases: int
    n_ensemble_basis: int
    miss_rate_ensemble: float | None
    miss_rate_climatology: float | None

    def to_dict(self) -> dict:
        return {
            "lead_hours": self.lead_hours,
            "n_cases": self.n_cases,
            "n_ensemble_basis": self.n_ensemble_basis,
            "miss_rate_ensemble": self.miss_rate_ensemble,
            "miss_rate_climatology": self.miss_rate_climatology,
        }


@dataclass(slots=True)
class SpreadBacktestReport:
    diffusion_version: int
    group1_versions: dict[str, int]
    n_members: int
    n_val_cases: int
    overall: list[LeadCalibration]
    recurving: list[LeadCalibration]
    recommendation: str
    reasons: list[str] = field(default_factory=list)
    cone: ConeOutcome | None = None

    def to_dict(self) -> dict:
        return {
            "diffusion_version": self.diffusion_version,
            "group1_versions": self.group1_versions,
            "n_members": self.n_members,
            "n_val_cases": self.n_val_cases,
            "overall": [r.to_dict() for r in self.overall],
            "recurving": [r.to_dict() for r in self.recurving],
            "recommendation": self.recommendation,
            "reasons": self.reasons,
            "cone": self.cone.to_dict() if self.cone else None,
        }


def served_cone_outcome(
    members_abs: np.ndarray, true_abs: np.ndarray, mask: np.ndarray, lead_hours: tuple[int, ...],
) -> ConeOutcome | None:
    """Run the real `build_cone` on each case and score the cone it would
    actually serve at the longest lead that has verifying observations."""
    from ..geo import haversine_nm
    from ..inference.postprocess import EnsembleMember, build_cone

    li = len(lead_hours) - 1
    cases = np.flatnonzero(mask[:, li])
    if len(cases) == 0:
        return None
    hits: dict[str, list[bool]] = {"ensemble": [], "climatology": []}
    for ci in cases:
        members = [
            EnsembleMember(
                member_id=mi, lead_hours=lead_hours,
                lats=members_abs[ci, mi, :, 0], lons=members_abs[ci, mi, :, 1],
                winds_kt=members_abs[ci, mi, :, 2],
            )
            for mi in range(members_abs.shape[1])
        ]
        segments, _notes = build_cone(members, lead_hours)
        seg = segments[li]
        miss = haversine_nm(seg.center_lat, seg.center_lon, *true_abs[ci, li, :2]) > seg.radius_nm
        hits[seg.basis].append(bool(miss))

    def rate(xs: list[bool]) -> float | None:
        return float(np.mean(xs)) if xs else None

    return ConeOutcome(
        lead_hours=int(lead_hours[li]),
        n_cases=len(cases),
        n_ensemble_basis=len(hits["ensemble"]),
        miss_rate_ensemble=rate(hits["ensemble"]),
        miss_rate_climatology=rate(hits["climatology"]),
    )


def recommend_extra_conditioning(
    overall: list[LeadCalibration], recurving: list[LeadCalibration],
) -> tuple[str, list[str]]:
    """The #10 decision rule, stated up front rather than tuned after
    seeing results: extra conditioning is warranted if the *track* spread is
    underdispersed (`metrics.probabilistic.SpreadSkill.underdispersed`, the
    codebase's existing ratio < 0.8 threshold) at a long lead, overall or
    for recurving storms specifically. Intensity is reported but doesn't
    drive this decision -- `extra_conditioning_dim`'s stated purpose is
    raw fields/GEFS perturbations for the bimodal *track* case."""
    reasons: list[str] = []
    for label, results in (("overall", overall), ("recurving", recurving)):
        for r in results:
            if (
                r.lead_hours in LONG_LEADS
                and r.quantity in ("along_track_nm", "cross_track_nm")
                and r.verdict == "underdispersed"
            ):
                reasons.append(
                    f"{label} {r.quantity} at {r.lead_hours}h: spread/skill {r.ratio:.2f} "
                    f"(n={r.n_cases}), truth outside every member in "
                    f"{r.outer_rank_fraction:.0%} of cases"
                )
    if reasons:
        return "warranted", reasons
    long_track = [
        r for r in overall
        if r.lead_hours in LONG_LEADS and r.quantity in ("along_track_nm", "cross_track_nm")
    ]
    if not long_track:
        return "insufficient_data", ["no long-lead track case met the minimum sample size"]
    return "not_warranted", [
        f"overall {r.quantity} at {r.lead_hours}h: spread/skill {r.ratio:.2f} ({r.verdict})"
        for r in long_track
    ]


def run_spread_backtest(
    tracks: list[Track],
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    gdas_cache_dir: Path | str,
    *,
    n_members: int = 20,
    seed: int = 20260806,
    sample_seed: int = 0,
    min_cases: int = 10,
    diffusion_version: int | None = None,
    device=None,
) -> SpreadBacktestReport:
    """Run the real backtest end to end. See the module docstring.

    ``diffusion_version``, when given, measures that specific registered
    version instead of the current champion -- a real candidate not yet
    staged, so it can be measured against real calibration *before* a
    promotion decision, the same "measure before promoting" reasoning
    `evaluate_promotion` already applies to the point-verification metric
    (which doesn't see calibration at all -- a higher-capacity-trained
    candidate can look better on `track_error_48h_nm` while being *more*
    underdispersed, or vice versa, exactly the real case #166 found).
    """
    import torch

    from ..models.base import DEFAULT_LEADS
    from ..tracking.registry import GROUP1_MODELS, RegistryError, latent_signature
    from .real_inference import load_run_artifacts, load_standardization_stats, load_trained_model
    from .real_latents import CONTEXT_FEATURE_NAMES, extract_joint_latents
    from .real_run import displacement_to_latlon

    champions = {m: registry.champion(m) for m in GROUP1_MODELS}
    missing = [m for m, v in champions.items() if v is None]
    if missing:
        raise SpreadBacktestError(f"no staging/production champion for: {missing}")
    group1_versions = {m: v.version for m, v in champions.items()}

    if diffusion_version is not None:
        try:
            diffusion = registry.get("diffusion", diffusion_version)
        except RegistryError as exc:
            raise SpreadBacktestError(str(exc)) from exc
    else:
        diffusion = registry.champion("diffusion")
    if diffusion is None:
        raise SpreadBacktestError("no staging/production diffusion version")
    expected = latent_signature(group1_versions)
    if diffusion.latent_signature != expected:
        raise SpreadBacktestError(
            f"diffusion v{diffusion.version} was trained against {diffusion.latent_signature!r}, "
            f"not the live champion set {expected!r} -- no real cycle can run it; re-sync first "
            "(train-schedule --derived-from-champions)"
        )

    artifacts = {m: load_run_artifacts(m, v, checkpoint_store) for m, v in champions.items()}
    val = extract_joint_latents(tracks, artifacts, gdas_cache_dir, seed=seed, device=device).val
    if len(val) == 0:
        raise SpreadBacktestError("no validation windows had cached gridded fields")

    model, _spec = load_trained_model("diffusion", diffusion, checkpoint_store)
    stats = load_standardization_stats(diffusion)
    if not {"z_mean", "z_std", "y_mean", "y_std"} <= set(stats):
        raise SpreadBacktestError(f"diffusion v{diffusion.version} has no standardisation stats")

    n_cases, n_leads = val.mask.shape
    members_abs = np.zeros((n_cases, n_members, n_leads, 3))
    true_abs = np.zeros((n_cases, n_leads, 3))
    generator = torch.Generator().manual_seed(sample_seed)
    z_z = (val.z - stats["z_mean"]) / stats["z_std"]
    with torch.no_grad():
        for ci in range(n_cases):
            z_t = torch.as_tensor(z_z[ci : ci + 1], dtype=torch.float32)
            samples = model.sample(z_t, n_members=n_members, generator=generator).cpu().numpy()
            disp = samples * stats["y_std"] + stats["y_mean"]  # (n_members, n_leads, 3)
            base_lat, base_lon = val.base_lat[ci], val.base_lon[ci]
            for li in range(n_leads):
                for mi in range(n_members):
                    lat, lon = displacement_to_latlon(base_lat, base_lon, *disp[mi, li, :2])
                    members_abs[ci, mi, li] = (lat, lon, disp[mi, li, 2])
                obs_dx, obs_dy, obs_wind = val.y[ci, li]
                obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
                true_abs[ci, li] = (obs_lat, obs_lon, obs_wind)

    base = np.stack([val.base_lat, val.base_lon], axis=1)
    sin_i = CONTEXT_FEATURE_NAMES.index("heading_sin")
    cos_i = CONTEXT_FEATURE_NAMES.index("heading_cos")
    base_bearing = np.degrees(np.arctan2(val.context[:, sin_i], val.context[:, cos_i])) % 360.0
    lead_hours = tuple(DEFAULT_LEADS)

    overall = calibrate(members_abs, true_abs, val.mask, base, lead_hours, min_cases=min_cases)
    recurving = calibrate(
        members_abs, true_abs, val.mask, base, lead_hours,
        case_filter=recurving_cases(true_abs, base, base_bearing), min_cases=min_cases,
    )
    recommendation, reasons = recommend_extra_conditioning(overall, recurving)
    return SpreadBacktestReport(
        diffusion_version=diffusion.version,
        group1_versions=group1_versions,
        n_members=n_members,
        n_val_cases=n_cases,
        overall=overall,
        recurving=recurving,
        recommendation=recommendation,
        reasons=reasons,
        cone=served_cone_outcome(members_abs, true_abs, val.mask, lead_hours),
    )


def format_report(report: SpreadBacktestReport) -> str:
    lines = [
        f"Anemoi-Spread calibration backtest -- diffusion v{report.diffusion_version}, "
        f"{report.n_members} members, {report.n_val_cases} validation windows",
        "Group 1: " + ", ".join(f"{m} v{v}" for m, v in report.group1_versions.items()),
    ]
    for label, results in (("overall", report.overall), ("recurving", report.recurving)):
        lines.append(f"\n{label}:")
        if not results:
            lines.append("  (no lead met the minimum case count)")
            continue
        lines.append(f"  {'lead':>5} {'quantity':<16} {'n':>5} {'spread':>9} {'rmse':>9} "
                     f"{'ratio':>6} {'outside':>8}  verdict")
        for r in results:
            lines.append(
                f"  {r.lead_hours:>4}h {r.quantity:<16} {r.n_cases:>5} "
                f"{r.spread_skill.spread:>9.1f} {r.spread_skill.skill:>9.1f} "
                f"{r.ratio:>6.2f} {r.outer_rank_fraction:>8.0%}  {r.verdict}"
            )
    if report.cone is not None:
        c = report.cone

        def pct(x):
            return "n/a" if x is None else f"{x:.0%}"

        lines.append(
            f"\nserved cone at {c.lead_hours}h (build_cone, 2/3-probability circle -- "
            f"calibrated misses ~33%): ensemble basis on {c.n_ensemble_basis}/{c.n_cases} "
            f"cases; truth outside the served cone: ensemble-basis {pct(c.miss_rate_ensemble)}, "
            f"climatology-basis {pct(c.miss_rate_climatology)}"
        )
    lines.append(f"\nextra_conditioning_dim: {report.recommendation}")
    lines.extend(f"  - {reason}" for reason in report.reasons)
    return "\n".join(lines)

