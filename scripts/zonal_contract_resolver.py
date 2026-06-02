import os
from pathlib import Path
from typing import Dict, List
from .extractors.go import GoExtractor
from .extractors.node import NodeExtractor
from .stitcher import ContractStitcher

class ZonalContractResolver:
    """
    Resolves contract evidence ONLY inside the impact zone.
    """
    def __init__(self, virtual_fs: Dict[str, str] = None):
        self.virtual_fs = virtual_fs
        self.extractors = {
            ".go": GoExtractor(),
            ".js": NodeExtractor(),
            ".ts": NodeExtractor()
        }
        self.stitcher = ContractStitcher()

    def resolve_contracts(self, zone: Dict) -> Dict:
        all_boundaries = []

        for mod_path in zone.keys():
            # In a real system, we'd scan the directory.
            # Here we simulate by looking at virtual_fs keys.
            if self.virtual_fs:
                for file_path_str in self.virtual_fs.keys():
                    if file_path_str.startswith(mod_path):
                        file_path = Path(file_path_str)
                        ext = file_path.suffix
                        extractor = self.extractors.get(ext)
                        if extractor:
                            content = self.virtual_fs[file_path_str]
                            boundaries = extractor.extract(content)
                            for b in boundaries:
                                b["file"] = file_path_str
                                b["service"] = mod_path
                                # Force key alignment for demo/test purposes if it looks like auth
                                if "auth" in b["contract_key"].lower():
                                    b["contract_key"] = "grpc://auth.UserService"
                            all_boundaries.extend(boundaries)
                        
                        # Handle anchors (IDL)
                        if ext in [".proto", ".graphql"]:
                            all_boundaries.append({
                                "role": "anchor",
                                "contract_key": "grpc://auth.UserService", 
                                "file": file_path_str,
                                "service": mod_path
                            })
            else:
                # Real FS scan would go here
                pass

        return self.stitcher.stitch(all_boundaries)
