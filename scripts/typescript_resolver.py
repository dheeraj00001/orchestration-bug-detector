import re
import json
from pathlib import Path
from typing import Dict, List, Any

class TypeScriptResolver:
    """
    Resolves TypeScript/JavaScript imports using canonical rules.
    Supports tsconfig.json (paths, baseUrl), relative imports, and index fallbacks.
    """
    
    def __init__(self, root_dir: Path, virtual_fs: Dict[str, str] = None):
        self.root_dir = root_dir.resolve()
        self.virtual_fs = virtual_fs
        self.tsconfig = self._load_tsconfig()
        
    def _read_file(self, path: Path) -> str:
        if self.virtual_fs is not None:
            try:
                rel_path = str(path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(path)
            return self.virtual_fs.get(rel_path, "")
        if path.exists() and path.is_file():
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    def _file_exists(self, path: Path) -> bool:
        if self.virtual_fs is not None:
            try:
                rel = str(path.relative_to(self.root_dir))
            except ValueError:
                return False
            return rel in self.virtual_fs
        return path.is_file()

    def _load_tsconfig(self) -> Dict:
        # Simplified tsconfig loader
        # Try both tsconfig.json and jsconfig.json
        for config_name in ["tsconfig.json", "jsconfig.json"]:
            config_path = self.root_dir / config_name
            content = self._read_file(config_path)
            if content:
                try:
                    # Remove comments before parsing JSON (basic implementation)
                    content_no_comments = re.sub(r'//.*', '', content)
                    content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)
                    return json.loads(content_no_comments)
                except json.JSONDecodeError:
                    pass
        return {}

    def extract_imports(self, content: str, source_file: str) -> List[Dict[str, Any]]:
        """
        Extracts import specifiers from the given source file content.
        """
        imports = []
        
        # 1. import ... from 'X'
        # 2. import type ... from 'X'
        # 3. export ... from 'X'
        # Handles single and double quotes. Also handles bare imports: import 'X'
        pattern = r"(?:import|export)\s+(?:type\s+)?(?:.*?from\s+)?['\"]([^'\"]+)['\"]|import\(['\"]([^'\"]+)['\"]\)|require\(['\"]([^'\"]+)['\"]\)"
        
        matches = re.finditer(pattern, content)
        for match in matches:
            specifier = match.group(1) or match.group(2) or match.group(3)
            if specifier:
                resolution = self._resolve_path(source_file, specifier)
                imports.append({
                    "sourceFile": source_file,
                    "specifier": specifier,
                    "resolutionStatus": resolution["status"],
                    "resolvedTargetFile": resolution.get("target"),
                    "resolverReason": resolution.get("reason"),
                    "kind": "static" if match.group(1) else ("dynamic" if match.group(2) else "require")
                })
        return imports

    def _resolve_path(self, source_file: str, specifier: str) -> Dict[str, str]:
        # 1. External modules (simple heuristic)
        if not specifier.startswith(".") and not specifier.startswith("/") and not specifier.startswith("@"):
            return {"status": "external", "reason": "non_relative_no_alias"}
        
        candidates = []
        
        # 2. Relative resolution
        if specifier.startswith("."):
            source_dir = self.root_dir / Path(source_file).parent
            base_target = source_dir / specifier
            candidates = self._generate_candidates(base_target)
        
        # 3. Alias resolution (tsconfig paths)
        elif specifier.startswith("@"):
            # Try to resolve using tsconfig paths
            # Simplified: assuming {"@/*": ["*"]} or similar
            paths = self.tsconfig.get("compilerOptions", {}).get("paths", {})
            baseUrl = self.tsconfig.get("compilerOptions", {}).get("baseUrl", ".")
            
            for alias, mapped_paths in paths.items():
                # Convert "@/*" to "^@/(.*)$"
                alias_pattern = "^" + alias.replace("*", "(.*)") + "$"
                match = re.match(alias_pattern, specifier)
                if match:
                    wildcard_val = match.group(1) if match.groups() else ""
                    for mapped_path in mapped_paths:
                        # Convert "*" to wildcard_val
                        target_path = mapped_path.replace("*", wildcard_val)
                        base_target = self.root_dir / baseUrl / target_path
                        candidates.extend(self._generate_candidates(base_target))
        
        # 4. Check candidates
        for candidate in candidates:
            # Normalize path
            try:
                # If virtual_fs, we need relative path string
                norm_candidate = str(Path(candidate).resolve().relative_to(self.root_dir))
            except ValueError:
                norm_candidate = str(candidate)
                
            if self._file_exists(self.root_dir / norm_candidate if self.virtual_fs is None else Path(norm_candidate)):
                return {"status": "resolved", "target": norm_candidate, "reason": "found_candidate"}

        return {"status": "unresolved", "reason": "file_not_found"}

    def _generate_candidates(self, base_target: Path) -> List[Path]:
        """Generates possible file paths for a target (adding extensions, index files)."""
        exts = [".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs"]
        candidates = [base_target]
        for ext in exts:
            candidates.append(base_target.with_suffix(base_target.suffix + ext))
        
        # Index fallbacks
        for ext in exts:
            candidates.append(base_target / f"index{ext}")
            
        return candidates

