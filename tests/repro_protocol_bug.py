import pytest
import json
from pathlib import Path
from scripts.engine import DiscoveryEngine
from scripts.trace_engine import TraceEngine

def test_reproduce_protocol_bug():
    # Setup a virtual FS mimicking a Next.js monorepo with internal imports
    virtual_fs = {
        "tsconfig.json": json.dumps({
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["*"]
                }
            }
        }),
        "app/api/track-user/route.ts": """
import { trackUserProtection } from "@/services/security/track-user-protection";

export async function POST(req: Request) {
    const data = await req.json();
    await trackUserProtection({ 
        userId: data.userId,
        action: "track-user"
    });
}
""",
        "services/security/track-user-protection.ts": """
export async function trackUserProtection(payload: { userId: string, action: string }) {
    console.log("Tracking user:", payload.userId);
    return { success: true };
}
""",
        # Adding some junk to test MAP filtering
        ".temp_binaries/junk.exe": "binary content",
        "node_modules/lodash/index.js": "module.exports = {};",
        "dist/bundle.js": "some bundle",
    }
    
    # 1. Test MAP Filtering
    discovery_engine = DiscoveryEngine(virtual_fs=virtual_fs)
    # Generate full map to see if junk is included
    full_map = discovery_engine.generate(root_dir=".")
    
    # Junk should be excluded
    assert ".temp_binaries" not in full_map
    assert "node_modules" not in full_map
    assert "dist" not in full_map
    
    # 2. Test Zonal Traversal
    # Seed from app/api/track-user
    zone = discovery_engine.generate(seed_service="app/api/track-user", max_distance=2)
    
    # It should have found the edge to services/security
    assert "services/security" in zone, f"Zone missing services/security. Current zone: {list(zone.keys())}"
    
    # 3. Test TRACE (Resolution)
    trace_engine = TraceEngine(virtual_fs=virtual_fs)
    result = trace_engine.trace_zone(zone)
    
    # It should find at least one boundary representing the internal orchestration
    assert len(result["boundaries"]) > 0, "No boundaries found in TRACE result"
    
    # Check if the boundary correctly identifies the internal call
    boundary = result["boundaries"][0]
    assert boundary["contract_key"].startswith("internal://") or "trackUserProtection" in boundary["contract_key"]
    assert boundary["dre_status"] == "MISSING_ANCHOR" # Expected as there's no anchor (IDL/Zod) yet

if __name__ == "__main__":
    pytest.main([__file__])
