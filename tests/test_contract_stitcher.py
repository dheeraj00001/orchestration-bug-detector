import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.stitcher import ContractStitcher

def test_contract_stitcher_detects_payload_mismatch():
    # ARRANGE: Mocked outputs from our future TreeSitterAdapter
    # 1. Node.js Client (Caller) sends 'user_id'
    node_client_boundary = {
        "language": "node",
        "role": "caller",
        "file": "src/checkout.ts",
        "line": 45,
        "contract_key": "grpc://auth.UserService/ValidateToken",
        "payload_shape": {"user_id": "string", "token": "string"}
    }

    # 2. Go Server (Callee) expects 'session_token' instead of 'token'
    go_server_boundary = {
        "language": "go",
        "role": "callee",
        "file": "internal/rpc/server.go",
        "line": 112,
        "contract_key": "grpc://auth.UserService/ValidateToken",
        "payload_shape": {"user_id": "string", "session_token": "string"}
    }

    stitcher = ContractStitcher()

    # ACT: Pass the disparate language boundaries to the stitcher
    result = stitcher.stitch([node_client_boundary, go_server_boundary])

    # ASSERT: The output matches our strict PRD schema
    assert len(result["boundaries"]) == 1
    
    matched_edge = result["boundaries"][0]
    assert matched_edge["contract_key"] == "grpc://auth.UserService/ValidateToken"
    
    # Verify caller/callee mapping is preserved
    assert matched_edge["caller"]["language"] == "node"
    assert matched_edge["callee"]["language"] == "go"
    
    # THE CORE VALUE: Deterministic mismatch detection
    assert matched_edge["dre_status"] == "CONTRACT_MISMATCH"

def test_contract_stitcher_ignores_unrelated_boundaries():
    # ARRANGE: Two boundaries that do NOT share a contract key
    boundary_a = {
        "contract_key": "grpc://auth.UserService/Login", 
        "payload_shape": {"user": "string"},
        "role": "caller",
        "language": "node",
        "file": "a.ts",
        "line": 1
    }
    boundary_b = {
        "contract_key": "event://user-lifecycle/UserCreated", 
        "payload_shape": {"id": "int"},
        "role": "callee",
        "language": "go",
        "file": "b.go",
        "line": 1
    }
    
    stitcher = ContractStitcher()
    
    # ACT
    result = stitcher.stitch([boundary_a, boundary_b])
    
    # ASSERT: They should NOT be stitched together, but both should be returned as partial boundaries
    assert len(result["boundaries"]) == 2
    keys = [b["contract_key"] for b in result["boundaries"]]
    assert "grpc://auth.UserService/Login" in keys
    assert "event://user-lifecycle/UserCreated" in keys

if __name__ == "__main__":
    pytest.main([__file__])
