from typing import Dict, List, Tuple

class InterceptionChain:
    """
    Implements the Hierarchical Evidence Chain from the PRD.
    Resolves middleware in fixed priority:
    1. Infrastructure (highest precedence)
    2. Shared Platform
    3. Local Service Middleware (lowest precedence)
    """

    def check_interception(self, evidence: Dict[str, List[str]]) -> Tuple[str, str]:
        """
        Returns (status, layer).
        Status is 'suppressed' if a higher layer handles it, 'confirmed' otherwise.
        """
        infra = evidence.get("infra", [])
        platform = evidence.get("platform", [])
        local = evidence.get("local", [])

        if infra:
            return "suppressed", "infrastructure"
        
        if platform:
            return "suppressed", "platform"
        
        if local:
            return "confirmed", "local"

        return "confirmed", "unresolved"
