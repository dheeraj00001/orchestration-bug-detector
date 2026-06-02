import re
from typing import Dict

class EvidenceResolver:
    """
    Implements Phase 1 Pass 2 scoring rules:
    - Tier 1: Anchor + High-signal usage on BOTH sides.
    - Tier 2: Shared internal packages or service-discovery patterns.
    - Tier 3: Generic orchestration libraries.
    """

    ANCHOR_PATTERNS = [
        r'\.proto$', r'\.graphql$', r'\.avsc$', r'\.tf$', r'openapi\.yaml$', r'swagger\.json$'
    ]

    USAGE_PATTERNS = {
        "caller": [
            r'Client\.', r'Call\(', r'fetch\(', r'axios\.', r'\.validateToken', r'\.request\('
        ],
        "callee": [
            r'func.*server', r'router\.', r'app\.(get|post|put|delete)', r'rpc.*returns', r'handler'
        ]
    }

    COMPANY_PATTERNS = [
        r'@company/', r'github\.com/company/', r'company-'
    ]

    LIBRARY_PATTERNS = [
        r'amqplib', r'kafkajs', r'grpc', r'axios', r'requests', r'pika', r'grpcio'
    ]

    def score_edge(self, caller_data: Dict, callee_data: Dict, raw_edge: Dict) -> Dict:
        """Returns a dict with 'tier' and 'is_strong_candidate'."""
        has_anchor = any(
            re.search(p, filename) 
            for p in self.ANCHOR_PATTERNS 
            for filename in callee_data.get("files", {}).keys()
        )

        caller_usage = any(
            re.search(p, content) 
            for p in self.USAGE_PATTERNS["caller"] 
            for content in caller_data.get("files", {}).values()
        )

        callee_usage = any(
            re.search(p, content) 
            for p in self.USAGE_PATTERNS["callee"] 
            for content in callee_data.get("files", {}).values()
        )

        is_strong_candidate = (not has_anchor) and caller_usage and callee_usage

        # Tier 1: Anchor + Usage on BOTH sides
        if has_anchor and caller_usage and callee_usage:
            return {"tier": 1, "is_strong_candidate": False}

        # Tier 2: Shared company packages
        all_caller_content = "".join(caller_data.get("files", {}).values())
        if any(re.search(p, all_caller_content) for p in self.COMPANY_PATTERNS):
            return {"tier": 2, "is_strong_candidate": is_strong_candidate}

        # Tier 3: Generic libraries
        return {"tier": 3, "is_strong_candidate": is_strong_candidate}
