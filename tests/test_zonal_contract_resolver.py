import pytest
from scripts.zonal_contract_resolver import ZonalContractResolver

def test_zonal_contract_resolver_basic():
    # Mock zone and file contents
    zone = {
        "services/auth": {"path": "services/auth"},
        "services/payments": {"path": "services/payments"}
    }
    virtual_fs = {
        "services/auth/auth.proto": "service UserService { rpc ValidateToken ... }",
        "services/payments/src/client.js": "const authClient = new auth_server(); authClient.validateToken({ token: 'abc' });"
    }
    
    resolver = ZonalContractResolver(virtual_fs)
    graph = resolver.resolve_contracts(zone)
    
    # It should find at least one boundary
    assert len(graph["boundaries"]) > 0
    boundary = graph["boundaries"][0]
    assert "contract_key" in boundary
