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
            method_pattern = fr"{client_var}\.(\w+)\(\s*\{{([^}}]+)\}}\s*[,)]"
            method_matches = re.finditer(method_pattern, content)

            for m in method_matches:
                method_name = m.group(1)
                payload_str = m.group(2)
                
                # Simple extraction of keys from object literal
                keys = re.findall(r"(\w+)\s*:", payload_str)
                payload_shape = {k: "string" for k in keys}

                # DETECTION: Look for bypassCache: true
                if re.search(r"bypassCache\s*:\s*true", payload_str):
                    payload_shape["__ORCHESTRATION_BYPASS__"] = "true"

                normalized_service = service_name.replace("_", ".")

                boundaries.append({
                    "role": "caller",
                    "contract_key": f"grpc://{normalized_service}/{method_name}",
                    "payload_shape": payload_shape
                })

        # 3. INTERNAL ORCHESTRATION: Detect imports from lib/ or other internal modules
        # Matches: import { X } from "../lib/Y"
        import_matches = re.finditer(r"import\s+\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]", content)
        for m in import_matches:
            imported_vars = [v.strip() for v in m.group(1).split(",")]
            import_path = m.group(2)
            
            # If it's an internal-looking path
            if import_path.startswith(".") or import_path.startswith("@/"):
                for var in imported_vars:
                    # Also look for calls to this var
                    if re.search(fr"{var}\(", content):
                        boundaries.append({
                            "role": "caller",
                            "contract_key": f"internal://{import_path}/{var}",
                            "payload_shape": {"type": "internal_call"}
                        })

        # 4. DETECTION: Atomic Inconsistency (Missing Rollback)
        # Matches recordRefresh without a corresponding rollback in the same file (simplified check)
        if "recordRefresh" in content and "rollback" not in content:
            boundaries.append({
                "role": "logic_flaw",
                "contract_key": "orchestration://atomic_inconsistency",
                "details": "Potential missing compensation: recordRefresh called without rollback defined in file."
            })

        # 4. DETECTION: Missing Quota/Policy Guard
        # If the file seems to be a service/worker but doesn't mention quotaMonitor or refreshPolicy
        if any(x in content for x in ["triggerRefresh", "BackgroundRefresh"]):
            if not any(x in content for x in ["quotaMonitor", "refreshPolicy"]):
                boundaries.append({
                    "role": "logic_flaw",
                    "contract_key": "orchestration://missing_guard",
                    "details": "High-risk orchestration: Background refresh trigger detected without quota or policy guards."
                })

        # 5. DETECTION: Short-Lived Mutex Lock (Cache Stampede)
        # Matches Redis SET NX PX with low TTL (e.g., 10000ms)
        lock_match = re.search(r"['\"]PX['\"]\s*,\s*(\d+)", content)
        if lock_match:
            ttl = int(lock_match.group(1))
            if ttl <= 10000:
                boundaries.append({
                    "role": "logic_flaw",
                    "contract_key": "orchestration://short_mutex_lock",
                    "details": f"Cache Stampede risk: Distributed lock TTL is too short ({ttl}ms). Spikes may exceed this duration."
                })

        return boundaries
