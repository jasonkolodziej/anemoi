"""`configs/*.yaml` are read at runtime by `anemoi.config` (#211) -- the
module constants and function defaults that used to carry these values now
come from the files.

Before that, the YAML only documented the constants, nothing enforced the
pairing, and it drifted: raising `DEFAULT_ENSEMBLE_MEMBERS` 20 -> 50 (#188)
left the config still declaring 20. Now that the files *are* the values,
what needs proving is different:

* every key in the files is read by something -- a key nothing reads is a
  setting someone will edit expecting an effect;
* an edited file actually changes what runs, and a bad one is refused with a
  message naming the file and key, rather than half-applied;
* the deployed images can find the files, and a config change redeploys;
* the few copies that can't read Python (the Worker's cron, the console's
  run offset) still agree with the file.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from anemoi import config

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs"

#: Every module that reads configuration. Importing them all is what makes
#: `config.accessed()` complete.
CONSUMERS = (
    "anemoi.time_utils",
    "anemoi.data.availability",
    "anemoi.data.besttrack",
    "anemoi.inference.scheduler",
    "anemoi.inference.postprocess",
    "anemoi.training.curriculum",
    "anemoi.training.promotion",
    "anemoi.training.triggers",
    "anemoi.monitoring.skew",
    "anemoi.monitoring.drift",
    "anemoi.monitoring.calibration_audit",
)


def _load(name: str) -> dict:
    return yaml.safe_load((CONFIGS / name).read_text())


def _leaves(node, prefix: str = "") -> set[str]:
    """Dotted paths of every value. A mapping keyed by numbers (the cone
    table) is one value, not a set of keys."""
    if isinstance(node, dict) and not all(isinstance(k, int) for k in node):
        out: set[str] = set()
        for key, value in node.items():
            out |= _leaves(value, f"{prefix}{key}.")
        return out
    return {prefix[:-1]}


def _run(code: str, *, config_dir: Path | None = None, sys_path: Path | None = None):
    """Run `code` in a fresh interpreter, so module-level config reads happen
    against the given directory rather than this process's already-imported
    modules."""
    env = {k: v for k, v in os.environ.items() if k != config.CONFIG_DIR_ENV}
    if config_dir is not None:
        env[config.CONFIG_DIR_ENV] = str(config_dir)
    prelude = f"import sys; sys.path.insert(0, {str(sys_path)!r})\n" if sys_path else ""
    return subprocess.run(
        [sys.executable, "-c", prelude + textwrap.dedent(code)],
        env=env, capture_output=True, text=True, cwd=str(Path("/")), timeout=120,
    )


@pytest.fixture
def config_copy(tmp_path):
    """A writable copy of configs/, and a function to edit a value in it."""
    target = tmp_path / "configs"
    shutil.copytree(CONFIGS, target)

    def edit(file: str, pattern: str, replacement: str) -> None:
        path = target / file
        text, n = re.subn(pattern, replacement, path.read_text(), count=1, flags=re.MULTILINE)
        assert n == 1, f"{pattern!r} not found in {file}"
        path.write_text(text)

    return target, edit


# ---- every key is read ---------------------------------------------------


@pytest.mark.parametrize("name", ["curriculum.yaml", "inference.yaml", "monitoring.yaml"])
def test_every_config_key_is_read_by_the_code(name):
    import importlib

    for module in CONSUMERS:
        importlib.import_module(module)
    read = {key.split(":", 1)[1] for key in config.accessed() if key.startswith(f"{name}:")}
    unread = _leaves(_load(name)) - read
    assert not unread, (
        f"{name} declares {sorted(unread)}, but no code reads them -- read them through "
        "anemoi.config where they're used, or drop them from the file"
    )


def test_config_files_are_exactly_the_three_the_loader_knows():
    assert {p.stem for p in CONFIGS.glob("*.y*ml")} == set(config.FILES)


# ---- an edited file changes what runs ------------------------------------


def test_edited_values_take_effect_at_runtime(config_copy):
    target, edit = config_copy
    edit("inference.yaml", r"^  members: 50$", "  members: 40")
    edit("inference.yaml", r"^    48: 62$", "    48: 70")
    edit("inference.yaml", r"^  landfall_threshold_nm: 60$", "  landfall_threshold_nm: 45")
    edit("curriculum.yaml", r"^  epochs: 20$", "  epochs: 7")
    edit("monitoring.yaml", r"^  min_samples: 8$", "  min_samples: 9")
    edit("monitoring.yaml", r"^  min_cases: 5 ", "  min_cases: 6 ")
    edit("monitoring.yaml", r"^  scheduled_monthly_day: 1$", "  scheduled_monthly_day: 2")
    edit(
        "monitoring.yaml",
        r"track_error_48h_nm:         \{limit: 70\.0,",
        "track_error_48h_nm:         {limit: 65.0,",
    )
    result = _run(
        """
        from datetime import date
        from anemoi.inference import scheduler, postprocess
        from anemoi.training import curriculum, promotion, triggers
        from anemoi.monitoring import skew, calibration_audit
        print(scheduler.DEFAULT_ENSEMBLE_MEMBERS)
        print(postprocess.CLIMATOLOGICAL_CONE_NM[48])
        print(postprocess.LANDFALL_THRESHOLD_NM)
        print(curriculum.stage_b().epochs)
        print(skew.SkewMonitor().min_samples)
        print(calibration_audit.MIN_CASES)
        print(bool(triggers.scheduled_monthly(date(2026, 6, 2))))
        limits = {t.metric: t.limit for t in promotion.DEFAULT_THRESHOLDS}
        print(limits["track_error_48h_nm"])
        """,
        config_dir=target,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["40", "70.0", "45.0", "7", "9", "6", "True", "65.0"]


# ---- a bad file is refused, with the file and key named --------------------

_REFUSALS = [
    ("fixed key changed", "inference.yaml", r"^  synoptic_hours: \[0, 6, 12, 18\]",
     "  synoptic_hours: [0, 6, 12]", "cycle.synoptic_hours must be"),
    ("lead times aren't tunable", "inference.yaml",
     r"^  lead_hours: \[12, 24, 36, 48, 72, 96, 120\]",
     "  lead_hours: [12, 24, 48]", "products.lead_hours must be"),
    ("timeout disagrees with its budgets", "inference.yaml", r"^  vitals_timeout_minutes: 80",
     "  vitals_timeout_minutes: 90", "cycle.vitals_timeout_minutes must equal"),
    ("budget change without re-deriving the timeout", "inference.yaml",
     r"^    diffusion:     \{target: 6,  max: 10\}$", "    diffusion:     {target: 6,  max: 12}",
     "cycle.vitals_timeout_minutes must equal"),
    ("run offset before the timeout", "inference.yaml", r"^  scheduled_run_offset_minutes: 90$",
     "  scheduled_run_offset_minutes: 60", "scheduled_run_offset_minutes must be after"),
    ("wrong type", "inference.yaml", r"^  members: 50$", "  members: fifty",
     "ensemble.members must be int"),
    ("bool where a number belongs", "monitoring.yaml", r"^  min_samples: 30$",
     "  min_samples: true", "drift.min_samples must be int"),
    ("missing key", "monitoring.yaml", r"^  window_days: 14\n", "",
     "skew_audit.window_days is missing"),
    ("load shed bigger than the ensemble", "inference.yaml", r"^  reduced_members: 25$",
     "  reduced_members: 60", "ensemble.reduced_members must be between"),
    ("a budget whose max is below its target", "inference.yaml",
     r"^    fusion:        \{target: 2,  max: 4\}\n(?=    diffusion:     \{target: 13)",
     "    fusion:        {target: 5,  max: 4}\n",
     "budgets.standard.fusion: fusion: max budget below target"),
    ("cone table missing a lead", "inference.yaml", r"^    120: 200\n", "",
     "climatological_cone_nm needs exactly one radius per"),
    ("operational flavor changed", "monitoring.yaml", r"^  reference_flavor: gdas_finetune",
     "  reference_flavor: era5_pretrain", "drift.reference_flavor must be"),
    ("promotion on the test split", "monitoring.yaml", r"^  split: val", "  split: test",
     "promotion.split must be"),
    ("bad preseason date", "monitoring.yaml", r'^  preseason_date: "05-01"$',
     '  preseason_date: "13-40"', "triggers.preseason_date must be MM-DD"),
    ("stage B flavor changed", "curriculum.yaml", r"^  flavor: gdas_finetune",
     "  flavor: era5_pretrain", "stage_b.flavor must be"),
    ("label source leaking into inputs", "curriculum.yaml",
     r"^  input_sources: \[gdas_gfs, besttrack_working, goes, sst_ohc\]$",
     "  input_sources: [gdas_gfs, besttrack_final]", "labels-only"),
]


@pytest.mark.parametrize(
    ("file", "pattern", "replacement", "message"),
    [case[1:] for case in _REFUSALS],
    ids=[case[0] for case in _REFUSALS],
)
def test_an_invalid_config_is_refused_with_a_clear_message(
    config_copy, file, pattern, replacement, message
):
    target, edit = config_copy
    edit(file, pattern, replacement)
    code = (
        "import importlib\n"
        f"for m in {CONSUMERS!r}:\n"
        "    importlib.import_module(m)\n"
        "curriculum = importlib.import_module('anemoi.training.curriculum')\n"
        "curriculum.stage_a(); curriculum.stage_b()\n"
    )
    result = _run(code, config_dir=target)
    assert result.returncode != 0, f"{file} edit was accepted:\n{result.stdout}"
    assert message in result.stderr, result.stderr[-2000:]


def test_a_missing_config_dir_is_refused(tmp_path):
    result = _run("import anemoi.inference.scheduler", config_dir=tmp_path / "nope")
    assert result.returncode != 0
    assert "ANEMOI_CONFIG_DIR" in result.stderr and "is not a directory" in result.stderr


# ---- the deployed images find the files, and a change redeploys ----------


def _image_layout(tmp_path: Path, *, with_configs: bool) -> Path:
    """What both images built from docker/multistage.Dockerfile contain:
    /app/src and, since #211, /app/configs beside it."""
    app = tmp_path / "app"
    shutil.copytree(ROOT / "src", app / "src", ignore=shutil.ignore_patterns("__pycache__"))
    if with_configs:
        shutil.copytree(CONFIGS, app / "configs")
    return app


def test_the_image_layout_finds_its_configs_without_any_env(tmp_path):
    app = _image_layout(tmp_path, with_configs=True)
    code = (
        "import anemoi, anemoi.config as c, anemoi.inference.scheduler as s\n"
        f"assert anemoi.__file__.startswith({str(app)!r}), anemoi.__file__\n"
        "print(c.config_dir(), s.DEFAULT_ENSEMBLE_MEMBERS)\n"
    )
    result = _run(code, sys_path=app / "src")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [str(app / "configs"), "50"]


def test_an_image_without_configs_fails_at_import_and_says_why(tmp_path):
    app = _image_layout(tmp_path, with_configs=False)
    result = _run("import anemoi.inference.scheduler", sys_path=app / "src")
    assert result.returncode != 0
    assert "no configs/ directory found" in result.stderr
    assert "ANEMOI_CONFIG_DIR" in result.stderr


def test_both_images_copy_the_configs():
    dockerfile = (ROOT / "docker" / "multistage.Dockerfile").read_text()
    for stage, builder in (("training", "training-builder"), ("api", "api-builder")):
        body = dockerfile.split(f"AS {stage}\n", 1)[1].split("\nFROM ", 1)[0]
        assert re.search(rf"COPY --from={builder}\b.* /app/configs /app/configs", body), (
            f"the {stage} image doesn't copy configs/ -- it would fail at import"
        )
    ignore = (ROOT / "docker" / "multistage.Dockerfile.dockerignore").read_text().splitlines()
    assert "!configs/" in ignore and "!configs/**" in ignore, (
        "multistage.Dockerfile.dockerignore excludes configs/ from the build context"
    )


def test_every_image_build_is_smoke_tested_before_it_ships():
    """The images are built in three places; each must start the image and
    find /app/configs before anything is deployed or pushed."""
    script = ROOT / ".github" / "scripts" / "smoke-test-image.sh"
    assert os.access(script, os.X_OK), "smoke-test-image.sh must be executable"
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
    assert "--target api" in deploy and "smoke-test-image.sh anemoi-api:ci api" in deploy
    publish = (ROOT / ".github" / "workflows" / "publish-cloud-run-training.yml").read_text()
    assert publish.index("smoke-test-image.sh") < publish.index("push: true"), (
        "the GHCR training image is pushed before it is smoke-tested"
    )
    cloudbuild = (ROOT / "docker" / "cloud-run-training" / "cloudbuild.yaml").read_text()
    assert "smoke-test-image.sh" in cloudbuild


def test_a_config_change_redeploys_the_api():
    plan = (ROOT / ".github" / "scripts" / "deploy-plan.sh").read_text()
    api_re = re.search(r"^API_RE='([^']+)'", plan, re.MULTILINE).group(1)
    assert re.search(api_re, "configs/inference.yaml"), (
        "deploy-plan.sh's API_RE doesn't match configs/ -- an edited config would never ship"
    )


# ---- copies that can't read Python --------------------------------------


def _cron_run_offset_minutes() -> int:
    """Minutes after its synoptic time that production runs a cycle, from
    anemoi-api-real's cron -- one offset for all four synoptic times."""
    from anemoi.time_utils import SYNOPTIC_HOURS

    text = (ROOT / "docker" / "api" / "wrangler.jsonc").read_text()
    minute, hours = re.search(r'"crons":\s*\[\s*"(\d+) ([\d,]+) \* \* \*"', text).groups()
    offsets = {
        (h - max(s for s in SYNOPTIC_HOURS if s <= h)) * 60 + int(minute)
        for h in map(int, hours.split(","))
    }
    assert len(offsets) == 1, f"cron fires at different offsets per cycle: {sorted(offsets)}"
    return offsets.pop()


def test_the_worker_cron_runs_at_the_configured_offset():
    configured = _load("inference.yaml")["cycle"]["scheduled_run_offset_minutes"]
    assert _cron_run_offset_minutes() == configured, (
        "docker/api/wrangler.jsonc's cron no longer fires at "
        f"cycle.scheduled_run_offset_minutes ({configured})"
    )


def test_the_console_uses_the_same_scheduled_run_offset():
    """The storm page says when the next cycle is due (#209) from its own copy."""
    utils = (ROOT / "console" / "src" / "lib" / "utils.ts").read_text()
    console = int(re.search(r"CYCLE_RUN_DELAY_MIN = (\d+);", utils).group(1))
    assert console == _load("inference.yaml")["cycle"]["scheduled_run_offset_minutes"]


def test_the_lead_times_match_the_api_s_own_copy():
    """api.real_state keeps its own lead tuple for building real cycles."""
    pytest.importorskip("pydantic")
    from anemoi.api import real_state

    assert list(real_state._LEAD_HOURS) == _load("inference.yaml")["products"]["lead_hours"]


# ---- the files themselves ------------------------------------------------


def test_the_load_shed_comment_still_describes_the_real_reduced_count():
    """The budget comment carries the counts in prose -- a comment that
    contradicts the values beside it is worse than no comment."""
    ensemble = _load("inference.yaml")["ensemble"]
    text = (CONFIGS / "inference.yaml").read_text()
    assert f"~{ensemble['reduced_members']} ensemble members" in text
    assert f"instead of {ensemble['members']}" in text


def test_every_config_parses_and_has_no_duplicate_keys():
    """yaml.safe_load keeps the last of two duplicate keys silently, which
    would let a stale value hide behind a corrected one."""

    class Strict(yaml.SafeLoader):
        pass

    def no_duplicates(loader, node, deep=False):
        keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
        dupes = {k for k in keys if keys.count(k) > 1}
        line = node.start_mark.line + 1
        assert not dupes, f"duplicate keys {sorted(map(str, dupes))} at line {line}"
        return loader.construct_mapping(node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates)
    for path in sorted(CONFIGS.glob("*.yaml")):
        assert isinstance(yaml.load(path.read_text(), Loader=Strict), dict), path.name
