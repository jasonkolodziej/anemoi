"""Parity and benchmark probe for the compiled build.

Run by ``.github/scripts/test-compiled-wheel.sh`` once under the source
tree's interpreter and once under a venv holding the compiled wheel; the
script compares the two outputs. It imports ``anemoi`` from whatever the
running interpreter has installed and reports which it got (``compiled``),
so a run that silently picked up the source tree is visible.

    python compile/probe.py parity   # seeded training + one cycle -> JSON
    python compile/probe.py bench    # timings, seconds -> JSON

``parity`` output must be byte-identical between the two builds: the same
source run on the same interpreter, numpy and torch has to give the same
numbers. ``bench`` output is timings and is only ever compared by eye.

Needs the ``torch`` (or ``torch-cpu``) and ``api`` extras.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import warnings
from datetime import UTC, datetime

import numpy as np

SEED = 20260806
LEADS = (12, 24, 36, 48, 72, 96, 120)


def _is_compiled() -> bool:
    import anemoi.cli

    return not anemoi.cli.__file__.endswith(".py")


def _jsonable(value):
    """Exact, order-preserving JSON form: floats via repr, arrays by digest."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return {"shape": list(value.shape), "sha256": hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, (np.floating, float)):
        return repr(float(value))
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _tracks(start: int, end: int, storms: int):
    from anemoi.data.synthetic import generate_archive

    return generate_archive(start, end, storms_per_season=storms, seed=SEED)


def _state_digest(model) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def _ablation(tracks, *, hidden_dims, epochs):
    from anemoi.training.capacity_ablation import run_capacity_ablation

    return run_capacity_ablation(
        tracks, hidden_dims=hidden_dims, sample_fractions=(0.5, 1.0),
        n_augment=1, epochs=epochs, seed=SEED,
    )


def _lstm_stage(tracks, *, hidden_dim, epochs):
    """One real curriculum stage (Stage B) of the LSTM, as training runs it."""
    import torch

    from anemoi.data.splits import STAGE_B_BOUNDARIES, Split, assign_splits, filter_tracks
    from anemoi.data.storm_relative import STORM_RELATIVE_COLUMNS
    from anemoi.models.lstm import build_lstm
    from anemoi.training.curriculum import stage_b
    from anemoi.training.real_run import train_lstm_stage

    assignment = assign_splits(tracks, STAGE_B_BOUNDARIES)
    train = filter_tracks(tracks, assignment, Split.TRAIN)
    val = filter_tracks(tracks, assignment, Split.VAL)
    torch.manual_seed(SEED)
    model, _ = build_lstm(
        input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=hidden_dim, lead_hours=LEADS,
    )
    model, train_loss, val_loss, metrics, stats = train_lstm_stage(
        model, stage_b(epochs=epochs, learning_rate=1e-2), train, val,
        np.random.default_rng(SEED), n_augment=1, device="cpu",
    )
    return {
        "train_loss": train_loss,
        "val_loss": val_loss,
        "val_metrics": metrics,
        "standardization": list(stats),
        "weights_sha256": _state_digest(model),
    }


def _cycle(members: int = 20):
    """One demo forecast cycle, the way ``anemoi cycle`` builds it."""
    from anemoi.data.atcf import storm_basin
    from anemoi.data.availability import LatencyOracle
    from anemoi.data.besttrack import Fix, TrackQuality
    from anemoi.inference.cycle import (
        DeterministicForecast,
        climatological_ensemble,
        run_cycle,
    )
    from anemoi.inference.scheduler import plan_cycle
    from anemoi.time_utils import parse_cycle_label

    target = parse_cycle_label("20260806_06Z")
    plan = plan_cycle(target, LatencyOracle(use_max_latency=False))
    fix = Fix(
        storm_id="AL092026", valid_time=target, lat=22.4, lon=-72.1, max_wind_kt=85.0,
        min_pressure_mb=990.0,
        quality=TrackQuality.ESTIMATED if plan.vitals_estimated else TrackQuality.WORKING,
    )

    def deterministic(plan_, fix_):
        steps = np.arange(1, len(LEADS) + 1, dtype=float)
        return DeterministicForecast(
            target_time=plan_.target_time,
            lead_hours=LEADS,
            lats=fix_.lat + 0.9 * steps,
            lons=fix_.lon - 1.1 * steps,
            winds_kt=np.clip(fix_.max_wind_kt + 4.0 * steps - 0.4 * steps**2, 15.0, None),
            contributors={"lstm": 0.2, "transformer": 0.35, "gnn": 0.25, "cnn": 0.2},
        )

    output = run_cycle(
        plan, fix, deterministic,
        lambda det, n: climatological_ensemble(
            det, n_members=n, seed=1, basin=storm_basin(fix.storm_id),
        ),
        now=datetime(2026, 8, 6, 7, 30, tzinfo=UTC),
        requested_members=members,
    )
    return output.payload()


def parity() -> dict:
    import torch

    # One thread: multi-threaded reductions may sum in a different order
    # from run to run, which is noise this comparison must not contain.
    torch.set_num_threads(1)
    tracks = _tracks(2012, 2023, 6)
    return {
        "tracks": len(tracks),
        "capacity_ablation": _ablation(tracks, hidden_dims=(8, 16), epochs=5).cells,
        "lstm_stage_b": _lstm_stage(tracks, hidden_dim=16, epochs=5),
        "cycle": _cycle(),
    }


def _best(fn, repeats: int) -> float:
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return min(times)


def _bench_import() -> float:
    code = "import anemoi.cli, anemoi.api.main, anemoi.training.real_run"
    return _best(lambda: subprocess.run([sys.executable, "-c", code], check=True), 5)


def _bench_api() -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi.testclient import TestClient

    from anemoi.api.main import app

    client = TestClient(app)
    storm = client.get("/v1/storms").json()[0]["storm_id"]
    gets = [
        "/v1/health", "/v1/storms", f"/v1/storms/{storm}", "/v1/sources", "/v1/registry",
        "/v1/models", "/v1/schedule?date=2026-08-06", "/v1/monitoring/drift",
    ]

    def per_request(call, n: int) -> float:
        samples = []
        for _ in range(n):
            start = time.perf_counter()
            response = call()
            samples.append(time.perf_counter() - start)
            assert response.status_code < 400, response.text
        return statistics.median(samples)

    out = {f"GET {path}": per_request(lambda p=path: client.get(p), 200) for path in gets}
    out["POST /v1/storms/{id}/cycles"] = per_request(
        lambda: client.post(
            f"/v1/storms/{storm}/cycles", json={"cycle": "20260806_06Z", "members": 20},
        ),
        50,
    )
    return out


def bench() -> dict:
    from anemoi.training.capacity_ablation import build_samples

    small = _tracks(2012, 2023, 6)
    out: dict = {"import (cli + api + training)": _bench_import()}
    out["synthetic archive, 46 seasons"] = _best(lambda: _tracks(1980, 2025, 12), 3)
    full = _tracks(1980, 2025, 12)
    out["build training samples"] = _best(
        lambda: build_samples(full, np.random.default_rng(SEED), n_augment=3), 3,
    )
    out["forecast cycle (20 members)"] = _best(lambda: [_cycle() for _ in range(50)], 3) / 50
    out["LSTM capacity ablation, 4 cells x 30 epochs"] = _best(
        lambda: _ablation(small, hidden_dims=(32, 64), epochs=30), 2,
    )
    out["LSTM stage B, 30 epochs"] = _best(
        lambda: _lstm_stage(small, hidden_dim=64, epochs=30), 2,
    )
    out.update(_bench_api())
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("parity", "bench"):
        print(__doc__, file=sys.stderr)
        return 2
    # The API's demo state writes under the working directory.
    os.chdir(tempfile.mkdtemp(prefix="anemoi-probe-"))
    # Training prints progress ("Using CPU."); stdout is the JSON only.
    with contextlib.redirect_stdout(sys.stderr):
        result = parity() if argv[1] == "parity" else bench()
    json.dump({"compiled": _is_compiled(), argv[1]: _jsonable(result)}, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
