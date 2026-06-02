from typing import List, Dict, Optional

class ContractStitcher:
    """
    A deep module that stitches disparate language AST boundaries via universal 
    contract keys and flags deterministic payload mismatches.
    """

    def stitch(self, boundaries: List[Dict]) -> Dict:
        # Group by contract_key
        groups = {}
        for b in boundaries:
            key = b.get("contract_key")
            if not key:
                continue
            if key not in groups:
                groups[key] = {"caller": None, "callee": None}
            
            role = b.get("role")
            if role in ["caller", "callee"]:
                groups[key][role] = b

        stitched_boundaries = []

        for key, members in groups.items():
            caller = members["caller"]
            callee = members["callee"]

            # We only stitch if we have a pair
            if caller and callee:
                flag, status = self._compare_payloads(
                    caller.get("payload_shape", {}),
                    callee.get("payload_shape", {})
                )

                stitched_boundaries.append({
                    "contract_key": key,
                    "caller": caller,
                    "callee": callee,
                    "deterministic_flag": flag,
                    "status": status
                })

        return {"boundaries": stitched_boundaries}

    def _compare_payloads(self, sent: Dict, expected: Dict) -> (Optional[str], str):
        """Logic to compare dictionaries and detect mismatches."""
        if sent == expected:
            return None, "MATCHED"

        # Check for field name mismatches (case-sensitivity or snake vs camel)
        sent_keys = set(sent.keys())
        expected_keys = set(expected.keys())

        if sent_keys != expected_keys:
            # Simple mismatch detection for the flag
            mismatched_sent = list(sent_keys - expected_keys)
            mismatched_expected = list(expected_keys - sent_keys)
            
            # If there's one key that looks like a case/naming mismatch
            if len(mismatched_sent) == 1 and len(mismatched_expected) == 1:
                return f"FIELD_NAME_MISMATCH: '{mismatched_sent[0]}' vs '{mismatched_expected[0]}'", "MISMATCH_DETECTED"
            
            return f"SCHEMA_MISMATCH: keys {sent_keys} vs {expected_keys}", "MISMATCH_DETECTED"

        # Check for type mismatches
        for key in sent_keys:
            if sent[key] != expected[key]:
                return f"TYPE_MISMATCH: key '{key}' expects {expected[key]} but sent {sent[key]}", "MISMATCH_DETECTED"

        return "UNKNOWN_MISMATCH", "MISMATCH_DETECTED"
