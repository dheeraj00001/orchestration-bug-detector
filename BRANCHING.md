# Branching Strategy: Trunk-Based Development

This repository follows **Trunk-Based Development** to maintain high velocity and ensure continuous integration of deterministic rules.

## Core Branches
- **`main`**: The primary branch. Always reflects the current production-ready state of the detector.

## Feature & Fix Branches
- Use short-lived branches for all changes.
- Naming convention:
  - `feat/feature-name`
  - `fix/bug-description`
  - `docs/topic-name`
- Branches should be merged back to `main` within 48 hours.

## Merge Policy
- **Linear History**: We enforce a linear commit history. Only `Squash and Merge` or `Rebase and Merge` are permitted.
- **Status Checks**: All CI checks (Pytest) must be green before merging.
- **PR Review**: At least one technical review is required for all changes to the `scripts/` directory.

## Tagging & Releases
We use **Semantic Versioning (SemVer)** for releases.
- **Major (`!`)**: Breaking changes in the MCP tool interface or architectural protocol.
- **Minor (`feat`)**: New language support or enhanced scoring rules.
- **Patch (`fix`)**: Logic bug fixes or documentation improvements.
