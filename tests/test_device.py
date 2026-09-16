"""Device selection for local (non-cloud) training (PLAN.md §5 "Sample size" --
#9 and #12 are small enough to run on a laptop GPU instead of rented compute).
"""

import pytest

from anemoi.models.base import require_torch

pytestmark = pytest.mark.torch


def test_get_device_prefers_mps_over_cuda_and_cpu(monkeypatch):
    torch = require_torch()
    from anemoi.training.device import get_device

    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert get_device().type == "mps"


def test_get_device_falls_back_to_cuda_when_mps_is_unavailable(monkeypatch):
    torch = require_torch()
    from anemoi.training.device import get_device

    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert get_device().type == "cuda"


def test_get_device_falls_back_to_cpu_when_no_gpu_backend_is_available(monkeypatch):
    torch = require_torch()
    from anemoi.training.device import get_device

    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert get_device().type == "cpu"


def test_compile_model_rejects_non_module_input():
    torch = require_torch()
    from anemoi.training.device import compile_model

    with pytest.raises(TypeError, match="nn.Module"):
        compile_model(object(), torch.device("cpu"))


def test_compile_model_skips_compilation_on_mps():
    torch = require_torch()
    from anemoi.training.device import compile_model

    model = torch.nn.Linear(4, 4)
    compiled = compile_model(model, torch.device("mps"))
    assert compiled is model


def test_compile_model_does_not_raise_on_cpu():
    torch = require_torch()
    from anemoi.training.device import compile_model

    model = torch.nn.Linear(4, 4)
    compile_model(model, torch.device("cpu"))  # succeeds or degrades; must not raise
