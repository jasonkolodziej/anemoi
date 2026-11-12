#!/usr/bin/env bash
# Commits the rebuilt graphify-out/ files to the default branch through the
# Git Data API rather than `git push`.
#
#   .github/scripts/commit-graph.sh <base-sha> <branch>
#
# Why the API: the "main protect" ruleset requires signed commits and has no
# bypass actors. A commit created through the API with the workflow's
# GITHUB_TOKEN, and no author/committer given, is signed by GitHub and shows
# as Verified, so it satisfies the rule without a signing key in CI.
#
# The ref update is a fast-forward from <base-sha> only. If the branch has
# moved on since this run checked out, a newer push has started its own run,
# which will rebuild from the newer tree; this one steps aside.
set -euo pipefail

base=${1:?base commit sha}
branch=${2:?branch}
repo=${GITHUB_REPOSITORY:?}
files=(graphify-out/graph.json graphify-out/GRAPH_REPORT.md)

head=$(gh api "repos/${repo}/git/ref/heads/${branch}" --jq .object.sha)
if [[ "$head" != "$base" ]]; then
  echo "::notice::${branch} moved from ${base:0:8} to ${head:0:8}; the newer run publishes the graph"
  exit 0
fi

base_tree=$(gh api "repos/${repo}/git/commits/${base}" --jq .tree.sha)

entries='[]'
for f in "${files[@]}"; do
  # Blobs go up as base64 (graph.json is ~6 MB; the blob API takes up to 100 MB).
  blob=$(base64 -w0 "$f" \
    | jq -R '{content: ., encoding: "base64"}' \
    | gh api "repos/${repo}/git/blobs" --input - --jq .sha)
  entries=$(jq -c --arg path "$f" --arg sha "$blob" \
    '. + [{path: $path, mode: "100644", type: "blob", sha: $sha}]' <<<"$entries")
done

tree=$(jq -n --arg base "$base_tree" --argjson tree "$entries" '{base_tree: $base, tree: $tree}' \
  | gh api "repos/${repo}/git/trees" --input - --jq .sha)

message="chore(graph): rebuild graphify-out for ${base:0:8} [skip ci]

Built by .github/workflows/graphify.yml (graphifyy ${GRAPHIFY_VERSION:-?}, code-only)."

commit=$(jq -n --arg msg "$message" --arg tree "$tree" --arg parent "$base" \
  '{message: $msg, tree: $tree, parents: [$parent]}' \
  | gh api "repos/${repo}/git/commits" --input - --jq .sha)

verification=$(gh api "repos/${repo}/git/commits/${commit}" --jq '.verification | "\(.verified) \(.reason)"')
echo "created ${commit} (verification: ${verification})"
# The ruleset would reject an unsigned commit anyway; failing here says why.
if [[ "$verification" != true* ]]; then
  echo "::error::GitHub did not sign ${commit:0:8} (${verification}); ${branch} requires signed commits"
  exit 1
fi

# force=false: a fast-forward or nothing.
if ! gh api -X PATCH "repos/${repo}/git/refs/heads/${branch}" \
     -f sha="$commit" -F force=false >/dev/null; then
  head=$(gh api "repos/${repo}/git/ref/heads/${branch}" --jq .object.sha)
  if [[ "$head" != "$base" ]]; then
    echo "::notice::${branch} moved to ${head:0:8} while publishing; the newer run publishes the graph"
    exit 0
  fi
  # Branch didn't move, so the update itself was refused (ruleset, permissions).
  echo "::error::could not update ${branch} to ${commit:0:8}"
  exit 1
fi
echo "::notice::published graph at ${commit:0:8} on ${branch}"
