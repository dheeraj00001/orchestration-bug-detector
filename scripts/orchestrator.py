from typing import List, Dict

class SubagentOrchestrator:
    """
    Implements Phase 4 delegation:
    - Identifies high-risk paths from the prioritized digest.
    - Generates targeted task payloads for subagents.
    - Enforces bounded hypotheses.
    """

    def plan_subagent_tasks(self, prioritized_digest: List[Dict]) -> List[Dict]:
        tasks = []

        for anomaly in prioritized_digest:
            # Subagents receive: anomaly_id, file paths, hypothesis, anchor metadata
            aid = anomaly["anomaly_id"]
            paths = []
            
            caller = anomaly.get("caller")
            if caller and "file" in caller:
                paths.append(caller["file"])
            
            callee = anomaly.get("callee")
            if callee and "file" in callee:
                paths.append(callee["file"])

            # Bounded hypothesis based on classification
            classification = anomaly.get("dre_status", "UNCLASSIFIED")
            hypothesis = f"Verify {classification} for anomaly {aid}. Check for missing orchestration logic or contract drift."
            
            if classification == "CONTRACT_MISMATCH":
                hypothesis = f"Verify payload mismatch for {aid}. Confirm if field mapping is truly broken or handled via local transformation."
            elif classification == "MISSING_ANCHOR":
                hypothesis = f"Locate missing contract anchor for {aid}. Search for undeclared IDL or implicit documentation."

            tasks.append({
                "anomaly_id": aid,
                "evidence_paths": paths,
                "hypothesis": hypothesis,
                "anchor_metadata": anomaly.get("anchor_metadata", {}),
                "severity": anomaly.get("severity", "medium")
            })

        return tasks
