import os
import shutil
import subprocess
import json
from pathlib import Path

def test_module_map():
    test_dir = Path("test_monorepo")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    # Create Service A (Go)
    service_a = test_dir / "services" / "auth"
    service_a.mkdir(parents=True)
    (service_a / "go.mod").write_text("module company/auth\n\nrequire github.com/grpc/grpc-go v1.40.0")
    (service_a / "auth.proto").write_text("syntax = 'proto3';")

    # Create Service B (Node)
    service_b = test_dir / "services" / "payments"
    service_b.mkdir(parents=True)
    (service_b / "package.json").write_text('{"dependencies": {"@company/auth-client": "1.0.0", "axios": "0.21.1"}}')
    
    # Create Shared IaC
    iac = test_dir / "infrastructure" / "terraform"
    iac.mkdir(parents=True)
    (iac / "main.tf").write_text("resource 'aws_security_group' 'allow_auth' {}")
    (iac / "requirements.txt").write_text("awscli") # Just to mark as a module for testing

    # Run the script
    script_path = Path("scripts/generate_module_map.py").absolute()
    result = subprocess.run(["python3", str(script_path), str(test_dir)], capture_output=True, text=True)
    
    print("Script Output:")
    print(result.stdout)
    
    output = json.loads(result.stdout)
    
    # Assertions
    assert "services/auth" in output
    assert "auth.proto" in output["services/auth"]["edges"]["strong"]
    assert "axios" in output["services/payments"]["edges"]["weak"]
    assert '"@company/auth-client"' in output["services/payments"]["edges"]["medium"]
    
    print("\nTest Passed!")

if __name__ == "__main__":
    test_module_map()
