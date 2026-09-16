# GitHub Copilot Instructions

This file provides repository-wide custom instructions for GitHub Copilot across all agents (VS Code inline, Copilot Chat, CLI, and cloud agents).

## Repository Purpose

This is a **GitHub repository template** designed to provide a consistent, best-practice starting point for new projects. It includes Copilot configuration, CI/CD workflows, VS Code workspace settings, and reusable agent skills/prompts.

## Coding Guidelines

- Prefer clear, self-documenting code over excessive inline comments.
- Follow existing file and directory naming conventions in the repository.
- Write small, focused functions with a single responsibility.
- Add error handling for all I/O and network operations.
- Keep dependencies minimal — prefer standard library solutions when possible.

## Commit & Pull Request Guidelines

- Use [Conventional Commits](https://www.conventionalcommits.org/) format: `type(scope): description`
  - Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`
- Keep commits atomic — one logical change per commit.
- Reference issue numbers in commit messages and PR descriptions when applicable.
- Every PR should include a description of _what_ changed and _why_.

## Testing Guidelines

- Write tests alongside feature code (co-located or in a `tests/` directory).
- Aim for meaningful test coverage of public APIs and critical paths.
- Tests should be deterministic and independent of each other.
- Use descriptive test names that explain the expected behavior.

## Documentation Guidelines

- Update `README.md` when adding new features or changing configuration.
- Document public APIs, configuration options, and non-obvious decisions.
- Place architectural decisions in `.github/plans/` as ADR (Architecture Decision Record) files.

## Security Guidelines

- Never commit secrets, credentials, or API keys — use GitHub Secrets or environment variables.
- Validate and sanitize all external inputs.
- Keep dependencies up to date; review security advisories before upgrading.

## Workflow & CI Guidelines

- All workflows live in `.github/workflows/`.
- The `copilot-setup-steps.yml` workflow configures the cloud agent environment.
- CI should run on every push to `main` and on all pull requests.

## Project Planning & Traceability

- `PLAN.md` is the authoritative project plan and defines scope, sequencing, and open items.
- GitHub Project board items should map to plan sections, milestones, or explicit work streams; do not create ad hoc items without a source in `PLAN.md`.
- Issues are for actionable implementation work narrower than a plan section. Do not create an issue when a project board item is enough to track the work.
- Every issue must include traceability metadata: source plan reference, related project item, parent plan section, and acceptance criteria.
- Every project item should carry a clear `Source Plan` reference and acceptance criteria, even when the item is a high-level milestone.
- Do not let issue-only work drift away from the plan. If work changes scope or priority, update the plan and the project card together.
- The preferred flow is: plan update -> project item update -> issue creation only when needed -> implementation and validation.
- If a work item cannot be tied back to a plan section or milestone, stop and clarify the source before proceeding.

## Wiki Synchronization Rule

- The wiki is the canonical source of truth for architecture, scope, invariants, and operating assumptions.
- Before making changes to code, configuration, workflows, or project planning, read the relevant wiki pages first.
- If the code and wiki disagree, treat the wiki as the design source of truth unless the user explicitly requests a different behavior.
- Any substantive change must be accompanied by a matching wiki update when architecture, system boundaries, operational behavior, or user-facing workflows change.
- If a feature or workflow is not documented in the wiki, add or update the relevant wiki page in the same change.
- Do not leave documentation drift behind: code, plan, and wiki must stay aligned.
- When unsure, say which wiki page you are checking and which code path you are validating before proceeding.
