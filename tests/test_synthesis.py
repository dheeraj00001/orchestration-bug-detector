import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.synthesis import SynthesisEngine

def test_synthesis_engine_filters_false_positive(tmp_path):
    # ARRANGE: 
    # 1. Subagent finding: "Missing auth in checkout.ts"
    finding = {
        "anomaly_id": "ANOM-001",
        "file": "services/payments/checkout.ts",
        "bug_type": "MISSING_AUTH",
        "details": "Function process() lacks validateToken call.",
        "severity": "high"
    }

    # 2. Mock RLM Search results: A global gateway handles it
    mock_rlm_results = [
        {"file": "infra/gateway.yaml", "content": "type: AuthGateway; enabled: true;"}
    ]

    engine = SynthesisEngine()
    output_dir = tmp_path / "results"

    # ACT
    report = engine.synthesize([finding], mock_rlm_results, output_dir=str(output_dir))

    # ASSERT: Finding is suppressed because infrastructure gateway exists
    assert len(report["findings"]) == 1
    f = report["findings"][0]
    assert f["anomaly_id"] == "ANOM-001"
    assert f["status"] == "suppressed"
    assert f["suppression_layer"] == "infrastructure"

    # Assert files are created in output_dir
    assert os.path.exists(output_dir / "report.md")
    assert os.path.exists(output_dir / "final_anomalies.json")

if __name__ == "__main__":
    pytest.main([__file__])
