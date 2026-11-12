# Agent notes

Instructions for coding agents (Claude Code, Copilot, Codex and others) working in this repository. Project conventions live in [`.github/copilot-instructions.md`](.github/copilot-instructions.md) and [`.github/instructions/`](.github/instructions/); the system itself is documented in [`wiki/`](wiki/), starting at [`wiki/Codebase-Map.md`](wiki/Codebase-Map.md).

## Code knowledge graph (`graphify-out/`)

`graphify-out/graph.json` is a graph of the code in this repo: every module, class, function and Svelte component, with the calls, imports and uses between them (Python, TypeScript, Svelte, shell, YAML). CI rebuilds it on every push to `main` ([`.github/workflows/graphify.yml`](.github/workflows/graphify.yml)), so it describes `main` as of the commit in its `built_at_commit` field.

**Use it before broad searching.** For "where is X used", "what depends on Y", "how does A reach B", or orienting in an unfamiliar area, query the graph first, then read the files it points to. It is faster and cheaper than grepping the tree.

1. **Overview:** read [`graphify-out/GRAPH_REPORT.md`](graphify-out/GRAPH_REPORT.md) — most-connected nodes ("god nodes"), communities, and surprising cross-module links.
2. **MCP tools** (server `graphify`, configured in `.mcp.json` and `.vscode/mcp.json`): `query_graph`, `get_node`, `get_neighbors`, `shortest_path`, `get_community`, `god_nodes`, `graph_stats`, and `get_pr_impact` for which areas a PR touches.
3. **CLI**, when MCP isn't available (needs `uv`):

   ```bash
   G='uvx --from graphifyy==0.9.97 graphify'
   $G query "drift monitoring retraining trigger" --budget 800
   $G explain "ModelRegistry"
   $G path "src/anemoi/inference/cycle.py::run_cycle()" "ModelRegistry"
   $G affected "CheckpointStore"        # what breaks if this changes
   ```

   A name that matches several nodes (`run_cycle` exists in four files) returns the candidates; retry with `path::symbol` or the node id.

**Know its limits.**

- Edges marked `EXTRACTED` were read from source; `INFERRED` ones (about 15%) were resolved heuristically. Confirm an `INFERRED` edge in the code before relying on it.
- It is code only. The wiki, `README.md` and other Markdown are not in the graph; read them directly.
- On a branch, the graph shows `main`, not your changes. To refresh your local copy, run `GRAPHIFY_VERSION=0.9.97 .github/scripts/build-graph.sh` from the repo root (needs `uv` and `jq`). Don't use `graphify update .`: it skips the stand-in for the console's `$lib` aliases, so console imports come out unresolved, and it builds on top of the existing graph, which doesn't reproduce CI's result.
- Communities are numbered, not named (`Community 42`); naming them needs an LLM and is not done in CI.

**Don't commit `graphify-out/`.** CI is its only writer; a hand-built graph in a PR just conflicts with the next rebuild. If you refreshed it locally, `git restore graphify-out/` before committing. What the graph skips is set in [`.graphifyignore`](.graphifyignore).
