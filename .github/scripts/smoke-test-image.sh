#!/usr/bin/env bash
# Smoke-tests an image built from docker/multistage.Dockerfile before it is
# pushed or deployed: does it start, and can the code find its configs?
#
# Usage: smoke-test-image.sh <image> <api|training>
#
# Since #211 every anemoi import reads configs/*.yaml (anemoi.config) and
# fails without them, so an image missing /app/configs would start and then
# crash -- found in production, not in a build log. This runs each image the
# way it really runs, with no ANEMOI_CONFIG_DIR, and checks:
#
#   both      the code imports and finds /app/configs on its own
#   api       the container's own CMD starts uvicorn and /v1/health answers
#   training  the curriculum, scheduler and promotion modules load
#   both      no SSH key, .ssh directory or OpenSSH private key anywhere
#             in the image's filesystem
#
# Used by .github/workflows/deploy.yml (api, every PR and deploy),
# build-training-image.yml and docker/cloud-run-training/cloudbuild.yaml
# (training, before push).
set -euo pipefail

image=${1:?usage: smoke-test-image.sh <image> <api|training>}
target=${2:?usage: smoke-test-image.sh <image> <api|training>}

check_configs() {
	docker run --rm --entrypoint python -e EXPECT_GIT_SHA="${EXPECT_GIT_SHA:-}" "$image" -c '
import os
import anemoi.config as c
import anemoi.provenance as prov
import anemoi.inference.scheduler as s
import anemoi.training.curriculum as cu
import anemoi.training.promotion as p
assert str(c.config_dir()) == "/app/configs", c.config_dir()
# The commit the image was built from (#214): CI passes the one it wrote.
expected = os.environ.get("EXPECT_GIT_SHA")
assert not expected or prov.git_sha() == expected, (prov.git_sha(), expected)
print("git sha:", prov.git_sha(), "| config sha256:", prov.config_digest()[:12])
print("configs:", c.config_dir(), "| members:", s.DEFAULT_ENSEMBLE_MEMBERS,
      "| stage B epochs:", cu.stage_b().epochs, "| thresholds:", len(p.DEFAULT_THRESHOLDS))
'
}

# Neither image needs SSH: the build context excludes everything but the
# package (multistage.Dockerfile.dockerignore) and nothing installs an SSH
# client. This keeps it that way: a key copied in by a future COPY, base
# image or package fails the build. Run as root so no directory is skipped
# for permissions.
check_no_ssh_keys() {
	docker run --rm --user 0 --entrypoint python "$image" -c '
import os, re, sys
NAME = re.compile(r"^(id_(rsa|dsa|ecdsa|ed25519)(_sk)?(\.pub)?|authorized_keys2?|known_hosts|ssh_host_.*_key(\.pub)?|identity)$")
# A whole key, not the marker alone: ssh.py in the cryptography package
# (it parses keys) holds the BEGIN line as a constant.
KEY = re.compile(rb"-----BEGIN OPENSSH PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]{64,}-----END OPENSSH PRIVATE KEY-----")
SKIP = ("/proc", "/sys", "/dev")
found = []
for root, dirs, files in os.walk("/", followlinks=False):
    if root.startswith(SKIP):
        dirs[:] = []
        continue
    found += [os.path.join(root, d) for d in dirs if d == ".ssh"]
    for f in files:
        path = os.path.join(root, f)
        if NAME.match(f):
            found.append(path)
            continue
        try:
            if os.path.islink(path) or os.path.getsize(path) > 64 * 1024:
                continue
            with open(path, "rb") as fh:
                if KEY.search(fh.read()):
                    found.append(path)
        except OSError:
            pass
if found:
    print("SSH key material in the image:", *found, sep="\n  ", file=sys.stderr)
    sys.exit(1)
print("no SSH keys in the image")
'
}

case "$target" in
training)
	check_configs
	check_no_ssh_keys
	echo "training image OK"
	;;
api)
	check_configs
	check_no_ssh_keys
	name="anemoi-smoke-$$"
	# The image's own CMD (registry-pull, then uvicorn on 8080). No R2
	# credentials here: registry-pull fails and `|| true` carries on, the
	# same as a misconfigured production start -- the API must still come up.
	docker run -d --name "$name" -p 18080:8080 "$image" >/dev/null
	trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
	for _ in $(seq 1 60); do
		if body=$(curl -fsS http://127.0.0.1:18080/v1/health 2>/dev/null); then
			echo "health: $body"
			grep -q '"state_mode":"real"' <<<"$body" || {
				echo "::error::the api image isn't running in real mode" >&2
				exit 1
			}
			echo "api image OK"
			exit 0
		fi
		if [ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]; then
			echo "::error::the api container exited during startup" >&2
			docker logs "$name" >&2
			exit 1
		fi
		sleep 2
	done
	echo "::error::/v1/health didn't answer within 120s" >&2
	docker logs "$name" >&2
	exit 1
	;;
*)
	echo "unknown target: $target (expected api or training)" >&2
	exit 2
	;;
esac
