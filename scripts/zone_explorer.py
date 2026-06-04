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

        # Sequential Recovery Path per PRD:
        # 1. Full exploration
        # 2. Prune Tier 3 at dist >= 1
        # 3. Prune Tier 2 & 3 at dist >= 1
        # 4. Reduce distance (recursive)
        
        fallbacks = [
            {"prune": []},
            {"prune": [3]},
            {"prune": [2, 3]}
        ]

        for config in fallbacks:
            try:
                return self._do_explore(seed_service, max_distance, max_nodes, prune_tiers=config["prune"])
            except RuntimeError as e:
                if "ZONE_OVERLOAD" not in str(e):
                    raise e
                # Else: continue to next fallback in loop
        
        # If all pruning failed, reduce distance if possible
        if max_distance > 1:
            return self.explore(seed_service, max_distance - 1, max_nodes)
        
        # If distance reduction also fails or is impossible, raise final error
        raise RuntimeError("ZONE_OVERLOAD: All recovery paths exhausted.")

    def _do_explore(self, seed_service: str, max_distance: int, max_nodes: int, prune_tiers: List[int] = None) -> Dict:
        prune_tiers = prune_tiers or []
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

                # Tier-based pruning (Recovery Path)
                if tier in prune_tiers and current_dist >= 1:
                    continue

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
