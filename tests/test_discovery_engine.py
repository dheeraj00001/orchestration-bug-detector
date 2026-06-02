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
        "services/payments/package.json": '{"dependencies": {"@company/auth-client": "1.0.0", "axios": "0.21.1"}}',
        "infrastructure/terraform/main.tf": "resource 'aws_security_group' 'allow_auth' {}"
    }
    engine = DiscoveryEngine(virtual_fs=virtual_fs)
    result = engine.generate()
    assert "services/auth" in result
    assert "auth.proto" in result["services/auth"]["edges"]["strong"]
    assert '"@company/auth-client"' in result["services/payments"]["edges"]["medium"]
    assert "company/auth" in result["services/auth"]["edges"]["medium"]
    assert "axios" in result["services/payments"]["edges"]["weak"]
    assert "grpc" in result["services/auth"]["edges"]["weak"]

def test_discovery_engine_real_fs(tmp_path):
    # ARRANGE: Create a real directory structure
    (tmp_path / "services" / "auth").mkdir(parents=True)
    (tmp_path / "services" / "auth" / "go.mod").write_text("module company/auth")
    (tmp_path / "services" / "auth" / "auth.proto").write_text("syntax = 'proto3';")
    
    (tmp_path / "services" / "payments").mkdir(parents=True)
    (tmp_path / "services" / "payments" / "package.json").write_text('{"dependencies": {"axios": "0.21.1"}}')

    # ACT
    engine = DiscoveryEngine()
    # We need to tell the engine WHERE to start walking
    result = engine.generate(root_dir=tmp_path)

    # ASSERT
    assert "services/auth" in result
    assert "auth.proto" in result["services/auth"]["edges"]["strong"]
    assert "axios" in result["services/payments"]["edges"]["weak"]

if __name__ == "__main__":
    pytest.main([__file__])
