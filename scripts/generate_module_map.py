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

HARD_EXCLUDE_DIRS = frozenset({
    "node_modules", ".next", ".temp_binaries", "dist", "build", ".turbo",
    ".git", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
    "coverage", ".nyc_output",
})

HARD_EXCLUDE_EXTENSIONS = frozenset({
    ".lock", ".log", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".map", ".d.ts",
})

SOURCE_PATTERNS = re.compile(
    r"\.(ts|tsx|js|jsx|py|go|java|rs|proto|graphql|tf)$"
)

ZOD_EXPORT_PATTERN = re.compile(
    r"export\s+(?:const|let)\s+(\w+)\s*=\s*z\."
)

MAX_MAP_PAYLOAD_BYTES = 512 * 1024

from .registry import ModuleRegistry

def _is_source_file(path: str) -> bool:
    return bool(SOURCE_PATTERNS.search(path))

def _discover_zod_anchors(content: str) -> list[str]:
    return ZOD_EXPORT_PATTERN.findall(content)

def _get_tier(file_path: str) -> int | None:
    # BUG-01: Use evidence_resolver for tiers if available
    try:
        from .evidence_resolver import EvidenceResolver
        resolver = EvidenceResolver()
        return resolver.get_tier(file_path)
    except:
        # Fallback to simple directory-based tiering
        TIER_MAP = {
            "app": 1, "pages": 1, "components": 1, "features": 1,
            "services": 2, "lib": 3, "utils": 3, "shared": 3,
            "config": 4, "types": 4,
        }
        top_dir = file_path.split("/")[0]
        return TIER_MAP.get(top_dir)

def _detect_idl_drift(modules: dict, zod_anchor_registry: dict, root: Path) -> list[dict]:
    findings = []
    anchor_graph = {} # anchor_key -> list of module paths

    # 1. Build anchor graph
    for mod_path, data in modules.items():
        mod_dir = root / (mod_path if mod_path != 'root' else '')
        for dirpath, dirs, files in os.walk(mod_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in HARD_EXCLUDE_DIRS and not d.startswith('.')]
            for filename in files:
                if not _is_source_file(filename):
                    continue
                path = Path(dirpath) / filename
                try:
                    content = path.read_text(errors='ignore')
                    # Look for imports: import { UserSchema } from ...
                    import_matches = re.finditer(r"import\s+\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]", content)
                    for m in import_matches:
                        imported_vars = [v.strip() for v in m.group(1).split(",")]
                        import_path = m.group(2)
                        # We would need to resolve import_path to check if it matches a Zod anchor
                        # For simplicity, we'll check if any imported_var is in any zod_anchor_registry entry
                        for var in imported_vars:
                            for anchor_file, anchors in zod_anchor_registry.items():
                                if var in anchors:
                                    # If the import path seems to point to anchor_file
                                    # (Heuristic: anchor_file name in import_path or vice versa)
                                    if Path(anchor_file).stem in import_path or import_path in str(anchor_file):
                                        key = f"{anchor_file}#{var}"
                                        if key not in anchor_graph:
                                            anchor_graph[key] = set()
                                        anchor_graph[key].add(mod_path)
                except:
                    pass

    # 2. Detect Drift
    for anchor_key, consumers in anchor_graph.items():
        tiers = { _get_tier(m) for m in consumers if _get_tier(m) is not None }
        # Add the tier of the anchor file itself
        anchor_file = anchor_key.split('#')[0]
        anchor_tier = _get_tier(anchor_file)
        if anchor_tier is not None:
            tiers.add(anchor_tier)

        if len(tiers) > 1:
            findings.append({
                "type": "general_insight",
                "title": f"Cross-Tier Contract Anchor: {anchor_key}",
                "description": f"Schema is consumed by modules in tiers {sorted(list(tiers))}. Changes are breaking changes.",
                "affected_modules": list(consumers),
                "severity": "warning",
                "evidence": {"anchor_key": anchor_key, "consumer_tiers": sorted(list(tiers))},
            })
    return findings

def _get_top_dirs(full_map: dict) -> list:
    dirs = {}
    for mod in full_map.keys():
        parts = mod.split('/')
        if parts[0]:
            dirs[parts[0]] = dirs.get(parts[0], 0) + 1
    return sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:10]

def _get_top_n_by_degree(full_map: dict, n: int = 50) -> list:
    degrees = []
    for mod_path, data in full_map.items():
        degree = len(data["edges"]["strong"]) + len(data["edges"]["medium"]) + len(data["edges"]["weak"])
        degrees.append({"path": mod_path, "degree": degree})
    return sorted(degrees, key=lambda x: x["degree"], reverse=True)[:n]

def _summarize_map(full_map: dict) -> dict:
    return {
        "summary_mode": True,
        "total_modules": len(full_map),
        "top_level_directories": _get_top_dirs(full_map),
        "high_connectivity_modules": _get_top_n_by_degree(full_map, n=50),
        "hint": "Full map exceeds size threshold. Run with a scoped root_path to get full detail.",
    }

def generate_module_map(root_path):
    root = Path(root_path)
    registry = ModuleRegistry(root)
    modules = {}
    zod_anchor_registry = {} # file_path -> list of symbols

    # Pass 1: Identify Nodes (Module Boundaries) and Zod Anchors
    discovered_files = []
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in HARD_EXCLUDE_DIRS and not d.startswith('.')]
        for filename in files:
            if Path(filename).suffix in HARD_EXCLUDE_EXTENSIONS:
                continue
            if not _is_source_file(filename):
                continue
            
            full_path = Path(dirpath) / filename
            discovered_files.append(full_path)
            
            # ARCH-04 Step 1: Discover Zod Anchors
            try:
                content = full_path.read_text(errors='ignore')
                anchors = _discover_zod_anchors(content)
                if anchors:
                    zod_anchor_registry[str(full_path.relative_to(root))] = anchors
            except:
                pass

    for path in discovered_files:
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
        
        # Optimized Pass 2: Walk mod_dir once and check all patterns
        for dirpath, dirs, files in os.walk(mod_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in HARD_EXCLUDE_DIRS and not d.startswith('.')]
            for filename in files:
                if Path(filename).suffix in HARD_EXCLUDE_EXTENSIONS:
                    continue
                if not _is_source_file(filename):
                    continue
                
                path = Path(dirpath) / filename
                for pattern in STRONG_SIGNALS:
                    if re.search(pattern, str(path.name)):
                        data["edges"]["strong"].append(str(path.relative_to(mod_dir)))

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

    # ARCH-04 Step 3: IDL Drift Detection
    findings = _detect_idl_drift(modules, zod_anchor_registry, root)
    if findings:
        modules["__findings__"] = findings

    # Check payload size
    payload = json.dumps(modules)
    if len(payload.encode()) > MAX_MAP_PAYLOAD_BYTES:
        return _summarize_map(modules)

    return modules

if __name__ == "__main__":
    import sys
    root_to_scan = sys.argv[1] if len(sys.argv) > 1 else "."
    result = generate_module_map(root_to_scan)
    print(json.dumps(result, indent=2))
