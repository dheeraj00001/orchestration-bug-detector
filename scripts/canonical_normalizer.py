import re
from typing import Dict, Tuple, Optional, Set

class CanonicalNormalizer:
    """
    Implements PRD Canonical Normalization rules:
    (1) lowercasing all characters;
    (2) stripping all underscores;
    (3) collapsing camelCase boundaries.
    
    Includes 1-to-1 mapping verification to prevent lossy collisions.
    """

    def normalize(self, field_name: str) -> str:
        # Step 3: Collapse camelCase (insert nothing, just lowercase later)
        # We do this by finding uppercase letters and making them lowercase
        # but the rule says "replacing each uppercase letter with its lowercase 
        # equivalent without inserting a separator". 
        # This is equivalent to just lowercasing the whole string after stripping underscores.
        
        # Step 1 & 2: Lowercase and strip underscores
        s = field_name.lower().replace("_", "")
        return s

    def compare_payloads(self, caller: Dict, callee: Dict) -> Tuple[bool, Optional[str]]:
        if caller == callee:
            return True, None

        caller_norm_map = self._get_normalization_map(caller)
        callee_norm_map = self._get_normalization_map(callee)

        # Check for collisions in either side
        if self._has_collisions(caller_norm_map) or self._has_collisions(callee_norm_map):
            # Fallback to case-insensitive exact matching
            return self._compare_case_insensitive(caller, callee)

        # Compare normalized maps
        norm_caller = {norm: caller[orig] for norm, orig in caller_norm_map.items()}
        norm_callee = {norm: callee[orig] for norm, orig in callee_norm_map.items()}

        if norm_caller == norm_callee:
            return True, None

        return False, "CONTRACT_MISMATCH"

    def _get_normalization_map(self, payload: Dict) -> Dict[str, str]:
        """Returns a map of normalized_name -> original_name."""
        norm_map = {}
        for orig in payload.keys():
            norm = self.normalize(orig)
            if norm in norm_map:
                # Mark collision by storing a special value or list
                if not isinstance(norm_map[norm], list):
                    norm_map[norm] = [norm_map[norm]]
                norm_map[norm].append(orig)
            else:
                norm_map[norm] = orig
        return norm_map

    def _has_collisions(self, norm_map: Dict) -> bool:
        return any(isinstance(v, list) for v in norm_map.values())

    def _compare_case_insensitive(self, caller: Dict, callee: Dict) -> Tuple[bool, Optional[str]]:
        lowered_caller = {k.lower(): v for k, v in caller.items()}
        lowered_callee = {k.lower(): v for k, v in callee.items()}
        
        if lowered_caller == lowered_callee:
            return True, None
        return False, "CONTRACT_MISMATCH"
