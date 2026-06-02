# Orchestration Bug Detector

LLM-orchestrated static analysis tool for detecting cross-module architectural defects in large-scale polyglot monorepos. It implements a 4-phase hierarchical protocol to identify API contract mismatches, distributed saga compensation failures, authorization boundary leaks, and event-driven infinite loops without context window exhaustion.

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

Register the plugin in your Gemini CLI configuration (`.gemini-plugin/plugin.json`):
```json
{
  "name": "orchestration-bug-detector",
  "engines": {
    "mcp": {
      "command": "python3",
      "args": ["mcp/server.py"]
    }
  },
  "skills": ["skills/orchestration-bug-detector.md"]
}
```

## System Architecture

The detector operates through four distinct layers to ensure context efficiency and deterministic accuracy:

1.  **Discovery (Level 1)**: Heuristic 3-tier signal weighting scans monorepo topology via configuration markers (`go.mod`, `package.json`, `.proto`) to identify suspicious communication paths.
2.  **Deterministic Trace (Level 2)**: Polyglot Contract-Key resolution engine stitches disparate language ASTs using universal identifiers to flag payload schema mismatches.
3.  **Delegated Analysis (Level 3)**: Isolated subagents investigate high-risk paths using Recursive Language Model (RLM) sandboxed execution, avoiding raw file reads.
4.  **Synthesis Validation (Phase 4)**: A challenge-response loop validates findings against global middleware snippets to eliminate false positives.

## Testing & Verification

The codebase follows Test-Driven Development (TDD) principles. Run the complete suite using `pytest`:

```bash
pytest tests/
```

| Module | Responsibility | Test File |
|--------|----------------|-----------|
| `DiscoveryEngine` | Module mapping & signal weighting | `tests/test_discovery_engine.py` |
| `ContractStitcher` | Cross-language boundary matching | `tests/test_contract_stitcher.py` |
| `TraceEngine` | End-to-end trace orchestration | `tests/test_trace_engine.py` |
| `SubagentOrchestrator` | Task generation for subagents | `tests/test_orchestrator.py` |
| `SynthesisEngine` | False positive reduction | `tests/test_synthesis.py` |

## Dependencies & Requirements

- `mcp`: Model Context Protocol Python SDK
- `pytest`: Testing framework
- `tree-sitter` (Optional): Required for AST-based boundary extraction (experimental)

## Configuration

The plugin behavior is controlled by the manifest and the skill instruction set:
- **Manifest**: `.gemini-plugin/plugin.json`
- **Protocol Brain**: `skills/orchestration-bug-detector.md`

## Development Setup

The project uses a deep module architecture to maintain locality of logic and high leverage at interfaces.

### Signal Resolvers
Adding support for a new language requires implementing a `SignalResolver` in `scripts/signals.py` and registering it in the `DiscoveryEngine`.

### Boundary Extractors
Language-specific parsing logic resides in `scripts/extractors/`. New extractors must implement the `BoundaryExtractor` interface defined in `base.py`.

## License & Attribution

Internal Engineering Tool. Created for large-scale monorepo analysis.
