import sys
import os

# Add scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.dre import DeterministicRuleEngine
from scripts.synthesizer import DeterministicSynthesizer

def test_repro_bug04():
    print("\n--- Testing BUG-04: Silent Suppression of Missing Anchors ---")
    dre = DeterministicRuleEngine()
    
    # Boundary with missing anchor and weak candidate
    boundary = {
        "anchor_status": "absent",
        "payload_match": True,
        "is_strong_candidate": False,
        "contract_key": "services/auth#Validate"
    }
    
    classification = dre.classify(boundary)
    print(f"Classification for weak missing anchor: {classification}")
    
    # Current behavior: returns MATCHED
    # Expected behavior: returns WEAK_MATCH
    if classification == "MATCHED":
        print("FAIL: BUG-04 reproduced. Weak missing anchor is masked as MATCHED.")
        return False
    elif classification == "WEAK_MATCH":
        print("SUCCESS: BUG-04 not present or fixed. Weak missing anchor is WEAK_MATCH.")
        return True
    else:
        print(f"UNEXPECTED: Returned {classification}")
        return False

def test_repro_arch03():
    print("\n--- Testing ARCH-03: Synthesizer Quarantine Trap ---")
    synth = DeterministicSynthesizer()
    
    # 1. Finding missing severity and classification
    finding1 = {
        "anomaly_id": "insight:1",
        "notes": "Important architectural observation",
        "evidence_paths": ["services/auth/client.ts"]
    }
    
    # 2. General insight finding
    finding2 = {
        "type": "general_insight",
        "title": "High fan-out hub",
        "description": "services/auth has many callers",
        "affected_modules": ["services/auth"],
        "severity": "info",
        "evidence": {"call_count": 12}
    }
    
    findings = [finding1, finding2]
    result = synth.synthesize(findings)
    
    valid_ids = [f.get("anomaly_id") or f.get("title") for f in result["valid"]]
    quarantine_reasons = [q["reason"] for q in result["quarantine"]]
    
    print(f"Valid findings: {valid_ids}")
    print(f"Quarantine reasons: {quarantine_reasons}")
    
    bug_repro = False
    
    if any(q["reason"] == "missing_required_fields" for q in result["quarantine"]):
        print("FAIL: ARCH-03 reproduced. Finding missing severity/classification was quarantined.")
        bug_repro = True
    
    # Check if finding2 was preserved (it should have classification 'general_insight' or be wrapped)
    if not any(f.get("type") == "general_insight" or f.get("classification") == "general_insight" for f in result["valid"]):
         # If it's in quarantine, that's also a failure
         if any(q.get("raw", {}).get("type") == "general_insight" for q in result["quarantine"]):
             print("FAIL: ARCH-03 reproduced. general_insight was quarantined.")
             bug_repro = True

    if not bug_repro:
        print("SUCCESS: ARCH-03 not present or fixed.")
        return True
    return False

if __name__ == "__main__":
    b04_ok = test_repro_bug04()
    a03_ok = test_repro_arch03()
    
    if not b04_ok or not a03_ok:
        sys.exit(1)
    sys.exit(0)
