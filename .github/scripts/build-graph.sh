#!/usr/bin/env bash
# Rebuilds graphify-out/ (the code knowledge graph agents query) and reports
# whether it changed in a way worth committing.
#
#   .github/scripts/build-graph.sh            # build, then compare with HEAD
#
# Writes `changed=true|false` to $GITHUB_OUTPUT when run in Actions.
#
# Code-only: tree-sitter extraction runs locally with no LLM and no API key,
# and the same tree always yields the same graph.json, so a rebuild that finds
# nothing new is byte-identical apart from the commit it was built at. That
# stamp (graph.json's built_at_commit, the report's date and "Built from commit"
# lines) is ignored when deciding whether to commit; otherwise every push to
# main would add a 6 MB graph.json revision whose only change is a SHA.
set -euo pipefail

: "${GRAPHIFY_VERSION:?set GRAPHIFY_VERSION (pinned in .github/workflows/graphify.yml)}"
graphify() { uvx --from "graphifyy==${GRAPHIFY_VERSION}" graphify "$@"; }

graphify extract . --code-only
# --no-label: community naming needs an LLM. --no-viz: graph.html is not committed.
graphify cluster-only . --no-label --no-viz

for f in graphify-out/graph.json graphify-out/GRAPH_REPORT.md; do
  [[ -s "$f" ]] || { echo "::error::graphify did not write $f"; exit 1; }
done

nodes=$(jq '.nodes | length' graphify-out/graph.json)
edges=$(jq '.links | length' graphify-out/graph.json)
echo "graph: ${nodes} nodes, ${edges} edges"
# A collapse (an ignore rule gone wrong, a parser failing to load) should fail
# loudly rather than replace the committed graph with a near-empty one.
if (( nodes < 1000 )); then
  echo "::error::graph has only ${nodes} nodes; refusing to publish it"
  exit 1
fi

normalise_graph()  { jq -S 'del(.built_at_commit)' "$1"; }
normalise_report() { grep -v -E '^# Graph Report|^- Built from commit' "$1"; }

changed=false
if ! git cat-file -e HEAD:graphify-out/graph.json 2>/dev/null \
  || ! git cat-file -e HEAD:graphify-out/GRAPH_REPORT.md 2>/dev/null; then
  changed=true
  echo "no committed graph yet"
elif ! diff -q <(git show HEAD:graphify-out/graph.json | normalise_graph /dev/stdin) \
               <(normalise_graph graphify-out/graph.json) >/dev/null \
  || ! diff -q <(git show HEAD:graphify-out/GRAPH_REPORT.md | normalise_report /dev/stdin) \
               <(normalise_report graphify-out/GRAPH_REPORT.md) >/dev/null; then
  changed=true
  echo "graph changed structurally"
else
  echo "graph unchanged apart from its commit stamp"
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "changed=${changed}" >> "$GITHUB_OUTPUT"
fi
