import pytest
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.typescript_resolver import TypeScriptResolver

def test_extract_imports():
    content = """
    import { foo } from "@/services/auth";
    import type { Bar } from './local';
    export { baz } from '../shared/utils';
    const x = await import('@/lazy/module');
    const y = require('commonjs-module');
    import "@/side-effects";
    """
    resolver = TypeScriptResolver(root_dir=Path("."))
    imports = resolver.extract_imports(content, source_file="src/app.ts")
    
    specifiers = [i["specifier"] for i in imports]
    assert "@/services/auth" in specifiers
    assert "./local" in specifiers
    assert "../shared/utils" in specifiers
    assert "@/lazy/module" in specifiers
    assert "commonjs-module" in specifiers
    assert "@/side-effects" in specifiers

def test_resolve_paths(tmp_path):
    # Setup mock file system
    # root/
    #   tsconfig.json
    #   src/
    #     app.ts
    #     local.ts
    #     shared/
    #       utils.ts
    #   services/
    #     auth.ts
    #     payment/
    #       index.ts
    
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["*"]}}}')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text("")
    (tmp_path / "src" / "local.ts").write_text("")
    (tmp_path / "src" / "shared").mkdir()
    (tmp_path / "src" / "shared" / "utils.ts").write_text("")
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "auth.ts").write_text("")
    (tmp_path / "services" / "payment").mkdir()
    (tmp_path / "services" / "payment" / "index.ts").write_text("")
    
    resolver = TypeScriptResolver(root_dir=tmp_path)
    
    # 1. Alias @/services/auth -> services/auth.ts
    res1 = resolver._resolve_path("src/app.ts", "@/services/auth")
    assert res1.get("status") == "resolved"
    assert res1.get("target") == "services/auth.ts"
    
    # 2. Relative ./local -> src/local.ts
    res2 = resolver._resolve_path("src/app.ts", "./local")
    assert res2.get("status") == "resolved"
    assert res2.get("target") == "src/local.ts"
    
    # 3. Relative ../shared/utils -> src/shared/utils.ts
    # Wait, from src/app.ts, ../shared/utils -> shared/utils? No, from src, .. is root.
    # Actually from src/app.ts, its directory is src. So ./local is src/local.ts
    res3 = resolver._resolve_path("src/app.ts", "./shared/utils")
    assert res3.get("status") == "resolved"
    assert res3.get("target") == "src/shared/utils.ts"
    
    # 4. Alias directory with index @/services/payment -> services/payment/index.ts
    res4 = resolver._resolve_path("src/app.ts", "@/services/payment")
    assert res4.get("status") == "resolved"
    assert res4.get("target") == "services/payment/index.ts"

    # 5. External module
    res5 = resolver._resolve_path("src/app.ts", "express")
    assert res5.get("status") == "external"

    # 6. Unresolved alias
    res6 = resolver._resolve_path("src/app.ts", "@/missing/file")
    assert res6.get("status") == "unresolved"
    assert res6.get("reason") == "file_not_found"

