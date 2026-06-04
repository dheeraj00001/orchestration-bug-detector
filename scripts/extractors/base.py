from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BoundaryExtractor(ABC):
    @abstractmethod
    def extract(self, content: str, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Parses file content and returns a list of boundary dictionaries.
        Each dict must contain: 'role', 'contract_key', 'payload_shape'
        """
        pass
