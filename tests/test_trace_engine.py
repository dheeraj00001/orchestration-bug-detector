import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.trace_engine import TraceEngine

def test_trace_engine_end_to_end():
    # ARRANGE: Real code snippets from different languages
    go_content = """
package auth
type server struct{}
func (s *server) ValidateToken(ctx context.Context, in *pb.TokenRequest) (*pb.TokenResponse, error) {
    return nil, nil
}
"""
    
    node_content = """
const client = new auth_server('localhost', credentials);
client.ValidateToken({ user_id: '123' }, (err, res) => {});
"""

    engine = TraceEngine({
        "auth.go": go_content,
        "checkout.ts": node_content
    })

    # ACT: Process both files in a zone
    result = engine.trace_zone({
        "auth.go": {},
        "checkout.ts": {}
    })

    # ASSERT: One stitched boundary detected
    assert len(result["boundaries"]) == 1
    boundary = result["boundaries"][0]
    
    assert "UserService" in boundary["contract_key"]

if __name__ == "__main__":
    pytest.main([__file__])
