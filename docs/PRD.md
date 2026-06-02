Product Requirements Document (PRD): Large‑Giant Orchestration Bug Detector Plugin

Problem Statement
As a developer or architect working in a large‑giant polyglot monorepo, I need a way to detect orchestration bugs that do not show up in local, file-by-file analysis. These include API contract mismatches, missing saga compensation, authorization boundary leaks, and event-driven infinite loops.
The failure mode today is not just low signal. It is context collapse: naïve LLM-assisted code review attempts to read too much of the repository at once, exhaust context windows, and return brittle or hallucinated judgments. I need a static analysis system that is deterministic, bounded, and able to reason across modules without turning the LLM into a raw-file parser.

Solution
We will build an LLM-Orchestrated Static Codebase Analyzer plugin that uses deterministic tooling for discovery, graph construction, and anomaly classification, while reserving the LLM for planning, hypothesis selection, bounded script generation, and report synthesis.
The system will:
- discover service boundaries and contract anchors;
- build a scoped dependency graph around a seed service;
- classify likely orchestration bugs with a deterministic rule engine;
- downsample large source artifacts into structural summaries instead of raw content;
- spawn bounded subagents only for prioritized anomalies; and
- produce a final human-readable report with stable identifiers and traceable evidence.
The design is intentionally layered so that the system can scale to large repositories without requiring global raw-file ingestion.

User Stories
1. As a developer, I want the plugin to generate a high-level module map of my monorepo, so that I can understand service boundaries without manual exploration.
2. As an architect, I want the plugin to prioritize contract anchors such as IDL and IaC artifacts, so that analysis follows declared boundaries instead of incidental file structure.
3. As a security engineer, I want the plugin to detect authorization boundary leaks, so that internal endpoints without proper checks are surfaced before exploitation.
4. As a backend developer, I want the plugin to identify API contract mismatches across polyglot services, so that breaking payload changes are caught before deployment.
5. As a reliability engineer, I want the plugin to trace event-driven workflows and identify missing compensation logic, so that corrupted distributed state is prevented.
6. As a performance engineer, I want the plugin to map publishers and subscribers and detect event-driven loops, so that cascading load amplification is prevented.
7. As a user of the plugin, I want the system to block naïve context-busting commands on large directories, so that the session remains stable and token-efficient.
8. As a user, I want the plugin to delegate high-risk subpaths to isolated subagents, so that analysis can proceed in parallel without contaminating the main context.
9. As a reviewer, I want the final bug report to be checked against global middleware and shared infrastructure rules, so that I am not alerted to false positives that are actually handled centrally.
10. As a maintainer, I want subagent outputs to follow a strict JSON schema with a typed anomaly buffer, so that the main agent can absorb unknown findings without losing structure.
11. As a developer integrating this into my workflow, I want the plugin to work in both Claude Code and OpenCode host environments, so that my team can use the same analyzer in different assistants.
12. As a maintainer, I want the system to distinguish confirmed edges from candidate edges, so that missing-anchor cases are handled consistently instead of being classified against impossible prerequisites.
13. As a reviewer, I want evaluation to use explicit pass/fail thresholds, so that flakiness is measured instead of argued about.
14. As an architect, I want the analyzer to prefer deterministic evidence over LLM interpretation, so that the same repository state produces the same anomaly set.

Implementation Decisions

1. Architectural Decisions: The 4-Phase Hierarchical Protocol
The plugin will enforce a 4-phase workflow that keeps the analysis bounded and deterministic.

Phase 1: MAP (Zonal Discovery)
The analyzer performs a lightweight two-pass scan to identify modules, contract anchors, and edges.
- Pass 1 — Discovery: The analyzer traverses the repository using bounded tree exploration to identify module roots, locate contract anchor files (IDL, OpenAPI, proto, IaC), and record declared dependency edges from package manifests and import graphs. Pass 1 produces a raw node list and a raw edge list; edges at this stage carry no tier score.
- Pass 2 — Scoring: The analyzer revisits each raw edge and applies the tier-scoring rules. For each edge it checks for caller-side and callee-side high-signal usage evidence. An edge is promoted to Tier 1 only when a contract anchor is paired with high-signal usage evidence on both sides. All other edges remain at Tier 2 or Tier 3 according to the strength of their available signals. Pass 2 outputs the scored adjacency list that Phase 2 consumes.
- Contract anchors are static artifacts such as IDL files or IaC resources that define a potential boundary.
- Edge strength is scored in three tiers:
  - Tier 1 (Strong / Confirmed Edge): a contract anchor plus high-signal usage evidence on both sides of the boundary.
  - Tier 2 (Medium): shared internal packages or standard service-discovery patterns without full high-signal confirmation.
  - Tier 3 (Weak): generic orchestration-library signals with no stronger evidence.
- Dependency declarations alone never promote an edge to Tier 1.
- The MAP phase outputs an adjacency list and a seed-centered impact zone request.
- The MAP phase accepts `seed_service` and `max_distance` as inputs to define the initial zone.

Phase 2: TRACE (Zonal Contract Resolution)
The analyzer resolves contract evidence only inside the impact zone.
- Default `max_distance` is 2.
- Default `max_nodes` is 30.
- Tier-based pruning rules:
  - follow Tier 1 edges up to distance 2;
  - follow Tier 2 and Tier 3 edges only at distance 1, **except when a Tier 2 or Tier 3 edge exhibits high-signal usage evidence on both the caller and callee sides. In this specific case, it is treated as a "strong candidate" and followed up to distance 2 to ensure the DRE can evaluate it for `MISSING_ANCHOR` classification.**
  - stop expanding once the node cap is reached.
- Tier boundary behavior: the tier of a traversal step is determined by the edge being crossed, not by the path taken to reach the source node. Distance is always measured from the seed service. When a node is reachable at distance 1 via a Tier 2 edge, any Tier 1 edges departing that node are still evaluated against the Tier 1 distance limit (≤ 2). Because those edges lead to distance-2 nodes they are within the Tier 1 limit and are followed. The incoming path's tier does not restrict outgoing edge traversal.
- If the zone would exceed `max_nodes`, the analyzer returns a `ZONE_OVERLOAD` result instead of widening scope silently.
- ZONE_OVERLOAD recovery: when `ZONE_OVERLOAD` is returned, the main agent reduces `max_distance` by 1 sequentially (e.g., from 5 to 4, 3, 2, 1) and retries `extract_zonal_graph`. If `ZONE_OVERLOAD` persists at `max_distance: 1`, the main agent applies **explicit Tier-based pruning at distance 1 (dropping Tier 3 edges first, then Tier 2 if necessary)** to bring the node count under `max_nodes`. If the overload still persists after maximum pruning at distance 1, the main agent halts expansion and presents the user with the overloaded zone size, the seed service, and a request to supply a narrower seed or to explicitly increase `max_nodes`. The main agent must not silently widen scope or silently drop nodes to work around the cap without applying this explicit pruning fallback first.
- Anchor-first validation means that if caller and callee resolve to the same contract anchor version or hash, the boundary is treated as schema-aligned and payload extraction is skipped.
- When no shared anchor exists, the analyzer falls back to canonical payload comparison.

Phase 3: DRE & DIGEST (Deterministic Classification)
A deterministic rule engine classifies the resolved graph and writes results into two outputs:
- `top_anomalies.json` for prioritized follow-up; and
- `all_anomalies.json` for the full audit trail.
- Canonical normalization: when no shared anchor exists, field names are normalized before comparison by: (1) lowercasing all characters; (2) stripping all underscores; and (3) collapsing camelCase boundaries by replacing each uppercase letter with its lowercase equivalent without inserting a separator. Under this rule, `user_id`, `userId`, and `UserID` all normalize to `userid`. **However, to prevent false negatives from lossy collisions (e.g., a payload containing both `user_id` and `userid`, or `f_i_r_s_t_n_a_m_e` erroneously matching `firstname`), the engine must first verify 1-to-1 mapping. If multiple distinct fields in either the caller or callee payload normalize to the identical string, the engine abandons underscore-stripping for those specific colliding fields and falls back to case-insensitive exact matching. If they still do not match, it constitutes a `CONTRACT_MISMATCH`.** Only fields whose normalized forms differ (and do not suffer from ambiguous 1-to-many collisions) constitute a mismatch.
- Classification rules are:
  - `MATCHED`: caller usage, callee usage, and anchor all align; or both sides resolve to the same anchor version/hash and no additional drift signal exists.
  - `ANCHOR_DRIFT`: caller usage and callee usage align with each other, but diverge from the anchor or the anchor metadata is stale or outdated. `ANCHOR_DRIFT` is informational by default and is promoted to high priority when either of the following deterministic conditions is met:
    - Staleness: the anchor's recorded version is more than one minor version behind the current resolved version, or the anchor file's recorded hash does not match the hash present in the repository at analysis time.
    - Security sensitivity: the `contract_key` begins with one of the configurable security-sensitive namespace prefixes. The default prefix set is: `auth`, `authz`, `payment`, `billing`, `iam`, `rbac`. This set is configurable via plugin settings.
  - `CONTRACT_MISMATCH`: caller usage and callee usage diverge after canonical normalization or schema comparison. This is the highest-priority contract anomaly.
  - `MISSING_ANCHOR`: a strong-edge candidate has high-signal usage evidence but no anchor artifact can be found. This is not a Tier 1 edge; it is a failed confirmation state that needs investigation.
- Classification precedence when multiple conditions are satisfied: when a boundary has no anchor (`anchor_status: "absent"`) and payload fields also diverge after canonical normalization, the boundary is classified as `CONTRACT_MISMATCH`. `MISSING_ANCHOR` applies only when no independent payload divergence can be detected — that is, when the absence of an anchor is the sole reason classification cannot be completed.
- Digest selection rules are explicit:
  - include all `CONTRACT_MISMATCH` findings;
  - include `MISSING_ANCHOR` findings when the candidate edge has confirmed high-signal usage evidence on both the caller side and the callee side — meaning it would qualify as a Tier 1 edge if an anchor were present — and the anchor is absent; suppress `MISSING_ANCHOR` findings for Tier 2 or Tier 3 candidate edges unless the user requests exhaustive audit mode;
  - include `ANCHOR_DRIFT` findings when the anchor is stale, version-skewed, or touches a security-sensitive boundary as defined by the deterministic priority-escalation rules above;
  - suppress `MATCHED` findings.

Phase 4: DELEGATE & SYNTHESIZE (Structural Verification)
The main agent spawns isolated subagents only for anomalies present in the prioritized digest, or when the user explicitly drills down.
- Subagents receive:
  - the anomaly identifier;
  - the relevant file paths;
  - a bounded hypothesis; and
  - any resolved anchor metadata.
- Subagents are not allowed to read raw large files directly. Instead, they rely on bounded structural views:
  - structural skeletons for large files;
  - function-only extraction when body inspection is necessary; and
  - line-bounded reads as a fallback.
- Subagent outputs must stay within the fixed JSON schema defined in Section 2 and may include the typed `notes` field for unknowns that are not yet classifiable.
- Synthesis: after all delegated subagents complete, the main agent performs a deterministic merge of their outputs:
  - De-duplicate by `anomaly_id`. Where two subagents report findings on the same `anomaly_id`, retain the finding with the higher `severity`; if severity is equal, **merge the `evidence_paths` arrays from all contributing subagents into a single, deduplicated list to preserve all distinct evidence**, and retain the finding with the most comprehensive `notes`.
  - Apply interception suppression. For each surviving finding, call `check_interception_chain`. If the chain confirms the concern is handled at a higher-precedence middleware layer, set `status` to `suppressed` and record the suppression reason in `notes`.
  - Sort for stability. Order surviving findings by `severity` descending (critical → informational), then by `anomaly_id` ascending as a tiebreaker.
  - Render the report. Convert the sorted finding list into a Markdown report. Each finding entry must include: the anomaly identifier, severity, evidence paths, and a one-sentence plain-English description. Write the report to `report.md` and the merged JSON to `final_anomalies.json`.
- Synthesis is deterministic: the same subagent output set always produces the same merged result and the same report.

2. Module Interfaces & API Contracts
The core trace phase consumes a strict JSON contract graph.

Contract graph schema — boundary entry example:
{
   "boundaries": [
    {
       "contract_key": "grpc://auth.UserService/ValidateToken",
       "caller": {
         "service": "payments",
         "language": "node",
         "payload_sent": { "user_id": "string", "auth_token": "string" }
      },
       "callee": {
         "service": "auth",
         "language": "go",
         "payload_expected": { "userId": "string", "access_token": "string" }
      },
       "has_shared_idl": false,
       "anchor_status": "absent",
       "dre_status": "CONTRACT_MISMATCH"
    }
  ]
}
In this example: `user_id` (caller) and `userId` (callee) both normalize to `userid` and therefore match. `auth_token` normalizes to `authtoken` and `access_token` normalizes to `accesstoken`; these differ, so the boundary is classified as `CONTRACT_MISMATCH`. Because `anchor_status` is `absent` and payload divergence is independently detectable, `CONTRACT_MISMATCH` takes precedence over `MISSING_ANCHOR` per the classification-precedence rule above.

`anchor_status` values and their interaction with `has_shared_idl`:
| anchor_status | Meaning | Valid `has_shared_idl` values |
| --- | --- | --- |
| present | Anchor exists and its recorded hash matches the current repository state | true or false |
| stale | Anchor exists but its recorded hash does not match the current repository state | false only |
| version_mismatch | Anchor exists on both sides but the two sides resolve to different anchor versions | false only |
| absent | No anchor artifact can be found | false only |

`anchor_status` is the authoritative field for classification. `has_shared_idl` is a derived convenience flag that must be `true` only when `anchor_status` is `present` and both sides resolve to the same anchor version or hash. In any conflict between the two fields, `anchor_status` takes precedence. The `ANCHOR_DRIFT` DRE state corresponds to `anchor_status: "stale"` or `anchor_status: "version_mismatch"` at the schema level.

Contract graph rules:
- `has_shared_idl: true` means the caller and callee both resolve to the same anchor version/hash, which requires `anchor_status: "present"`.
- `anchor_status` must be one of `present`, `stale`, `version_mismatch`, or `absent`.
- `dre_status` must be derived from deterministic comparison rules, not from freeform LLM judgment.
- Example data in the spec must never contradict the classifier semantics.

Subagent output schema:
Each subagent must return a single JSON object conforming to the following schema. The main agent rejects any output that does not validate against it.
{
   "$schema": "http://json-schema.org/draft-07/schema#",
   "type": "object",
   "required": ["anomaly_id", "severity", "classification", "evidence_paths", "status"],
   "additionalProperties": false,
   "properties": {
     "anomaly_id": {
       "type": "string",
       "description": "Stable identifier matching the entry in top_anomalies.json"
    },
     "severity": {
       "type": "string",
       "enum": ["critical", "high", "medium", "low", "informational"]
    },
     "classification": {
       "type": "string",
       "enum": ["CONTRACT_MISMATCH", "ANCHOR_DRIFT", "MISSING_ANCHOR", "MATCHED", "UNCLASSIFIED"]
    },
     "evidence_paths": {
       "type": "array",
       "items": { "type": "string" },
       "minItems": 1,
       "description": "Repository-relative paths to the files that support this finding"
    },
     "status": {
       "type": "string",
       "enum": ["confirmed", "suppressed", "needs_review"],
       "description": "'suppressed' means check_interception_chain resolved the concern at a higher-precedence middleware layer"
    },
     "notes": {
       "type": "object",
       "required": ["type", "value"],
       "additionalProperties": false,
       "properties": {
         "type": {
           "type": "string",
           "enum": ["payload_detail", "anchor_reference", "middleware_hint", "other"]
        },
         "value": {
           "type": "string",
           "minLength": 1,
           "description": "Free-form text elaborating on the finding; must be non-empty when present"
        }
      },
       "description": "Optional. The 'type' tag constrains interpretation; the 'value' field carries open-ended text. Use for findings that do not fit the main schema fields."
    }
  }
}

3. Plugin Shell & Interception
The plugin shell will intercept unsafe or unbounded tool calls and replace them with bounded alternatives where possible.
- A request to read a file larger than 5KB is rewritten to a structural skeleton request by default.
- A request for recursive directory exploration is rewritten to a bounded tree summary.
- If no bounded equivalent exists, the tool call is rejected with a diagnostic that names the safer alternative.
- Direct raw reads are allowed only when the file is already within safe size bounds or when the user explicitly drills down through a bounded function or line range.
- The interception layer must preserve user intent while preventing context exhaustion.

4. MCP Toolset Extensions
The MCP server will expose the following capabilities:
- `generate_module_map(seed_service, max_distance=2)` — returns the adjacency list for the requested zone.
- `extract_zonal_graph(seed_service, max_distance=2, max_nodes=30)` — returns the stitched graph or a `ZONE_OVERLOAD` error.
- `run_dre_rules(graph)` — returns the prioritized anomaly digest and writes the full anomaly list to disk.
- `rlm_skeleton(file, focus_symbol=None)` — returns a structural skeleton for a file, optionally focused on one symbol.
- `rlm_extract_function(file, function_name)` — returns the body of a single function when body-level inspection is necessary.
- `rlm_tree(path, max_depth=2)` — returns a bounded hierarchical summary.
- `check_interception_chain(contract_key)` — resolves middleware in a fixed priority order where broader scopes suppress narrower scopes: (1) **infrastructure-level anchors (e.g., API gateways, global service mesh) are checked first and take highest precedence**; (2) shared platform middleware is checked second; (3) **local service middleware is checked last**. A concern resolved at a higher-precedence (broader) layer suppresses the same concern from all lower-precedence (narrower) layers. The tool returns the layer at which the concern was resolved, or `unresolved` if no layer handles it.

Tool contract rules:
- each tool must have a stable input schema and stable error shape;
- bounded outputs are preferred over raw outputs;
- all overload conditions must fail closed and emit a machine-readable diagnostic.

5. Host Environment Compatibility
The plugin must operate correctly in both Claude Code and OpenCode host environments. This satisfies User Story 11.
- Shared abstraction layer: the plugin shell defines a `HostAdapter` interface with three methods: `call_tool(name, args)`, `stream_output(text)`, and `get_config(key)`. All four plugin phases interact exclusively through `HostAdapter`. No phase contains host-specific branching logic.
- Claude Code adapter: implements `HostAdapter` using the MCP tool-call protocol directly. Tool definitions are registered via the standard Claude Code MCP server manifest.
- OpenCode adapter: implements `HostAdapter` by mapping method calls to OpenCode's tool-invocation protocol. Tool definitions are registered via the OpenCode plugin manifest format. Any tool name or parameter that conflicts with an OpenCode reserved keyword is remapped via a configurable alias table declared in the adapter's configuration block.
- Configuration: host-specific settings — including manifest paths, alias tables, and protocol versions — are declared in `host_config.json` at the plugin root. The selected `HostAdapter` implementation reads this file at startup.
- Testing: the end-to-end eval suite includes one run against each host environment. User Story 11 is satisfied only when both runs pass the guardrail assertions and the golden terminal assertions defined in the Testing Decisions section.

Testing Decisions

What Makes a Good Test
A good test validates external behavior, deterministic protocol adherence, and boundary conditions. It should not assert on prompt phrasing, hidden chain-of-thought, or incidental implementation details.

Failure Classification
The following definitions govern how test failures are recorded and whether they block acceptance:
- Hard failure: an assertion that produces a structurally invalid result (missing required fields, wrong type, schema violation), that fails identically across all runs in an eval suite, or that causes an unrecoverable agent error. Hard failures always block acceptance.
- Flaky failure: an assertion that passes in at least one run but fails in at least one other run within the same eval suite. Flaky failures do not block acceptance on their own.
- Flakiness threshold: if the same assertion fails in 2 of 3 runs, it is reclassified as a hard failure and blocks acceptance. If it fails in exactly 1 of 3 runs, it is recorded as a flaky failure, assigned a stable tracking identifier, and excluded from the acceptance gate but must be investigated before the next eval cycle.

Modules to be Tested
- Scenario-based end-to-end evals: a known-bug monorepo fixture containing golden orchestration bugs and deliberate red herrings.
  - The final Markdown report must contain the exact anomaly identifiers listed in `golden_anomalies.json`.
  - The execution log must show zero unbounded raw file reads and zero recursive directory listings.
  - The agent must stay within the configured tool-call and wall-clock budgets (see Acceptance Thresholds below).
  - Stability is measured across three runs; hard failures and flaky failures are classified according to the definitions above.
- DRE unit tests: deterministic tests covering `MATCHED`, `ANCHOR_DRIFT`, `CONTRACT_MISMATCH`, and `MISSING_ANCHOR` against synthetic graphs, including cases where both `MISSING_ANCHOR` and `CONTRACT_MISMATCH` conditions are simultaneously satisfied to verify correct precedence.
- Structural downsampling tests: verify that structural skeletons preserve signatures, decorators, fields, and tags while staying under the size cap.
- Zonal pruning tests: verify `extract_zonal_graph` respects `max_distance`, `max_nodes`, and tier-based pruning rules, including the tier-boundary traversal behavior specified in Phase 2.
- Interception tests: verify unsafe tool calls are rewritten or rejected consistently.

Acceptance Thresholds
To remove ambiguity, the eval rules are explicit:
- Guardrail assertions must pass in all 3/3 runs.
- Deterministic unit and pruning tests must pass in all 3/3 runs.
- Golden end-to-end terminal assertions must pass in at least 2/3 runs.
- Any repeated failure pattern on the same assertion is treated as a regression, even if one run succeeded; see the Flakiness threshold rule above.
- Performance budgets (per run, not averaged across runs):
  - **Global Tool-call limit:** 40 tool calls for the main agent's Phase 1, 2, and 4 orchestration.
  - **Subagent Tool-call limit:** Each spawned subagent is allocated a strict, isolated budget of **3 tool calls** maximum. If a subagent exceeds this, it must synthesize its findings from the bounded inputs provided by the main agent without making further tool calls.
  - **Wall-clock limit:** 90 seconds per run (enforced globally). If the wall-clock limit is approaching, the main agent must halt further subagent delegation and synthesize a report from completed subagents and the DRE digest.
- Both limits are configurable via plugin settings and are enforced independently per run.

Prior Art
The testing strategy follows the base `rlm-skill` repository pattern:
- use fake filesystem-backed MCP tools where appropriate;
- snapshot JSON outputs for deterministic artifacts; and
- prefer stable terminal assertions over brittle call-sequence assertions.

Out of Scope
- Dynamic runtime monitoring: the plugin will not attach to live processes, inspect runtime memory, or trace live CPU usage.
- Full monolithic AST graphing: the plugin will not build a single global program-dependence graph for the entire repository.
- Infrastructure deployment validation: IaC is used as a signal anchor, not as a target for deployment correctness checks.
- Automated code fixes: the plugin reports bugs but does not generate pull requests or patch code.
- IDL semantic validation: the plugin does not prove that the IDL itself is semantically correct.
- Internet-scale dependency analysis: the plugin only analyzes what is inside the repository and its configured inputs.

Further Notes
- The LLM acts as a project manager and interpreter, not as the source of truth for code semantics.
- Adding a new language should require only a new Tree-sitter query set and a small discovery marker update.
- The next implementation step is to lock the design in an ADR and implement the Level 1 `generate_module_map` path first.
