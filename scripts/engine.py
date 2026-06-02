import os
from pathlib import Path
from .signals import NodeResolver, GoResolver
from .registry import ModuleRegistry

# The Seam: Map file names/extensions to their specific resolver
RESOLVER_MAP = {
    "package.json": NodeResolver(),
    "go.mod": GoResolver(),
}

# Tier 1: Pure extension-based strong signals
STRONG_EXTENSIONS = {".proto", ".graphql", ".avsc"}

class DiscoveryEngine:
    def __init__(self, virtual_fs: dict = None):
        self.virtual_fs = virtual_fs
        self.registry = None

    def _read_content(self, file_path: Path) -> str:
        if self.virtual_fs is not None:
            return self.virtual_fs.get(str(file_path), "")
        return file_path.read_text()

    def generate(self, root_dir: str = ".") -> dict:
        root_path = Path(root_dir)
        self.registry = ModuleRegistry(root_path)
        modules = {}
        
        # Determine file list based on FS type
        if self.virtual_fs:
            files = [Path(f) for f in self.virtual_fs.keys()]
        else:
            files = self._walk_real_fs(root_path)

        for file_path in files:
            module_name = self.registry.get_module_name(file_path)
            file_name = file_path.name
            file_ext = file_path.suffix

            if module_name not in modules:
                modules[module_name] = {"edges": {"strong": [], "medium": [], "weak": []}}

            # 1. Check Tier 1 (Strong Signals)
            if file_ext in STRONG_EXTENSIONS:
                modules[module_name]["edges"]["strong"].append(file_name)

            # 2. Check Tier 2 & 3 via Resolvers
            if file_name in RESOLVER_MAP:
                content = self._read_content(file_path if self.virtual_fs else root_path / file_path)
                signals = RESOLVER_MAP[file_name].resolve(content)
                
                modules[module_name]["edges"]["medium"].extend(signals["medium"])
                modules[module_name]["edges"]["weak"].extend(signals["weak"])

        return modules

    def _walk_real_fs(self, root_path: Path):
        return [f for f in root_path.rglob('*') if f.is_file()]
