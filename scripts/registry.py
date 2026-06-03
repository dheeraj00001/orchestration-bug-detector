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
        root_abs = self.root_dir.resolve()
        if self.virtual_fs is not None:
            abs_path = root_abs / file_path
        else:
            abs_path = (root_abs / file_path).resolve()
        
        # Check cache
        if abs_path in self._module_cache:
            return self._module_cache[abs_path]

        try:
            rel_path = abs_path.relative_to(root_abs)
            parts = rel_path.parts
            
            # Remove 'src' prefix if present
            if len(parts) > 0 and parts[0] == "src":
                parts = parts[1:]
                
            # HEURISTIC: Next.js App Router (app/**/route.ts, page.tsx, etc.)
            if len(parts) >= 1 and parts[0] == "app":
                # Special case: middleware.ts is often at root or src/
                if abs_path.name in ["route.ts", "route.js", "page.tsx", "page.jsx", "layout.tsx", "layout.jsx", "loading.tsx", "error.tsx"]:
                    # The module is the directory containing this entry point
                    module_name = "/".join(rel_path.parts[:-1]) # use original rel_path for module name
                    self._module_cache[abs_path] = module_name
                    return module_name
                    
            # HEURISTIC: Next.js Pages Router API (pages/api/**)
            if len(parts) >= 2 and parts[0] == "pages" and parts[1] == "api":
                module_name = "/".join(rel_path.parts[:-1])
                if module_name == "pages/api" or module_name == "src/pages/api":
                    module_name = str(rel_path) # the file itself is the endpoint
                self._module_cache[abs_path] = module_name
                return module_name
                
            # HEURISTIC: middleware.ts
            if rel_path.name in ["middleware.ts", "middleware.js"]:
                module_name = "middleware"
                self._module_cache[abs_path] = module_name
                return module_name

        except ValueError:
            pass

        # HEURISTIC 2: Generic Services folder (services/[service]/...)
        try:
            rel_path = abs_path.relative_to(root_abs)
            parts = rel_path.parts
            if len(parts) >= 2 and parts[0] == "services":
                module_name = f"services/{parts[1]}"
                self._module_cache[abs_path] = module_name
                return module_name
        except ValueError:
            pass

        current = abs_path if (self.virtual_fs or abs_path.is_dir()) else abs_path.parent
        
        while current != root_abs.parent:
            if any(self._exists(current / marker) for marker in self.MODULE_MARKERS):
                try:
                    rel_root = str(current.relative_to(root_abs))
                except ValueError:
                    rel_root = "root"
                if rel_root == ".": rel_root = "root"
                self._module_cache[abs_path] = rel_root
                return rel_root
            
            if current == root_abs:
                break
            current = current.parent

        self._module_cache[abs_path] = "root"
        return "root"
