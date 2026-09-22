"""Model registry.

Scope v2.1 §7.1 and §10.1. MLflow is the intended backend; when it is absent or
unreachable the registry degrades to a local JSON store and syncs later, which
is the §10.1 "MLflow server down" mitigation made real rather than aspirational.

Beyond plain versioning this module implements **model-set pinning**. Anemoi-Spread's
diffusion model and the fusion model are trained on latents extracted from
specific Group 1 checkpoints. Promoting a new LSTM on its own therefore does not
produce a better system -- it produces a diffusion model conditioned on latents
that no longer exist. Production pins a coherent *set*, and a set is only
promotable when every member agrees on the latent signature it was built from.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from ..data.sources import Flavor

GROUP1_MODELS: tuple[str, ...] = ("lstm", "cnn", "transformer", "gnn", "pinn")
DERIVED_MODELS: tuple[str, ...] = ("diffusion", "fusion")
ALL_MODELS: tuple[str, ...] = GROUP1_MODELS + DERIVED_MODELS

#: Durable-storage key `registry.json` is mirrored to/hydrated from, when a
#: `checkpoint_store` is provided -- see `ModelRegistry`'s docstring. Same
#: bucket `tracking.checkpoint_store.CheckpointStore` already uploads real
#: checkpoints to, a fixed prefix so every writer/reader agrees on it.
REGISTRY_STORE_KEY = "registry/registry.json"


class Stage(str, Enum):
    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class RegistryError(RuntimeError):
    pass


@dataclass(slots=True)
class ModelVersion:
    name: str
    version: int
    stage: Stage
    run_id: str
    input_flavor: Flavor
    metrics: dict[str, float]
    tags: dict[str, str]
    #: Identifies the Group 1 checkpoint set the latents were extracted from.
    #: None for Group 1 models themselves.
    latent_signature: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    #: Where this version's real trained weights live (`register`'s
    #: ``checkpoint_uri`` argument) -- persisted here, not just mirrored to
    #: MLflow (#78). Before this field existed, a real inference process
    #: had no way to look up "given this registered version, where's its
    #: checkpoint" without an MLflow client configured and reachable; local-
    #: registry-only deployments (`ModelRegistry.mlflow_available is
    #: False`, Scope v2.1 SS10.1's real degraded mode) had no way at all.
    #: None for a version registered before this field existed.
    checkpoint_uri: str | None = None

    def to_json(self) -> dict:
        data = asdict(self)
        data["stage"] = self.stage.value
        data["input_flavor"] = self.input_flavor.value
        return data

    @classmethod
    def from_json(cls, data: dict) -> ModelVersion:
        data = dict(data)
        data["stage"] = Stage(data["stage"])
        data["input_flavor"] = Flavor(data["input_flavor"])
        return cls(**data)


class ModelRegistry:
    """Local-first registry with an optional MLflow mirror and an optional
    durable-storage (R2/S3) mirror.

    ``mlflow_client`` is any object exposing MLflow's model-registry surface; it
    is duck-typed so tests can pass a stub and so an MLflow outage degrades to
    the local store instead of failing the run.

    ``checkpoint_store`` is any object exposing
    ``tracking.checkpoint_store.CheckpointStore``'s ``upload``/``download``/
    ``exists`` surface (duck-typed the same way), and exists for a different
    reason than the MLflow mirror: MLflow is a one-way mirror humans browse,
    but ``registry.json`` itself is never read back from it (`versions`/
    `latest`/`production` only ever read local state -- see `_load`). A
    process with no local ``registry.json`` at all (a fresh Cloudflare
    Container's ephemeral disk being the motivating case -- issue #91) has
    nothing to load from unless something durable holds a copy. When set,
    local state is always reconciled against ``checkpoint_store`` at
    construction -- not just hydrated once when local is entirely missing
    -- since a persistent-disk process (the training VM) would otherwise
    never see state another process wrote to the same durable store (see
    `_load`'s own comment for the real incident this closes). Every real
    save is mirrored back to it -- same never-fail-the-caller contract as
    the MLflow mirror below.
    """

    def __init__(self, root: Path | str, mlflow_client=None, checkpoint_store=None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "registry.json"
        self._mlflow = mlflow_client
        self._checkpoint_store = checkpoint_store
        self._versions: dict[str, list[ModelVersion]] = {}
        self._pins: dict[str, dict] = {}
        self._load()

    # ---- persistence -----------------------------------------------------

    def _load(self) -> None:
        # Always reconcile with the durable mirror when one is configured,
        # not just when no local file exists at all -- a persistent-disk
        # process (the training VM's real case: registry.json survives
        # across runs) would otherwise never see state written by any
        # *other* process sharing the same durable store (the deployed
        # API's own ModelRegistry instance, a manual promotion, a
        # different machine's training run). Found for real: a manual
        # promotion applied only to the deployed container's registry.json
        # was silently discarded the next time the VM ran a full training
        # pass and pushed its own (unaware, stale) local copy back over
        # it. Durable storage is the real shared source of truth here, so
        # it wins whenever it has something -- safe to do unconditionally
        # at construction time since no writes from *this* process have
        # happened yet.
        self._pull_from_checkpoint_store()
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        self._versions = {
            name: [ModelVersion.from_json(v) for v in versions]
            for name, versions in raw.get("versions", {}).items()
        }
        self._pins = raw.get("pins", {})

    def reload(self, checkpoint_store=None) -> None:
        """Re-run `_load` -- re-pulls from the durable mirror (when
        configured) and re-reads whatever ends up on local disk. Exists
        for a long-lived process (a warm Cloudflare Containers singleton
        instance, per `docker/api/README.md`'s own documented "a redeploy
        does not restart an already-running instance") that would
        otherwise only ever see the registry state that existed at its own
        construction time, for its entire warm lifetime -- the same class
        of staleness `_load`'s own reconciliation fix addresses at
        construction, just needing a way to re-trigger it later too.

        ``checkpoint_store``, if given, replaces this instance's mirror
        before reloading -- for a caller that (like `api.real_state
        .RealState`) deliberately builds its `ModelRegistry` with no
        checkpoint_store at construction (listing/reading real storms
        needs no S3 credentials at all), and only wants to pay for
        resolving one lazily, the first time a real reload is actually
        needed."""
        if checkpoint_store is not None:
            self._checkpoint_store = checkpoint_store
        self._load()

    def _save(self) -> None:
        payload = {
            "versions": {
                name: [v.to_json() for v in versions]
                for name, versions in self._versions.items()
            },
            "pins": self._pins,
        }
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        self._push_to_checkpoint_store()

    # ---- durable-storage mirror -------------------------------------------

    def _pull_from_checkpoint_store(self) -> None:
        if self._checkpoint_store is None:
            return
        try:
            if self._checkpoint_store.exists(REGISTRY_STORE_KEY):
                bucket = self._checkpoint_store.config.bucket
                self._checkpoint_store.download(f"s3://{bucket}/{REGISTRY_STORE_KEY}", self._path)
        except Exception:  # noqa: BLE001 - starting empty must never crash construction
            pass

    def _push_to_checkpoint_store(self) -> None:
        if self._checkpoint_store is None:
            return
        try:
            self._checkpoint_store.upload(self._path, REGISTRY_STORE_KEY)
        except Exception:  # noqa: BLE001 - tracking must never fail a training run
            self._checkpoint_store = None

    @property
    def mlflow_available(self) -> bool:
        return self._mlflow is not None

    @property
    def mlflow_client(self):
        """The underlying (duck-typed) MLflow client, or None -- for
        callers that need to pass it on elsewhere (e.g.
        `tracking.experiment_tracking.log_curriculum_stages`) rather than
        reach into a private attribute."""
        return self._mlflow

    # ---- registration ----------------------------------------------------

    def register(
        self,
        name: str,
        *,
        run_id: str,
        input_flavor: Flavor,
        metrics: dict[str, float],
        tags: dict[str, str] | None = None,
        latent_signature: str | None = None,
        checkpoint_uri: str | None = None,
        mlflow_run_id: str | None = None,
    ) -> ModelVersion:
        """Register a new version.

        Rejects non-operational-flavor weights outright: per §4.6.1 only Stage B
        output is a candidate for anything, so an ERA5-flavor artifact has no
        business in the registry at all.

        ``checkpoint_uri`` is stored on the returned `ModelVersion` (#78,
        so a real inference process can look up where a version's weights
        live without an MLflow client) and, together with ``mlflow_run_id``,
        optionally mirrors to MLflow (below): the real `create_model_version`
        API needs a real artifact ``source`` URI, so without one the mirror
        is skipped rather than sent a fabricated placeholder. ``mlflow_run_id``
        (from `tracking.experiment_tracking.log_curriculum_stages`) links the
        mirrored model version back to the real run that produced it, when
        one exists.
        """
        if name not in ALL_MODELS:
            raise RegistryError(f"unknown model {name!r}; expected one of {ALL_MODELS}")
        if input_flavor is not Flavor.GDAS_FINETUNE:
            raise RegistryError(
                f"{name}: refusing to register {input_flavor.value} weights -- only "
                "Stage B (operational-flavor) artifacts are registrable (§4.6.1)"
            )
        if name in DERIVED_MODELS and not latent_signature:
            raise RegistryError(
                f"{name}: derived models must record the latent_signature of the "
                "Group 1 set they were trained against (§5.7)"
            )

        versions = self._versions.setdefault(name, [])
        version = ModelVersion(
            name=name,
            version=len(versions) + 1,
            stage=Stage.NONE,
            run_id=run_id,
            input_flavor=input_flavor,
            metrics=dict(metrics),
            tags=dict(tags or {}),
            latent_signature=latent_signature,
            checkpoint_uri=checkpoint_uri,
        )
        versions.append(version)
        self._save()
        if checkpoint_uri is not None:
            self._mirror_model_version(name, checkpoint_uri, mlflow_run_id, tags)
        return version

    def get(self, name: str, version: int) -> ModelVersion:
        for v in self._versions.get(name, []):
            if v.version == version:
                return v
        raise RegistryError(f"{name} v{version} not found")

    def versions(self, name: str) -> list[ModelVersion]:
        return list(self._versions.get(name, []))

    def latest(self, name: str) -> ModelVersion:
        versions = self._versions.get(name)
        if not versions:
            raise RegistryError(f"no versions registered for {name!r}")
        return versions[-1]

    def in_stage(self, name: str, stage: Stage) -> ModelVersion | None:
        for v in reversed(self._versions.get(name, [])):
            if v.stage is stage:
                return v
        return None

    def production(self, name: str) -> ModelVersion | None:
        return self.in_stage(name, Stage.PRODUCTION)

    def champion(self, name: str) -> ModelVersion | None:
        """The version actually serving real inference right now -- the
        correct incumbent for a promotion decision (§5.3). Production if
        one exists, else staging, else `None` (no champion yet).

        Deliberately not `latest(name)` (the most recently *registered*
        version, regardless of stage) -- a promotion candidate must beat
        what real cycles are actually using, not whatever the version list
        happens to end with. Using `latest` here was a real, found bug
        (`training.real_orchestrator`/`cli.cmd_train` both did this): it let
        a worse candidate reach staging whenever the immediately-prior
        *registered* version wasn't itself the best one on record, since
        each new candidate only ever had to beat its immediate predecessor,
        not the version real inference was actually falling back to
        (`inference.real_inference_cycle`'s own lookup is this exact
        production-else-staging pattern, mirrored here).
        """
        return self.production(name) or self.in_stage(name, Stage.STAGING)

    # ---- transitions -----------------------------------------------------

    def transition(self, name: str, version: int, stage: Stage) -> ModelVersion:
        """Move a version to a stage, archiving any incumbent in that stage.

        Real bug closed here: the docstring always promised this for *any*
        stage, but the code only ever did it for `Stage.PRODUCTION` --
        `Stage.STAGING` had no incumbent-archiving at all. Two versions
        promoted to staging in sequence (a real, found scenario: `champion`
        correctly beating each successive candidate) left both marked
        `staging` simultaneously, which `in_stage`'s own `reversed()` search
        papered over by always returning the newest match, but the
        registry's on-disk state was genuinely inconsistent -- more than
        one version claiming to be *the* staging candidate.
        """
        target = self.get(name, version)
        if stage in (Stage.PRODUCTION, Stage.STAGING):
            incumbent = self.in_stage(name, stage)
            if incumbent is not None and incumbent.version != version:
                incumbent.stage = Stage.ARCHIVED
        target.stage = stage
        self._save()
        self._mirror_stage_transition(name, version, stage)
        return target

    def rollback(self, name: str) -> ModelVersion:
        """Revert production to the most recent previously-archived version (§10.2)."""
        current = self.production(name)
        candidates = [
            v
            for v in self._versions.get(name, [])
            if v.stage is Stage.ARCHIVED and (current is None or v.version != current.version)
        ]
        if not candidates:
            raise RegistryError(f"{name}: no archived version to roll back to")
        previous = max(candidates, key=lambda v: v.version)
        if current is not None:
            current.stage = Stage.ARCHIVED
        previous.stage = Stage.PRODUCTION
        self._save()
        return previous

    # ---- model-set pinning ----------------------------------------------

    def pin_set(self, label: str, members: dict[str, int]) -> dict:
        """Pin a coherent set of versions as the production system.

        Every model in :data:`ALL_MODELS` must be present, all members must be
        operational-flavor, and every derived model's ``latent_signature`` must
        match the signature computed from the pinned Group 1 versions. This is
        what stops a single-model retrain from silently invalidating Anemoi-Spread.
        """
        missing = [m for m in ALL_MODELS if m not in members]
        if missing:
            raise RegistryError(f"model set is missing members: {missing}")

        resolved = {name: self.get(name, ver) for name, ver in members.items()}
        signature = latent_signature({n: resolved[n].version for n in GROUP1_MODELS})

        for name in DERIVED_MODELS:
            got = resolved[name].latent_signature
            if got != signature:
                raise RegistryError(
                    f"{name} v{resolved[name].version} was trained against latent "
                    f"signature {got!r}, but the pinned Group 1 set is {signature!r}. "
                    "Regenerate latents and retrain the derived models (§5.7)."
                )

        pin = {
            "label": label,
            "members": {n: v.version for n, v in resolved.items()},
            "latent_signature": signature,
            "pinned_at": datetime.now(UTC).isoformat(),
        }
        self._pins[label] = pin
        for name, v in resolved.items():
            self.transition(name, v.version, Stage.PRODUCTION)
        self._save()
        return pin

    def active_pin(self) -> dict | None:
        if not self._pins:
            return None
        return max(self._pins.values(), key=lambda p: p["pinned_at"])

    # ---- mlflow mirror ---------------------------------------------------

    def _mirror_model_version(
        self,
        name: str,
        checkpoint_uri: str,
        mlflow_run_id: str | None,
        tags: dict[str, str] | None,
    ) -> None:
        """Best-effort mirror of a new version to MLflow's real Model
        Registry API; failures degrade to local-only (§10.1).

        Real ``create_model_version`` requires the registered model to
        already exist (``create_registered_model`` first -- a plain lookup
        get-or-create, not idempotent on its own) and a real ``source``
        artifact URI as its second argument, not a local version number.
        """
        if self._mlflow is None:
            return
        try:
            try:
                self._mlflow.get_registered_model(name)
            except Exception:  # noqa: BLE001 - "doesn't exist yet" is the common case
                self._mlflow.create_registered_model(name)
            self._mlflow.create_model_version(
                name, checkpoint_uri, run_id=mlflow_run_id, tags=dict(tags or {}),
            )
        except Exception:  # noqa: BLE001 - tracking must never fail a training run
            self._mlflow = None

    #: registry.Stage's own lowercase values -> the real MLflow Model
    #: Registry API's TitleCase stage strings
    #: (mlflow.entities.model_registry.model_version_stages.ALL_STAGES).
    _MLFLOW_STAGE_NAMES: dict[Stage, str] = {
        Stage.NONE: "None",
        Stage.STAGING: "Staging",
        Stage.PRODUCTION: "Production",
        Stage.ARCHIVED: "Archived",
    }

    def _mirror_stage_transition(self, name: str, version: int, stage: Stage) -> None:
        """Best-effort mirror of a stage transition; failures degrade to
        local-only (§10.1)."""
        if self._mlflow is None:
            return
        try:
            self._mlflow.transition_model_version_stage(
                name, str(version), self._MLFLOW_STAGE_NAMES[stage],
            )
        except Exception:  # noqa: BLE001 - tracking must never fail a training run
            self._mlflow = None


def latent_signature(group1_versions: dict[str, int]) -> str:
    """Deterministic signature of a Group 1 checkpoint set.

    Any change to any Group 1 version changes the signature, which is precisely
    what invalidates downstream diffusion and fusion models.
    """
    missing = [m for m in GROUP1_MODELS if m not in group1_versions]
    if missing:
        raise RegistryError(f"latent signature needs all Group 1 models; missing {missing}")
    parts = [f"{name}v{group1_versions[name]}" for name in GROUP1_MODELS]
    return "-".join(parts)


def invalidated_by(model_name: str) -> tuple[str, ...]:
    """Which models must be retrained when ``model_name`` is retrained (§5.7).

    Used by the drift trigger so that "retrain the affected model only" cannot
    leave the derived models conditioned on latents that no longer exist.
    """
    if model_name in GROUP1_MODELS:
        return DERIVED_MODELS
    return ()
