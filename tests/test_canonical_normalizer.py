import pytest
from scripts.canonical_normalizer import CanonicalNormalizer

def test_canonical_normalization_basic():
    normalizer = CanonicalNormalizer()
    # user_id, userId, and UserID all normalize to userid
    assert normalizer.normalize("user_id") == "userid"
    assert normalizer.normalize("userId") == "userid"
    assert normalizer.normalize("UserID") == "userid"

def test_canonical_normalization_camel_case():
    normalizer = CanonicalNormalizer()
    assert normalizer.normalize("MySpecialField") == "myspecialfield"
    assert normalizer.normalize("my_special_field") == "myspecialfield"

def test_payload_match_with_normalization():
    normalizer = CanonicalNormalizer()
    caller_payload = {"user_id": "string", "auth_token": "string"}
    callee_payload = {"userId": "string", "authToken": "string"}
    
    is_match, _ = normalizer.compare_payloads(caller_payload, callee_payload)
    assert is_match is True

def test_payload_mismatch_with_normalization():
    normalizer = CanonicalNormalizer()
    caller_payload = {"user_id": "string", "auth_token": "string"}
    callee_payload = {"userId": "string", "accessToken": "string"}
    
    is_match, mismatch_reason = normalizer.compare_payloads(caller_payload, callee_payload)
    assert is_match is False
    assert "CONTRACT_MISMATCH" in mismatch_reason

def test_collision_prevention():
    """
    To prevent false negatives from lossy collisions (e.g., a payload containing 
    both user_id and userid), the engine must first verify 1-to-1 mapping.
    """
    normalizer = CanonicalNormalizer()
    # Collision: both "user_id" and "userid" normalize to "userid"
    payload = {"user_id": "string", "userid": "int"}
    
    # In case of collision, it should fall back to case-insensitive exact matching
    caller_payload = {"user_id": "string", "userid": "int"}
    callee_payload = {"user_id": "string", "userid": "int"}
    
    is_match, _ = normalizer.compare_payloads(caller_payload, callee_payload)
    assert is_match is True
    
    # Different values/types for colliding fields
    callee_payload_diff = {"user_id": "int", "userid": "string"}
    is_match, _ = normalizer.compare_payloads(caller_payload, callee_payload_diff)
    assert is_match is False
