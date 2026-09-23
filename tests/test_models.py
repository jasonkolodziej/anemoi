"""Model architectures (Scope v2.1 §3). Requires the optional torch extra."""

import pytest

from anemoi.models.base import ModelSpec, require_torch, torch_available

pytestmark = pytest.mark.torch

LEADS = (12, 24, 48, 72, 120)


def test_spec_output_dim_is_leads_times_outputs():
    spec = ModelSpec("x", input_dim=4, latent_dim=8, lead_hours=LEADS)
    assert spec.output_dim == len(LEADS) * 3


def test_require_torch_message_names_the_extra():
    if torch_available():
        pytest.skip("torch installed; the failure path cannot be exercised")
    with pytest.raises(ModuleNotFoundError, match="uv sync --extra torch"):
        require_torch()


def test_lstm_shapes_and_latent():
    torch = require_torch()
    from anemoi.models.lstm import build_lstm

    model, spec = build_lstm(input_dim=14, hidden_dim=32, lead_hours=LEADS)
    x = torch.randn(4, 8, 14)
    assert model(x).shape == (4, len(LEADS), 3)
    assert model.encode(x).shape == (4, spec.latent_dim)


def test_gru_variant_builds():
    torch = require_torch()
    from anemoi.models.lstm import build_lstm

    model, _ = build_lstm(input_dim=6, hidden_dim=16, lead_hours=LEADS, cell="gru")
    assert model(torch.randn(2, 5, 6)).shape == (2, len(LEADS), 3)


def test_invalid_cell_is_rejected():
    from anemoi.models.lstm import build_lstm

    require_torch()
    with pytest.raises(ValueError, match="lstm|gru"):
        build_lstm(cell="rnn")


def test_cnn_is_resolution_agnostic():
    torch = require_torch()
    from anemoi.models.cnn import build_cnn

    model, spec = build_cnn(in_channels=5, base_width=8, depth=3, latent_dim=32,
                            lead_hours=LEADS)
    assert model.encode(torch.randn(2, 5, 64, 64)).shape == (2, 32)
    assert model.encode(torch.randn(2, 5, 128, 128)).shape == (2, 32)
    assert model(torch.randn(2, 5, 64, 64)).shape == (2, len(LEADS), 3)
    assert spec.latent_dim == 32


def test_transformer_emits_track_and_regime():
    torch = require_torch()
    from anemoi.models.transformer import build_transformer

    model, spec = build_transformer(n_variables=8, patch_size=4, grid_size=(32, 32),
                                    d_model=64, n_heads=4, n_layers=2, lead_hours=LEADS)
    track, regime = model(torch.randn(2, 8, 32, 32))
    assert track.shape == (2, len(LEADS), 3)
    assert regime.shape == (2, 4)
    assert model.encode(torch.randn(2, 8, 32, 32)).shape == (2, spec.latent_dim)


def test_transformer_rejects_an_indivisible_grid():
    from anemoi.models.transformer import build_transformer

    require_torch()
    with pytest.raises(ValueError, match="divisible"):
        build_transformer(grid_size=(30, 30), patch_size=4)


def test_gnn_message_passing_runs_over_a_small_graph():
    torch = require_torch()
    from anemoi.models.gnn import build_gnn

    model, _ = build_gnn(node_features=12, edge_features=3, hidden_dim=32, n_layers=2,
                         lead_hours=LEADS)
    x = torch.randn(10, 12)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]])
    edge_attr = torch.randn(4, 3)
    assert model(x, edge_index, edge_attr).shape == (1, len(LEADS), 3)


def test_untrained_pinn_is_the_identity():
    """A physics corrector must not degrade a forecast before it has learned."""
    torch = require_torch()
    from anemoi.models.pinn import build_pinn

    model, _ = build_pinn(input_dim=10, hidden_dim=16, lead_hours=LEADS)
    candidate = torch.randn(3, len(LEADS), 3)
    corrected = model(torch.randn(3, 10), candidate)
    assert torch.allclose(corrected, candidate, atol=1e-6)


def test_physics_residuals_penalise_impossible_motion():
    torch = require_torch()
    from anemoi.models.pinn import physics_residuals

    slow = torch.zeros(1, 5, 3)
    slow[0, :, 0] = torch.tensor([20.0, 20.5, 21.0, 21.5, 22.0])
    fast = torch.zeros(1, 5, 3)
    fast[0, :, 0] = torch.tensor([20.0, 30.0, 40.0, 50.0, 60.0])
    assert physics_residuals(fast)["speed"] > physics_residuals(slow)["speed"]


def test_diffusion_sampling_produces_distinct_members():
    torch = require_torch()
    from anemoi.models.diffusion import build_diffusion

    model, _ = build_diffusion(latent_dim=16, hidden_dim=32, n_layers=2,
                               n_timesteps=10, lead_hours=LEADS)
    members = model.sample(torch.randn(1, 16), n_members=6)
    assert members.shape == (6, len(LEADS), 3)
    assert not torch.allclose(members[0], members[1])


def test_diffusion_sampling_clips_x0_to_bound_a_diverging_denoiser():
    """Real bug found training diffusion against real ERA5/GDAS latents
    (2026-09-18): a denoiser badly out-of-distribution at inference (this
    model overfits fast on a small real latent dataset) could drift its
    implied x0 to an arbitrary magnitude at an early step, and every
    later step's posterior mean is a moving average that includes that
    unclipped x0 -- so the drift persisted and compounded across ~200
    steps instead of self-correcting. Confirmed via a real MLflow query:
    track_error_48h_nm around 4800 (every other model that run landed
    250-310). This simulates the worst case directly -- a denoiser that
    always predicts a wildly wrong (huge) noise value -- and confirms
    `clip_x0` keeps the final samples in a bounded, plausible range
    instead of exploding."""
    torch = require_torch()
    from anemoi.models.diffusion import build_diffusion

    model, _ = build_diffusion(latent_dim=16, hidden_dim=32, n_layers=2,
                               n_timesteps=20, lead_hours=LEADS)

    def diverging_forward(noisy_traj, t, conditioning):
        return torch.full((noisy_traj.shape[0], len(LEADS), 3), 1000.0)

    model.forward = diverging_forward
    members = model.sample(torch.randn(1, 16), n_members=4, clip_x0=6.0)

    assert torch.isfinite(members).all()
    assert members.abs().max() < 100.0  # bounded, not exploded into the thousands


def test_diffusion_accepts_extra_conditioning():
    torch = require_torch()
    from anemoi.models.diffusion import build_diffusion

    model, spec = build_diffusion(latent_dim=16, extra_conditioning_dim=8, hidden_dim=32,
                                  n_layers=2, n_timesteps=5, lead_hours=LEADS)
    assert spec.input_dim == 24
    assert model.sample(torch.randn(1, 24), n_members=3).shape == (3, len(LEADS), 3)


# --- consistency model (#15) -------------------------------------------------


def _consistency_model(**overrides):
    from anemoi.models.consistency import build_consistency_model

    kwargs = dict(latent_dim=16, hidden_dim=32, n_layers=2, n_timesteps=10, lead_hours=LEADS)
    kwargs.update(overrides)
    return build_consistency_model(**kwargs)


def test_consistency_boundary_condition_is_exact_at_step_zero():
    """f(x, 0) = x is the defining property of a consistency function
    (Song et al. 2023) -- not approximate, exact by the skip-connection
    construction (`models.consistency`'s own module docstring), for any
    input, any conditioning, any untrained weights."""
    torch = require_torch()
    model, _ = _consistency_model()

    x = torch.randn(5, len(LEADS), 3)
    t0 = torch.zeros(5, dtype=torch.long)
    cond = torch.randn(5, 16)
    out = model.consistency_fn(x, t0, cond)

    assert torch.allclose(out, x)


def test_consistency_one_step_sampling_produces_distinct_members():
    torch = require_torch()
    model, _ = _consistency_model()

    members = model.sample(torch.randn(1, 16), n_members=6, n_steps=1)
    assert members.shape == (6, len(LEADS), 3)
    assert not torch.allclose(members[0], members[1])


def test_consistency_multistep_sampling_matches_one_step_shape_and_is_deterministic():
    torch = require_torch()
    model, _ = _consistency_model()
    cond = torch.randn(1, 16)

    gen_a = torch.Generator().manual_seed(7)
    out_a = model.sample(cond, n_members=4, n_steps=4, generator=gen_a)
    gen_b = torch.Generator().manual_seed(7)
    out_b = model.sample(cond, n_members=4, n_steps=4, generator=gen_b)

    assert out_a.shape == (4, len(LEADS), 3)
    assert torch.allclose(out_a, out_b)


def test_consistency_rejects_a_non_positive_step_count():
    from anemoi.models.consistency import build_consistency_model

    model, _ = build_consistency_model(latent_dim=4, hidden_dim=8, n_layers=1,
                                       n_timesteps=5, lead_hours=LEADS)
    with pytest.raises(ValueError, match="n_steps"):
        model.sample(require_torch().randn(1, 4), n_members=2, n_steps=0)


def test_consistency_accepts_extra_conditioning():
    torch = require_torch()
    model, spec = _consistency_model(extra_conditioning_dim=8)
    assert spec.input_dim == 24
    assert model.sample(torch.randn(1, 24), n_members=3, n_steps=2).shape == (3, len(LEADS), 3)


def test_fusion_weights_are_normalised_and_floored():
    torch = require_torch()
    from anemoi.models.fusion import build_fusion

    model, _ = build_fusion(n_models=5, context_dim=16, lead_hours=LEADS, weight_floor=0.05)
    w = model.weights(torch.randn(2, 16))
    assert w.shape == (2, len(LEADS), 5)
    assert torch.allclose(w.sum(-1), torch.ones(2, len(LEADS)), atol=1e-5)
    assert float(w.min()) >= 0.04


def test_fusion_rejects_the_wrong_number_of_models():
    torch = require_torch()
    from anemoi.models.fusion import build_fusion

    model, _ = build_fusion(n_models=5, context_dim=16, lead_hours=LEADS)
    with pytest.raises(ValueError, match="expected 5"):
        model(torch.randn(2, 3, len(LEADS), 3), torch.randn(2, 16))
