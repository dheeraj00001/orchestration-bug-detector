from typing import Dict, List, Tuple
from .dre import DeterministicRuleEngine

class AnomalyDigester:
    """
    Applies DRE rules and generates prioritized vs full anomaly lists.
    """
    def __init__(self):
        self.dre = DeterministicRuleEngine()

    def digest(self, graph: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Processes the graph and returns (top_anomalies, all_anomalies).
        """
        all_anomalies = []
        top_anomalies = []

        for boundary in graph.get("boundaries", []):
            classification = self.dre.classify(boundary)
            
            # Enrich boundary with classification
            enriched = boundary.copy()
            enriched["dre_status"] = classification
            
            # Stable anomaly identifier (Simplified)
            enriched["anomaly_id"] = f"{classification}_{boundary.get('contract_key')}"
            
            all_anomalies.append(enriched)
            
            if self.dre.is_high_priority(boundary, classification):
                # Suppress MATCHED findings from top_anomalies
                if classification != "MATCHED":
                    top_anomalies.append(enriched)

        return top_anomalies, all_anomalies
