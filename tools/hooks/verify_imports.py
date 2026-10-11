#!/usr/bin/env python3
"""
Verify module imports exist (prevent hallucinated imports)

Per AI Prompt Engineering Guide §3.4, §11:
- Do not invent APIs, files, settings, roles, or UX elements
- Ground every suggestion in current code paths

This hook catches hallucinated imports before commit.
"""
import ast
import sys
from pathlib import Path
from typing import List, Tuple


def extract_imports(file_path: Path) -> List[Tuple[str, int]]:
    """Extract all import statements from a Python file"""
    imports = []

    try:
        with open(file_path, "r") as f:
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
    """Verify that an import path corresponds to an existing module."""
    parts = import_path.split(".")
    top = parts[0]

    if top in sys.stdlib_module_names or top not in ("app", "backend"):
        return True

    # `from app.models.document import Document` includes the class name.
    # Walk from the full path down until a real module file or package exists.
    for end in range(len(parts), 0, -1):
        candidate = project_root.joinpath(*parts[:end])
        if candidate.with_suffix(".py").is_file():
            return True
        if (candidate / "__init__.py").is_file():
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
                print(
                    f"❌ {file_path}:{lineno} - Potentially hallucinated import: {import_path}"
                )
                print("   Module file not found. Verify this import is correct.")
                errors_found = True

    if errors_found:
        print("\n⚠️  Hallucinated imports detected!")
        print("   Per AI Prompt Engineering Guide §3.4, §11:")
        print("   - Verify all imports reference existing modules")
        print("   - Do not fabricate file paths or APIs")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
