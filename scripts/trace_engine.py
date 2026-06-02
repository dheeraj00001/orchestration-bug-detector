from typing import List, Dict, Optional
from .zonal_contract_resolver import ZonalContractResolver

class TraceEngine:
    """
    Orchestrates Phase 2: Zonal Contract Resolution.
    """
    def __init__(self, virtual_fs: Dict[str, str] = None):
        self.resolver = ZonalContractResolver(virtual_fs)

    def trace_zone(self, zone: Dict) -> Dict:
        """Resolves contract evidence only inside the provided impact zone."""
        return self.resolver.resolve_contracts(zone)
