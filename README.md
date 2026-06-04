# Orchestration Bug Detector

Deterministic static analysis engine for detecting architectural defects in large-scale polyglot monorepos. It implements a 4-phase zonal protocol to identify API contract mismatches, authorization boundary leaks, and contract drift without context window exhaustion.

## Quickstart

### Prerequisites
- Python 3.10+
- `pip install mcp pytest`

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage
Expose the detection tools via Model Context Protocol (MCP):
```bash
python3 mcp/server.py
```

## System Architecture

The detector operates through four distinct phases to ensure context efficiency and deterministic accuracy.

### Phase 1: MAP (Zonal Discovery)
Performs a two-pass scan of the repository topology.
- **Pass 1**: Identifies module boundaries via markers (`package.json`, `go.mod`, `requirements.txt`).
- **Pass 2**: Scores edges into Tiers 1-3 based on usage evidence on both sides of the boundary.
- **Zonal Scoping**: Implements bounded BFS traversal to prevent analysis bloat.

### Phase 2: TRACE (Zonal Contract Resolution)
Resolves contract evidence exclusively within the identified impact zone.
- **Anchor-First Validation**: Prioritizes official IDLs (Proto/GraphQL) over implementation details.
- **Canonical Normalization**: Standardizes field names (lowercase, strip underscores, collapse camelCase) to detect mismatches across different naming conventions.

### Phase 3: DRE & DIGEST (Deterministic Classification)
Applies a **Deterministic Rule Engine (DRE)** to classify anomalies:
- `CONTRACT_MISMATCH`: Payload discrepancy detected (highest precedence).
- `ANCHOR_DRIFT`: Payload aligns but anchor is stale or version-skewed.
- `MISSING_ANCHOR`: High-signal usage evidence exists without a declared IDL.
- `MATCHED`: Contract and implementation are fully aligned.

### Phase 4: DELEGATE & SYNTHESIZE (Verification)
Merges findings and applies the **Hierarchical Evidence Chain** (Infra > Platform > Local) to suppress false positives handled by global middleware.

## MCP Tool Reference

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `generate_module_map` | `root_path`, `seed_service`, `max_distance` | Returns a high-level weighted dependency map. |
| `extract_zonal_graph` | `seed_service`, `max_distance`, `max_nodes` | Performs zonal contract resolution and returns a stitched graph. |
| `run_dre_rules` | `graph`, `output_dir` | Classifies anomalies and writes results to disk. |
| `plan_subagent_tasks` | `prioritized_digest` | Generates targeted payloads for subagent verification. |
| `check_interception_chain`| `infra_evidence`, `platform_evidence`, `local_evidence` | Resolves middleware suppression priority. |
| `synthesize_findings` | `findings`, `service_directory`, `output_dir` | Merges subagent results into a final report. |

## Testing & Verification

Execute the comprehensive test suite covering all architectural phases:
```bash
pytest tests/
```

Core test areas:
- `tests/test_dre.py`: Anomaly classification logic.
- `tests/test_zonal_explorer.py`: Bounded BFS and Tier-based pruning.
- `tests/test_canonical_normalizer.py`: Field normalization edge cases.
- `tests/test_interception_chain.py`: Middleware suppression hierarchy.

## Development Workflow

### Conventional Commits
All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
```bash
git config commit.template .gitmessage
```

### Branching
Standard GitHub Flow. Create feature branches from `main` and merge via Pull Request. See `BRANCHING.md` for details.

## Technical Context
Detailed design specifications and architectural decisions are maintained in:
- `CONTEXT.md`: Project glossary and core terminology.
- `docs/PRD.md`: Full product requirements and phase definitions.
- `docs/adr/`: Architectural Decision Records.
