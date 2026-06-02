import pytest
from scripts.interception_chain import InterceptionChain

def test_interception_priority_infra_suppresses_local():
    chain = InterceptionChain()
    # If infra handles it, it's suppressed
    evidence = {
        "infra": ["api-gateway-auth"],
        "platform": [],
        "local": ["local-middleware"]
    }
    status, layer = chain.check_interception(evidence)
    assert status == "suppressed"
    assert layer == "infrastructure"

def test_interception_priority_platform_suppresses_local():
    chain = InterceptionChain()
    evidence = {
        "infra": [],
        "platform": ["service-mesh-retry"],
        "local": ["local-retry-logic"]
    }
    status, layer = chain.check_interception(evidence)
    assert status == "suppressed"
    assert layer == "platform"

def test_interception_unresolved():
    chain = InterceptionChain()
    evidence = {
        "infra": [],
        "platform": [],
        "local": []
    }
    status, layer = chain.check_interception(evidence)
    assert status == "confirmed"
    assert layer == "unresolved"

def test_interception_local_only_not_suppressed():
    # Local middleware alone doesn't "suppress" the anomaly unless it's external to the service
    # Actually PRD says: "infrastructure-level anchors... take highest precedence... local service middleware is checked last."
    # "A concern resolved at a higher-precedence (broader) layer suppresses the same concern from all lower-precedence (narrower) layers."
    # If it's ONLY in local, it's NOT suppressed by a higher layer.
    chain = InterceptionChain()
    evidence = {
        "infra": [],
        "platform": [],
        "local": ["validator"]
    }
    status, layer = chain.check_interception(evidence)
    assert status == "confirmed" # It's resolved locally, but not suppressed by a higher layer
    assert layer == "local"
