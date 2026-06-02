import pytest
import json
from scripts.digester import AnomalyDigester

def test_digester_outputs():
    digester = AnomalyDigester()
    graph = {
        "boundaries": [
            {
                "contract_key": "grpc://auth",
                "anchor_status": "absent",
                "payload_match": False,
                "is_strong_candidate": True
            },
            {
                "contract_key": "grpc://matched",
                "anchor_status": "present",
                "payload_match": True,
                "is_strong_candidate": False
            }
        ]
    }
    
    top, all_anom = digester.digest(graph)
    
    # MATCHED findings are suppressed from the report but present in the audit trail
    assert len(top) == 1
    assert top[0]["dre_status"] == "CONTRACT_MISMATCH"
    
    assert len(all_anom) == 2
    assert any(a["dre_status"] == "MATCHED" for a in all_anom)

def test_digester_prioritization_rules():
    digester = AnomalyDigester()
    graph = {
        "boundaries": [
            {
                "contract_key": "grpc://other",
                "anchor_status": "stale",
                "payload_match": True,
                "is_strong_candidate": False
            }
        ]
    }
    
    # Stale ANCHOR_DRIFT should be promoted
    top, _ = digester.digest(graph)
    assert len(top) == 1
    assert top[0]["dre_status"] == "ANCHOR_DRIFT"
