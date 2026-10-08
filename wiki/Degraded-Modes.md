# Degraded Modes

Scope v2.1 §4.6.4, §6.2.2, §10.1.

The cycle is written around its failure modes, because a hurricane forecast that arrives late or not at all is a worse outcome than a degraded one that arrives on time.

> **Degradation is always flagged, never silent.** Every fallback appends to `CycleOutput.flags` and surfaces in the dissemination payload. A forecaster who cannot tell a full-ensemble cycle from a climatological-fallback cycle will eventually treat both the same way, and the second is much weaker.

---

## Modes

| Condition | Behaviour | Flag |
|---|---|---|
| Working fix late past the timeout | Extrapolate from the last two fixes | `vitals=estimated` |
| `t−6` NWP missing | Fall back to `t−12` | `nwp_stale=12h` |
| All NWP missing within 12 h | Abandon the cycle; LSTM + climatology mode | `CycleAbandoned` raised |
| Diffusion crash or empty ensemble | Climatological-spread ensemble | `spread_fallback:<ExcType>` |
| Optional feed missing | Continue | `missing:<source>` |
| **Opportunistic** feed missing | Continue | **no flag** |
| Late start would breach the margin | Reduced-ensemble profile | `load_shed` on the plan |
| Ensemble underdispersed or < 10 members | Climatological cone radii | `basis: "climatology"` per segment |

---

## Late working fix

Past `t + 1:20` the cycle stops waiting and runs on an extrapolated vitals estimate. Late is worse than approximate: an advisory published without our guidance is worth nothing.

```python
from anemoi.inference.cycle import extrapolate_fix
fix = extrapolate_fix(history, target_time)   # quality = ESTIMATED
```

Linear extrapolation of the last motion vector, with **intensity held constant**. Persistence is the right choice over the ~45 minutes being bridged — a cleverer intensity model adds variance without adding skill.

`run_cycle` refuses to proceed if the plan expects an extrapolated fix but is handed a `WORKING` one, and vice versa. The two must agree.

Set `allow_estimated_vitals=False` to abandon instead:

```python
plan_cycle(t, oracle, allow_estimated_vitals=False)
# CycleAbandoned: working fix for 20260806_06Z not available by 07:20Z
```

---

## Stale or missing NWP

`select_nwp_cycle` walks back `t−6` → `t−12`. Beyond that:

```python
# CycleAbandoned: no NWP cycle within 12h for 20260806_06Z;
# fall back to LSTM + climatology mode (Scope v2.1 §4.6.4)
```

A `t−12` cycle runs but is marked `degraded` and carries `nwp_stale=12h`, which also appears as `nwp_cycle_lag_hours: 12` in the payload.

---

## Anemoi-Spread failure

Any exception from the ensemble generator — or an empty member list — degrades rather than blocks:

```python
def climatological_ensemble(deterministic, n_members=20, seed=0): ...
```

Members are drawn around the deterministic track using the **climatological cone radii**, converted to a per-member sigma via the Rayleigh quantile. The resulting spread is honest about being climatology rather than a learned distribution.

It carries no flow-dependent structure and is emphatically not a substitute for the diffusion ensemble. It keeps a probabilistic product on the wire.

---

## Optional vs opportunistic

This distinction exists so the degradation flag keeps its meaning.

| Tier | Sources | Missing → |
|---|---|---|
| Optional | `goes`, `ndbc`, `sst_ohc`, `ensemble_perturbations` | Flag `missing:<source>`, mark degraded |
| Opportunistic | `dropsonde`, `microwave` | Nothing. This is normal |

Aircraft recon only flies for threatening storms; a microwave overpass either happened in the window or did not. Flagging their routine absence would mark every cycle degraded.

`test_absent_opportunistic_feeds_do_not_flag_the_cycle` asserts a clean cycle with both absent.

---

## Full failure scenario table

§10.1.

| Scenario | Impact | Mitigation |
|---|---|---|
| Primary GPU node failure | Training halted | Kubernetes pod rescheduling; checkpoint resume from last epoch |
| Copernicus CDS outage | Stage A data delayed; **zero operational impact** | Queue ERA5 backfill; pause skew-audit jobs |
| NOMADS outage | Operational gridded input missing | Cached `t−12`; > 12 h stale → LSTM + climatology with staleness flag |
| Single model divergence | Bad forecast | Fusion layer down-weights on recent validation performance |
| Diffusion model crash | No ensemble | Anemoi-Core deterministic + climatological spread |
| Data corruption | Garbage in, garbage out | Great Expectations gates prevent it reaching inference |
| MLflow server down | No tracking | Local JSON/SQLite fallback; sync when restored |
| Parallel worker crash | One model fails | Orchestrator marks the job failed; siblings continue; downstream skipped |
| GPU OOM (parallel) | Large model evicted | Kubernetes reschedule to a higher-memory node (A100 80 GB) |

---

## Fusion divergence handling

The fusion layer down-weights a divergent model by inverse recent error, **with a floor**:

```python
from anemoi.inference.cycle import fusion_weights
fusion_weights({"lstm": 100.0, "transformer": 50.0, "gnn": 12.0}, floor=0.02)
```

Mid-season there may be only a handful of verifying storms. A model zeroed out on three cases is unrecoverable for the rest of the season, so no model is ever fully discarded.

---

Related: [Inference Cycle](Inference-Cycle) · [Operations Runbook](Operations-Runbook) · [Train/Serve Consistency](Train-Serve-Consistency)
