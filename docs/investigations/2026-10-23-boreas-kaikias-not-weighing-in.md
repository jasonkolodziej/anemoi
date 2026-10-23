# Boreas and Kaikias not weighing in on a live storm (2026-10-23)

**Status:** root cause found in the code, not yet confirmed against the live
storm's data. This note is the hand-off for a laptop session that has
production access. Steps 1–3 below confirm the cause; step 4 is the fix.

## What was seen

Two cycles of the same storm on the console's storm page (Model Pantheon card):

| | Notus (transformer) | Eurus (gnn) | Zephyrus (cnn) | Boreas (lstm) | Kaikias (pinn) |
|---|---|---|---|---|---|
| Weight | 32% | 31% | 36% | not weighing in | not weighing in |
| Reason shown | | | | `no real live feature (no cache, on-demand fetch failed)` | `no real live feature, checkpoint, or env standardisation stats` |

Fusion fell back to inverse-error weights, since learned `ConsensusFusion`
needs all five models (`_real_fusion_forecast`).

## Why the reasons don't add up

* **Boreas's reason is wrong.** LSTM never fetches gridded fields.
  `build_live_lstm_x(track, current)` (`src/anemoi/training/real_inference_live.py`)
  only reads the track, and returns `None` for one reason only:
  `track.window_ending(current.valid_time, SEQUENCE_LENGTH + 1)` is `None`.
  `deterministic_fn` (`src/anemoi/training/real_inference_cycle.py`) labels
  any `None` from a non-PINN builder as a fetch failure.
* **The fields were fine.** Notus, Eurus and Zephyrus all ran on the same
  shared fetch (`shared_fetcher` / `live_fields`), so the GFS fetch worked.
* **Kaikias needs the same window.** `build_live_pinn_x` calls the same
  `_current_window(track, current, SEQUENCE_LENGTH + 1)` to feed its
  candidate LSTM. Its message lumps every failure together, so this cause
  can't be told apart from the others.

The only thing that drops exactly LSTM and PINN while the three gridded
models still run is the track-history window.

## Root cause

`Track.window_ending(ts, length)` (`src/anemoi/data/besttrack.py`) returns
`None` unless the track holds a fix whose `valid_time == ts` **exactly** and
at least `length - 1` fixes come before it (`SEQUENCE_LENGTH = 4`, so 5
fixes in all).

The cycle's `current` fix comes from `initial_fix()`
(`src/anemoi/api/real_state.py`), and its `valid_time` is always the cycle
`target`. That gives two ways for the window to be `None`:

1. **No fix at the cycle time yet (most likely).** If TC-Vitals for `target`
   haven't reached `storm.track`, `initial_fix` extrapolates
   (`fix_source="extrapolated"`) or holds the last fix (`"persisted"`). The
   new fix is not in `track.fixes`, so `window_ending` can't find
   `target`, and LSTM and PINN both drop out on every such cycle. A
   scheduled cycle runs at about t+1:30, which is close to when vitals land,
   so this can happen often.
2. **A young storm.** With fewer than 5 fixes up to `target`, LSTM and PINN
   can't run until the storm has 24 h of history.

This isn't a #214 regression. Before #214 the cycle also relabelled a fix
with `valid_time=target`, so case 1 behaved the same way.

`worst_case=True` (`withhold_vitals`) does **not** trigger it on its own: the
fix is extrapolated, but the track still holds the `target` fix, so the
window is found.

### Reproduction (no torch needed)

```python
# uv run --extra api python repro.py
from datetime import UTC, datetime, timedelta
import numpy as np
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.api.real_state import initial_fix
from anemoi.training.real_inference_live import build_live_lstm_x

def make_track(storm_id, n, seed=0):  # same as tests/test_real_inference_cycle.make_track
    rng = np.random.default_rng(seed); lat, lon = 15.0, -50.0
    start = datetime(2026, 8, 1, tzinfo=UTC); fixes = []
    for i in range(n):
        lat += float(rng.uniform(0.1, 0.3)); lon -= float(rng.uniform(0.2, 0.5))
        fixes.append(Fix(storm_id=storm_id, valid_time=start + timedelta(hours=6 * i),
            lat=round(lat, 2), lon=round(lon, 2), max_wind_kt=float(50 + 2 * i),
            min_pressure_mb=float(995 - 1.5 * i), quality=TrackQuality.WORKING))
    return Track(storm_id=storm_id, fixes=tuple(fixes))

track = make_track("AL992026", 8)
for target in (track.fixes[-1].valid_time, track.fixes[-1].valid_time + timedelta(hours=6)):
    fix, src = initial_fix(track, target)
    print(src, build_live_lstm_x(track, fix) is not None)
young = make_track("AL982026", 4)
fix, src = initial_fix(young, young.fixes[-1].valid_time)
print("young", src, build_live_lstm_x(young, fix) is not None)
```

Output on `main` at `aba5d99`:

```
tcvitals True
extrapolated False
young tcvitals False
```

## Laptop session: confirm on the real storm

The cloud session has no production access. Steps 1–3 need it.

1. **Look at the console.** On the storm page, above the intensity chart,
   the cycle header says `Started from …`
   (`console/src/routes/storms/[stormId]/+page.svelte`, `FIX_SOURCE_TEXT`).
   For both cycles in the screenshots:
   * `a fix extrapolated from earlier ones` or the persisted wording →
     **case 1**.
   * `the storm's own TC-Vitals` → go to step 2 (likely case 2).
2. **Read the cycle and the storm from the API.** Use the deployed real API
   (`anemoi-api-real` Worker; see `docker/api/README.md` for access and the
   console proxy secret):
   ```bash
   API=https://anemoi-api-real.jasonkolodziej.workers.dev/v1
   STORM=<storm id from the console URL>   # e.g. AL172026
   CYCLE=<cycle label shown on the page>
   curl -s "$API/storms/$STORM/cycles/$CYCLE" \
     | jq '{fix_source: .provenance.fix_source, fix: .provenance.fix,
            reasons: .products.missing_model_reasons,
            contributors: .products.contributors,
            versions: .provenance.model_versions, fusion: .provenance.fusion,
            flags: .payload.flags}'
   curl -s "$API/storms/$STORM" | jq '[.history[].valid_time] | (length, .[-6:])'
   ```
   The field names come from `src/anemoi/api/schemas.py` (`CycleResult`,
   `CycleProducts`, `ProvenanceOut`, `StormDetail`). `.payload.flags` is a
   guess; drop it if `jq` returns null. Confirm:
   * `provenance.fix.valid_time` (= the cycle target) is **not** among the
     track's `valid_time`s → case 1.
   * fewer than 5 track fixes at or before the target → case 2.
3. **Rule out the other PINN failures.** Kaikias's message also covers a
   missing candidate checkpoint and missing `env_mean`/`env_std`. Check the
   registry for PINN's served version:
   ```bash
   curl -s "$API/registry/pinn" | jq
   ```
   Then, with the checkpoint store configured (same env as the API
   container), run `_run_pinn` from a `uv run --extra torch-cpu --extra api
   python` shell against that version and the storm's track. Step into it:
   `load_trained_pinn_candidate`, then `build_live_pinn_x`, then
   `load_standardization_stats(version)` keys. Note which one returns
   `None`. If the window is the only failure, the fix below covers both
   models.

## Step 4: the fix (one PR, after steps 1–3 confirm)

**a. Honest reasons (do this regardless).** In `deterministic_fn`:

* For `lstm`, a `None` from `_build_live_x` means "not enough track history
  ending at the cycle time". Say so, with the fix count and whether the
  cycle's fix was extrapolated or persisted. Don't say fetch failure.
* For `pinn`, have `_run_pinn` return *why* it got `None`, as other models
  already do, instead of one combined string. A small `(pred, reason)` tuple
  or a sentinel is enough.
* Tests in `tests/test_real_inference_cycle.py`: one per new reason,
  following `test_deterministic_fn_reports_missing_standardisation_stats_by_name`.

**b. Let LSTM and PINN run on an extrapolated or persisted fix (case 1).**
Build the window from the track's fixes before `current.valid_time`, plus
`current` itself, instead of requiring `current` to be in `track.fixes`.
For example, a helper in `real_inference_live`:

```python
def _current_window(track, current, length):
    window = track.window_ending(current.valid_time, length)
    if window is not None:
        return window
    prior = tuple(f for f in track.fixes if f.valid_time < current.valid_time)
    if len(prior) < length - 1:
        return None
    return (*prior[-(length - 1):], current)
```

Decide before merging:

* **Spacing.** `storm_relative_sequence` assumes the 6-hourly spacing that
  training used. An extrapolated `current` is always at a synoptic time
  6 h after the last fix, so spacing holds. A *persisted* fix (fewer than 2
  prior fixes) can't meet the length-5 requirement anyway. Assert the
  spacing, or reject windows that aren't 6-hourly.
* **Skew.** Training never saw an ESTIMATED final fix. Flag it the way
  `input_skew` does (for example, `input_skew["lstm"] = "extrapolated
  initial fix"`) so the cycle reports it, rather than hiding it.
* **The same exact-match assumption appears in two more places.** Fix it
  in all three, or LSTM and PINN will come back while learned fusion and
  the diffusion ensemble still fall back:
  * `_build_live_context` (`real_inference_cycle.py`): learned fusion's
    context vector calls `track.window_ending(current.valid_time, 5)`, so
    on an extrapolated fix it returns `None` and fusion stays
    `inverse_error`.
  * `build_real_ensemble_fn` (`real_inference_ensemble.py`) recovers
    `current` with `track.window_ending(deterministic.target_time, 1)` and
    raises `InferenceEnsembleError` when there's no track fix at the
    target. `run_cycle` then falls back to the climatological ensemble.
    This may also be why Skiron shows "not available". Pass the cycle's
    real `current` fix through (the closure already captures `track`; add
    the fix the same way) instead of re-deriving it from the track.
    Under `worst_case` it currently picks up the track's WORKING fix
    rather than the extrapolated one the deterministic path used.
* **Skew audit.** `monitoring.skew_audit` re-runs this path. Check it still
  compares like with like.

**c. Young storms (case 2).** These are a different regime (see
`window_ending`'s docstring: no zero-padding). Keep them excluded, but with
the honest reason from (a). Padding or a shorter-sequence model is a
separate decision.

### Acceptance

* Re-running the screenshotted cycle (same storm and label) gives Boreas and
  Kaikias weights. If it was case 2, they show an accurate reason instead.
* When all five contribute and fusion's `latent_signature` matches, the
  cycle reports `fusion: learned`, even on an extrapolated fix.
* An extrapolated-fix cycle no longer falls back to the climatological
  ensemble just because the track has no fix at the target.
* A regression test for each: a track whose last fix is 6 h before the
  cycle target.
* `uv run --extra torch-cpu --extra api --extra dev pytest
  tests/test_real_inference_cycle.py tests/test_real_inference_ensemble.py
  tests/test_cycle_provenance.py` passes,
  and `ruff check` is clean.
* Add a Decision Log entry under `wiki/` for the window rule (b), since it
  changes what the LSTM sees at inference.
