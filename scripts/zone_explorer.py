from typing import Dict, List, Set

class ZonalExplorer:
    """
    Implements bounded zonal exploration logic.
    """
    def __init__(self, graph: Dict):
        self.graph = graph

    def explore(self, seed_service: str, max_distance: int = 2, max_nodes: int = 30) -> Dict:
        if seed_service not in self.graph:
            return {}

        queue = [(seed_service, 0)]
        visited = {seed_service: 0}
        zone = {seed_service: self.graph[seed_service]}

        while queue:
            current_node, current_dist = queue.pop(0)

            if current_dist >= max_distance:
                continue

            for edge in self.graph.get(current_node, {}).get("edges", []):
                target = edge["target"]
                tier = edge.get("tier", 3)
                is_strong = edge.get("is_strong_candidate", False)

                # Tier-based pruning rules
                allowed = False
                if tier == 1 and current_dist < 2:
                    allowed = True
                elif (tier == 2 or tier == 3):
                    if current_dist == 0:
                        allowed = True
                    elif current_dist == 1 and is_strong:
                        # Follow Tier 2/3 strong candidates up to distance 2
                        allowed = True

                if allowed:
                    if target not in visited:
                        if len(zone) >= max_nodes:
                            raise RuntimeError("ZONE_OVERLOAD")
                        
                        visited[target] = current_dist + 1
                        if target in self.graph:
                            zone[target] = self.graph[target]
                            queue.append((target, current_dist + 1))

        return zone
