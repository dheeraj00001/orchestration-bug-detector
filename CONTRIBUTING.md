# Contributing to Orchestration Bug Detector

This project implements a high-leverage architectural analysis tool. We prioritize deterministic logic, context efficiency, and robust test coverage.

## Development Workflow

We strictly follow **Test-Driven Development (TDD)** via vertical slices.
- Every architectural change must start with a failing test in `tests/`.
- Implementation must be the minimal code required to satisfy the test.
- Refactoring is encouraged only when the test suite is GREEN.

### Local Setup
1. Create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the test suite: `pytest`

## Code Standards

### Architectural Principles
- **Locality**: Business logic for specific phases (MAP, TRACE, DRE, SYNTHESIZE) must reside within their respective modules in `scripts/`.
- **Interface Leverage**: Keep module interfaces small. A deep module provides significant behavior behind a narrow API.
- **Context Preservation**: Avoid raw-file reads during synthesis. Use structural views and bounded hypotheses to stay within LLM context limits.

### Commit Guidelines
We use **Conventional Commits** (v1.0.0).
- `feat`: A new feature or capability.
- `fix`: A bug fix in logic or extraction.
- `docs`: Documentation updates.
- `refactor`: Code changes that neither fix a bug nor add a feature.
- `test`: Adding or correcting tests.
- `chore`: Updating build tasks, package manager configs, etc.

Apply the template: `git config commit.template .gitmessage`

## Review Process
All Pull Requests must:
1. Pass all automated tests (`pytest`).
2. Adhere to the 4-phase protocol defined in `docs/PRD.md`.
3. Receive approval from at least one core maintainer.
4. Maintain a linear git history (Squash or Rebase merge only).
