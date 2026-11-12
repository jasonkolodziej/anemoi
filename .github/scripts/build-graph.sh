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

# graphify resolves the console's `$lib/...` imports through the path aliases
# in console/.svelte-kit/tsconfig.json, which `svelte-kit sync` generates and
# git ignores. Without it (CI, a fresh clone) every `$lib` import collapses
# into one unresolved `$lib` node and the console loses ~400 edges. Stand in
# for it with just the aliases it would define; a real one (from a local
# `pnpm dev`/`check`) is left alone and yields the same graph.
kit_tsconfig=console/.svelte-kit/tsconfig.json
if [[ ! -f "$kit_tsconfig" ]]; then
  mkdir -p "$(dirname "$kit_tsconfig")"
  cat > "$kit_tsconfig" <<'JSON'
{
  "compilerOptions": {
    "paths": {
      "$lib": ["../src/lib"],
      "$lib/*": ["../src/lib/*"],
      "$app/types": ["./types/index.d.ts"]
    },
    "rootDirs": ["..", "./types"]
  }
}
JSON
  echo "wrote a stand-in ${kit_tsconfig} for \$lib alias resolution"
fi

# Always build from an empty graphify-out/. extract reads whatever is already
# there (the previous graph.json, the AST cache, manifest.json), and a build
# on top of an existing graph comes out differently from a fresh one: the
# placeholder nodes for external imports ($env, svelte-sonner, ...) come and
# go between runs. From empty, the same tree gives byte-identical output, and
# a local run of this script agrees with CI. The comparison below reads the
# committed graph from git, not from disk. A full build takes seconds.
rm -rf graphify-out
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

normalise_graph()  { jq -S 'del(.built_at_commit)'; }
normalise_report() { grep -v -E '^# Graph Report|^- Built from commit'; }

changed=false
if ! git cat-file -e HEAD:graphify-out/graph.json 2>/dev/null \
  || ! git cat-file -e HEAD:graphify-out/GRAPH_REPORT.md 2>/dev/null; then
  changed=true
  echo "no committed graph yet"
else
  # Normalise into files rather than comparing two pipes, so neither side is
  # cut off mid-write when the comparison stops early.
  tmp=$(mktemp -d)
  git show HEAD:graphify-out/graph.json      | normalise_graph  > "$tmp/old.json"
  normalise_graph  < graphify-out/graph.json                    > "$tmp/new.json"
  git show HEAD:graphify-out/GRAPH_REPORT.md | normalise_report > "$tmp/old.md"
  normalise_report < graphify-out/GRAPH_REPORT.md               > "$tmp/new.md"
  if cmp -s "$tmp/old.json" "$tmp/new.json" && cmp -s "$tmp/old.md" "$tmp/new.md"; then
    echo "graph unchanged apart from its commit stamp"
  else
    changed=true
    echo "graph changed structurally"
  fi
  rm -r "$tmp"
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "changed=${changed}" >> "$GITHUB_OUTPUT"
fi
