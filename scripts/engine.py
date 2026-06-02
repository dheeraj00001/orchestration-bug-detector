import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from .registry import ModuleRegistry
from .evidence_resolver import EvidenceResolver
from .zone_explorer import ZonalExplorer

from .safe_fs import SafeFileSystem

class DiscoveryEngine:
    def __init__(self, virtual_fs: Dict[str, str] = None):
        self.virtual_fs = virtual_fs
        self.registry = None
        self.evidence_resolver = EvidenceResolver()
        self.fs = SafeFileSystem()

    def _read_content(self, file_path: Path) -> str:
        if self.virtual_fs is not None:
            return self.virtual_fs.get(str(file_path), "")
        return self.fs.read_text(file_path)

    def generate(self, root_dir: str = ".", seed_service: Optional[str] = None, max_distance: int = 2) -> Dict:
        root_path = Path(root_dir).resolve()
        self.registry = ModuleRegistry(root_path, virtual_fs=self.virtual_fs)
        
        # Pass 1: Discovery (Raw nodes and files)
        raw_modules = self._perform_pass1(root_path)
        
        # Pass 2: Scoring (Promote edges to Tiers)
        scored_graph = self._perform_pass2(raw_modules)
        
        # Zonal Scoping
        if seed_service:
            explorer = ZonalExplorer(scored_graph)
            return explorer.explore(seed_service, max_distance=max_distance)
        
        return scored_graph

    def _perform_pass1(self, root_path: Path) -> Dict:
        modules = {}
        
        if self.virtual_fs:
            files = [Path(f) for f in self.virtual_fs.keys()]
        else:
            files = [f.relative_to(root_path) for f in root_path.rglob('*') if f.is_file()]

        for file_path in files:
            module_name = self.registry.get_module_name(file_path)
            if module_name not in modules:
                modules[module_name] = {"path": module_name, "files": {}, "raw_edges": []}
            
            content = self._read_content(file_path if self.virtual_fs else root_path / file_path)
            modules[module_name]["files"][file_path.name] = content

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

    def _perform_pass2(self, raw_modules: Dict) -> Dict:
        scored_graph = {}
        
        for mod_name, data in raw_modules.items():
            scored_graph[mod_name] = {
                "path": data["path"],
                "edges": []
            }
            
            for raw_edge in data["raw_edges"]:
                target = raw_edge["target"]
                if target in raw_modules:
                    score = self.evidence_resolver.score_edge(data, raw_modules[target], raw_edge)
                    scored_graph[mod_name]["edges"].append({
                        "target": target,
                        "tier": score["tier"],
                        "is_strong_candidate": score["is_strong_candidate"],
                        "type": raw_edge["type"]
                    })
        
        return scored_graph
