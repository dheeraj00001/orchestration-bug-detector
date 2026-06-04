import re
import json
import os
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
        """Reads a file from virtual_fs or real FS. 'path' is expected to be root-relative or absolute."""
        if self.virtual_fs is not None:
            # Try to get relative path string
            try:
                rel_path = str(path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(path)
            
            # Normalize for dict lookup (remove leading ./)
            rel_path = os.path.normpath(rel_path)
            if rel_path.startswith("./"): rel_path = rel_path[2:]
            if rel_path == ".": rel_path = ""
            
            return self.virtual_fs.get(rel_path, "")
            
        if path.exists() and path.is_file():
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    def _file_exists(self, path: Path) -> bool:
        """Checks if a file exists. 'path' is expected to be root-relative or absolute."""
        if self.virtual_fs is not None:
            try:
                rel = str(path.relative_to(self.root_dir))
            except ValueError:
                rel = str(path)
            
            rel = os.path.normpath(rel)
            if rel.startswith("./"): rel = rel[2:]
            if rel == ".": rel = ""
            
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
            # source_file is root-relative (e.g., 'app/api/route.ts')
            source_dir = Path(source_file).parent
            base_target = source_dir / specifier
            candidates = self._generate_candidates(base_target)
        
        # 3. Alias resolution (tsconfig paths)
        elif specifier.startswith("@"):
            paths = self.tsconfig.get("compilerOptions", {}).get("paths", {})
            baseUrl = self.tsconfig.get("compilerOptions", {}).get("baseUrl", ".")
            
            for alias, mapped_paths in paths.items():
                alias_pattern = "^" + alias.replace("*", "(.*)") + "$"
                match = re.match(alias_pattern, specifier)
                if match:
                    wildcard_val = match.group(1) if match.groups() else ""
                    for mapped_path in mapped_paths:
                        target_path = mapped_path.replace("*", wildcard_val)
                        # All paths relative to root_dir
                        base_target = Path(baseUrl) / target_path
                        candidates.extend(self._generate_candidates(base_target))
        
        # 4. Check candidates
        for candidate in candidates:
            # Normalize to root-relative path string
            norm_candidate = os.path.normpath(str(candidate))
            if norm_candidate.startswith("./"):
                norm_candidate = norm_candidate[2:]
            if norm_candidate.startswith("."):
                # Handle relative paths that went above root
                continue
            
            # Use root_dir to make it absolute-ish for _file_exists
            full_path = self.root_dir / norm_candidate
            if self._file_exists(full_path):
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

    def resolve(self, import_path: str, source_file: str) -> str:
        """Exposed method for BUG-01: Resolves an import to a canonical path."""
        res = self._resolve_path(source_file, import_path)
        if res["status"] == "resolved":
            return self.canonical_path(res["target"])
        return self.canonical_path(import_path) # Normalize even if unresolved

    def canonical_path(self, file_path: str) -> str:
        """Exposed method for BUG-01: Normalizes a path to a canonical root-relative format."""
        # Remove leading ./, /, @/, or ~/
        path_str = str(file_path).replace("\\", "/")
        
        # Regex to strip common prefixes and aliases
        path_str = re.sub(r"^(\./|/|@/|~/)", "", path_str)
        
        # Strip common prefixes that shouldn't be in the key
        for prefix in ["src/"]:
            if path_str.startswith(prefix):
                path_str = path_str[len(prefix):]
        
        # BUG-01: Strip extensions to ensure alignment
        # .ts, .tsx, .js, .jsx, .mts, .cts, .mjs, .cjs
        path_str = re.sub(r"\.(ts|tsx|js|jsx|mts|cts|mjs|cjs)$", "", path_str)
        
        # Handle index files: normalize 'path/index' to 'path'
        if path_str.endswith("/index"):
            path_str = path_str[:-6]
        if path_str == "index":
            path_str = ""
            
        return path_str

