from typing import List, Dict
from .extractors.go import GoExtractor
from .extractors.node import NodeExtractor
from .stitcher import ContractStitcher

class TraceEngine:
    """
    Orchestrates the Level 2 deterministic trace by coordinating language-specific
    extractors and the ContractStitcher.
    """
    def __init__(self):
        self.extractors = {
            "go": GoExtractor(),
            "node": NodeExtractor()
        }
        self.stitcher = ContractStitcher()

    def trace(self, files: List[Dict]) -> Dict:
        all_boundaries = []

        for file_data in files:
            lang = file_data.get("language")
            content = file_data.get("content", "")
            path = file_data.get("path", "")

            extractor = self.extractors.get(lang)
            if extractor:
                boundaries = extractor.extract(content)
                # Decorate with file path info
                for b in boundaries:
                    b["file"] = path
                all_boundaries.extend(boundaries)

        return self.stitcher.stitch(all_boundaries)
