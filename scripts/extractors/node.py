import re
import json
from typing import List, Dict, Any
from .base import BoundaryExtractor

class NodeExtractor(BoundaryExtractor):
    ZOD_EXPORT_PATTERN = re.compile(
        r"export\s+(?:const|let)\s+(\w+)\s*=\s*z\."
    )

    def __init__(self, resolver=None):
        self.resolver = resolver

    def _discover_zod_anchors(self, content: str) -> List[str]:
        return self.ZOD_EXPORT_PATTERN.findall(content)

    def _strip_comments(self, source: str) -> str:
        # Remove single line comments
        source = re.sub(r"//[^\n]*", "", source)
        # Remove multi-line comments
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        # Remove single and double quoted strings to avoid false positives
        # We don't strip backticks (template literals) to avoid missing legitimate calls in ${...}
        source = re.sub(r"(['\"])(?:(?!\1|\\).|\\.)*\1", " ", source)
        return source

    def _is_called(self, var: str, content: str) -> bool:
        clean = self._strip_comments(content)
        # Use word boundaries and negative lookbehind to avoid method chains and substring matches
        pattern = rf"(?<![.\w])\b{re.escape(var)}\s*\("
        return bool(re.search(pattern, clean))

    def _build_contract_key(self, resolved_module_path: str, symbol_name: str) -> str:
        normalized = resolved_module_path.strip("/").replace("\\", "/")
        return f"internal://{normalized}#{symbol_name}"

    def _find_balanced(self, text: str, start_index: int, open_char: str = "(", close_char: str = ")") -> str:
        """Finds the content within balanced characters starting from start_index."""
        depth = 0
        in_string = None
        for i in range(start_index, len(text)):
            c = text[i]
            if in_string:
                if c == in_string and (i == 0 or text[i-1] != "\\"):
                    in_string = None
            elif c in ("'", '"', "`"):
                in_string = c
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return text[start_index+1:i]
        return None

    def extract_payload_shape(self, payload_str: str) -> Dict[str, Any]:
        shape = {}
        payload_str = payload_str.strip()
        
        # 1. Strip trailing type assertions (e.g., 'as UserRequest')
        # We look for ' as ' followed by something that isn't a brace or comma
        payload_str = re.split(r"\s+as\s+[a-zA-Z_$][\w$<>\[\]]*$", payload_str)[0].strip()

        if not payload_str:
            return shape

        # 2. Case: Simple variable reference
        if re.match(r"^[a-zA-Z_$][\w$]*$", payload_str):
            shape["__ref"] = payload_str
            shape["__shape"] = "variable_ref"
            return shape

        # 3. Case: Object literal
        if payload_str.startswith("{") and payload_str.endswith("}"):
            inner = payload_str[1:-1]
            depth = 0
            in_string = None
            i = 0
            while i < len(inner):
                c = inner[i]
                if in_string:
                    if c == in_string and (i == 0 or inner[i-1] != "\\"):
                        in_string = None
                elif c in ("'", '"', "`"):
                    in_string = c
                elif c in ("{", "[", "("):
                    depth += 1
                elif c in ("}", "]", ")"):
                    depth -= 1
                elif depth == 0:
                    # Look for key: (top-level only)
                    key_match = re.match(r"\s*(\w+)\s*:", inner[i:])
                    if key_match:
                        shape[key_match.group(1)] = "unknown"
                        i += key_match.end() - 1
                    # Look for spread ...var (top-level only)
                    spread_match = re.match(r"\s*\.\.\.\s*(\w+)", inner[i:])
                    if spread_match:
                        shape[f"...{spread_match.group(1)}"] = "spread_ref"
                        i += spread_match.end() - 1
                i += 1
        return shape

    def extract(self, content: str, file_path: str = None) -> List[Dict[str, Any]]:
        boundaries = []

        # 1. Identify gRPC Clients
        # Matches: const client = new auth_server(...)
        client_matches = re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*new\s+([\w_]+)\(", content)
        clients = {m.group(1): m.group(2) for m in client_matches}

        # 2. Identify Method Calls on those clients
        # Matches: client.ValidateToken({ ... }, ...) or client.ValidateToken(request)
        for client_var, service_name in clients.items():
            method_pattern = fr"{client_var}\.(\w+)\("
            for m in re.finditer(method_pattern, content):
                method_name = m.group(1)
                start_of_args = m.end() - 1
                payload_raw = self._find_balanced(content, start_of_args)
                
                if payload_raw is None:
                    continue
                
                payload_raw = payload_raw.strip()
                # Extract payload shape using the new robust helper
                payload_shape = self.extract_payload_shape(payload_raw)

                # DETECTION: Look for bypassCache: true
                if re.search(r"bypassCache\s*:\s*true", payload_raw):
                    payload_shape["__ORCHESTRATION_BYPASS__"] = "true"

                normalized_service = service_name.replace("_", ".")

                boundaries.append({
                    "role": "caller",
                    "contract_key": f"grpc://{normalized_service}/{method_name}",
                    "payload_shape": payload_shape
                })

        # 3. INTERNAL ORCHESTRATION: Detect imports/exports from lib/ or other internal modules
        # Matches: import { X } from "../lib/Y"
        import_matches = re.finditer(r"(?:import|export)\s+\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]", content)
        for m in import_matches:
            imported_vars = [v.strip() for v in m.group(1).split(",")]
            import_path = m.group(2)
            
            # If it's an internal-looking path
            if import_path.startswith(".") or import_path.startswith("@/"):
                for var in imported_vars:
                    # Also look for calls to this var
                    if self._is_called(var, content):
                        if self.resolver and file_path:
                            resolved = self.resolver.resolve(import_path, file_path)
                            contract_key = self._build_contract_key(resolved, var)
                        else:
                            contract_key = f"internal://{import_path}/{var}"

                        boundaries.append({
                            "role": "caller",
                            "contract_key": contract_key,
                            "payload_shape": {"type": "internal_call"}
                        })

        # Callee side: Detect exported functions, arrow functions, and classes
        if self.resolver and file_path:
            module_path = self.resolver.canonical_path(file_path)
        else:
            module_path = None

        # ZOD ANCHORS: Detect exported Zod schemas
        zod_anchors = self._discover_zod_anchors(content)
        for anchor in zod_anchors:
            if module_path:
                contract_key = self._build_contract_key(module_path, anchor)
            else:
                contract_key = f"internal://{anchor}"
            
            boundaries.append({
                "role": "callee",
                "contract_key": contract_key,
                "payload_shape": {"type": "zod_anchor"}
            })

        # 1. Named function declarations: export [async] function name(...)
        named_func_matches = re.finditer(r"export\s+(?:async\s+)?function\s*(?:\*\s*)?(\w+)\s*\(", content)
        for m in named_func_matches:
            func_name = m.group(1)
            if module_path:
                contract_key = self._build_contract_key(module_path, func_name)
            else:
                contract_key = f"internal://{func_name}"

            boundaries.append({
                "role": "callee",
                "contract_key": contract_key,
                "payload_shape": {"type": "internal_call"}
            })

        # 2. Arrow functions / Const exports: export const name = (...) => ...
        arrow_matches = re.finditer(r"export\s+(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w_]+)\s*=>", content)
        for m in arrow_matches:
            func_name = m.group(1)
            if module_path:
                contract_key = self._build_contract_key(module_path, func_name)
            else:
                contract_key = f"internal://{func_name}"

            boundaries.append({
                "role": "callee",
                "contract_key": contract_key,
                "payload_shape": {"type": "internal_call"}
            })

        # 3. Default exports: export default [function|class] name ...
        default_matches = re.finditer(r"export\s+default\s+(?:async\s+)?(?:function|class)\s+(\w+)", content)
        for m in default_matches:
            name = m.group(1)
            if module_path:
                contract_key = self._build_contract_key(module_path, name)
            else:
                contract_key = f"internal://{name}"

            boundaries.append({
                "role": "callee",
                "contract_key": contract_key,
                "payload_shape": {"type": "internal_call"}
            })
        
        # 4. Anonymous default exports: export default (...) => ...
        if re.search(r"export\s+default\s+(?:async\s+)?(?:\([^)]*\)|[\w_]+)\s*=>", content):
            if module_path:
                contract_key = self._build_contract_key(module_path, "default")
            else:
                contract_key = "internal://default"

            boundaries.append({
                "role": "callee",
                "contract_key": contract_key,
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
