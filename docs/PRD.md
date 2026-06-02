# Product Requirements Document (PRD): Large-Giant Orchestration Bug Detector Plugin

## Problem Statement
As a developer or architect working in a large-giant polyglot monorepo, I am facing a critical blind spot: standard linters and static analysis tools cannot detect complex, cross-module orchestration bugs (e.g., API contract mismatches, missing distributed saga compensation logic, authorization boundary leaks, or event-driven infinite loops). Meanwhile, existing LLM-based code analysis tools fail at this scale because they attempt to read raw files into limited context windows, leading to context exhaustion, truncated outputs, and severe hallucinations. I need a scalable, deterministic, and context-efficient way to detect these high-value architectural bugs without overwhelming the AI or the system.

## Solution
We will build an LLM-Orchestrated Static Codebase Analyzer plugin, modeled after the `rlm-skill` architecture. It employs a **4-Phase Hierarchical Discovery Protocol** that delegates heavy lifting to deterministic tools (Tree-sitter, FTS5 SQLite indexing, sandboxed script execution) while reserving the LLM strictly for high-level orchestration, hypothesis generation, and logical synthesis. This ensures 100% scalability across 10,000+ file monorepos, zero context bloat, and a drastic reduction in false positives.

## User Stories
1. As a developer, I want the plugin to automatically generate a high-level "Module Map" of my monorepo, so that I can understand service boundaries without manual exploration.
2. As an architect, I want the plugin to prioritize Interface Definition Language (IDL) files (e.g., `.proto`, OpenAPI) and Infrastructure-as-Code (IaC) as "Strong Edges," so that the analysis reflects the actual declared system contracts, not just orphaned code.
3. As a security engineer, I want the plugin to detect "Authorization Boundary Leaks," so that I can identify internal microservice endpoints that lack input validation or auth checks before they are exploited.
4. As a backend developer, I want the plugin to identify "API Contract Mismatches" across polyglot services (e.g., Go to Node.js), so that I can catch silent breaking changes in payload schemas before deployment.
5. As a system reliability engineer, I want the plugin to trace event-driven workflows to detect "Missing Compensation Logic" in distributed sagas, so that I can prevent corrupted system states.
6. As a performance engineer, I want the plugin to map event publishers and subscribers to identify "Event-Driven Infinite Loops," so that I can prevent thundering herd resource exhaustion.
7. As a user of the plugin, I want the system to automatically block naive, context-busting commands (like `cat` or `grep -r` on large directories), so that my LLM session does not crash or waste tokens.
8. As a user, I want the plugin to spawn parallel, isolated subagents to investigate specific high-risk paths concurrently, so that analysis time scales efficiently with monorepo size.
9. As a reviewer of the plugin's output, I want the final bug report to be validated against global middleware configurations, so that I am not alerted to false positives (e.g., a missing check that is actually handled by a global interceptor).
10. As a maintainer, I want all subagent outputs to be strictly bounded to a predefined JSON schema, so that the main agent's context window remains clean and predictable.
11. As a developer integrating this into my workflow, I want the plugin to be compatible with both Claude Code and OpenCode host environments, so that my team can use their preferred AI coding assistant.

## Implementation Decisions

### 1. Architectural Decisions: The 4-Phase Hierarchical Protocol
The plugin will strictly enforce a 4-phase workflow, preventing the LLM from deviating into unstructured exploration.
*   **Phase 1: MAP (Level 1)**: A lightweight, 2-pass heuristic scan. It identifies module boundaries (via `go.mod`, `package.json`, etc.) and maps edges using a **3-Tier Signal Weighting** model:
    *   *Tier 1 (Strong)*: IDL matches (`.proto`, `.graphql`), event schemas, IaC network/IAM linkages.
    *   *Tier 2 (Medium)*: Shared internal packages, standard service discovery routing patterns.
    *   *Tier 3 (Weak)*: Presence of generic orchestration libraries (`amqplib`, `requests`).
*   **Phase 2: TRACE (Level 2)**: A deterministic **Contract-Key Resolution Engine**. Instead of attempting monolithic cross-language AST parsing, the tool extracts "Entry/Exit Points" and maps them to universal keys (e.g., `grpc://auth.UserService/ValidateToken`). It extracts both the `payload_sent` (caller) and `payload_expected` (callee) to flag schema mismatches deterministically.
*   **Phase 3: DELEGATE (Level 3)**: The Main Agent spawns parallel, isolated subagents. Each subagent is given *only* the specific file paths and a targeted bug hypothesis for a single suspicious path. Subagents must use RLM sandboxed execution (`rlm_execute`, `rlm_search`) and are forbidden from reading raw files directly.
*   **Phase 4: SYNTHESIZE**: A **Challenge-Response Validation Loop**. Before reporting a bug, the Main Agent performs a targeted `rlm_search` for global middleware/interceptors. It logically evaluates if the global handler covers the reported vulnerable path. If yes, it is marked a False Positive and discarded.

### 2. Module Interfaces & API Contracts
The core of the Level 2 Trace phase relies on a strict JSON schema for the "Stitched Graph" to ensure the LLM can reliably parse polyglot boundaries. 

*Schema Prototype (Decision-Rich Snippet):*
```json
{
  "boundaries": [
    {
      "contract_key": "grpc://auth.UserService/ValidateToken",
      "caller": {
        "service": "payments",
        "language": "node",
        "payload_sent": {"user_id": "string", "token": "string"}
      },
      "callee": {
        "service": "auth",
        "language": "go",
        "payload_expected": {"userId": "string", "token": "string"}
      },
      "deterministic_flag": "FIELD_NAME_MISMATCH: 'user_id' vs 'userId'"
    }
  ]
}
```

### 3. Plugin Shell & Interception (Hooks)
*   **PreToolUse Interception**: Hooks will listen for `Read`, `Bash`, and `WebFetch` tool calls.
*   **Silent Rewriting**: If a `Read` or `Bash` targets a directory or file exceeding a safe threshold (e.g., >5KB or recursive listing), the hook mutates the `updatedInput` to execute a bounded Python metadata/script via `rlm_execute` instead. The LLM never sees the raw file read attempt.

### 4. MCP Toolset Extensions
The existing `rlm-skill` MCP server will be extended with orchestration-specific tools:
*   `generate_module_map`: Executes the Level 1 2-pass heuristic.
*   `extract_contract_graph`: Executes the Level 2 Tree-sitter-based Contract-Key extraction on specified directories.
*   `trace_orchestration_path`: A utility to resolve the file paths connecting two known Contract Keys.

## Testing Decisions

### What Makes a Good Test
Tests must validate **external behavior and deterministic guarantees**, not LLM prompt internal states. We test the tools and the protocol enforcement, not the LLM's "creativity."

### Modules to be Tested
1.  **Level 1 Heuristic Script**: Unit tests verifying that given a mock monorepo structure, it correctly identifies Tier 1, 2, and 3 edges without reading source code contents.
2.  **Level 2 Tree-Sitter Extractors**: Unit tests for the specific language parsers (Go, Node.js, Python) ensuring they correctly extract the `contract_key`, `payload_sent`, and `payload_expected` from predefined code snippets.
3.  **Hook Interceptors**: Integration tests simulating an LLM attempting to `Read` a 10MB file, verifying the hook successfully intercepts and rewrites it to an `rlm_execute` call.
4.  **Subagent Output Schema**: Validation tests ensuring that mocked subagent outputs strictly conform to the required bounded JSON schema, rejecting any markdown or conversational filler.

### Prior Art
*   We will mirror the testing strategy of the base `rlm-skill` repository, utilizing mock filesystems (`pyfakefs` or similar) for the Python MCP tools and snapshot testing for the JSON schema outputs.

## Out of Scope
*   **Dynamic Runtime Monitoring**: The plugin will not attach to running processes, monitor live memory/CPU, or track real-time agent message loops. It is strictly a static analyzer.
*   **Full Monolithic AST Parsing**: We will not attempt to build a single, unified Global Program Dependence Graph for the entire repository. 
*   **Infrastructure Deployment Validation**: While IaC (Terraform/K8s) is used as a *signal anchor* (Tier 1 Strong Edge) to understand network topology, the plugin will not validate the correctness of the IaC itself (tools like Checkov or tfsec already do this).
*   **Automated Code Fixes**: The plugin will detect, synthesize, and report bugs with high precision, but will not automatically generate or apply PRs to fix them (this is left to the developer's discretion).

## Further Notes
*   **ML Beginner Accessibility**: This architecture is deliberately designed to be highly accessible. The LLM is treated strictly as a "Project Manager" and "Interpreter." It writes simple, bounded Python scripts and reads their short, deterministic outputs. The heavy computational lifting (parsing, searching, graph building) is handled by traditional, deterministic code. This drastically reduces the surface area for LLM hallucination and makes the system highly debuggable.
*   **Polyglot Agnosticism**: Because Level 1 relies on file markers and Level 2 relies on normalized Contract Keys, adding support for a new language (e.g., Rust or Java) only requires adding a new Tree-sitter query file and a `Cargo.toml`/`pom.xml` marker to Level 1. The core orchestration logic remains untouched.
*   **Next Action**: Upon approval of this PRD, development will commence with the drafting of the Architecture Decision Record (ADR) to formally lock this design, followed by the implementation of the Level 1 `generate_module_map` Python script.