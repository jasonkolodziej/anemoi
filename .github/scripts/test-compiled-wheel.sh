#!/usr/bin/env bash
# Checks that the compiled wheel behaves like the source tree it was built
# from (docs/compiled_build_plan.md, phase 2):
#
#   1. the test suite, run against the *installed* compiled wheel;
#   2. parity: compile/probe.py's seeded training run and forecast cycle
#      give byte-identical output from source and from the wheel;
#   3. with --bench, timings of both, side by side.
#
# Usage: test-compiled-wheel.sh [--bench] [wheel]   (run from the repo root)
#
# With no wheel given, uses the one in dist-compiled/, building it first if
# there is none (build-compiled-wheel.sh).
#
#   EXTRAS="dev api gridded storage tracking torch-cpu"   extras both environments get. Use `torch`
#                                in place of `torch-cpu` where PyTorch's CPU
#                                index is unreachable.
#   PYTHON=3.12                  interpreter; must match the wheel's.
#   ENV_DIR=.venv-compiled       where the two environments live.
#
# Both environments are built from uv.lock, so they differ only in where
# `anemoi` comes from: $ENV_DIR/source has the project installed editable,
# $ENV_DIR/compiled has the wheel. The project's own .venv is not touched.
set -euo pipefail

bench=0
wheel=
for arg in "$@"; do
	case "$arg" in
	--bench) bench=1 ;;
	-*)
		echo "test-compiled-wheel: unknown option $arg" >&2
		exit 2
		;;
	*) wheel=$arg ;;
	esac
done

root=$(pwd)
[[ -f "$root/compile/probe.py" && -d "$root/src/anemoi" ]] || {
	echo "test-compiled-wheel: run from the repo root" >&2
	exit 1
}

if [[ -z "$wheel" ]]; then
	shopt -s nullglob
	found=("$root"/dist-compiled/anemoi-*.whl)
	shopt -u nullglob
	if ((${#found[@]} == 0)); then
		"$root/.github/scripts/build-compiled-wheel.sh"
		found=("$root"/dist-compiled/anemoi-*.whl)
	fi
	((${#found[@]} == 1)) || {
		echo "test-compiled-wheel: ${#found[@]} wheels in dist-compiled/; pass the one to test" >&2
		exit 1
	}
	wheel=${found[0]}
fi
[[ -f "$wheel" ]] || {
	echo "test-compiled-wheel: no such wheel: $wheel" >&2
	exit 1
}

env_dir=${ENV_DIR:-.venv-compiled}
[[ "$env_dir" = /* ]] || env_dir="$root/$env_dir"
source_py="$env_dir/source/bin/python"
compiled_py="$env_dir/compiled/bin/python"

sync_args=(--locked)
[[ -n "${PYTHON:-}" ]] && sync_args+=(--python "$PYTHON")
for extra in ${EXTRAS:-dev api gridded storage tracking torch-cpu}; do
	sync_args+=(--extra "$extra")
done

echo "== environments (uv.lock; extras: ${EXTRAS:-dev api gridded storage tracking torch-cpu})"
UV_PROJECT_ENVIRONMENT="$env_dir/source" uv sync --quiet "${sync_args[@]}"
UV_PROJECT_ENVIRONMENT="$env_dir/compiled" uv sync --quiet "${sync_args[@]}" --no-install-project
uv pip install --quiet --python "$compiled_py" --no-deps --reinstall "$wheel"

# An installed wheel has no checkout above it to find configs/ in.
export ANEMOI_CONFIG_DIR="$root/configs"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Run from outside the repo so nothing can be imported from it by accident.
(
	cd "$work"
	"$compiled_py" - "$root" <<'EOF'
import sys

import anemoi.cli

path = anemoi.cli.__file__
if path.endswith(".py") or path.startswith(sys.argv[1] + "/src/"):
    sys.exit(f"test-compiled-wheel: not the compiled wheel: {path}")
print(f"compiled: {path}")
EOF
	"$source_py" -c "
import anemoi.cli
assert anemoi.cli.__file__.endswith('.py'), anemoi.cli.__file__
print(f'source:   {anemoi.cli.__file__}')"
)

echo "== test suite against the compiled wheel"
# `-o pythonpath=` drops pyproject's `pythonpath = [\"src\"]`; the guard in
# tests/conftest.py (ANEMOI_EXPECT_COMPILED) fails the run if the source
# tree is imported anyway. `source`-marked tests read the package's .py
# files, which the wheel does not have.
status=0
ANEMOI_EXPECT_COMPILED=1 "$compiled_py" -m pytest -q -p no:cacheprovider \
	-o pythonpath= -m "not source" --junitxml "$work/junit.xml" || status=$?
if ((status == 134)); then
	# SIGABRT. With the `gridded` extra the interpreter can abort while
	# exiting, after every test has reported ("free(): invalid pointer":
	# `import eccodes, pyproj` alone does it, from source too -- two
	# bundled native libraries, nothing to do with this build). That
	# hides pytest's own exit status, so read the result it wrote instead.
	"$source_py" - "$work/junit.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET

suite = ET.parse(sys.argv[1]).getroot()
suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
bad = int(suite.get("failures")) + int(suite.get("errors"))
if bad or not int(suite.get("tests")):
    sys.exit(f"test-compiled-wheel: {bad} failed of {suite.get('tests')} tests")
print("test-compiled-wheel: all tests passed; the interpreter aborted while exiting (see above)")
PY
elif ((status != 0)); then
	exit "$status"
fi

echo "== parity: seeded training and a forecast cycle, source vs compiled"
"$source_py" compile/probe.py parity >"$work/parity-source.json" 2>"$work/parity-source.log" ||
	{
		cat "$work/parity-source.log" >&2
		exit 1
	}
"$compiled_py" compile/probe.py parity >"$work/parity-compiled.json" 2>"$work/parity-compiled.log" ||
	{
		cat "$work/parity-compiled.log" >&2
		exit 1
	}
"$source_py" - "$work/parity-source.json" "$work/parity-compiled.json" <<'EOF'
import json
import sys

source, compiled = (json.load(open(path)) for path in sys.argv[1:3])
if source["compiled"] or not compiled["compiled"]:
    sys.exit("parity: the two runs did not use the builds they were meant to")


def differences(a, b, at=""):
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        for key in a:
            yield from differences(a[key], b[key], f"{at}.{key}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            yield from differences(x, y, f"{at}[{i}]")
    elif a != b:
        yield f"  {at.lstrip('.')}: source {a!r} != compiled {b!r}"


found = list(differences(source["parity"], compiled["parity"]))
if found:
    print("\n".join(found[:40]))
    sys.exit(f"parity: {len(found)} values differ between source and compiled")
leaves = json.dumps(source["parity"]).count(":")
print(f"identical ({leaves} values: losses, metrics, weight digests, cycle payload)")
EOF

if ((bench)); then
	echo "== benchmark (best of a few runs each; same machine, one after the other)"
	"$source_py" compile/probe.py bench >"$work/bench-source.json" 2>/dev/null
	"$compiled_py" compile/probe.py bench >"$work/bench-compiled.json" 2>/dev/null
	"$source_py" - "$work/bench-source.json" "$work/bench-compiled.json" <<'EOF'
import json
import sys

source, compiled = (json.load(open(path))["bench"] for path in sys.argv[1:3])
print(f"{'':46s} {'source':>10s} {'compiled':>10s}  speedup")
for name in source:
    a, b = float(source[name]), float(compiled[name])
    print(f"{name:46s} {a * 1e3:8.2f}ms {b * 1e3:8.2f}ms  {a / b:5.2f}x")
EOF
fi
