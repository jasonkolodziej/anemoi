#!/usr/bin/env bash
# Writes build-info.json at the repo root: the commit an image is built
# from, which both images copy to /app/build-info.json and anemoi.provenance
# reads (#214) -- neither image carries .git, so without this every served
# cycle and registered model said nothing about the code that produced it.
#
# Usage: write-build-info.sh <git-sha>   (run from the repo root, before
# `docker build` / `wrangler deploy`).
set -euo pipefail
sha=${1:?usage: write-build-info.sh <git-sha>}
if [[ ! "$sha" =~ ^[0-9a-f]{7,40}$ ]]; then
	# e.g. Cloud Build's default _TAG=manual: say nothing rather than
	# record something that isn't a commit.
	echo '{}' >build-info.json
	echo "write-build-info: '$sha' is not a commit; wrote {}" >&2
	exit 0
fi
printf '{"git_sha": "%s", "built_at": "%s"}\n' "$sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >build-info.json
cat build-info.json
