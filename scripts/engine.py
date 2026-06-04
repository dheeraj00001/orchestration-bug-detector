import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from .registry import ModuleRegistry
from .evidence_resolver import EvidenceResolver
from .zone_explorer import ZonalExplorer
from .typescript_resolver import TypeScriptResolver

from .safe_fs import SafeFileSystem

class DiscoveryEngine:
    def __init__(self, virtual_fs: Dict[str, str] = None):
        self.virtual_fs = virtual_fs
        self.registry = None
        self.ts_resolver = None
        self.evidence_resolver = EvidenceResolver()
        self.fs = SafeFileSystem()
        self._file_index = set()

    def _read_content(self, file_path: Path) -> str:
        if self.virtual_fs is not None:
            return self.virtual_fs.get(str(file_path), "")
        return self.fs.read_text(file_path)

    HARD_EXCLUDE_DIRS = frozenset({
        "node_modules",
        ".next",
        ".temp_binaries",
        "dist",
        "build",
        ".turbo",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        "coverage",
        ".nyc_output",
    })

    HARD_EXCLUDE_EXTENSIONS = frozenset({
        ".lock", ".log", ".png", ".jpg", ".jpeg",
        ".gif", ".svg", ".woff", ".woff2", ".ttf",
        ".eot", ".ico", ".map", ".d.ts",
    })

    def _should_skip(self, file_path: Path) -> bool:
        """Check if a file should be skipped based on its path components."""
        for part in file_path.parts:
            if part in self.HARD_EXCLUDE_DIRS:
                return True
        return False

    def generate(self, root_dir: str = ".", seed_service: Optional[str] = None, max_distance: int = 2) -> Dict:
        root_path = Path(root_dir).resolve()
        self.registry = ModuleRegistry(root_path, virtual_fs=self.virtual_fs)
        self.ts_resolver = TypeScriptResolver(root_path, virtual_fs=self.virtual_fs)
        
        # ARCH-01: Re-initialize evidence resolver with root_dir for tier mapping
        self.evidence_resolver = EvidenceResolver(root_dir=root_dir)
        
        # Pass 1: Discovery (Raw nodes and files)
        raw_modules = self._perform_pass1(root_path)
        
        # Pass 2: Scoring (Promote edges to Tiers)
        scored_graph = self._perform_pass2(raw_modules)
        
        # Zonal Scoping
        if seed_service:
            explorer = ZonalExplorer(scored_graph)
            zone = explorer.explore(seed_service, max_distance=max_distance)
            
            # ARCH-01: Panic-Expand Fallback
            # If the zone is too small (e.g., only the seed), expand to 1-level imports
            if len(zone) < 2 and seed_service in scored_graph:
                zone = self._panic_expand(seed_service, scored_graph)
            
            return zone
        
        return scored_graph

    def _panic_expand(self, seed_service: str, scored_graph: Dict) -> Dict:
        """ARCH-01: Fallback when normal exploration fails to find boundaries."""
        zone = {seed_service: scored_graph[seed_service]}
        
        for edge in scored_graph[seed_service].get("edges", []):
            target = edge["target"]
            if target in scored_graph:
                zone[target] = scored_graph[target]
                # Label as unclassified import for the fallback
                edge["type"] = "UNCLASSIFIED_IMPORT"
        
        # Add fallback metadata to the seed module
        zone[seed_service]["metadata"] = {
            "fallback_mode": True,
            "fallback_reason": "sub_threshold_graph"
        }
        return zone

    def _perform_pass1(self, root_path: Path) -> Dict:
        modules = {}
        
        if self.virtual_fs:
            files = [Path(f) for f in self.virtual_fs.keys()]
        else:
            files = []
            for dirpath, dirs, filenames in os.walk(root_path, topdown=True):
                # Mutate dirs in-place to prune excluded directories at the OS level
                dirs[:] = [
                    d for d in dirs 
                    if d not in self.HARD_EXCLUDE_DIRS and not d.startswith('.')
                ]
                
                for filename in filenames:
                    if Path(filename).suffix in self.HARD_EXCLUDE_EXTENSIONS:
                        continue
                    full_path = Path(dirpath) / filename
                    files.append(full_path.relative_to(root_path))

        # BUG-02: Build file index for fallback resolution
        self._file_index = {str(f).replace("\\", "/") for f in files}

        for file_path in files:
            # Secondary safety check
            if self._should_skip(file_path):
                continue

            module_name = self.registry.get_module_name(file_path)
            if module_name not in modules:
                modules[module_name] = {"path": module_name, "files": {}, "raw_edges": [], "unresolved_imports": []}
            
            content = self._read_content(file_path if self.virtual_fs else root_path / file_path)
            modules[module_name]["files"][file_path.name] = content

            # Extract imports from source files
            if file_path.suffix in [".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs"]:
                imports = self.ts_resolver.extract_imports(content, str(file_path))
                for imp in imports:
                    if imp["resolutionStatus"] == "resolved":
                        target_file = Path(imp["resolvedTargetFile"])
                        target_module = self.registry.get_module_name(target_file)
                        if target_module != module_name:
                            modules[module_name]["raw_edges"].append({
                                "target": target_module, 
                                "type": "import", 
                                "details": imp
                            })
                    elif imp["resolutionStatus"] == "unresolved":
                        # PRD: Treat unresolved aliases as data, not failure
                        # FIX: Even unresolved internal-looking imports should be tracked
                        spec = imp.get("specifier", "")
                        if spec.startswith(".") or spec.startswith("@/"):
                            modules[module_name]["unresolved_imports"].append(imp)
                            # BUG-02: Use depth-iterative search fallback
                            resolved_fallback = self._resolve_with_fallback(spec)
                            if resolved_fallback:
                                target_file = Path(resolved_fallback)
                                target_guess = self.registry.get_module_name(target_file)
                            else:
                                # Final desperate fallback to first segment
                                target_guess = spec.replace("@/", "").split("/")[0]
                            
                            modules[module_name]["raw_edges"].append({
                                "target": target_guess,
                                "type": "import",
                                "details": imp,
                                "is_unresolved": True
                            })

            # Extract potential edges (declared dependencies)
            if file_path.name == "package.json":
                deps = re.findall(r'"@company/([^"]+)"', content)
                for d in deps:
                    modules[module_name]["raw_edges"].append({"target": f"services/{d}", "type": "package"})
            elif file_path.name == "go.mod":
                deps = re.findall(r'company/([^\s\n]+)', content)
                for d in deps:
                    modules[module_name]["raw_edges"].append({"target": f"services/{d}", "type": "go-mod"})
            elif file_path.name in ["requirements.txt", "pyproject.toml"]:
                deps = re.findall(r'company-([^\s\n=<>]+)', content)
                for d in deps:
                    modules[module_name]["raw_edges"].append({"target": f"services/{d}", "type": "python-dep"})

        return modules

    def _resolve_with_fallback(self, import_path: str) -> str | None:
        """BUG-02: Depth-iterative search for unresolved imports."""
        # Normalize: strip @/, ~/, src/
        clean_path = re.sub(r"^@/|^~/|^src/", "", import_path)
        parts = clean_path.split("/")

        for depth in range(len(parts), 0, -1):
            candidate_path = "/".join(parts[:depth])
            # Check for file or index.ts
            for ext in [".ts", ".tsx", ".js", ".jsx"]:
                full_candidate = f"{candidate_path}{ext}"
                if full_candidate in self._file_index:
                    return full_candidate
            
            index_candidate = f"{candidate_path}/index.ts"
            if index_candidate in self._file_index:
                return index_candidate

        return None

    def _perform_pass2(self, raw_modules: Dict) -> Dict:
        scored_graph = {}
        
        for mod_name, data in raw_modules.items():
            scored_graph[mod_name] = {
                "path": data["path"],
                "edges": [],
                "unresolved_imports": data.get("unresolved_imports", [])
            }
            
            for raw_edge in data["raw_edges"]:
                target = raw_edge["target"]
                if target in raw_modules:
                    score = self.evidence_resolver.score_edge(data, raw_modules[target], raw_edge)
                    scored_graph[mod_name]["edges"].append({
                        "target": target,
                        "tier": score["tier"],
                        "is_strong_candidate": score["is_strong_candidate"],
                        "type": raw_edge["type"],
                        "details": raw_edge.get("details")
                    })
        
        return scored_graph
