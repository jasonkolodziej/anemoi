# Operations Runbook

Scope v2.1 §8, §10.2–10.3.

---

## Seasonal calendar

| Period | Activity |
|---|---|
| **January–April** | Off-season. Full retraining on the complete historical dataset. Architecture experiments. Hyperparameter sweeps. |
| **May** | Pre-season. Deploy production models. Load-test the inference pipeline. Validate against the 2025 test storms — **spend a test-set budget entry**. |
| **June–November** | Active season. Real-time inference every 6 hours. Weekly incremental retraining on new storms. Performance monitoring. |
| **December** | Post-season. Archive season data. Retrospective analysis. Identify failure modes. Plan architecture improvements. |

> **Test-set discipline.** §8.1's pre-season validation against held-out storms is a legitimate use, but it is not free. Route it through `TestSetBudget.spend()` with a written justification so the number of looks is recorded. See [Training Architecture](Training-Architecture).

---

## Daily schedule

Every cycle is gated on its working fix and delivers **at least 30 minutes before** the corresponding NHC advisory.

| Time (UTC) | Activity |
|---|---|
| ~00:45–01:00 | 00Z working fix received; 00Z cycle runs using **18Z NWP valid 00Z** |
| ~01:45–02:30 | **00Z Anemoi-Core + Anemoi-Spread products out** (before the 03Z advisory) |
| ~03:45 | 00Z GDAS/GFS lands → staged for the 06Z cycle |
| ~06:45–07:00 | 06Z cycle runs using **00Z NWP valid 06Z** |
| ~07:45–08:30 | **06Z products out** (before the 09Z advisory) |
| ~09:45 | 06Z GDAS/GFS lands → staged for 12Z |
| ~12:45–13:00 | 12Z cycle runs |
| ~13:45–14:30 | **12Z products out** (before the 15Z advisory) |
| ~15:45 | 12Z GDAS/GFS lands → staged for 18Z |
| ~18:45–19:00 | 18Z cycle runs |
| ~19:45–20:30 | **18Z products out** (before the 21Z advisory) |
| 21:00 | Daily performance report generated (vs NHC, ECMWF) |
| 23:00 | Automated drift check + skew audit on validation metrics |

Note the staging pattern: each NWP cycle lands mid-way through the *following* forecast cycle's gap and is staged for the one after. That is why prefetch at `t+0:00` has something to work with.

Inspect any day's real timeline:

```bash
uv run anemoi schedule 2026-08-06
uv run anemoi schedule 2026-08-06 --worst-case
```

### Automatic cycles in production

The deployed `anemoi-api-real` Worker's cron (`30 1,7,13,19 * * *`, UTC) fires at **t+1:30** after each synoptic time -- 10 minutes past the derived vitals timeout, so vitals have landed or the honest `vitals_estimated` fallback applies. Each firing starts one instance of the **`anemoi-cycle` Workflow** ([Decision Log #46](Decision-Log#46-the-cron-became-a-durable-workflow-208--reliability)):

1. **find due storms** -- active storms whose last cycle isn't this one yet;
2. **run cycle {storm}** -- one step per storm, retried twice on a 5xx or an unreachable container; a 4xx is recorded as `refused`;
3. **refresh read cache** -- the KV snapshot the console reads;
4. **calibration audit** -- see [Monitoring](Monitoring#calibration-audit).

So between t+0:00 and t+1:30 the newest forecast on a storm is still the previous cycle's.

**Where to look:** Cloudflare dashboard → **Workers & Pages → Workflows → anemoi-cycle** (its own sidebar entry, not a tab on the Worker). Instances are named `cycle-<label>`, e.g. `cycle-20261008_06Z`; each shows per-step outcomes and retries, and its output lists every storm as `ran`, `refused`, `already run` or `failed`. Or: `wrangler workflows instances list anemoi-cycle`. Step logs appear in `wrangler tail` as `cycle workflow <label>: ...`.

---

## The GCP training instance

`anemoi-train-1` (GPU, real training only — never in the request path) does not need to run 24/7, and running it idle is a real, found cost mistake, not a defensible steady state: confirmed live (2026-09-17) via `gcloud compute ssh` — 8+ hours uptime, 0% GPU utilization, no active session, after its most recent real training run had already completed.

**The correct pattern is wake → check → (train if due) → shut down, not "stay on."** `anemoi retrain-check` (see [Retraining Triggers](Retraining-Triggers)) is built for exactly this: on an ordinary day it evaluates real triggers, finds nothing due, and exits in seconds without touching the GPU; on the rare day a trigger fires (the 1st of the month, May 1, or a real >500-synoptic-time data-volume threshold), it runs the real multi-hour training wave. A [GCP instance schedule](https://cloud.google.com/compute/docs/instances/schedule-instance-start-stop) waking the instance once daily, with a startup script invoking `anemoi retrain-check` and then stopping the instance when it returns (regardless of outcome), gets genuine autonomy — no human SSH session required on an ordinary day — for a small fraction of the cost of leaving a GPU box running continuously. This is provisioning, not code, and is not stood up automatically by anything in this repo; see [Decision Log](Decision-Log) for the real registry/promotion bugs `anemoi retrain-check`'s own dispatch logic depends on having been fixed first.

**Drift/skew triggers cannot fire against a real deployment yet** (see [Roadmap §7](Roadmap#7-autonomous-retraining-orchestration--calendardata-volume-done-driftskew-blocked-on-real-data)), so today's real cadence is: idle almost every day, a few hours on the 1st of each month, a few hours on May 1, and rare data-volume-triggered days — nothing that benefits from the instance staying warm between cycles.

To stop it manually right now: `gcloud compute instances stop anemoi-train-1 --zone=us-central1-b` (this preserves the disk; nothing is deleted). To check its state: `gcloud compute instances list`.

---

## Alerting

§8.3. PagerDuty / Slack on:

- Inference pipeline failure
- Track error > 200 nm at 48 h — catastrophic failure indicator
- Data source outage > 2 hours
- GPU node failure during training

Add to these from the v2.1 monitoring layer:

- Skew alert (rolling 14-day 48 h delta over threshold)
- Feature drift alert
- Any cycle delivering with `load_shed` or `vitals=estimated` more than occasionally — a persistent pattern means the vitals feed or the compute envelope needs attention, not the flag

---

## Human-in-the-loop

§10.3.

- **Storm analyst review.** For Category 3+ hurricanes, a human meteorologist reviews Anemoi output before public dissemination.
- **Failure mode logging.** Every significant forecast miss triggers a post-mortem document linked to the MLflow run, identifying whether the error was data, model or physics related.

The post-mortem requirement is why [run tagging](Experiment-Tracking) is validated rather than optional — an untagged run cannot be found again when you need it most.

---

## Incident procedures

### A production model is degrading in real time

1. `reg.rollback("<model>")` — reverts to the most recent archived version. Survives a process restart.
2. Confirm the active pin: `reg.active_pin()`.
3. If the rollback breaks the latent signature (rolling back a Group 1 model with derived models pinned to it), re-pin a coherent set. See [Model Registry](Model-Registry).

### Corrupted data detected

1. DVC checkout the previous known-good dataset version.
2. Retrain from the last clean checkpoint.
3. Check whether any run tagged with the bad `dvc_version` reached staging or production.

### Parallel training keeps failing on resource contention

The orchestrator falls back to sequential mode automatically and alerts. Expect a ~6–10× longer cycle.

### NOMADS has been down for hours

- Under 12 h: cycles run on `t−12` with `nwp_stale=12h`. Degraded but functional.
- Over 12 h: cycles abandon. Fall to LSTM + climatology mode with an explicit staleness flag.
- ERA5-based skew-audit jobs are unaffected by NOMADS but should be paused if **CDS** is the outage instead.

### A scheduled cycle didn't appear

1. Find the instance `cycle-<label>` (above). No instance at all means the cron didn't fire or the Worker isn't deployed with the `anemoi-cycle` Workflow binding -- check the Deploy run.
2. A storm marked `refused` was rejected by the API (`4xx`, message in the output) and won't be retried; `failed` exhausted its retries -- `wrangler tail` and the step's attempts show why.
3. A cycle can always be run by hand from the console's storm page (**Run cycle**); it writes the read cache like a scheduled one.

**Console shows something older than the API has:** the read cache (KV) serves a storm for up to 30 minutes before refreshing, and every cycle run refreshes it. To check what the API itself returns, request it with `Cache-Control: no-cache` (`X-Anemoi-Cache: bypass` confirms the cache was skipped).

### The skew audit is alerting

Trigger a **Stage B re-fine-tune only** for the affected model — the pretrained representation is still valid. The cascade to diffusion and fusion applies automatically. See [Retraining Triggers](Retraining-Triggers).

---

Related: [Inference Cycle](Inference-Cycle) · [Degraded Modes](Degraded-Modes) · [Monitoring](Monitoring) · [Model Registry](Model-Registry) · [Retraining Triggers](Retraining-Triggers) · [Roadmap](Roadmap)
