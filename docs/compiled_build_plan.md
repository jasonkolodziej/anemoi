# Anemoi — Compiled (C) Build Plan

Nov 17, 2026

**Status:** plan only. Nothing in the package, the images or CI has changed.
The one thing done so far is a throwaway feasibility spike, described under
[What the spike showed](#what-the-spike-showed).

## Goal

Have the Python training code and the API compiled to C and run as native
code, **without changing what runs today**. The current pure-Python package,
`uv sync`, the `training` and `api` images and the `anemoi` CLI all stay as
they are; the compiled build is a second, opt-in artifact built from the same
source files, and it becomes the default only after it has been shown to
behave the same.

## What "run as C" means here

The recommended route is **Cython in pure-Python mode**: each module under
`src/anemoi/` is translated to a C file and compiled to an extension module
(`.so`), with no edits to the `.py` source. `import anemoi.cli` then loads
machine code instead of bytecode. `anemoi …` and
`uvicorn anemoi.api.main:app` are invoked exactly as now.

Two limits to be clear about before committing to this:

- **It still needs CPython.** The generated C calls the Python C-API, so the
  interpreter, torch, numpy, FastAPI and the rest are still installed and
  loaded. This is not a standalone C program with no Python.
- **The heavy math is already native.** Training time is spent inside torch
  (C++/CUDA) and numpy (C). Compiling the orchestration around it removes
  interpreter overhead from Anemoi's own code only. Expect little change in
  training wall time and a modest one in API request handling and the
  numpy-loop-heavy data and metrics code. Phase 2 measures this; no speedup
  is claimed until then.

If the aim is instead to serve the *models* with no Python at all, that is a
different project (export to ONNX or TorchScript, serve from C++), listed as
optional [phase 6](#phase-6-optional-going-further).

## What the spike showed

Run in a scratch copy of `src/anemoi`, Python 3.13, Cython 3.3.1, gcc 13,
without torch (PyTorch's CPU wheel index was unreachable from the sandbox).

| | Result |
|---|---|
| Modules compiled | 114 of 114 (every `.py` except `__init__.py`/`__main__.py`), no source edits |
| Build time | 80 s on 4 cores at `-O1` |
| Size | 3.5 MB of `.py` becomes 25 MB of `.so` |
| API | `anemoi.api.main` imports from the `.so` files, 14 routes registered |
| Tests, source tree | 1014 passed, 4 failed, 99 skipped |
| Tests, compiled tree (`.py` deleted) | 1010 passed, 8 failed, 99 skipped |

The 4 failures on the source tree (`test_real_dropsonde` ×1,
`test_spread_backtest` ×3) fail the same way compiled; they are a
pre-existing condition of this sandbox, not caused by compilation, and were
not investigated. The 4 extra failures compiled are all in
`tests/test_sources.py`, which parses the package's `.py` files with `ast`;
with the source deleted there is nothing to parse.

Not covered by the spike: the 99 skipped tests, which are mostly the
torch-marked model and training tests. **The training loops themselves have
not been run compiled.** That is the main unknown and is phase 2's first job.

Problems found, each with a known fix:

1. **Cython enforces annotations by default.** `x: str = Header(...)` in
   `api/deps.py` raised `TypeError: Expected str, got Header` at import.
   Fixed with the directive `annotation_typing=False`, which the build must
   set globally.
2. **`config.py` finds `configs/` via `Path(__file__).parents[2]`.** That
   works for a checkout but not for a wheel installed into `site-packages`.
   Compiled images must set `ANEMOI_CONFIG_DIR=/app/configs` (the override
   already exists).
3. **`api/static/redoc-theme.css` must ship beside the compiled
   `api/main`.** It is located by `Path(__file__).parent / "static"`.
4. **Tests that read source** (`test_sources.py`, and candidates
   `test_config_sync.py`, `test_retrain_seasons.py`, `test_cycle_policy.py`,
   `test_atcf_archive.py`, which use `__file__`/`ast`) belong to the source
   tree and should run only there.

## Risks still to check

- **Torch code compiled.** `nn.Module` subclasses defined in compiled
  modules, `torch.compile` (`training/device.py`) tracing through compiled
  functions, and `inspect.signature` on builders in
  `models/architecture.py`. Checkpoints are saved as `state_dict` and loaded
  with `weights_only=True`, so pickling of compiled classes should not come
  up, but this needs a run to confirm.
- **`torch.compile` may fall back.** Dynamo traces Python bytecode, and a
  compiled function has none. If a model's `forward` is compiled by Cython,
  `torch.compile` may skip or fail on it. Likely outcome: `models/` is
  excluded from compilation and stays `.py`. That is fine, since `forward`
  is torch calls anyway.
- **`provenance.py`** runs `git rev-parse` with `cwd=Path(__file__).parent`
  and reads `build-info.json` by path. Confirm both resolve from an
  installed wheel in the image.
- **Tracebacks** from compiled modules show file and line but not the source
  text unless the `.py` files are shipped alongside. Decide whether to ship
  them (better debugging) or not (source not in the image).
- **One wheel per Python version and platform.** The images are Python 3.12
  on linux/amd64; the compiled wheel is built for exactly that inside the
  Docker builder. Local development on macOS stays pure Python.
- **Coverage** (`pytest --cov`) does not see compiled code. Coverage stays a
  source-tree measurement.

## Phases

Each phase is its own PR and leaves the default path untouched until phase 5.

### Phase 1: build plumbing, off by default

- [ ] Add `compile/setup.py` (setuptools + Cython, pinned) and
      `.github/scripts/build-compiled-wheel.sh`. It reads `src/anemoi`,
      writes a platform wheel to `dist-compiled/`, and touches nothing in
      `src/`. `pyproject.toml`'s `[build-system]` stays hatchling, so
      `uv sync`, editable installs and the existing wheel are unchanged.
- [ ] Directives: `language_level=3`, `binding=True`,
      `annotation_typing=False`, `always_allow_keywords=True`.
- [ ] Keep `__init__.py` and `__main__.py` as `.py`; ship
      `api/static/` as package data; a single exclude list in
      `compile/setup.py` for modules that must stay interpreted.
- [ ] `.gitignore` the generated `.c`, `.so` and `dist-compiled/`.

### Phase 2: prove it behaves the same

- [ ] Mark source-reading tests with a new `source` pytest marker.
- [ ] Add a script that installs the compiled wheel into a clean venv and
      runs `pytest -m "not source"` against the *installed* package (not
      `src/`), asserting that `anemoi.cli.__file__` ends in `.so` so the run
      cannot silently test the source tree.
- [ ] Run it with the `torch-cpu` extra so the 99 skipped tests execute.
      Fix or exclude whatever fails; record each exclusion and why.
- [ ] Parity check: one small seeded training run and one inference cycle,
      source vs compiled, asserting identical metrics and outputs.
- [ ] Benchmark: test-suite time, API request latency, one training epoch,
      source vs compiled. Write the numbers here.
- [ ] CI: a `compiled` job running the above on pull requests. Note that
      `ci.yml` today only validates YAML and scans for secrets; it does not
      run pytest, so this job would be the first test run in CI. Adding a
      plain source-tree pytest job alongside is recommended.

**Gate:** stop here if the benchmark shows no gain worth a second build
artifact, unless the aim is something other than speed.

### Phase 3: compiled images, beside the current ones

- [ ] Add stages `training-compiled` and `api-compiled` to
      `docker/multistage.Dockerfile`: a builder stage with gcc builds the
      wheel, the runtime stage installs it instead of copying `/app/src`,
      and sets `ANEMOI_CONFIG_DIR=/app/configs`. `api` must remain the
      **last** stage, because Cloudflare Containers builds the final stage.
- [ ] Publish under separate tags (`anemoi-train:<sha>-compiled`); `latest`
      is not moved.
- [ ] Run `.github/scripts/smoke-test-image.sh` against both new targets.

### Phase 4: trial

- [ ] API: run the compiled image locally and in a non-production
      Cloudflare environment; compare responses for a full cycle against
      the current image.
- [ ] Training: run one scheduled Cloud Run job from the compiled image by
      overriding the image tag; compare its metrics and registry entry with
      the same job from the current image.
- [ ] Rollback is switching the tag back; nothing else changes.

### Phase 5: decide the default

- [ ] If phases 2–4 are clean, point the deploy workflows at the compiled
      targets and keep the pure-Python targets building as the fallback.
- [ ] Document in `wiki/Getting-Started.md`, `wiki/Testing.md` and
      `docker/*/README.md`; add a Decision Log entry.

### Phase 6 (optional): going further

Only if phase 2's numbers justify it:

- Type the hot numpy loops (about 59 `for … in range` loops, mostly in
  `data/` and `metrics/`) with Cython pure-mode annotations, which is where
  real speedups come from.
- Export trained models (ONNX or TorchScript) and serve inference from a
  C++ runtime, removing Python from the serving path altogether. This
  changes the train-serve consistency story and needs its own plan.

## Alternatives considered

| Option | Why not first choice |
|---|---|
| **Nuitka** (whole program to C, one binary) | Closest to "a C executable", but bundling torch, mlflow, eccodes and gcsfs into a standalone build is slow and fragile, and uvicorn's `module:app` import string and MLflow's entry-point plugin need special handling. Worth revisiting for the API alone if a single binary is wanted. |
| **mypyc** | Needs strictly typed code and rejects much of what pydantic, FastAPI and dataclass-heavy modules do dynamically. More source changes, so more risk to current behaviour. |
| **Hand-rewriting in C/C++** | Discards 33k lines of tested Python and the policy checks that are the point of this codebase. |

## Open question

What is the compiled build for: speed, keeping source out of the images, or
a simpler deployment? The phases above assume speed. If it is source
protection, phase 2's benchmark gate goes away and `.py` files are left out
of the image; if it is a single deployable binary, Nuitka for the API moves
up.
