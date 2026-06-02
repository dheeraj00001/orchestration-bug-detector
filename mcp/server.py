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
def generate_module_map(root_path: str, seed_service: str = None, max_distance: int = 2) -> str:
    """
    Generates a high-level, weighted dependency map of a monorepo.
    Use this FIRST to identify suspicious cross-service paths before drilling down.
    
    Args:
        root_path: The absolute or relative path to the root of the monorepo to scan.
        seed_service: Optional. The name of the service to start exploration from (e.g., "services/auth").
        max_distance: Optional. The maximum distance to explore from the seed service. Defaults to 2.
    """
    logger.info(f"Generating module map for: {root_path} (seed: {seed_service}, dist: {max_distance})")
    try:
        engine = DiscoveryEngine()
        result = engine.generate(root_dir=root_path, seed_service=seed_service, max_distance=max_distance)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error generating module map: {e}")
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# Tool 2: extract_zonal_graph
# -----------------------------------------------------------------------------
@mcp.tool()
def extract_zonal_graph(seed_service: str, max_distance: int = 2, max_nodes: int = 30) -> str:
    """
    Performs Phase 2: Zonal Contract Resolution starting from a seed service.
    Use this SECOND, after generate_module_map identifies a suspicious path.
    
    Args:
        seed_service: The service to start exploration from.
        max_distance: Maximum distance to explore.
        max_nodes: Maximum nodes to include in the zone.
    """
    logger.info(f"Extracting zonal graph for seed: {seed_service} (dist: {max_distance})")
    try:
        # Phase 1: MAP (Discovery)
        discovery_engine = DiscoveryEngine()
        zone = discovery_engine.generate(seed_service=seed_service, max_distance=max_distance)
        
        # Phase 2: TRACE (Resolution)
        trace_engine = TraceEngine()
        result = trace_engine.trace_zone(zone)
        return json.dumps(result, indent=2)
    except RuntimeError as e:
        if "ZONE_OVERLOAD" in str(e):
            return json.dumps({"error": "ZONE_OVERLOAD", "message": str(e)})
        raise e
    except Exception as e:
        logger.error(f"Error extracting zonal graph: {e}")
        return json.dumps({"error": str(e)})

from scripts.digester import AnomalyDigester

# ... (rest of imports)

# -----------------------------------------------------------------------------
# Tool 3: run_dre_rules
# -----------------------------------------------------------------------------
@mcp.tool()
def run_dre_rules(graph: Dict[str, Any], output_dir: str = ".") -> str:
    """
    Performs Phase 3: Deterministic Classification on a contract graph.
    Returns the prioritized anomaly digest and writes all anomalies to disk.
    
    Args:
        graph: The stitched contract graph from extract_zonal_graph.
        output_dir: Optional. The directory where to save the anomaly JSON files. Defaults to ".".
    """
    logger.info(f"Running DRE rules on contract graph, output_dir: {output_dir}")
    try:
        digester = AnomalyDigester()
        top, all_anom = digester.digest(graph)
        
        # Ensure output_dir exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Write to disk as per PRD
        with open(os.path.join(output_dir, "top_anomalies.json"), "w") as f:
            json.dump(top, f, indent=2)
        with open(os.path.join(output_dir, "all_anomalies.json"), "w") as f:
            json.dump(all_anom, f, indent=2)
            
        return json.dumps(top, indent=2)
    except Exception as e:
        logger.error(f"Error running DRE rules: {e}")
        return json.dumps({"error": str(e)})

from scripts.orchestrator import SubagentOrchestrator
from scripts.interception_chain import InterceptionChain

# -----------------------------------------------------------------------------
# Tool 4: plan_subagent_tasks
# -----------------------------------------------------------------------------
@mcp.tool()
def plan_subagent_tasks(prioritized_digest: List[Dict[str, Any]]) -> str:
    """
    Performs Phase 4: DELEGATE. Generates targeted task payloads for subagents.
    
    Args:
        prioritized_digest: The list of top anomalies from run_dre_rules.
    """
    logger.info(f"Planning subagent tasks for {len(prioritized_digest)} anomalies")
    try:
        orchestrator = SubagentOrchestrator()
        tasks = orchestrator.plan_subagent_tasks(prioritized_digest)
        return json.dumps(tasks, indent=2)
    except Exception as e:
        logger.error(f"Error planning subagent tasks: {e}")
        return json.dumps({"error": str(e)})

# -----------------------------------------------------------------------------
# Tool 5: check_interception_chain
# -----------------------------------------------------------------------------
@mcp.tool()
def check_interception_chain(infra_evidence: List[str] = None, platform_evidence: List[str] = None, local_evidence: List[str] = None) -> str:
    """
    Resolves middleware in a fixed priority order: Infra > Platform > Local.
    Returns the layer at which the concern was resolved, or 'unresolved'.
    """
    try:
        chain = InterceptionChain()
        evidence = {
            "infra": infra_evidence or [],
            "platform": platform_evidence or [],
            "local": local_evidence or []
        }
        status, layer = chain.check_interception(evidence)
        return json.dumps({"status": status, "resolved_layer": layer})
    except Exception as e:
        return json.dumps({"error": str(e)})

from scripts.safe_fs import SafeFileSystem

# ... (rest of imports)

# -----------------------------------------------------------------------------
# Tool 6: synthesize_findings
# -----------------------------------------------------------------------------
@mcp.tool()
def synthesize_findings(findings: List[Dict[str, Any]], service_directory: str, output_dir: str = ".") -> str:
    """
    Performs Phase 4: SYNTHESIZE. Merges findings and renders the final report.
    
    Args:
        findings: A list of dictionaries containing subagent results.
        service_directory: The root directory of the service to search for global middleware.
        output_dir: Optional. The directory where to save the report files. Defaults to ".".
    """
    logger.info(f"Synthesizing {len(findings)} findings for: {service_directory}, output_dir: {output_dir}")
    try:
        engine = SynthesisEngine()
        fs = SafeFileSystem()
        
        # Simulate RLM Search for middleware/interceptors
        service_path = Path(service_directory)
        middleware_evidence = []
        if service_path.exists():
            for file in service_path.rglob('*'):
                if file.is_file() and fs.is_safe(file) and ("middleware" in file.name.lower() or "interceptor" in file.name.lower()):
                    try:
                        middleware_evidence.append({
                            "file": str(file),
                            "content": fs.read_text(file)
                        })
                    except:
                        pass

        result = engine.synthesize(findings, middleware_evidence, output_dir=output_dir)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error synthesizing findings: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run(transport='stdio')
