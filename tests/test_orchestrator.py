import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.orchestrator import SubagentOrchestrator

def test_orchestrator_generates_tasks_for_mismatches():
    # ARRANGE: A list of prioritized anomalies (digests)
    prioritized_digest = [
        {
            "anomaly_id": "ANOM-001",
            "contract_key": "grpc://auth.server/ValidateToken",
            "caller": {"service": "payments", "file": "checkout.ts", "language": "node", "payload_shape": {"user_id": "string"}},
            "callee": {"service": "auth", "file": "auth.go", "language": "go", "payload_shape": {"UserId": "string"}},
            "dre_status": "CONTRACT_MISMATCH",
            "severity": "high"
        }
    ]

    orchestrator = SubagentOrchestrator()

    # ACT
    tasks = orchestrator.plan_subagent_tasks(prioritized_digest)

    # ASSERT: One task generated
    assert len(tasks) == 1
    task = tasks[0]
    
    assert task["anomaly_id"] == "ANOM-001"
    assert "payload mismatch" in task["hypothesis"]
    assert "checkout.ts" in task["evidence_paths"]
    assert "auth.go" in task["evidence_paths"]
    assert task["severity"] == "high"

if __name__ == "__main__":
    pytest.main([__file__])
