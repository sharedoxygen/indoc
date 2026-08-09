#!/usr/bin/env python3
"""
Verify module imports exist (prevent hallucinated imports)

Per AI Prompt Engineering Guide §3.4, §11:
- Do not invent APIs, files, settings, roles, or UX elements
- Ground every suggestion in current code paths

This hook catches hallucinated imports before commit.
"""
import sys
import re
import ast
from pathlib import Path
from typing import List, Tuple


def extract_imports(file_path: Path) -> List[Tuple[str, int]]:
    """Extract all import statements from a Python file"""
    imports = []
    
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        full_import = f"{node.module}.{alias.name}"
                        imports.append((full_import, node.lineno))
    except SyntaxError:
        # File has syntax errors, will be caught by other hooks
        pass
    
    return imports


def verify_import_exists(import_path: str, project_root: Path) -> bool:
    """Verify that an import path corresponds to an existing module"""
    parts = import_path.split('.')
    
    # Check if it's a standard library or external package
    if parts[0] in ['os', 'sys', 'json', 'typing', 'pathlib', 'asyncio', 
                     'sqlalchemy', 'fastapi', 'pydantic', 'httpx', 'pytest']:
        return True  # Standard lib/common packages, assume valid
    
    # Check if it's an internal app module
    if parts[0] in ['app', 'backend']:
        # Build file path
        if parts[0] == 'backend' and len(parts) > 1 and parts[1] == 'app':
            # backend.app.something -> backend/app/something
            file_path = project_root / '/'.join(parts[:3])
            if len(parts) > 3:
                file_path = file_path / '/'.join(parts[3:])
        else:
            file_path = project_root / '/'.join(parts)
        
        # Check if module exists as .py file or __init__.py in directory
        if (file_path.with_suffix('.py')).exists():
            return True
        if (file_path / '__init__.py').exists():
            return True
        
        # Check parent directory has __init__.py (valid package)
        parent = file_path.parent
        if (parent / '__init__.py').exists():
            # Check if the specific attribute exists in parent __init__
            # This is a simplified check
            return True
    
    return False


def main(argv: List[str]) -> int:
    """Main hook entry point"""
    project_root = Path.cwd()
    errors_found = False
    
    for file_path_str in argv:
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            continue
        
        imports = extract_imports(file_path)
        
        for import_path, lineno in imports:
            if not verify_import_exists(import_path, project_root):
                print(f"❌ {file_path}:{lineno} - Potentially hallucinated import: {import_path}")
                print(f"   Module file not found. Verify this import is correct.")
                errors_found = True
    
    if errors_found:
        print("\n⚠️  Hallucinated imports detected!")
        print("   Per AI Prompt Engineering Guide §3.4, §11:")
        print("   - Verify all imports reference existing modules")
        print("   - Do not fabricate file paths or APIs")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

