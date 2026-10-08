# Anemoi — Wiki source

These files are the source for the GitHub wiki of the `anemoi` repository. They document **Scope v2.1** and the reference implementation.

`README.md` (this file) is **not** a wiki page — GitHub ignores it in wiki repos. It exists for whoever clones this to edit.

---

## Publishing

**This folder is the source of truth.** It lives at `wiki/` in the main `anemoi` repository, and `.github/workflows/wiki.yml` publishes it to the GitHub wiki (`anemoi.wiki.git`) on every push to `main` that changes it. Edit the wiki through a pull request like any other change, so docs land in the same PR as the code they describe.

- **Don't edit in the GitHub wiki UI.** The next publish would overwrite the edit, so the workflow refuses instead: if the wiki has changed since the commit it last published (recorded as a `Source-Commit:` trailer on each wiki commit), it fails and names the files. Copy the edit into `wiki/` in a PR, then re-run it.
- **Manual publish:** Actions → *Publish wiki* → *Run workflow*.
- **The console's `/docs` pages** are built from this folder too (`console/scripts/sync-wiki.mjs`), and a change here counts as a console change for the Deploy workflow, so they update on the same merge.

## Conventions used here

**Filenames map to page titles.** `Train-Serve-Consistency.md` becomes the page *Train Serve Consistency* at `/wiki/Train-Serve-Consistency`. Dashes become spaces in the title.

**Links are plain relative markdown**, `[Inference Cycle](Inference-Cycle)`, rather than the `[[Page]]` gollum syntax. Both work in GitHub wikis, but plain markdown also renders correctly on any other markdown viewer and in local previews, including the console's `/docs`.

**Flat structure, no subdirectories.** GitHub's wiki UI does not present a folder hierarchy; navigation comes from `_Sidebar.md`.

**Mermaid diagrams** are used where a diagram earns its place. GitHub wikis render fenced `mermaid` code blocks natively. The scope document's ASCII diagrams were converted; if you need the originals they are in `Anemoi_Project_Scope_v2.1.md`.

**Special pages**

| File | Role |
|---|---|
| `Home.md` | Landing page. Required name |
| `_Sidebar.md` | Right-hand navigation on every page |
| `_Footer.md` | Footer on every page |

---

## Page inventory

29 files: 26 content pages, 2 special pages, this README.

| Page | Covers |
|---|---|
| `Home` | Landing, invariants, page index |
| `Getting-Started` | Install, CLI, what is real vs synthetic |
| `System-Architecture` | §2 — layers and forecast path |
| `Model-Catalog` | §3 — seven builders, resource profiles |
| `Data-Sources` | §4.1 — registry, roles, working/final split |
| `Data-Pipeline` | §4.2–4.5 — ingestion, preprocessing, splits, versioning |
| `Train-Serve-Consistency` | §4.6 — the central v2.1 policy |
| `Training-Architecture` | §5.1–5.4, §5.7 — modes, waves, promotion gates |
| `Retraining-Triggers` | §5.5 — triggers and the derived-model cascade |
| `Model-Registry` | §7.1, §5.7, §10.2 — pinning and rollback |
| `Experiment-Tracking` | §7.2–7.3 — tags and metrics |
| `Inference-Cycle` | §6 — timing, budgets, the derived timeout |
| `Degraded-Modes` | §4.6.4, §6.2.2, §10.1 — every fallback path |
| `Operations-Runbook` | §8, §10.2–10.3 — schedules, alerting, incidents |
| `Monitoring` | §4.6.3, §8.3 — skew audit and drift |
| `Verification-Metrics` | §7.3, Appendix B — scoring and targets |
| `Storage-and-Versioning` | §9 — hierarchy, tiers, retention |
| `Codebase-Map` | Module layout (src/, docker/api, console, CI), key types, exceptions |
| `API` | Anemoi-API: endpoints, payload, read cache, errors |
| `Branding` | Wind-god names, colours, typography |
| `Configuration-Reference` | The three YAML files |
| `Testing` | Suite map, conventions, fixtures |
| `References` | Verified scholarly citations for algorithms, thresholds and baselines |
| `Decision-Log` | v2→v2.1 changes plus implementation findings |
| `Roadmap` | Synthetic components, open questions, sequencing |
| `Glossary` | Appendix A, extended |

---

## Maintaining

**When the scope changes,** update the affected page *and* `Decision-Log`. The decision log is the page that makes the others trustworthy — a wiki that records what changed but not why decays into a description of the current state, which the code already provides.

**When adding a page,** add it to three places: `_Sidebar.md`, the page index at the bottom of `Home.md`, and the inventory above.

**Numbers that appear in more than one page** — stage budgets, alert thresholds, promotion limits — are duplicated deliberately, so each page reads standalone. `Configuration-Reference` is the canonical statement; if they diverge, that page wins.

**The derived vitals timeout** (`t+1:20`) is the one number that must never be edited in isolation. It is a function of the reduced-profile worst case and the advisory margin. Change either and recompute — see `Configuration-Reference`.
