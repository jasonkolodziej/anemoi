"""No SSH access into the API or training containers.

The API container once carried an ``authorized_keys`` entry in
``docker/api/wrangler.jsonc`` (for ``wrangler containers ssh``): Cloudflare
installs those keys into every running instance, so they never appear in the
image and the image smoke test (``.github/scripts/smoke-test-image.sh``)
can't see them. This checks the files that configure and build the
containers instead.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# An SSH grant in container config: Cloudflare's `authorized_keys` (and any
# `ssh` block that would enable it), or an OpenSSH public or private key.
FORBIDDEN = re.compile(
    r'"(authorized_keys|ssh)"\s*:'
    r"|\bssh-(ed25519|rsa|dss)\s+AAAA"
    r"|\becdsa-sha2-nistp\d+\s+AAAA"
    r"|-----BEGIN (OPENSSH|RSA|DSA|EC) PRIVATE KEY-----"
)


def _container_files() -> list[Path]:
    """Every tracked file that configures or builds a container."""
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    pattern = re.compile(
        r"(^|/)(wrangler\.jsonc?|wrangler\.toml|[^/]*Dockerfile[^/]*|cloudbuild\.yaml"
        r"|docker-compose[^/]*\.ya?ml|entrypoint\.sh)$"
    )
    return [ROOT / f for f in tracked if pattern.search(f) and "node_modules" not in f]


def test_the_container_files_are_found():
    names = {p.relative_to(ROOT).as_posix() for p in _container_files()}
    assert "docker/api/wrangler.jsonc" in names
    assert "docker/multistage.Dockerfile" in names


@pytest.mark.parametrize("path", _container_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_container_grants_ssh_access(path):
    hits = [
        f"{n}: {line.strip()[:80]}"
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1)
        if FORBIDDEN.search(line)
    ]
    assert not hits, f"SSH access configured in {path.relative_to(ROOT)}:\n" + "\n".join(hits)


@pytest.mark.parametrize("line", [
    '"authorized_keys": [',
    '      "ssh": { "enabled": true },',
    '"public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHfz anemoi-api-real-debug",',
    "-----BEGIN OPENSSH PRIVATE KEY-----",
])
def test_the_pattern_catches_an_ssh_grant(line):
    assert FORBIDDEN.search(line)
