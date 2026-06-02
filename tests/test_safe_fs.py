import pytest
from pathlib import Path
from scripts.safe_fs import SafeFileSystem

def test_safe_read_text_binary(tmp_path):
    fs = SafeFileSystem()
    binary_file = tmp_path / "test.bin"
    with open(binary_file, "wb") as f:
        f.write(b"\xb5\x00\xff")
    
    # Should not crash, should return empty or sanitized string
    content = fs.read_text(binary_file)
    assert isinstance(content, str)

def test_safe_read_text_valid(tmp_path):
    fs = SafeFileSystem()
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello world")
    
    assert fs.read_text(txt_file) == "hello world"

def test_file_filtering():
    fs = SafeFileSystem(ignored_extensions=[".bin", ".png", ".exe"])
    assert fs.is_safe(Path("code.py")) is True
    assert fs.is_safe(Path("image.png")) is False
    assert fs.is_safe(Path("asset.bin")) is False
