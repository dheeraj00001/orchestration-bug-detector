import os
import json
import re
from pathlib import Path

# Tier 1: Strong Edges (Hard Contracts)
STRONG_SIGNALS = [
    r'\.proto$',
    r'\.graphql$',
    r'\.avsc$',
    r'terraform/.*\.tf$',
]

# Tier 2: Medium Edges (Soft Contracts)
MEDIUM_SIGNALS = {
    'package.json': [r'"@company/[^"]*"'],
    'go.mod': [r'company/[^\s\n]*'],
    'requirements.txt': [r'company-[^\s\n]*'],
    'pyproject.toml': [r'company-[^\s\n]*'],
}

# Tier 3: Weak Edges (Contextual Clues)
WEAK_SIGNALS = {
    'package.json': ['amqplib', 'kafkajs', 'grpc', 'axios', 'requests'],
    'go.mod': ['grpc', 'amqp'],
    'requirements.txt': ['pika', 'grpcio', 'requests'],
}

from .registry import ModuleRegistry

def generate_module_map(root_path):
    root = Path(root_path)
    registry = ModuleRegistry(root)
    modules = {}

    # Pass 1: Identify Nodes (Module Boundaries)
    for path in root.rglob('*'):
        if path.is_file():
            module_name = registry.get_module_name(path.relative_to(root))
            if module_name not in modules:
                # Find the marker file for this module to determine type
                marker_type = "unknown"
                module_dir = root / (module_name if module_name != 'root' else '')
                for marker in registry.MODULE_MARKERS:
                    if (module_dir / marker).exists():
                        marker_type = marker
                        break
                
                modules[module_name] = {
                    "path": module_name,
                    "type": marker_type,
                    "edges": {
                        "strong": [],
                        "medium": [],
                        "weak": []
                    }
                }

    # Pass 2: Identify Edges (Heuristics)
    for mod_path, data in modules.items():
        mod_dir = root / (mod_path if mod_path != 'root' else '')
        
        # Scan for Strong Signals (Files)
        for pattern in STRONG_SIGNALS:
            for match in mod_dir.rglob('*'):
                if re.search(pattern, str(match.name)):
                    data["edges"]["strong"].append(str(match.relative_to(mod_dir)))

        # Scan for Medium/Weak Signals (Inside config files)
        config_file = mod_dir / data["type"]
        if config_file.exists():
            try:
                from .safe_fs import SafeFileSystem
                fs = SafeFileSystem()
                content = fs.read_text(config_file)
                
                # Medium
                for pattern in MEDIUM_SIGNALS.get(data["type"], []):
                    matches = re.findall(pattern, content)
                    data["edges"]["medium"].extend(matches)
                
                # Weak
                for keyword in WEAK_SIGNALS.get(data["type"], []):
                    if keyword in content:
                        data["edges"]["weak"].append(keyword)
            except Exception:
                pass

    return modules

if __name__ == "__main__":
    import sys
    root_to_scan = sys.argv[1] if len(sys.argv) > 1 else "."
    result = generate_module_map(root_to_scan)
    print(json.dumps(result, indent=2))
