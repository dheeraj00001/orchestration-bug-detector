import re
import json
from typing import List, Dict, Any
from .base import BoundaryExtractor

class NodeExtractor(BoundaryExtractor):
    def extract(self, content: str) -> List[Dict[str, Any]]:
        boundaries = []

        # 1. Identify gRPC Clients
        # Matches: const client = new auth_server(...)
        client_matches = re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*new\s+([\w_]+)\(", content)
        clients = {m.group(1): m.group(2) for m in client_matches}

        # 2. Identify Method Calls on those clients
        # Matches: client.ValidateToken({ ... }, ...)
        for client_var, service_name in clients.items():
            # This regex looks for the method call and tries to capture the object literal payload
            # Updated to handle case-sensitive method names and optional spaces
            method_pattern = fr"{client_var}\.(\w+)\(\s*\{{([^}}]+)\}}\s*[,)]"
            method_matches = re.finditer(method_pattern, content)

            for m in method_matches:
                method_name = m.group(1)
                payload_str = m.group(2)
                
                # Simple extraction of keys from object literal
                keys = re.findall(r"(\w+)\s*:", payload_str)
                payload_shape = {k: "string" for k in keys}

                # Normalize service name: replace underscores with dots to match Go's pkg.server
                normalized_service = service_name.replace("_", ".")

                boundaries.append({
                    "role": "caller",
                    "contract_key": f"grpc://{normalized_service}/{method_name}",
                    "payload_shape": payload_shape
                })

        return boundaries
