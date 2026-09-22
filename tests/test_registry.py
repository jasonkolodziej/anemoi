"""Registry, model-set pinning and rollback (Scope v2.1 §7.1, §5.7, §10.2)."""

import pytest

from anemoi.data.sources import Flavor
from anemoi.tracking.registry import (
    ALL_MODELS,
    GROUP1_MODELS,
    REGISTRY_STORE_KEY,
    ModelRegistry,
    RegistryError,
    Stage,
    invalidated_by,
    latent_signature,
)


class _FakeS3Config:
    bucket = "fake-bucket"

METRICS = {"track_error_48h_nm": 70.0}


def register_group1(reg, version_bump=()):
    versions = {}
    for name in GROUP1_MODELS:
        v = reg.register(name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
                         metrics=METRICS)
        versions[name] = v.version
    for name in version_bump:
        v = reg.register(name, run_id=f"run-{name}-2", input_flavor=Flavor.GDAS_FINETUNE,
                         metrics=METRICS)
        versions[name] = v.version
    return versions


def full_set(reg, tmp_signature=None):
    versions = register_group1(reg)
    sig = tmp_signature or latent_signature(versions)
    for name in ("diffusion", "fusion"):
        v = reg.register(name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
                         metrics=METRICS, latent_signature=sig)
        versions[name] = v.version
    return versions


def test_era5_flavor_weights_cannot_be_registered(tmp_path):
    reg = ModelRegistry(tmp_path)
    with pytest.raises(RegistryError, match="Stage B"):
        reg.register("lstm", run_id="r", input_flavor=Flavor.ERA5_PRETRAIN, metrics=METRICS)


def test_derived_models_require_a_latent_signature(tmp_path):
    reg = ModelRegistry(tmp_path)
    with pytest.raises(RegistryError, match="latent_signature"):
        reg.register("diffusion", run_id="r", input_flavor=Flavor.GDAS_FINETUNE,
                     metrics=METRICS)


def test_versions_increment(tmp_path):
    reg = ModelRegistry(tmp_path)
    assert reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE,
                        metrics=METRICS).version == 1
    assert reg.register("lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE,
                        metrics=METRICS).version == 2


def test_registry_persists_across_instances(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    assert len(ModelRegistry(tmp_path).versions("lstm")) == 1


def test_checkpoint_uri_persists_on_the_version_itself(tmp_path):
    """Real gap found while wiring real inference (#78): checkpoint_uri
    was accepted by register() but only ever used for the MLflow mirror,
    never stored on the ModelVersion itself -- so a real inference process
    had no way to look up where a version's weights live without an
    MLflow client configured and reachable."""
    reg = ModelRegistry(tmp_path)
    version = reg.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
        checkpoint_uri="s3://fake/lstm.pt",
    )
    assert version.checkpoint_uri == "s3://fake/lstm.pt"

    # And it survives a real reload from disk, not just the in-memory object.
    reloaded = ModelRegistry(tmp_path).get("lstm", 1)
    assert reloaded.checkpoint_uri == "s3://fake/lstm.pt"


def test_checkpoint_uri_defaults_to_none_when_not_given(tmp_path):
    reg = ModelRegistry(tmp_path)
    version = reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    assert version.checkpoint_uri is None


def test_pinning_a_full_coherent_set_succeeds(tmp_path):
    reg = ModelRegistry(tmp_path)
    versions = full_set(reg)
    pin = reg.pin_set("2026-preseason", versions)
    assert set(pin["members"]) == set(ALL_MODELS)
    assert reg.production("diffusion").version == versions["diffusion"]


def test_pinning_an_incomplete_set_is_refused(tmp_path):
    reg = ModelRegistry(tmp_path)
    versions = register_group1(reg)
    with pytest.raises(RegistryError, match="missing members"):
        reg.pin_set("partial", versions)


def test_retraining_one_group1_model_invalidates_the_derived_models(tmp_path):
    """The v2 'retrain the affected model only' bug, caught mechanically."""
    reg = ModelRegistry(tmp_path)
    versions = full_set(reg)
    new_lstm = reg.register("lstm", run_id="lstm-v2", input_flavor=Flavor.GDAS_FINETUNE,
                            metrics=METRICS)
    versions["lstm"] = new_lstm.version
    with pytest.raises(RegistryError, match="latent signature"):
        reg.pin_set("broken", versions)


def test_signature_changes_when_any_group1_version_changes():
    base = {m: 1 for m in GROUP1_MODELS}
    bumped = dict(base, gnn=2)
    assert latent_signature(base) != latent_signature(bumped)


def test_signature_requires_every_group1_model():
    with pytest.raises(RegistryError, match="missing"):
        latent_signature({"lstm": 1})


def test_invalidation_map_covers_group1_only():
    assert invalidated_by("lstm") == ("diffusion", "fusion")
    assert invalidated_by("diffusion") == ()


def test_promoting_a_new_production_archives_the_incumbent(tmp_path):
    reg = ModelRegistry(tmp_path)
    v1 = reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    v2 = reg.register("lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    reg.transition("lstm", v1.version, Stage.PRODUCTION)
    reg.transition("lstm", v2.version, Stage.PRODUCTION)
    assert reg.get("lstm", v1.version).stage is Stage.ARCHIVED
    assert reg.production("lstm").version == v2.version


def test_rollback_restores_the_previous_production_version(tmp_path):
    reg = ModelRegistry(tmp_path)
    v1 = reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    v2 = reg.register("lstm", run_id="b", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    reg.transition("lstm", v1.version, Stage.PRODUCTION)
    reg.transition("lstm", v2.version, Stage.PRODUCTION)
    assert reg.rollback("lstm").version == v1.version


def test_rollback_without_history_raises(tmp_path):
    reg = ModelRegistry(tmp_path)
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    with pytest.raises(RegistryError, match="roll back"):
        reg.rollback("lstm")


def test_mlflow_failure_degrades_to_local_only(tmp_path):
    class BrokenClient:
        def __getattr__(self, name):
            def raiser(*args, **kwargs):
                raise RuntimeError("mlflow unreachable")

            return raiser

    reg = ModelRegistry(tmp_path, mlflow_client=BrokenClient())
    reg.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
        checkpoint_uri="s3://fake/lstm.pt",
    )
    assert not reg.mlflow_available
    assert len(reg.versions("lstm")) == 1


def test_mlflow_mirror_is_skipped_without_a_checkpoint_uri(tmp_path):
    """No real artifact source -- the real create_model_version API needs
    one -- so the mirror must not even attempt a call, not fail one."""
    calls: list[str] = []

    class TrackingClient:
        def __getattr__(self, name):
            calls.append(name)

            def noop(*args, **kwargs):
                return None

            return noop

    reg = ModelRegistry(tmp_path, mlflow_client=TrackingClient())
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    assert calls == []
    assert reg.mlflow_available


def test_mlflow_mirror_registers_model_then_version_with_a_real_source_uri(tmp_path):
    calls: list[tuple] = []

    class RecordingClient:
        def get_registered_model(self, name):
            calls.append(("get_registered_model", name))
            raise RuntimeError("does not exist yet")

        def create_registered_model(self, name):
            calls.append(("create_registered_model", name))

        def create_model_version(self, name, source, run_id=None, tags=None):
            calls.append(("create_model_version", name, source, run_id, tags))

    reg = ModelRegistry(tmp_path, mlflow_client=RecordingClient())
    reg.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
        tags={"model_type": "lstm"}, checkpoint_uri="s3://fake/lstm.pt",
        mlflow_run_id="real-mlflow-run-id",
    )

    assert calls == [
        ("get_registered_model", "lstm"),
        ("create_registered_model", "lstm"),
        ("create_model_version", "lstm", "s3://fake/lstm.pt", "real-mlflow-run-id",
         {"model_type": "lstm"}),
    ]
    assert reg.mlflow_available


def test_mlflow_mirror_skips_create_registered_model_if_it_already_exists(tmp_path):
    calls: list[str] = []

    class RecordingClient:
        def get_registered_model(self, name):
            calls.append("get_registered_model")
            return object()  # already exists -- no create_registered_model needed

        def create_registered_model(self, name):
            calls.append("create_registered_model")

        def create_model_version(self, name, source, run_id=None, tags=None):
            calls.append("create_model_version")

    reg = ModelRegistry(tmp_path, mlflow_client=RecordingClient())
    reg.register(
        "lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
        checkpoint_uri="s3://fake/lstm.pt",
    )
    assert calls == ["get_registered_model", "create_model_version"]


def test_mlflow_transition_mirror_uses_real_titlecase_stage_names(tmp_path):
    calls: list[tuple] = []

    class RecordingClient:
        def transition_model_version_stage(self, name, version, stage):
            calls.append((name, version, stage))

    reg = ModelRegistry(tmp_path, mlflow_client=RecordingClient())
    v = reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    reg.transition("lstm", v.version, Stage.PRODUCTION)

    assert calls == [("lstm", str(v.version), "Production")]


def test_checkpoint_store_push_mirrors_registry_json_after_every_save(tmp_path):
    """The durable-storage counterpart to the MLflow mirror (#91): every
    save should push the real registry.json to the fixed key every reader
    (a fresh Cloudflare Container's bootstrap, `anemoi registry-pull`)
    agrees on."""
    calls: list[tuple] = []

    class RecordingStore:
        config = _FakeS3Config()

        def upload(self, local_path, key):
            calls.append((local_path, key))

    reg = ModelRegistry(tmp_path, checkpoint_store=RecordingStore())
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)

    assert len(calls) == 1
    local_path, key = calls[0]
    assert key == REGISTRY_STORE_KEY
    assert local_path == tmp_path / "registry.json"
    assert local_path.exists()


def test_checkpoint_store_push_failure_degrades_to_local_only(tmp_path):
    class BrokenStore:
        config = _FakeS3Config()

        def upload(self, local_path, key):
            raise RuntimeError("R2 unreachable")

    reg = ModelRegistry(tmp_path, checkpoint_store=BrokenStore())
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    reg.register("cnn", run_id="b", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)

    assert len(reg.versions("lstm")) == 1
    assert len(reg.versions("cnn")) == 1


def test_pull_from_checkpoint_store_hydrates_a_missing_local_registry(tmp_path):
    """The read-side counterpart: a fresh process with no local
    registry.json (a Cloudflare Container's ephemeral disk on every cold
    start) should hydrate from durable storage instead of starting empty."""
    remote_path = tmp_path / "remote.json"
    reg = ModelRegistry(tmp_path / "writer", checkpoint_store=None)
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)
    remote_path.write_text((reg.root / "registry.json").read_text())  # simulate a prior push

    class FakeStore:
        config = _FakeS3Config()

        def exists(self, key):
            assert key == REGISTRY_STORE_KEY
            return True

        def download(self, uri, local_path):
            assert uri == f"s3://{_FakeS3Config.bucket}/{REGISTRY_STORE_KEY}"
            local_path.write_text(remote_path.read_text())

    reader = ModelRegistry(tmp_path / "reader", checkpoint_store=FakeStore())
    assert len(reader.versions("lstm")) == 1
    assert reader.latest("lstm").run_id == "a"


def test_pull_reconciles_with_durable_storage_even_when_local_already_exists(tmp_path):
    """A persistent local registry.json (the VM's real case -- it survives
    across training runs on its persistent disk) must not shadow durable
    storage forever. A real incident this closes: a manual promotion
    applied only to the deployed container's registry.json was silently
    discarded the next time the training VM ran a full pass and pushed
    its own (unaware, stale) local copy back over it -- because
    construction only ever pulled when local was entirely missing.
    Durable storage is the real shared source of truth multiple
    independent processes write to, so it must win at construction even
    when a local file is already present."""
    remote_path = tmp_path / "remote.json"
    writer = ModelRegistry(tmp_path / "writer", checkpoint_store=None)
    writer.register(
        "lstm", run_id="remote-truth", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
    )
    remote_path.write_text((writer.root / "registry.json").read_text())

    class FakeStore:
        config = _FakeS3Config()

        def exists(self, key):
            return True

        def download(self, uri, local_path):
            local_path.write_text(remote_path.read_text())

        def upload(self, local_path, key):
            pass

    local_root = tmp_path / "local"
    stale = ModelRegistry(local_root, checkpoint_store=None)
    stale.register(
        "lstm", run_id="stale-local-only", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS,
    )
    assert stale.latest("lstm").run_id == "stale-local-only"

    # A fresh instance over the same (already-populated) local root, now
    # with a checkpoint_store configured, must reflect durable storage's
    # real state, not the stale local one.
    reconciled = ModelRegistry(local_root, checkpoint_store=FakeStore())
    assert reconciled.latest("lstm").run_id == "remote-truth"


def test_pull_is_skipped_entirely_without_a_checkpoint_store(tmp_path):
    """No checkpoint_store at all (e.g. a plain local-only CLI run) must
    never attempt any durable-storage call -- local disk stays the only
    source of truth, unchanged from before."""
    reg = ModelRegistry(tmp_path, checkpoint_store=None)
    reg.register("lstm", run_id="a", input_flavor=Flavor.GDAS_FINETUNE, metrics=METRICS)

    reg2 = ModelRegistry(tmp_path, checkpoint_store=None)
    assert reg2.latest("lstm").run_id == "a"


def test_pull_failure_degrades_to_an_empty_registry(tmp_path):
    class BrokenStore:
        config = _FakeS3Config()

        def exists(self, key):
            raise RuntimeError("R2 unreachable")

    reg = ModelRegistry(tmp_path, checkpoint_store=BrokenStore())
    assert reg.versions("lstm") == []


def test_pull_is_a_noop_when_the_key_does_not_exist_remotely_yet(tmp_path):
    """Before any run has ever pushed a registry.json -- e.g. the very
    first real deploy -- there is nothing to pull; must not raise."""

    class EmptyStore:
        config = _FakeS3Config()

        def exists(self, key):
            return False

        def download(self, uri, local_path):
            raise AssertionError("should not be called when the remote key doesn't exist")

    reg = ModelRegistry(tmp_path, checkpoint_store=EmptyStore())
    assert reg.versions("lstm") == []
