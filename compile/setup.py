"""Build the compiled (C extension) wheel of ``anemoi``.

Not the project's build backend: ``pyproject.toml`` builds the ordinary
pure-Python wheel with hatchling, and nothing there refers to this file.
This is run only by ``.github/scripts/build-compiled-wheel.sh``, from a
staging directory holding a *copy* of ``src/anemoi`` -- so the generated
``.c`` and ``.so`` files never land in ``src/``. See
``docs/compiled_build_plan.md``.

Every module is translated to C by Cython and compiled to an extension
module, except ``__init__.py``/``__main__.py`` (kept as source so packages
and ``python -m`` work as usual) and anything matching ``KEEP_AS_SOURCE``.
The wheel carries the same name, version, dependencies, extras and entry
points as the pure-Python one, read from ``pyproject.toml``, so it is a
drop-in replacement for it.

Expected layout of the staging directory (the script creates it)::

    setup.py  pyproject.toml  README.md  LICENSE  anemoi/
"""

from __future__ import annotations

import fnmatch
import os
import tomllib
from pathlib import Path

from Cython.Build import cythonize
from setuptools import find_packages, setup
from setuptools.command.build_py import build_py

HERE = Path(__file__).resolve().parent
PACKAGE = "anemoi"

#: Modules that stay interpreted, as glob patterns over POSIX paths relative
#: to the staging directory (e.g. ``"anemoi/models/*.py"``). Say why beside
#: each entry. Empty for now: every module compiles and passes the
#: non-torch test suite; the torch-marked tests are phase 2 of the plan and
#: may add entries here (``torch.compile`` traces bytecode, which a compiled
#: ``forward`` does not have).
KEEP_AS_SOURCE: tuple[str, ...] = ()

#: Never compiled: package markers and ``python -m`` entry points.
_ALWAYS_SOURCE = ("__init__.py", "__main__.py")

COMPILER_DIRECTIVES = {
    "language_level": 3,
    # Compiled functions keep signatures and bind like Python functions:
    # FastAPI and models.architecture read them with inspect.signature.
    "binding": True,
    # Annotations stay documentation, as in Python. With Cython's default,
    # `x: str = Header(...)` (api/deps.py) raises TypeError at import.
    "annotation_typing": False,
    "always_allow_keywords": True,
}


def _is_kept(path: str) -> bool:
    return path.endswith(_ALWAYS_SOURCE) or any(
        fnmatch.fnmatch(path, pattern) for pattern in KEEP_AS_SOURCE
    )


def _modules_to_compile() -> list[str]:
    paths = sorted(p.relative_to(HERE).as_posix() for p in (HERE / PACKAGE).rglob("*.py"))
    return [p for p in paths if not _is_kept(p)]


COMPILED = _modules_to_compile()
_COMPILED_SET = {os.path.normpath(p) for p in COMPILED}


class BuildPyWithoutCompiledSources(build_py):
    """Leave the ``.py`` of every compiled module out of the wheel."""

    def find_package_modules(self, package, package_dir):
        return [
            (pkg, module, path)
            for pkg, module, path in super().find_package_modules(package, package_dir)
            if os.path.normpath(path) not in _COMPILED_SET
        ]


def _project() -> dict:
    with (HERE / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]


def _entry_points(project: dict) -> dict[str, list[str]]:
    groups = {"console_scripts": project.get("scripts", {})}
    groups.update(project.get("entry-points", {}))
    return {
        group: [f"{name} = {target}" for name, target in entries.items()]
        for group, entries in groups.items()
        if entries
    }


project = _project()
jobs = int(os.environ.get("ANEMOI_COMPILE_JOBS") or os.cpu_count() or 1)

setup(
    name=project["name"],
    version=project["version"],
    description=project["description"],
    long_description=(HERE / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    python_requires=project["requires-python"],
    install_requires=project["dependencies"],
    extras_require=project["optional-dependencies"],
    entry_points=_entry_points(project),
    packages=find_packages(where=str(HERE), include=[PACKAGE, f"{PACKAGE}.*"]),
    # Located at runtime by Path(__file__).parent / "static" (api/main.py).
    package_data={f"{PACKAGE}.api": ["static/*"]},
    ext_modules=cythonize(
        COMPILED,
        nthreads=jobs,
        compiler_directives=COMPILER_DIRECTIVES,
        build_dir="build/cython",
    ),
    cmdclass={"build_py": BuildPyWithoutCompiledSources},
    options={"build_ext": {"parallel": jobs}},
    zip_safe=False,
)
