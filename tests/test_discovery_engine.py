import pytest
import sys
import os
import json
from pathlib import Path

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.engine import DiscoveryEngine

def test_discovery_engine_virtual_fs():
    virtual_fs = {
        "services/auth/go.mod": "module company/auth\nrequire github.com/grpc/grpc-go v1.40.0",
        "services/auth/auth.proto": "syntax = 'proto3'; package auth;",
        "services/payments/package.json": '{"dependencies": {"@company/auth": "1.0.0", "axios": "0.21.1"}}', # Changed auth-client to auth
        "services/payments/src/client.js": "authClient.validateToken(token)",
        "services/auth/src/handler.go": "func (s *server) ValidateToken(...) ...",
    }
    engine = DiscoveryEngine(virtual_fs=virtual_fs)
    result = engine.generate()
    
    assert "services/auth" in result
    assert "services/payments" in result
    
    # Check edges from payments to auth
    payments_edges = result["services/payments"]["edges"]
    auth_edge = next((e for e in payments_edges if e["target"] == "services/auth"), None)
    assert auth_edge is not None
    assert auth_edge["tier"] == 1 

def test_discovery_engine_zonal_scoping():
    virtual_fs = {
        "services/seed/package.json": '{"dependencies": {"@company/a": "1.0.0"}}',
        "services/seed/src/use.js": "a.Call()",
        "services/a/package.json": '{"dependencies": {"@company/b": "1.0.0"}}',
        "services/a/a.proto": "syntax = 'proto3';", # Anchor for seed->a
        "services/a/src/server.go": "func server()", # Usage for seed->a
        "services/a/src/use.js": "b.Call()", # Usage for a->b
        "services/b/package.json": '{"dependencies": {"@company/c": "1.0.0"}}',
        "services/b/b.proto": "syntax = 'proto3';", # Anchor for a->b
        "services/b/src/server.go": "func server()", # Usage for a->b
        "services/c/package.json": '{}',
    }
    engine = DiscoveryEngine(virtual_fs=virtual_fs)
    
    # Distance 1 (seed -> a)
    result = engine.generate(seed_service="services/seed", max_distance=1)
    assert "services/seed" in result
    assert "services/a" in result
    
    # Distance 2 (seed -> a -> b)
    # seed -> a is Tier 1 (proto + usage on both sides)
    # a -> b is Tier 1 (proto + usage on both sides)
    result = engine.generate(seed_service="services/seed", max_distance=2)
    assert "services/b" in result
    assert "services/c" not in result

if __name__ == "__main__":
    pytest.main([__file__])
