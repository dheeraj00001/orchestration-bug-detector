import json
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Ensure the project root is in the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback or instruction for user to install dependency
    print("Error: 'mcp' library not found. Please install with 'pip install mcp'")
    sys.exit(1)

from scripts.engine import DiscoveryEngine
from scripts.trace_engine import TraceEngine
from scripts.synthesis import SynthesisEngine

# Initialize the FastMCP server
mcp = FastMCP("Orchestration Bug Detector")

# Configure logging to stderr
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("mcp-server")

# -----------------------------------------------------------------------------
# Tool 1: generate_module_map
# -----------------------------------------------------------------------------
@mcp.tool()
def generate_module_map(root_path: str) -> str:
    """
    Generates a high-level, weighted dependency map of a monorepo.
    Use this FIRST to identify suspicious cross-service paths before drilling down.
    
    Args:
        root_path: The absolute or relative path to the root of the monorepo to scan.
    """
    logger.info(f"Generating module map for: {root_path}")
    try:
        engine = DiscoveryEngine()
        result = engine.generate(root_dir=root_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error generating module map: {e}")
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# Tool 2: extract_contract_graph
# -----------------------------------------------------------------------------
@mcp.tool()
def extract_contract_graph(directories: List[str]) -> str:
    """
    Performs deterministic, polyglot Contract-Key Resolution on specific directories.
    Use this SECOND, after generate_module_map identifies a suspicious path.
    
    Args:
        directories: A list of service directories to scan (e.g., ["services/auth", "services/payments"]).
    """
    logger.info(f"Extracting contract graph for directories: {directories}")
    try:
        engine = TraceEngine()
        files_to_process = []
        
        # Extensions we support
        EXTENSIONS = {".go": "go", ".ts": "node", ".js": "node"}

        for dir_path in directories:
            path = Path(dir_path)
            if not path.exists():
                continue
                
            for file_path in path.rglob('*'):
                if file_path.is_file() and file_path.suffix in EXTENSIONS:
                    try:
                        files_to_process.append({
                            "path": str(file_path),
                            "content": file_path.read_text(encoding='utf-8'),
                            "language": EXTENSIONS[file_path.suffix]
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read {file_path}: {e}")

        result = engine.trace(files_to_process)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error extracting contract graph: {e}")
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# Tool 3: synthesize_findings
# -----------------------------------------------------------------------------
@mcp.tool()
def synthesize_findings(findings: List[Dict[str, Any]], service_directory: str) -> str:
    """
    Validates potential bug findings against global context to reduce false positives.
    Use this THIRD, right before reporting bugs to the user.
    
    Args:
        findings: A list of dictionaries containing bug details.
        service_directory: The root directory of the service to search for global middleware.
    """
    logger.info(f"Synthesizing {len(findings)} findings for: {service_directory}")
    try:
        engine = SynthesisEngine()
        
        # Simulate RLM Search for middleware/interceptors in the target service
        service_path = Path(service_directory)
        middleware_evidence = []
        for file in service_path.rglob('*'):
            if file.is_file() and ("middleware" in file.name.lower() or "interceptor" in file.name.lower()):
                try:
                    middleware_evidence.append({
                        "file": str(file),
                        "content": file.read_text(encoding='utf-8')
                    })
                except:
                    pass

        result = engine.synthesize(findings, middleware_evidence)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error synthesizing findings: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run(transport='stdio')
