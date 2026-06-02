from pathlib import Path
from typing import List, Optional

class SafeFileSystem:
    """
    Adapter for safe file system operations.
    Prevents UnicodeDecodeError and provides centralized file filtering.
    """

    DEFAULT_IGNORED_EXTENSIONS = [
        ".bin", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".o"
    ]

    def __init__(self, ignored_extensions: List[str] = None):
        self.ignored_extensions = ignored_extensions or self.DEFAULT_IGNORED_EXTENSIONS

    def is_safe(self, path: Path) -> bool:
        """Determines if a file is safe to read as text."""
        return path.suffix.lower() not in self.ignored_extensions

    def read_text(self, path: Path, errors: str = "replace") -> str:
        """Reads file as text with error-tolerant decoding."""
        if not self.is_safe(path):
            return ""
        
        try:
            return path.read_text(encoding="utf-8", errors=errors)
        except Exception:
            return ""
