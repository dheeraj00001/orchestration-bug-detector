
import os
import shutil
from pathlib import Path
from scripts.engine import DiscoveryEngine
from scripts.extractors.node import NodeExtractor
from scripts.typescript_resolver import TypeScriptResolver
from scripts.zonal_contract_resolver import ZonalContractResolver

def setup_mock_monorepo(root: Path):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    
    # Create structure for BUG-01
    (root / "app/api").mkdir(parents=True)
    (root / "lib").mkdir(parents=True)
    
    with open(root / "app/api/notify.ts", "w") as f:
        f.write("""
import { Validate } from "@/lib/validations";
export const POST = async (req) => {
    Validate(req.body);
    return { ok: true };
}
""")
    
    with open(root / "lib/validations.ts", "w") as f:
        f.write("""
export const Validate = (data: any) => {
    return true;
}
""")

    # Create structure for BUG-02
    (root / "services/security/protections").mkdir(parents=True)
    (root / "services/github").mkdir(parents=True)
    
    with open(root / "services/security/protections/track-user.ts", "w") as f:
        f.write("""
import { logEvent } from "@/services/github/client/extra/deep";
export const track = () => {
    logEvent("user_track");
}
""")
    
    with open(root / "services/github/client.ts", "w") as f:
        f.write("""
export const logEvent = (name: string) => {}
""")

    with open(root / "tsconfig.json", "w") as f:
        f.write("""
{
    "compilerOptions": {
        "baseUrl": ".",
        "paths": {
            "@/*": ["*"]
        }
    }
}
""")

def test_repro():
    root = Path("repro_bug01_02")
    setup_mock_monorepo(root)
    
    print("\n--- Testing BUG-02: Heuristic Failure ---")
    engine = DiscoveryEngine()
    module_map = engine.generate(root_dir=str(root))
    
    track_mod = "services/security"
    if track_mod in module_map:
        edges = module_map[track_mod].get("edges", [])
        found_github = any(e["target"] == "services/github" for e in edges)
        if found_github:
            print("BUG-02 FIXED: Resolved to services/github via fallback!")
        else:
            print("BUG-02 STILL BROKEN: Failed to resolve to services/github.")
    else:
        print(f"FAILED: Module {track_mod} not found in map.")

    print("\n--- Testing BUG-01: Key Mismatch ---")
    virtual_fs = {
        "app/api/notify.ts": (root / "app/api/notify.ts").read_text(),
        "lib/validations.ts": (root / "lib/validations.ts").read_text()
    }
    zonal_resolver = ZonalContractResolver(virtual_fs=virtual_fs)
    
    zone = {
        "app/api": {},
        "lib": {}
    }
    
    stitched = zonal_resolver.resolve_contracts(zone)
    boundaries = stitched.get("boundaries", [])
    
    matched_boundary = None
    for b in boundaries:
        if b["contract_key"] == "internal://lib/validations#Validate":
            matched_boundary = b
            break
            
    if matched_boundary:
        print(f"Found boundary: {matched_boundary['contract_key']}")
        has_caller = matched_boundary.get("caller") is not None
        has_callee = matched_boundary.get("callee") is not None
        print(f"Has Caller: {has_caller}")
        print(f"Has Callee: {has_callee}")
        print(f"DRE Status: {matched_boundary.get('dre_status')}")
        
        if has_caller and has_callee:
            print("BUG-01 FIXED: Keys aligned and boundaries matched!")
        else:
            print("BUG-01 STILL BROKEN: Missing one side of the boundary.")
    else:
        print("BUG-01 STILL BROKEN: Could not find the expected boundary key.")
        print(f"All keys: {[b['contract_key'] for b in boundaries]}")

if __name__ == "__main__":
    test_repro()
