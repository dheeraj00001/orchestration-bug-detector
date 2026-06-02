# Context: Large-Giant Orchestration Bug Detector

## Glossary

### Application-Level Orchestration
The flow of data and control between distinct services, modules, or event-driven components. This contrasts with Infrastructure-Level Orchestration (K8s/Terraform).

### Orchestration Bug
A defect emerging from the interaction between services, typically invisible to local linters. Examples include API contract mismatches, missing compensation logic in Sagas, authorization boundary leaks, and event-driven infinite loops.

### Semantic Call Graph (CloudPG Lite)
A unified, JSON-represented map of API routes, exported functions, and event-driven pub/sub relationships extracted from a codebase via deterministic tools (e.g., tree-sitter).

### 4-Phase Orchestration Protocol
The execution lifecycle for analysis:
1. **MAP**: Generate the high-level semantic call graph.
2. **HYPOTHESIZE**: Identify high-risk cross-module paths.
3. **DELEGATE & TRACE**: Spawn parallel subagents to verify specific bug hypotheses on isolated paths.
4. **SYNTHESIZE**: Aggregate findings into a unified report.

### Silent Interceptor (Hook)
A mechanism that intercepts generic, high-volume LLM actions (like recursive grep) and redirects them to specialized, deterministic orchestration tools to preserve context efficiency.
