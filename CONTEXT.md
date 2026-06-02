Context: Large‑Giant Orchestration Bug Detector
Purpose
This context is a glossary for the language of the large‑giant orchestration bug detector project. It captures the canonical terms used to discuss boundaries, evidence, anomalies, and verification in a polyglot monorepo.

Glossary
Application-Level Orchestration
The flow of data and control between distinct services, modules, or event-driven components.

Anchor-First Validation
A boundary-checking approach that treats a shared contract anchor as the highest-confidence source of truth when both sides resolve to the same version or hash.

Anchor Drift
A condition where the caller and callee appear aligned, but the anchor is stale, version-skewed, or otherwise out of sync with the resolved usage.

Canonical Normalization
A deterministic field-name normalization used when no shared anchor exists. It involves lowercasing characters, stripping underscores, and collapsing camelCase boundaries. To prevent false negatives from lossy collisions, it verifies 1-to-1 mapping; if multiple distinct fields normalize to the same string, the engine falls back to case-insensitive exact matching for those specific colliding fields.

Confirmed Edge
A high-confidence link between two modules established when a contract anchor is paired with strong usage evidence on both sides of the boundary.

Contract Anchor
A static artifact such as an IDL file, OpenAPI spec, proto definition, or IaC resource that defines a potential service boundary or communication protocol.

Contract Mismatch
A boundary anomaly where the caller and callee do not agree after normalization or schema comparison.

Deterministic Rule Engine
A deterministic rule set that classifies resolved contract evidence into stable anomaly categories.

Event-Driven Loop
A feedback cycle in which one event triggers another in a way that can amplify load or repeat indefinitely.

Guardrail Assertion
A test assertion that checks the system avoided forbidden or unsafe operations.

High-Signal Usage Evidence
Concrete code patterns that confirm active use of a contract, such as caller-side client usage and callee-side endpoint registration.

Hierarchical Evidence Chain
A deterministic way to resolve cross-cutting concerns by checking evidence across middleware layers in a fixed priority order where broader scopes suppress narrower scopes: (1) infrastructure-level anchors (highest precedence), (2) shared platform middleware, and (3) local service middleware (lowest precedence).

Host Adapter
The shared abstraction used to talk to a host environment without embedding host-specific branching logic in the analysis flow.

Missing Anchor
A boundary anomaly where strong usage evidence exists but no usable contract anchor can be found.

Orchestration Bug
A defect that emerges from the interaction between services or components and is typically invisible to local linters.

Performance Budget
Strict execution limits enforced per run to prevent context exhaustion, consisting of a global tool-call limit for the main agent's orchestration phases and a separate, isolated tool-call limit for each spawned subagent.

Prioritized Digest
A compact anomaly set containing the highest-priority findings for follow-up.

Semantic Downsampling
The process of turning large source artifacts into structural summaries that preserve the parts needed for boundary analysis while discarding unrelated detail.

Structural Verification
The follow-up step in which a subagent checks a prioritized anomaly using bounded evidence only.

Strong Edge Candidate
A boundary with high-signal usage evidence on both sides that has not yet been confirmed by a usable contract anchor. During zonal scoping, these candidates are explicitly followed up to distance 2 to ensure the Deterministic Rule Engine can evaluate them for `MISSING_ANCHOR` classification.

Synthesis
The deterministic merging phase where subagent outputs are de-duplicated by `anomaly_id`. When multiple subagents report on the same anomaly, the finding with the highest severity is retained, and all distinct `evidence_paths` are merged into a single, deduplicated list to preserve complete evidence.

Terminal Assertion
A test assertion that checks the final user-visible result.

Tier 1 Edge
A confirmed edge with a contract anchor and high-signal usage evidence on both sides.

Tier 2 Edge
A potential edge based on shared internal packages or standard service-discovery patterns, without full confirmation.

Tier 3 Edge
An edge inferred only from weak orchestration-library signals.

Zonal Scoping
A bounded analysis approach that starts from a seed service and explores only nearby neighbors to prevent context bloat.

Zone Overload
A state returned when the bounded analysis zone would exceed the configured node cap. Recovery involves sequentially reducing `max_distance` and applying explicit Tier-based pruning at distance 1 (dropping Tier 3, then Tier 2 edges) before halting expansion and requesting user intervention.
