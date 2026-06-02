import pytest
from scripts.zone_explorer import ZonalExplorer

def test_zonal_explorer_distance_limit():
    # Setup a simple graph
    # Seed -> A (dist 1) -> B (dist 2) -> C (dist 3)
    graph = {
        "seed": {"edges": [{"target": "A", "tier": 1}]},
        "A": {"edges": [{"target": "B", "tier": 1}]},
        "B": {"edges": [{"target": "C", "tier": 1}]},
        "C": {"edges": []}
    }
    
    explorer = ZonalExplorer(graph)
    
    # Distance 1
    zone = explorer.explore(seed_service="seed", max_distance=1)
    assert "seed" in zone
    assert "A" in zone
    assert "B" not in zone
    
    # Distance 2
    zone = explorer.explore(seed_service="seed", max_distance=2)
    assert "B" in zone
    assert "C" not in zone

def test_zonal_explorer_max_nodes_overload():
    graph = {
        "seed": {"edges": [{"target": "A", "tier": 1}, {"target": "B", "tier": 1}]},
        "A": {"edges": []},
        "B": {"edges": []}
    }
    
    # Limit to 2 nodes (Seed + 1 neighbor)
    explorer = ZonalExplorer(graph)
    with pytest.raises(RuntimeError) as excinfo:
        explorer.explore(seed_service="seed", max_distance=2, max_nodes=2)
    assert "ZONE_OVERLOAD" in str(excinfo.value)

def test_zonal_explorer_tier_pruning():
    """
    Tier-based pruning rules:
    - follow Tier 1 edges up to distance 2;
    - follow Tier 2 and Tier 3 edges only at distance 1
    
    Tier boundary behavior:
    - the tier of a traversal step is determined by the edge being crossed, 
      not by the path taken to reach the source node.
    """
    graph = {
        "seed": {
            "edges": [
                {"target": "T1", "tier": 1},
                {"target": "T2", "tier": 2}
            ]
        },
        "T1": {
            "edges": [
                {"target": "T1_dist2_T1", "tier": 1}, # Should be followed (T1, dist 2)
                {"target": "T1_dist2_T2", "tier": 2}  # Should be pruned (T2, dist 2)
            ]
        },
        "T2": {
            "edges": [
                {"target": "T2_dist2_T1", "tier": 1}  # Should be followed (T1, dist 2)
            ]
        },
        "T1_dist2_T1": {"edges": []},
        "T1_dist2_T2": {"edges": []},
        "T2_dist2_T1": {"edges": []}
    }
    
    explorer = ZonalExplorer(graph)
    zone = explorer.explore(seed_service="seed", max_distance=2)
    
    assert "T1_dist2_T1" in zone
    assert "T2_dist2_T1" in zone # Followed because the EDGE is Tier 1
    assert "T1_dist2_T2" not in zone # Pruned because the EDGE is Tier 2 at dist 2

def test_zonal_explorer_strong_candidate():
    """
    Tier 2 and Tier 3 edges are followed at distance 2 
    if they are marked as 'is_strong_candidate'.
    """
    graph = {
        "seed": {
            "edges": [{"target": "A", "tier": 2, "is_strong_candidate": True}]
        },
        "A": {
            "edges": [
                {"target": "StrongB", "tier": 2, "is_strong_candidate": True},
                {"target": "WeakC", "tier": 2, "is_strong_candidate": False}
            ]
        },
        "StrongB": {"edges": []},
        "WeakC": {"edges": []}
    }
    
    explorer = ZonalExplorer(graph)
    zone = explorer.explore(seed_service="seed", max_distance=2)
    
    assert "StrongB" in zone
    assert "WeakC" not in zone
