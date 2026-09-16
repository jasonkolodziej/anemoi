---
applyTo: "**"
---

# General Coding Instructions

These instructions apply to all files in this repository and supplement the guidelines in `.github/copilot-instructions.md`.

## Code Style

- Use consistent indentation: 4 spaces for most languages; 2 spaces for JSON, YAML, and HTML.
- End every file with a single newline character.
- Remove trailing whitespace on all lines.
- Limit line length to 120 characters where practical.

## Naming Conventions

- **Variables and functions**: `camelCase` (JavaScript/TypeScript/Go), `snake_case` (Python/Rust)
- **Classes and types**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `kebab-case` for most files; match language conventions for source files

## Import / Dependency Order

Order imports as: standard library → third-party → local modules. Separate each group with a blank line.

## Error Messages

Write error messages that are actionable: describe what went wrong, where, and how to fix it.
Example: `"Missing required environment variable DATABASE_URL — set it in .env or GitHub Secrets"`

## Comments

- Avoid restating what the code does — explain _why_ non-obvious decisions were made.
- Use `TODO(username):` and `FIXME(username):` prefixes for outstanding work items.
- Keep comments up to date when code changes.

## Wiki Synchronization Rule

- The wiki is the canonical source of truth for architecture, scope, invariants, and operating assumptions.
- Before making changes to code, configuration, workflows, or project planning, read the relevant wiki pages first.
- If the code and wiki disagree, treat the wiki as the design source of truth unless the user explicitly requests a different behavior.
- Any substantive change must be accompanied by a matching wiki update when architecture, system boundaries, operational behavior, or user-facing workflows change.
- If a feature or workflow is not documented in the wiki, add or update the relevant wiki page in the same change.
- Do not leave documentation drift behind: code, plan, and wiki must stay aligned.
- When unsure, say which wiki page you are checking and which code path you are validating before proceeding.
