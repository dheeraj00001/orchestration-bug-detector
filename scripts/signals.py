import re
from abc import ABC, abstractmethod

class SignalResolver(ABC):
    @abstractmethod
    def resolve(self, content: str) -> dict:
        """Returns a dict with 'medium' and 'weak' signal lists."""
        pass

class NodeResolver(SignalResolver):
    def resolve(self, content: str) -> dict:
        medium = re.findall(r'"@company/[^"]+"', content)
        weak_keywords = ['amqplib', 'kafkajs', 'grpc', 'axios', 'requests']
        weak = [kw for kw in weak_keywords if kw in content]
        return {"medium": medium, "weak": weak}

class GoResolver(SignalResolver):
    def resolve(self, content: str) -> dict:
        # Matches 'company/anything' in require statements
        medium = re.findall(r'company/[^\s\n]+', content)
        weak_keywords = ['grpc', 'amqp']
        weak = [kw for kw in weak_keywords if kw in content]
        return {"medium": medium, "weak": weak}

class ProtoResolver(SignalResolver):
    def resolve(self, content: str) -> dict:
        # For IDLs, the file's existence is the strong signal. 
        return {"medium": [], "weak": []}
