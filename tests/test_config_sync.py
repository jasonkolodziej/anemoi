"""`configs/*.yaml` mirror values that live in Python, with no loader between
them -- the YAML is documentation of what the code does (wiki Roadmap,
"Config loader").

That pairing has no enforcement of its own, so it drifts silently: raising
`DEFAULT_ENSEMBLE_MEMBERS` 20 -> 50 (#188) left the config still declaring
20, and it took a review to catch. These assert every value in all three
files against what the code actually does, so the next such change fails
here instead of shipping a config that describes a system that no longer
exists. A key added to a config that nothing here checks fails too: an
unchecked key is a claim nobody verified.

Expected values are read off the real constants, function signatures, or
behaviour (which day the monthly trigger fires on, which hour the nightly
refresh runs at) rather than hoisted into new module constants -- the point
is to check what the code does, not to reshape the code so it is easier to
assert against.
"""

from __future__ import annotations

import inspect
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from anemoi.data.besttrack import WorkingTrackNoise
from anemoi.data.sources import Flavor
from anemoi.inference import postprocess, scheduler
from anemoi.models.base import DEFAULT_LEADS
from anemoi.monitoring import calibration_audit, drift, skew
from anemoi.time_utils import ADVISORY_OFFSET, SYNOPTIC_HOURS, select_nwp_cycle
from anemoi.training import promotion, triggers
from anemoi.training.curriculum import stage_a, stage_b

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs"


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIGS / name).read_text())


def _default(fn, name: str):
    return inspect.signature(fn).parameters[name].default


def _minutes(td: timedelta) -> float:
    return td.total_seconds() / 60


def _leaves(node, prefix: str = "") -> dict[str, object]:
    """Dotted path -> value. A mapping keyed by numbers (the cone table) is
    one value, not a set of keys."""
    if isinstance(node, dict) and not all(isinstance(k, int) for k in node):
        out: dict[str, object] = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}{key}."))
        return out
    return {prefix[:-1]: node}


# ---- what the code does, per config file ----------------------------------


def _stage(spec, *, with_frozen: bool) -> dict[str, object]:
    out = {
        "name": spec.name,
        "flavor": spec.flavor.value,
        "input_sources": list(spec.input_sources),
        "label_source": spec.label_source,
        "season_range": list(spec.season_range),
        "epochs": spec.epochs,
        "learning_rate": spec.learning_rate,
    }
    if with_frozen:
        out["frozen_modules"] = list(spec.frozen_modules)
    return out


def _curriculum() -> dict[str, object]:
    noise = WorkingTrackNoise()
    expected = {
        **{f"stage_a.{k}": v for k, v in _stage(stage_a(), with_frozen=False).items()},
        **{f"stage_b.{k}": v for k, v in _stage(stage_b(), with_frozen=True).items()},
        "working_track_noise.position_rms_nm": noise.position_rms_nm,
        "working_track_noise.intensity_rms_kt": noise.intensity_rms_kt,
        "working_track_noise.pressure_rms_mb": noise.pressure_rms_mb,
        "working_track_noise.quantise": noise.quantise,
    }
    return expected


def _first_nwp_lag_hours() -> int:
    """The lag select_nwp_cycle picks when every candidate cycle is available."""
    t = datetime(2026, 8, 6, 12, tzinfo=UTC)
    available = {t - timedelta(hours=h) for h in range(0, 49, 6)}
    return select_nwp_cycle(t, available).lag_hours


def _cron_run_offset_minutes() -> int:
    """Minutes after its synoptic time that production runs a cycle, from
    anemoi-api-real's cron -- one offset for all four synoptic times."""
    text = (ROOT / "docker" / "api" / "wrangler.jsonc").read_text()
    minute, hours = re.search(r'"crons":\s*\[\s*"(\d+) ([\d,]+) \* \* \*"', text).groups()
    offsets = {
        (h - max(s for s in SYNOPTIC_HOURS if s <= h)) * 60 + int(minute)
        for h in map(int, hours.split(","))
    }
    assert len(offsets) == 1, f"cron fires at different offsets per cycle: {sorted(offsets)}"
    return offsets.pop()


def _budgets(budgets) -> dict[str, object]:
    out: dict[str, object] = {}
    for b in budgets:
        out[f"{b.stage.value}.target"] = _minutes(b.target)
        out[f"{b.stage.value}.max"] = _minutes(b.maximum)
    return out


def _inference() -> dict[str, object]:
    expected: dict[str, object] = {
        "cycle.synoptic_hours": list(SYNOPTIC_HOURS),
        "cycle.nwp_lag_hours": _first_nwp_lag_hours(),
        "cycle.max_nwp_lag_hours": _default(select_nwp_cycle, "max_lag_hours"),
        "cycle.nominal_vitals_offset_minutes": _minutes(scheduler.NOMINAL_VITALS_OFFSET),
        "cycle.vitals_timeout_minutes": _minutes(scheduler.derive_vitals_timeout()),
        "cycle.advisory_offset_minutes": _minutes(ADVISORY_OFFSET),
        "cycle.advisory_margin_minutes": _minutes(scheduler.ADVISORY_MARGIN),
        "cycle.allow_estimated_vitals": _default(scheduler.plan_cycle, "allow_estimated_vitals"),
        "cycle.allow_load_shedding": _default(scheduler.plan_cycle, "allow_load_shedding"),
        "cycle.scheduled_run_offset_minutes": _cron_run_offset_minutes(),
        "ensemble.members": scheduler.DEFAULT_ENSEMBLE_MEMBERS,
        "ensemble.reduced_members": scheduler.REDUCED_ENSEMBLE_MEMBERS,
        "ensemble.min_members_for_ensemble_cone": _default(postprocess.build_cone, "min_members"),
        "ensemble.underdispersion_fraction": _default(
            postprocess.build_cone, "underdispersion_fraction"
        ),
        "ensemble.climatological_cone_nm": dict(postprocess.CLIMATOLOGICAL_CONE_NM),
        "products.lead_hours": list(DEFAULT_LEADS),
        "products.cone_percentile": _default(postprocess.cone_radius_from_spread, "percentile"),
        "products.landfall_threshold_nm": _default(
            postprocess.landfall_probability, "threshold_nm"
        ),
        "products.ri_threshold_kt": postprocess.RI_THRESHOLD_KT,
        "products.ri_window_hours": postprocess.RI_WINDOW_HOURS,
        "products.ri_alert_probability": _default(
            postprocess.build_products, "ri_alert_threshold"
        ),
    }
    for profile, budgets in (
        ("standard", scheduler.DEFAULT_BUDGETS),
        ("reduced", scheduler.REDUCED_BUDGETS),
    ):
        expected.update({f"budgets.{profile}.{k}": v for k, v in _budgets(budgets).items()})
    return expected


def _trigger_days(fn) -> list[str]:
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
    return [d.strftime("%m-%d") for d in days if fn(d)]


def _monitoring() -> dict[str, object]:
    monitor = skew.SkewMonitor()
    loss = drift.ValidationLossMonitor()
    budget = promotion.TestSetBudget()
    monthly = {int(d[3:]) for d in _trigger_days(triggers.scheduled_monthly)}
    nightly_hours = [
        h for h in range(24)
        if triggers.nightly_latent(datetime(2026, 6, 2, h, tzinfo=UTC), triggers.SeasonState())
    ]
    expected: dict[str, object] = {
        "skew_audit.audit_delay_days": skew.AUDIT_DELAY.days,
        "skew_audit.window_days": monitor.window.days,
        "skew_audit.min_samples": monitor.min_samples,
        "skew_audit.lead_hours": _default(skew.SkewMonitor.report, "lead_hours"),
        "skew_audit.alert_track_delta_nm": monitor.track_threshold_nm,
        "skew_audit.alert_intensity_delta_kt": monitor.intensity_threshold_kt,
        # Not tunable: ReferenceDistribution refuses any other flavor
        # (test_drift_reference_flavor_is_enforced below).
        "drift.reference_flavor": Flavor.GDAS_FINETUNE.value,
        "drift.shift_sigma": _default(drift.detect_feature_drift, "shift_sigma"),
        "drift.variance_ratio_limit": _default(
            drift.detect_feature_drift, "variance_ratio_limit"
        ),
        "drift.min_samples": _default(drift.detect_feature_drift, "min_samples"),
        "drift.validation_loss.threshold_fraction": loss.threshold_fraction,
        "drift.validation_loss.consecutive_required": loss.consecutive_required,
        "calibration_audit.cone_nominal_rate": round(calibration_audit.CONE_NOMINAL_RATE, 3),
        "calibration_audit.intensity_nominal_rate": calibration_audit.INTENSITY_NOMINAL_RATE,
        "calibration_audit.verdict_margin": calibration_audit._VERDICT_MARGIN,
        "calibration_audit.min_cases": calibration_audit.MIN_CASES,
        # Not tunable: evaluate_promotion refuses any other split or flavor.
        "promotion.split": "val",
        "promotion.flavor": Flavor.GDAS_FINETUNE.value,
        "promotion.primary_metric": _default(promotion.evaluate_promotion, "primary_metric"),
        "promotion.require_manual_gate": _default(
            promotion.evaluate_promotion, "require_manual_gate"
        ),
        "test_set_budget.max_evaluations_per_season": budget.max_evaluations_per_season,
        "triggers.scheduled_monthly_day": monthly.pop() if len(monthly) == 1 else sorted(monthly),
        "triggers.preseason_date": next(iter(_trigger_days(triggers.preseason)), None),
        "triggers.data_volume_threshold": _default(triggers.on_data_volume, "threshold"),
        "triggers.nightly_latent_hour_utc": (
            nightly_hours[0] if len(nightly_hours) == 1 else nightly_hours
        ),
        "triggers.suppress_nightly_latent_during_active_storms": not triggers.nightly_latent(
            datetime(2026, 6, 2, nightly_hours[0], tzinfo=UTC),
            triggers.SeasonState(active_storms=("AL012026",)),
        ),
    }
    for t in promotion.DEFAULT_THRESHOLDS:
        expected[f"promotion.thresholds.{t.metric}.limit"] = t.limit
        expected[f"promotion.thresholds.{t.metric}.lower_is_better"] = t.lower_is_better
    return expected


EXPECTED = {
    "curriculum.yaml": _curriculum,
    "inference.yaml": _inference,
    "monitoring.yaml": _monitoring,
}

CASES = [
    (name, path)
    for name, build in EXPECTED.items()
    for path in sorted(set(_leaves(_load(name))) | set(build()))
]


@pytest.mark.parametrize(("config", "path"), CASES, ids=[f"{c}:{p}" for c, p in CASES])
def test_config_value_matches_the_code(config, path):
    configured = _leaves(_load(config))
    expected = EXPECTED[config]()
    assert path in configured, f"{config} is missing {path} (the code uses {expected[path]!r})"
    assert path in expected, (
        f"{config} declares {path}, but nothing checks it against the code -- "
        "add it to tests/test_config_sync.py, or drop it from the config"
    )
    value, want = configured[path], expected[path]
    if isinstance(want, dict):
        value = {int(k): float(v) for k, v in value.items()}
        want = {int(k): float(v) for k, v in want.items()}
    assert value == want, f"{config} {path} = {value!r}, but the code uses {want!r}"


def test_the_console_uses_the_same_scheduled_run_offset():
    """The storm page says when the next cycle is due (#209) from its own copy
    of the cron's offset."""
    utils = (ROOT / "console" / "src" / "lib" / "utils.ts").read_text()
    console = int(re.search(r"CYCLE_RUN_DELAY_MIN = (\d+);", utils).group(1))
    assert console == _load("inference.yaml")["cycle"]["scheduled_run_offset_minutes"]


def test_scheduled_runs_start_after_the_vitals_timeout():
    """The cron is placed after the derived vitals timeout so a cycle never
    starts waiting on vitals that may still arrive."""
    cycle = _load("inference.yaml")["cycle"]
    assert cycle["scheduled_run_offset_minutes"] > cycle["vitals_timeout_minutes"]


def test_vitals_timeout_is_the_module_constant_too():
    assert scheduler.VITALS_TIMEOUT == scheduler.derive_vitals_timeout()


def test_drift_reference_flavor_is_enforced():
    import numpy as np

    with pytest.raises(drift.DriftError):
        drift.ReferenceDistribution(
            flavor=Flavor.ERA5_PRETRAIN, feature_names=("x",),
            mean=np.zeros(1), std=np.ones(1), n=1,
        )


def test_the_load_shed_comment_still_describes_the_real_reduced_count():
    """The budget comment carries the counts in prose -- a comment that
    contradicts the code is worse than no comment."""
    text = (CONFIGS / "inference.yaml").read_text()
    assert f"~{scheduler.REDUCED_ENSEMBLE_MEMBERS} ensemble members" in text, (
        "the load-shedding comment in inference.yaml no longer matches "
        f"REDUCED_ENSEMBLE_MEMBERS ({scheduler.REDUCED_ENSEMBLE_MEMBERS})"
    )
    assert f"instead of {scheduler.DEFAULT_ENSEMBLE_MEMBERS}" in text


def test_every_config_parses_and_has_no_duplicate_keys():
    """yaml.safe_load keeps the last of two duplicate keys silently, which
    would let a stale value hide behind a corrected one."""

    class Strict(yaml.SafeLoader):
        pass

    def no_duplicates(loader, node, deep=False):
        keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
        dupes = {k for k in keys if keys.count(k) > 1}
        line = node.start_mark.line + 1
        assert not dupes, f"duplicate keys {sorted(map(str, dupes))} at line {line}"
        return loader.construct_mapping(node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates)
    for path in sorted(CONFIGS.glob("*.yaml")):
        assert isinstance(yaml.load(path.read_text(), Loader=Strict), dict), path.name
    assert {p.name for p in CONFIGS.glob("*.y*ml")} == set(EXPECTED), (
        "a config file exists that no test checks"
    )


def test_the_lead_times_match_the_api_s_own_copy():
    """api.real_state keeps its own lead tuple for building real cycles."""
    pytest.importorskip("pydantic")
    from anemoi.api import real_state

    assert list(real_state._LEAD_HOURS) == _load("inference.yaml")["products"]["lead_hours"]
