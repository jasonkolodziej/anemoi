---
applyTo: "PLAN.md, PROJECT.md, .github/**, **/*.md"
description: "Enforces plan-to-project-to-issue traceability for work tracked in this repository."
---

# Project Traceability Instructions

These instructions apply whenever work is derived from the repository plan, the project board, or issue tracking.

## Governing rule

`PLAN.md` is the authoritative source of strategy, scope, sequencing, and open items. GitHub Project items are execution trackers. Issues are actionable implementation units.

## Required behavior

- Treat `PLAN.md` as the source of truth for planning decisions.
- Do not create a project item without a clear plan section, milestone, or approved work stream behind it.
- Do not create an issue for a task that is still planning-level unless it has been converted to an actionable work item.
- Every project item should include a `Source Plan` reference and acceptance criteria.
- Every issue should include traceability metadata:
  - Source plan
  - Parent plan section
  - Related project item
  - Acceptance criteria
  - Dependencies / blockers as needed
- When scope or priority changes, update the relevant project card and the plan together.
- Prefer a narrow issue for implementation detail, and keep the board item as the status-bearing record.

## Preferred workflow

1. Update `PLAN.md` first.
2. Update or create the matching project board item.
3. Only then create a linked issue if more detail or implementation tracking is needed.
4. Keep the issue linked back to the same plan section and project item.

## Prohibited behavior

- Ad hoc project items unrelated to the plan
- Issue-only work that is not traceable to a project item or plan section
- Unlinked issue work that drifts away from the plan
- Updating implementation without updating the plan or project board when the scope changes

## Success criteria

The plan, board, and issue records should read as a single coherent system: the plan defines the work, the project board tracks it, and the issue gives the execution detail.
