from pathlib import Path

class ModuleRegistry:
    """Encapsulates the locality of module boundaries and path grouping."""
    
    MODULE_MARKERS = ["package.json", "go.mod", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle"]

    def __init__(self, root_dir: Path, virtual_fs: dict = None):
        self.root_dir = root_dir
        self.virtual_fs = virtual_fs
        self._module_cache = {}

    def _exists(self, path: Path) -> bool:
        if self.virtual_fs is not None:
            # Normalize to relative path string for virtual_fs lookup
            try:
                rel_path = str(path.relative_to(self.root_dir))
                return rel_path in self.virtual_fs
            except ValueError:
                return False
        return path.exists()

    def get_module_name(self, file_path: Path) -> str:
        """Determines the module/service name for a given file path by finding its root."""
        if self.virtual_fs is not None:
            abs_path = self.root_dir / file_path
        else:
            abs_path = (self.root_dir / file_path).resolve()
        
        # Check cache
        if abs_path in self._module_cache:
            return self._module_cache[abs_path]

        current = abs_path if (self.virtual_fs or abs_path.is_dir()) else abs_path.parent
        
        while current != self.root_dir.parent:
            if any(self._exists(current / marker) for marker in self.MODULE_MARKERS):
                try:
                    rel_root = str(current.relative_to(self.root_dir))
                except ValueError:
                    rel_root = "root"
                if rel_root == ".": rel_root = "root"
                self._module_cache[abs_path] = rel_root
                return rel_root
            
            if current == self.root_dir:
                break
            current = current.parent

        self._module_cache[abs_path] = "root"
        return "root"
