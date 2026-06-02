# Contributing to Orchestration Bug Detector

## Development Workflow
We follow Test-Driven Development (TDD) via vertical slices. Do not write implementation without a corresponding failing test in `tests/`.

### Setup
1. `pip install -r requirements.txt`
2. Run tests: `pytest`

### Commit Strategy
Use Conventional Commits. Use the provided template:
`git config commit.template .gitmessage`

## Code Review Guidelines
- **Locality**: Ensure logic for signal extraction is concentrated in specific Resolvers/Extractors.
- **Interface Stability**: Deepen modules by keeping interfaces small and leverage high.
- **Context Efficiency**: Reject any PR that introduces recursive directory walking or large file reads into the LLM context.
- **Deterministic First**: Prefer deterministic Python logic over LLM-prompt-based heuristics for core graph construction.
