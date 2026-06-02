from pathlib import Path

class ModuleRegistry:
    """Encapsulates the locality of module boundaries and path grouping."""
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def get_module_name(self, file_path: Path) -> str:
        """Determines the module/service name for a given file path."""
        try:
            rel_path = file_path.relative_to(self.root_dir)
        except ValueError:
            rel_path = file_path # Already relative or virtual

        parts = rel_path.parts
        
        # Heuristic for 'services/X'
        if len(parts) >= 2 and parts[0] == "services":
            return f"{parts[0]}/{parts[1]}"
        
        # Heuristic for 'infrastructure/X'
        if len(parts) >= 1 and parts[0] == "infrastructure":
            return "infrastructure/terraform"
            
        return "root"
