import pytest
from scripts.dre import DeterministicRuleEngine

def test_classify_contract_mismatch():
    dre = DeterministicRuleEngine()
    boundary = {
        "contract_key": "grpc://auth",
        "anchor_status": "absent",
        "payload_match": False,
        "is_strong_candidate": True
    }
    # CONTRACT_MISMATCH takes precedence over MISSING_ANCHOR
    assert dre.classify(boundary) == "CONTRACT_MISMATCH"

def test_classify_missing_anchor():
    dre = DeterministicRuleEngine()
    boundary = {
        "contract_key": "grpc://auth",
        "anchor_status": "absent",
        "payload_match": True,
        "is_strong_candidate": True
    }
    assert dre.classify(boundary) == "MISSING_ANCHOR"

def test_classify_anchor_drift_stale():
    dre = DeterministicRuleEngine()
    boundary = {
        "contract_key": "grpc://auth",
        "anchor_status": "stale",
        "payload_match": True,
        "is_strong_candidate": False
    }
    assert dre.classify(boundary) == "ANCHOR_DRIFT"

def test_classify_matched():
    dre = DeterministicRuleEngine()
    boundary = {
        "contract_key": "grpc://auth",
        "anchor_status": "present",
        "payload_match": True,
        "is_strong_candidate": False
    }
    assert dre.classify(boundary) == "MATCHED"

def test_priority_escalation_security():
    dre = DeterministicRuleEngine()
    # auth is a security sensitive prefix
    boundary = {
        "contract_key": "grpc://auth.UserService/ValidateToken",
        "anchor_status": "stale",
        "payload_match": True
    }
    assert dre.is_high_priority(boundary, "ANCHOR_DRIFT") is True

def test_priority_escalation_staleness():
    dre = DeterministicRuleEngine()
    boundary = {
        "contract_key": "grpc://other",
        "anchor_status": "stale",
        "payload_match": True,
        "anchor_metadata": {"version_skew": True}
    }
    assert dre.is_high_priority(boundary, "ANCHOR_DRIFT") is True
