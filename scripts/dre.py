from typing import Dict, Optional

class DeterministicRuleEngine:
    """
    Implements Phase 3 classification rules and priority escalation.
    """

    SECURITY_SENSITIVE_PREFIXES = ["auth", "authz", "payment", "billing", "iam", "rbac"]

    def classify(self, boundary: Dict) -> str:
        """
        Classifies a boundary based on deterministic precedence rules.
        """
        # 0. ORCHESTRATION_BYPASS check
        payload_shape = boundary.get("payload_shape", {})
        if payload_shape.get("__ORCHESTRATION_BYPASS__") == "true":
            return "ORCHESTRATION_BYPASS"

        # 0b. LOGIC_FLAW check
        if boundary.get("role") == "logic_flaw":
            return "LOGIC_FLAW"

        anchor_status = boundary.get("anchor_status", "absent")
        payload_match = boundary.get("payload_match", True)
        is_strong = boundary.get("is_strong_candidate", False)

        # 1. CONTRACT_MISMATCH takes highest precedence
        if not payload_match:
            return "CONTRACT_MISMATCH"

        # 2. ANCHOR_DRIFT (payloads align, but anchor doesn't)
        if anchor_status in ["stale", "version_mismatch"]:
            return "ANCHOR_DRIFT"

        # 3. MISSING_ANCHOR (payloads align, no anchor found, strong candidate)
        if anchor_status == "absent" and is_strong:
            return "MISSING_ANCHOR"

        # 3b. WEAK_MATCH (no anchor found, but weak candidate)
        if anchor_status == "absent" and not is_strong:
            return "WEAK_MATCH"

        # 4. MATCHED (everything aligns)
        if anchor_status == "present" and payload_match:
            confidence = boundary.get("confidence", 1.0)
            if confidence < 0.85:
                return "WEAK_MATCH"
            return "MATCHED"

        return "MATCHED" # Default

    def is_high_priority(self, boundary: Dict, classification: str) -> bool:
        """
        Determines if a finding should be promoted to the prioritized digest.
        """
        if classification in ["CONTRACT_MISMATCH", "ORCHESTRATION_BYPASS", "LOGIC_FLAW"]:
            return True

        if classification == "MISSING_ANCHOR":
            # Digest rules: include MISSING_ANCHOR when it's a strong candidate
            return boundary.get("is_strong_candidate", False)

        if classification == "ANCHOR_DRIFT":
            # Priority escalation: staleness or security sensitivity
            anchor_metadata = boundary.get("anchor_metadata", {})
            if anchor_metadata.get("version_skew") or anchor_metadata.get("hash_mismatch"):
                return True
            
            if boundary.get("anchor_status") == "stale":
                return True

            contract_key = boundary.get("contract_key", "").lower()
            # Check for security-sensitive namespace prefixes
            # Usually after grpc:// or http://
            key_part = contract_key.split("://")[-1]
            if any(key_part.startswith(prefix) for prefix in self.SECURITY_SENSITIVE_PREFIXES):
                return True

        return False
