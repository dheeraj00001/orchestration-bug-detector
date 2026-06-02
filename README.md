# Orchestration Bug Detector

Deterministic static analysis tool for detecting architectural defects in large-scale polyglot monorepos. It implements a 4-phase zonal protocol to identify API contract mismatches, authorization boundary leaks, and contract drift without context window exhaustion.

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
Run the MCP server to expose the detection tools:
```bash
python3 mcp/server.py
```

The server provides the following Model Context Protocol (MCP) tools:
1. `generate_module_map`: Scans monorepo topology and scores edges (Tier 1-3).
2. `extract_zonal_graph`: Performs zonal contract resolution centered on a seed service.
3. `run_dre_rules`: Classifies anomalies using the Deterministic Rule Engine.
4. `plan_subagent_tasks`: Generates targeted verification tasks for subagents.
5. `check_interception_chain`: Validates findings against hierarchical middleware layers.
6. `synthesize_findings`: Merges subagent outputs into a final deterministic report.

## System Architecture

The detector operates through four distinct phases to ensure context efficiency and deterministic accuracy:

### Phase 1: MAP (Zonal Discovery)
Performs a two-pass scan. Pass 1 identifies module boundaries via markers (`package.json`, `go.mod`, `requirements.txt`). Pass 2 scores edges into Tiers 1-3 based on "High-Signal Usage Evidence" on both sides of the boundary. Includes `ZonalExplorer` for bounded BFS traversal.

### Phase 2: TRACE (Zonal Contract Resolution)
Resolves contract evidence exclusively within the identified impact zone. Implements **Anchor-First Validation**, prioritizing official IDLs (Proto/GraphQL) over implementation details.

### Phase 3: DRE & DIGEST (Deterministic Classification)
Applies a **Deterministic Rule Engine (DRE)** to classify anomalies:
- `MATCHED`: Contract and implementation align.
- `ANCHOR_DRIFT`: Payload aligns but anchor is stale or version-skewed.
- `CONTRACT_MISMATCH`: Payload discrepancy detected (highest precedence).
- `MISSING_ANCHOR`: High-signal usage without a declared IDL.

Includes `CanonicalNormalizer` for 1-to-1 field mapping verification (lowercase, strip underscores, collapse camelCase).

### Phase 4: DELEGATE & SYNTHESIZE (Verification & Reporting)
Spawns subagents with bounded hypotheses for structural verification. The `DeterministicSynthesizer` merges results, applying the **Hierarchical Evidence Chain** (Infra > Platform > Local) to suppress false positives handled by global middleware.

## Testing & Verification

The codebase adheres to strict Test-Driven Development (TDD) principles.

```bash
pytest tests/
```

| Module | Responsibility | Test Count |
|--------|----------------|------------|
| `DiscoveryEngine` | Zonal discovery & tier scoring | 2 |
| `EvidenceResolver` | Tier 1/2/3 scoring rules | 3 |
| `ZonalExplorer` | Bounded BFS & Tier pruning | 4 |
| `ZonalContractResolver`| Cross-service contract stitching | 1 |
| `CanonicalNormalizer` | Field-name normalization | 5 |
| `DeterministicRuleEngine`| Anomaly classification & priority | 6 |
| `AnomalyDigester` | Digest generation & suppression | 2 |
| `DeterministicSynthesizer`| Subagent merge & reporting | 3 |
| `InterceptionChain` | Hierarchical middleware logic | 4 |

## Configuration

- **Manifest**: `.gemini-plugin/plugin.json`
- **Skill Definitions**: `skills/orchestration-bug-detector.md`

## Development Setup

### Adding Language Support
1. Implement a new extractor in `scripts/extractors/` by satisfying the `BoundaryExtractor` interface.
2. Register the extension in `ZonalContractResolver`.
3. Add module root markers to `ModuleRegistry.MODULE_MARKERS`.

## License & Attribution

Internal Engineering Tool. Optimized for large-scale monorepo analysis.
