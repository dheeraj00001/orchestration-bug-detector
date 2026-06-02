import pytest
from pathlib import Path
from scripts.evidence_resolver import EvidenceResolver

def test_score_tier_1_confirmed_edge():
    """
    Tier 1 (Strong / Confirmed Edge): a contract anchor plus 
    high-signal usage evidence on both sides of the boundary.
    """
    resolver = EvidenceResolver()
    
    caller_data = {
        "path": "services/payments",
        "files": {
            "package.json": '{"dependencies": {"@company/auth-client": "1.0.0"}}',
            "src/client.js": "authClient.validateToken(token)" # Usage evidence
        }
    }
    callee_data = {
        "path": "services/auth",
        "files": {
            "auth.proto": "service UserService { rpc ValidateToken ... }", # Anchor
            "src/handler.go": "func (s *server) ValidateToken(...) ..." # Usage evidence
        }
    }
    raw_edge = {"type": "grpc", "target": "services/auth"}
    
    score = resolver.score_edge(caller_data, callee_data, raw_edge)
    assert score["tier"] == 1

def test_score_tier_2_medium_edge():
    """
    Tier 2 (Medium): shared internal packages or standard 
    service-discovery patterns without full high-signal confirmation.
    """
    resolver = EvidenceResolver()
    
    caller_data = {
        "path": "services/payments",
        "files": {
            "package.json": '{"dependencies": {"@company/common": "1.0.0"}}'
        }
    }
    callee_data = {
        "path": "services/auth",
        "files": {
            "package.json": '{"name": "@company/auth"}'
        }
    }
    raw_edge = {"type": "package", "target": "services/auth"}
    
    score = resolver.score_edge(caller_data, callee_data, raw_edge)
    assert score["tier"] == 2

def test_score_tier_3_weak_edge():
    """
    Tier 3 (Weak): generic orchestration-library signals 
    with no stronger evidence.
    """
    resolver = EvidenceResolver()
    
    caller_data = {
        "path": "services/payments",
        "files": {
            "package.json": '{"dependencies": {"axios": "0.21.1"}}'
        }
    }
    callee_data = {
        "path": "services/auth",
        "files": {}
    }
    raw_edge = {"type": "library", "target": "services/auth"}
    
    score = resolver.score_edge(caller_data, callee_data, raw_edge)
    assert score["tier"] == 3
