import pytest
import sys
import os

# Ensure the scripts directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.extractors.go import GoExtractor
from scripts.extractors.node import NodeExtractor

def test_go_extractor_identifies_grpc_server():
    # ARRANGE: A simplified Go gRPC server implementation snippet
    content = """
    package auth

    type server struct{}

    func (s *server) ValidateToken(ctx context.Context, in *pb.TokenRequest) (*pb.TokenResponse, error) {
        // Logic here
        return &pb.TokenResponse{Valid: true}, nil
    }
    """
    
    extractor = GoExtractor()
    
    # ACT
    boundaries = extractor.extract(content)
    
    # ASSERT
    assert len(boundaries) == 1
    boundary = boundaries[0]
    
    assert boundary["role"] == "callee"
    assert boundary["contract_key"] == "grpc://auth.server/ValidateToken"
    assert "pb.TokenRequest" in boundary["payload_shape"]["in"]

def test_node_extractor_identifies_grpc_client():
    # ARRANGE: A simplified Node.js gRPC client call snippet
    content = """
    const client = new UserService('localhost:50051', grpc.credentials.createInsecure());
    client.validateToken({ user_id: '123', token: 'abc' }, (err, response) => {
        // ...
    });
    """
    extractor = NodeExtractor()

    # ACT
    boundaries = extractor.extract(content)

    # ASSERT
    assert len(boundaries) == 1
    boundary = boundaries[0]

    assert boundary["role"] == "caller"
    assert boundary["contract_key"] == "grpc://UserService/validateToken"
    assert "user_id" in boundary["payload_shape"]
    assert "token" in boundary["payload_shape"]

if __name__ == "__main__":
    pytest.main([__file__])
