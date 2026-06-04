# Branching Strategy

This project follows **Trunk-Based Development** for high-velocity iteration. All development occurs on short-lived feature branches that are merged directly into the `main` branch.

## Branch Naming Conventions

- **Feature**: `feat/<short-description>`
- **Bug Fix**: `fix/<short-description>`
- **Documentation**: `docs/<short-description>`
- **Refactor**: `refactor/<short-description>`
- **Chore**: `chore/<short-description>`

## Merge Policy

1. **Pull Requests**: All changes must be submitted via a Pull Request (PR) to `main`.
2. **Review**: At least one approval is required for all PRs.
3. **Continuous Integration**: All tests must pass before merging.
4. **Merge Strategy**: **Squash and Merge** is the preferred method to maintain a clean linear history.

## Protection Rules

The `main` branch is protected:
- Require a pull request before merging.
- Require status checks to pass before merging.
- Require linear history (Squash or Rebase merge).
