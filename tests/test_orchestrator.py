import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.orchestrator import SubagentOrchestrator

def test_orchestrator_generates_tasks_for_mismatches():
    # ARRANGE: A stitched graph with one mismatch
    stitched_graph = {
        "boundaries": [
            {
                "contract_key": "grpc://auth.server/ValidateToken",
                "caller": {"service": "payments", "file": "checkout.ts", "language": "node", "payload_shape": {"user_id": "string"}},
                "callee": {"service": "auth", "file": "auth.go", "language": "go", "payload_shape": {"UserId": "string"}},
                "deterministic_flag": "FIELD_NAME_MISMATCH: 'user_id' vs 'UserId'",
                "status": "MISMATCH_DETECTED"
            }
        ]
    }

    orchestrator = SubagentOrchestrator()

    # ACT
    tasks = orchestrator.plan_subagent_tasks(stitched_graph)

    # ASSERT: One task generated
    assert len(tasks) == 1
    task = tasks[0]
    
    assert task["target_service"] == "auth"
    assert "UserId" in task["hypothesis"]
    assert "checkout.ts" in task["context_files"]
    assert "auth.go" in task["context_files"]

if __name__ == "__main__":
    pytest.main([__file__])
