from typing import List, Dict, Optional
from .canonical_normalizer import CanonicalNormalizer

class ContractStitcher:
    """
    A deep module that stitches disparate language AST boundaries via universal 
    contract keys and flags deterministic payload mismatches.
    """
    def __init__(self):
        self.normalizer = CanonicalNormalizer()

    def stitch(self, boundaries: List[Dict]) -> Dict:
        # Group by contract_key
        groups = {}
        for b in boundaries:
            key = b.get("contract_key")
            if not key:
                continue
            if key not in groups:
                groups[key] = {"caller": None, "callee": None, "anchor": None}
            
            role = b.get("role")
            if role in ["caller", "callee"]:
                groups[key][role] = b
            elif role == "anchor":
                groups[key]["anchor"] = b

        stitched_boundaries = []
        import sys
        # print(f"DEBUG: Processing {len(groups)} groups", file=sys.stderr)

        for key, members in groups.items():
            caller = members["caller"]
            callee = members["callee"]
            anchor = members["anchor"]
            
            # if caller and callee:
            #     print(f"DEBUG: Found match for {key}", file=sys.stderr)

            # We only stitch if we have at least one side
            if not (caller or callee):
                # print(f"DEBUG: Skipping {key} - no caller or callee", file=sys.stderr)
                continue
            
            # ARCH-01: Cross-Tier Boundary Classification
            is_cross_tier = False
            boundary_type = "INTERNAL_IMPORT"
            
            if caller and callee:
                caller_tier = caller.get("tier")
                callee_tier = callee.get("tier")
                if caller_tier and callee_tier and caller_tier != callee_tier:
                    is_cross_tier = True
                    boundary_type = "CROSS_TIER_IMPORT"
                elif caller_tier and callee_tier:
                    boundary_type = "SAME_TIER_IMPORT"

            # Determine anchor status
            anchor_status = "absent"
            if anchor:
                anchor_status = "present" # Simplified for now

            # Determine DRE status
            dre_status = "MATCHED"
            if caller and callee:
                is_match, reason = self.normalizer.compare_payloads(
                    caller.get("payload_shape", {}),
                    callee.get("payload_shape", {})
                )
                if not is_match:
                    dre_status = "CONTRACT_MISMATCH"
                elif anchor_status == "absent":
                    dre_status = "MISSING_ANCHOR"
            elif anchor_status == "absent":
                dre_status = "MISSING_ANCHOR"

            stitched_boundaries.append({
                "contract_key": key,
                "caller": caller,
                "callee": callee,
                "anchor_status": anchor_status,
                "has_shared_idl": anchor_status == "present",
                "dre_status": dre_status,
                "boundary_type": boundary_type,
                "is_cross_tier": is_cross_tier
            })

        return {"boundaries": stitched_boundaries}
