"""The real Anemoi-Spread calibration backtest (training.spread_backtest, #10)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.sources import Flavor
from anemoi.metrics.ensemble_calibration import LeadCalibration
from anemoi.metrics.probabilistic import SpreadSkill
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config
from anemoi.tracking.registry import GROUP1_MODELS, ModelRegistry, Stage, latent_signature
from anemoi.training.spread_backtest import (
    SpreadBacktestError,
    format_report,
    recommend_extra_conditioning,
    run_spread_backtest,
)


def _lc(lead, quantity, spread, rmse, n=50):
    return LeadCalibration(
        lead_hours=lead, quantity=quantity, n_cases=n,
        rank_counts=(20, 1, 1, 20), spread_skill=SpreadSkill(spread=spread, skill=rmse),
    )


# --- the #10 decision rule --------------------------------------------------


def test_long_lead_track_underdispersion_warrants_extra_conditioning():
    overall = [_lc(96, "cross_track_nm", spread=40.0, rmse=100.0)]
    decision, reasons = recommend_extra_conditioning(overall, [])
    assert decision == "warranted"
    assert "cross_track_nm at 96h" in reasons[0]


def test_underdispersion_among_recurving_storms_alone_is_enough():
    """#10's own motivation: the bimodal recurving case."""
    overall = [_lc(120, "along_track_nm", spread=95.0, rmse=100.0)]
    recurving = [_lc(120, "along_track_nm", spread=30.0, rmse=100.0, n=12)]
    decision, reasons = recommend_extra_conditioning(overall, recurving)
    assert decision == "warranted"
    assert reasons[0].startswith("recurving")


def test_intensity_underdispersion_alone_does_not_trigger_it():
    """extra_conditioning_dim is for the bimodal *track* case -- a tight
    intensity spread is a real finding but not this decision's evidence."""
    overall = [
        _lc(96, "wind_kt", spread=2.0, rmse=15.0),
        _lc(96, "cross_track_nm", spread=98.0, rmse=100.0),
    ]
    decision, _ = recommend_extra_conditioning(overall, [])
    assert decision == "not_warranted"


def test_short_lead_underdispersion_does_not_trigger_it():
    overall = [
        _lc(24, "cross_track_nm", spread=10.0, rmse=100.0),
        _lc(72, "cross_track_nm", spread=98.0, rmse=100.0),
    ]
    decision, _ = recommend_extra_conditioning(overall, [])
    assert decision == "not_warranted"


def test_no_long_lead_evidence_is_reported_as_such_not_as_a_verdict():
    decision, _ = recommend_extra_conditioning([_lc(24, "cross_track_nm", 98.0, 100.0)], [])
    assert decision == "insufficient_data"


# --- the real harness -------------------------------------------------------


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


def _store() -> CheckpointStore:
    return CheckpointStore(
        S3Config(endpoint_url="https://example.r2.cloudflarestorage.com", bucket="t",
                 access_key_id="k", secret_access_key="s"),
        client=_FakeS3Client(),
    )


_LEADS = [12, 24, 36, 48, 72, 96, 120]
_LATENT = 10


def _registry_with_champions(tmp_path, store, *, diffusion_signature=None):
    """Five staged Group 1 champions plus a staged diffusion whose recorded
    signature is either theirs (in sync) or ``diffusion_signature``."""
    import torch

    from anemoi.models.diffusion import build_diffusion

    registry = ModelRegistry(tmp_path / "registry")
    for name in GROUP1_MODELS:
        v = registry.register(name, run_id=name, input_flavor=Flavor.GDAS_FINETUNE,
                              metrics={"track_error_48h_nm": 100.0})
        registry.transition(name, v.version, Stage.STAGING)
    signature = diffusion_signature or latent_signature({m: 1 for m in GROUP1_MODELS})

    arch = {"latent_dim": _LATENT, "hidden_dim": 8, "n_layers": 1, "n_timesteps": 5,
            "lead_hours": _LEADS}
    model, _ = build_diffusion(**dict(arch, lead_hours=tuple(_LEADS)))
    path = tmp_path / "diffusion.pt"
    torch.save(model.state_dict(), path)
    uri = store.upload(path, "checkpoints/diffusion/B/t.pt")
    tags = {
        "arch_params": json.dumps(arch),
        "z_mean": json.dumps(np.zeros(_LATENT).tolist()),
        "z_std": json.dumps(np.ones(_LATENT).tolist()),
        "y_mean": json.dumps(np.zeros((7, 3)).tolist()),
        "y_std": json.dumps(np.full((7, 3), 50.0).tolist()),
    }
    v = registry.register("diffusion", run_id="d", input_flavor=Flavor.GDAS_FINETUNE,
                          metrics={"track_error_48h_nm": 100.0}, tags=tags,
                          checkpoint_uri=uri, latent_signature=signature)
    registry.transition("diffusion", v.version, Stage.STAGING)
    return registry


def _fake_val(n_cases=40, seed=0):
    from anemoi.training.real_latents import CONTEXT_FEATURE_NAMES, JointLatentSamples

    rng = np.random.default_rng(seed)
    n_leads = len(_LEADS)
    y = np.zeros((n_cases, n_leads, 3))
    y[..., 0] = -60.0 * (np.arange(n_leads) + 1)  # west
    y[..., 1] = 60.0 * (np.arange(n_leads) + 1)  # north
    y[..., 2] = 80.0
    y[..., :2] += rng.normal(0, 40.0, size=(n_cases, n_leads, 2))
    context = np.zeros((n_cases, len(CONTEXT_FEATURE_NAMES)))
    context[:, CONTEXT_FEATURE_NAMES.index("heading_sin")] = -0.7
    context[:, CONTEXT_FEATURE_NAMES.index("heading_cos")] = 0.7
    return JointLatentSamples(
        z=rng.normal(size=(n_cases, _LATENT)), y=y, mask=np.ones((n_cases, n_leads), dtype=bool),
        base_lat=np.full(n_cases, 20.0), base_lon=np.full(n_cases, -60.0),
        predictions=np.zeros((n_cases, 5, n_leads, 3)),
        true_absolute=np.zeros((n_cases, n_leads, 3)),
        context=context, latent_dims=(2, 2, 2, 2, 2),
    )


@pytest.fixture
def patched(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "anemoi.training.real_inference.load_run_artifacts",
        lambda name, version, store: SimpleNamespace(model=name),
    )
    calls: list = []

    def fake_extract(tracks, artifacts, cache_dir, **kwargs):
        calls.append((sorted(artifacts), kwargs))
        return SimpleNamespace(val=_fake_val())

    monkeypatch.setattr("anemoi.training.real_latents.extract_joint_latents", fake_extract)
    return calls


def test_refuses_a_diffusion_desynced_from_the_live_champions(tmp_path, patched):
    """Measuring a pipeline no real cycle can run would be measuring nothing
    real -- same §5.7 rule `build_real_ensemble_fn` applies live."""
    pytest.importorskip("torch")
    store = _store()
    registry = _registry_with_champions(
        tmp_path, store, diffusion_signature="lstmv9-cnnv9-transformerv9-gnnv9-pinnv9",
    )
    with pytest.raises(SpreadBacktestError, match="re-sync first"):
        run_spread_backtest([], registry, store, tmp_path)


@pytest.mark.torch
def test_runs_end_to_end_through_a_real_diffusion_model(tmp_path, patched):
    store = _store()
    registry = _registry_with_champions(tmp_path, store)

    report = run_spread_backtest([], registry, store, tmp_path, n_members=8, min_cases=10)

    assert report.n_val_cases == 40
    assert report.n_members == 8
    assert report.group1_versions == {m: 1 for m in GROUP1_MODELS}
    # latents built from all five champions, with the orchestrator's own seed
    assert patched[0][0] == sorted(GROUP1_MODELS)
    assert patched[0][1]["seed"] == 20260806
    leads = {r.lead_hours for r in report.overall}
    assert leads == set(_LEADS)
    for r in report.overall:
        assert sum(r.rank_counts) == r.n_cases
        assert np.isfinite(r.ratio)
    assert report.recommendation in {"warranted", "not_warranted", "insufficient_data"}
    assert report.cone is not None and report.cone.lead_hours == 120
    assert "served cone" in format_report(report)
    assert "extra_conditioning_dim" in format_report(report)
    json.dumps(report.to_dict())  # serialisable for the CLI's --out


def test_served_cone_scores_what_build_cone_actually_serves():
    """A tight ensemble must be scored against the climatological cone
    build_cone falls back to; a wide one against its own spread -- and a
    truth far outside the served radius counts as a miss either way."""
    from anemoi.geo import offset_position
    from anemoi.training.spread_backtest import served_cone_outcome

    leads = (24, 120)
    rng = np.random.default_rng(1)

    def ensemble(sigma_nm, n_members=20):
        out = np.zeros((n_members, len(leads), 3))
        for mi in range(n_members):
            for li in range(len(leads)):
                e, n = rng.normal(0, sigma_nm, size=2)
                bearing = float(np.degrees(np.arctan2(e, n)))
                out[mi, li, :2] = offset_position(25.0, -70.0, float(np.hypot(e, n)), bearing)
                out[mi, li, 2] = 80.0
        return out

    tight, wide = ensemble(5.0), ensemble(400.0)
    members = np.stack([tight, wide])
    far_truth = offset_position(25.0, -70.0, 1500.0, 0.0)
    truth = np.array([[[25.0, -70.0, 80.0], [*far_truth, 80.0]]] * 2)

    outcome = served_cone_outcome(members, truth, np.ones((2, 2), dtype=bool), leads)

    assert outcome.lead_hours == 120
    assert outcome.n_cases == 2
    assert outcome.n_ensemble_basis == 1  # only the wide one keeps its own spread
    assert outcome.miss_rate_ensemble == 1.0
    assert outcome.miss_rate_climatology == 1.0
