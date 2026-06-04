import re
from typing import Dict
from pathlib import Path

class EvidenceResolver:
    """
    Implements Phase 1 Pass 2 scoring rules:
    - Tier 1: Anchor + High-signal usage on BOTH sides.
    - Tier 2: Shared internal packages or service-discovery patterns.
    - Tier 3: Generic orchestration libraries.
    """

    # ARCH-01: Tier Map for monolith boundary detection
    DEFAULT_TIER_MAP = {
        "app": 1,
        "pages": 1,
        "components": 1,
        "features": 1,
        "services": 2,
        "lib": 3,
        "utils": 3,
        "shared": 3,
        "config": 4,
        "types": 4,
    }

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.tier_map = self._load_tier_map()

    def _load_tier_map(self) -> Dict[str, int]:
        config_path = self.root_dir / "orchestration.config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, "r") as f:
                    config = json.load(f)
                    return config.get("tier_map", self.DEFAULT_TIER_MAP)
            except Exception:
                pass
        return self.DEFAULT_TIER_MAP

    def _get_tier(self, file_path: str) -> int | None:
        parts = file_path.replace("\\", "/").split("/")
        if not parts:
            return None
        # Try to find a matching prefix in the tier map
        for i in range(len(parts), 0, -1):
            prefix = "/".join(parts[:i])
            if prefix in self.tier_map:
                return self.tier_map[prefix]
        return None

    def _is_orchestration_boundary(self, source_path: str, target_path: str) -> bool:
        source_tier = self._get_tier(source_path)
        target_tier = self._get_tier(target_path)
        if source_tier is None or target_tier is None:
            return False
        return source_tier != target_tier

    ANCHOR_PATTERNS = [
        r'\.proto$', r'\.graphql$', r'\.avsc$', r'\.tf$', r'openapi\.yaml$', r'swagger\.json$',
        r'schema\.ts$', r'schema\.js$', r'validations\.ts$', r'validations\.js$', r'zod\.ts$'
    ]

    USAGE_PATTERNS = {
        "caller": [
            r'Client\.', r'Call\(', r'fetch\(', r'axios\.', r'\.validateToken', r'\.request\(',
            r'\.parse\(', r'\.safeParse\(', r'useQuery\(', r'useMutation\('
        ],
        "callee": [
            r'func.*server', r'router\.', r'app\.(get|post|put|delete)', r'rpc.*returns', r'handler',
            r'export\s+const\s+\w+Schema', r'z\.object'
        ]
    }

    COMPANY_PATTERNS = [
        r'@company/', r'github\.com/company/', r'company-', r'@/'
    ]

    LIBRARY_PATTERNS = [
        r'amqplib', r'kafkajs', r'grpc', r'axios', r'requests', r'pika', r'grpcio', r'zod'
    ]

    def score_edge(self, caller_data: Dict, callee_data: Dict, raw_edge: Dict) -> Dict:
        """Returns a dict with 'tier' and 'is_strong_candidate'."""
        has_anchor = any(
            re.search(p, filename) 
            for p in self.ANCHOR_PATTERNS 
            for filename in callee_data.get("files", {}).keys()
        )

        # Schema modules are anchors
        all_callee_content = "".join(callee_data.get("files", {}).values())
        if any(re.search(p, all_callee_content) for p in [r'z\.object', r'joi\.', r'yup\.']):
            has_anchor = True

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

        # ARCH-01: Monolith Boundary Promotion
        # If it's an import crossing a tier, it's a strong candidate regardless of marker
        is_cross_tier = self._is_orchestration_boundary(caller_data["path"], callee_data["path"])
        
        is_strong_candidate = (not has_anchor) and caller_usage and callee_usage
        if is_cross_tier and raw_edge.get("type") == "import":
            is_strong_candidate = True

        # Tier 1: Anchor + Usage on BOTH sides
        if has_anchor and (caller_usage or callee_usage):
            return {"tier": 1, "is_strong_candidate": False, "is_cross_tier": is_cross_tier}

        # Tier 2: Shared company packages or internal orchestration
        all_caller_content = "".join(caller_data.get("files", {}).values())
        if any(re.search(p, all_caller_content) for p in self.COMPANY_PATTERNS):
            return {"tier": 2, "is_strong_candidate": is_strong_candidate, "is_cross_tier": is_cross_tier}
        
        # Internal cross-directory imports are Tier 2 candidates
        if raw_edge.get("type") == "import":
            return {"tier": 2, "is_strong_candidate": is_strong_candidate, "is_cross_tier": is_cross_tier}

        # Tier 3: Generic libraries
        return {"tier": 3, "is_strong_candidate": is_strong_candidate, "is_cross_tier": is_cross_tier}
