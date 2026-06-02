import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.synthesis import SynthesisEngine

def test_synthesis_engine_filters_false_positive():
    # ARRANGE: 
    # 1. Subagent finding: "Missing auth in checkout.ts"
    finding = {
        "file": "services/payments/checkout.ts",
        "bug_type": "MISSING_AUTH",
        "details": "Function process() lacks validateToken call."
    }

    # 2. Mock RLM Search results: A global middleware exists
    mock_rlm_results = [
        {"file": "services/payments/server.ts", "content": "app.use(authMiddleware);"}
    ]

    engine = SynthesisEngine()

    # ACT
    report = engine.synthesize([finding], mock_rlm_results)

    # ASSERT: Finding is filtered out because middleware exists
    assert len(report["valid_bugs"]) == 0
    assert len(report["false_positives"]) == 1
    assert report["false_positives"][0]["reason"] == "GLOBAL_MIDDLEWARE_PROTECTION"

if __name__ == "__main__":
    pytest.main([__file__])
