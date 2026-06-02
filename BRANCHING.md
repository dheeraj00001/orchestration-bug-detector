# Branching Strategy: Trunk-Based Development

## Principles
- All changes merge into `main`.
- Features live in short-lived branches: `feat/*` or `fix/*`.
- Branches should not exist for more than 48 hours.

## Protection Rules
- `main` branch requires PR review.
- Status checks (pytest) must pass before merging.
- Linear history enforced: Squash or Rebase merge only.

## Release Tagging
Use Semantic Versioning (`vX.Y.Z`).
- `feat`: Minor bump.
- `fix`: Patch bump.
- `!`: Major bump.
