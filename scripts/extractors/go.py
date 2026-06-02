import re
from typing import List, Dict, Any
from .base import BoundaryExtractor

class GoExtractor(BoundaryExtractor):
    def extract(self, content: str) -> List[Dict[str, Any]]:
        boundaries = []
        
        # 1. Extract Package Name
        pkg_match = re.search(r"^\s*package\s+(\w+)", content, re.MULTILINE)
        pkg_name = pkg_match.group(1) if pkg_match else "PackageName"

        # 2. Extract Methods (Tracer Bullet Regex)
        # Matches: func (s *server) ValidateToken(ctx context.Context, in *pb.TokenRequest) (*pb.TokenResponse, error)
        pattern = r"func\s+\(\w+\s+\*?(\w+)\)\s+(\w+)\s*\([^,]+,\s+in\s+([\w\.\*]+)\)"
        
        matches = re.finditer(pattern, content)
        
        for match in matches:
            receiver_type = match.group(1)
            method_name = match.group(2)
            input_type = match.group(3)
            
            # Normalize contract key to ignore receiver pointers for now
            boundaries.append({
                "role": "callee",
                "contract_key": f"grpc://{pkg_name}.{receiver_type}/{method_name}", 
                "payload_shape": {
                    "in": input_type
                }
            })
            
        return boundaries
