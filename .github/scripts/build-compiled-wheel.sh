#!/usr/bin/env bash
# Builds the compiled (C extension) wheel of `anemoi` into dist-compiled/:
# every module under src/anemoi translated to C by Cython and compiled,
# from the same source as the ordinary wheel. Opt-in -- nothing else in the
# repo runs this, and `uv sync`, `uv build` and both images are unaffected.
# See docs/compiled_build_plan.md and compile/setup.py.
#
# Usage: build-compiled-wheel.sh   (run from the repo root; needs `uv` and a
# C compiler). The wheel is for the interpreter and platform it is built
# with, so build it where it will run:
#
#   PYTHON=3.12            interpreter (anything `uv run --python` accepts);
#                          default: uv's choice for this directory
#   ANEMOI_COMPILE_JOBS=4  parallel compiles; default: all cores
#   OUT_DIR=dist-compiled  where the wheel goes
#
# src/ is never written to: the build runs on a copy in a temp directory.
set -euo pipefail

# Pinned: generated C differs between Cython releases, and the build should
# not change underneath a given commit.
CYTHON_VERSION=3.3.1
SETUPTOOLS_VERSION=84.2.1

root=$(pwd)
for needed in pyproject.toml src/anemoi compile/setup.py; do
	[[ -e "$root/$needed" ]] || {
		echo "build-compiled-wheel: run from the repo root ($needed not found)" >&2
		exit 1
	}
done
command -v uv >/dev/null || {
	echo "build-compiled-wheel: uv is required" >&2
	exit 1
}
command -v "${CC:-cc}" >/dev/null || {
	echo "build-compiled-wheel: a C compiler is required (${CC:-cc} not found)" >&2
	exit 1
}

out=${OUT_DIR:-dist-compiled}
[[ "$out" = /* ]] || out="$root/$out"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cp -R "$root/src/anemoi" "$stage/anemoi"
find "$stage/anemoi" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$root/compile/setup.py" "$root/pyproject.toml" "$root/README.md" "$root/LICENSE" "$stage/"
# setup.py is the build definition here; setuptools must not also read the
# hatchling configuration in pyproject.toml's [build-system]/[project].
mv "$stage/pyproject.toml" "$stage/pyproject.toml.in"
sed -i.bak 's/"pyproject\.toml"/"pyproject.toml.in"/' "$stage/setup.py" && rm "$stage/setup.py.bak"

python_args=()
[[ -n "${PYTHON:-}" ]] && python_args=(--python "$PYTHON")

(
	cd "$stage"
	uv run --no-project --isolated "${python_args[@]}" \
		--with "cython==$CYTHON_VERSION" --with "setuptools==$SETUPTOOLS_VERSION" \
		python setup.py --quiet bdist_wheel --dist-dir "$stage/dist"
)

wheel=$(find "$stage/dist" -name 'anemoi-*.whl')
[[ -n "$wheel" && $(wc -l <<<"$wheel") -eq 1 ]] || {
	echo "build-compiled-wheel: expected exactly one wheel, got: ${wheel:-none}" >&2
	exit 1
}

# A wheel that quietly fell back to source would pass every test while
# compiling nothing, so check what is in it.
listing=$(uv run --no-project --isolated "${python_args[@]}" python - "$wheel" <<'EOF'
import sys
import zipfile

names = zipfile.ZipFile(sys.argv[1]).namelist()
ext = [n for n in names if n.endswith((".so", ".pyd"))]
src = [n for n in names if n.endswith(".py")]
stray = [n for n in src if not n.endswith(("__init__.py", "__main__.py"))]
leaked = [n for n in names if n.endswith((".c", ".pyx"))]
static = [n for n in names if n.startswith("anemoi/api/static/")]
print(f"{len(ext)} compiled modules, {len(src)} source modules kept, {len(static)} static files")
problems = []
if not ext:
    problems.append("no compiled modules")
if leaked:
    problems.append(f"generated C in the wheel: {leaked[:3]}")
if not static:
    problems.append("anemoi/api/static/ missing")
for module in stray:
    twin = module[:-3] + "."
    if any(e.startswith(twin) for e in ext):
        problems.append(f"{module} shipped as both source and extension")
for line in stray:
    print(f"  kept as source: {line}")
if problems:
    sys.exit("build-compiled-wheel: " + "; ".join(problems))
EOF
)
echo "$listing"

mkdir -p "$out"
cp "$wheel" "$out/"
echo "built $out/$(basename "$wheel")"
