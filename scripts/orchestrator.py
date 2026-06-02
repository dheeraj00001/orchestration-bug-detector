from typing import List, Dict

class SubagentOrchestrator:
    """
    Identifies high-risk paths from the stitched graph and generates targeted 
    task payloads for parallel subagents.
    """

    def plan_subagent_tasks(self, stitched_graph: Dict) -> List[Dict]:
        tasks = []

        for boundary in stitched_graph.get("boundaries", []):
            if boundary.get("status") == "MISMATCH_DETECTED":
                caller = boundary["caller"]
                callee = boundary["callee"]
                flag = boundary["deterministic_flag"]

                # Generate a hypothesis for the subagent
                hypothesis = f"Verify if the callee service '{callee['service']}' correctly handles the payload mismatch identified by the deterministic engine: {flag}."

                tasks.append({
                    "target_service": callee["service"],
                    "hypothesis": hypothesis,
                    "context_files": [caller["file"], callee["file"]],
                    "contract_key": boundary["contract_key"]
                })

        return tasks
