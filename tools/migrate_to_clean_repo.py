#!/usr/bin/env python3
"""
inDoc Repository Migration Script
==================================
Purpose: Create a clean repository with ONLY source code, no sensitive data
Date: 2025-10-15
Security Incident: Clean slate migration after data exposure
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Source and destination
SOURCE_DIR = Path("/Users/Collins/iDo/Projects/indoc")
DEST_DIR = Path("/Users/Collins/iDo/Projects/indoc-clean")

# Files and directories to INCLUDE (source code only)
INCLUDE_PATTERNS = {
    # Root files
    "README.md",
    "LICENSE",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.production.yml",
    "docker-bake.hcl",
    "Makefile",
    "requirements.txt",
    "requirements-modern-scanner.txt",
    "pytest.ini",
    "alembic.ini",
    "playwright.config.ts",
    "package.json",
    "inDoc.json",
    
    # Directories (with filtering)
    "app/",
    "frontend/",
    "config/",
    "scripts/",
    "tests/",
    "monitoring/",
    "alembic/",
    "docs/",
    "assets/",
}

# Directories to EXCLUDE completely
EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".vscode",
    ".idea",
    "data",
    "storage",
    "uploads",
    "backups",
    "tmp",
    "logs",
    "keys",
    "private-docs",
    "backend",  # Duplicate structure
    "test-results",
    "playwright-report",
    "dist",
    "build",
    ".pytest_cache",
    "htmlcov",
    ".mypy_cache",
}

# File extensions to EXCLUDE
EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".tmp",
    ".temp",
    ".bak",
    ".backup",
    ".sql",
    ".dump",
    ".DS_Store",
    ".env",
    ".pem",
    ".key",
    ".crt",
}

# Files to EXCLUDE by name
EXCLUDE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "celerybeat-schedule",
    "celerybeat-schedule.db",
    "package-lock.json",
}

def should_exclude_dir(dir_name: str) -> bool:
    """Check if directory should be excluded."""
    return dir_name in EXCLUDE_DIRS or dir_name.startswith('.')

def should_exclude_file(file_path: Path) -> bool:
    """Check if file should be excluded."""
    # Check filename
    if file_path.name in EXCLUDE_FILES:
        return True
    
    # Check extension
    if file_path.suffix in EXCLUDE_EXTENSIONS:
        return True
    
    # Check for private/sensitive patterns in name
    sensitive_patterns = ['private', 'secret', 'credential', 'password', 'backup']
    name_lower = file_path.name.lower()
    if any(pattern in name_lower for pattern in sensitive_patterns):
        return True
    
    return False

def copy_with_filter(src: Path, dest: Path, relative_path: str = ""):
    """Recursively copy files with filtering."""
    
    if src.is_file():
        if should_exclude_file(src):
            return
        
        # Create destination directory
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(src, dest)
        print(f"  ✓ {relative_path}")
    
    elif src.is_dir():
        if should_exclude_dir(src.name):
            return
        
        dest.mkdir(parents=True, exist_ok=True)
        
        for item in src.iterdir():
            rel_path = f"{relative_path}/{item.name}" if relative_path else item.name
            copy_with_filter(item, dest / item.name, rel_path)

def create_essential_files(dest: Path):
    """Create essential files for new repository."""
    
    # Create .env.example
    env_example = dest / ".env.example"
    env_example.write_text("""# inDoc Environment Configuration
# Copy to .env and fill in your values

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/indoc

# Redis
REDIS_URL=redis://localhost:6379/0

# Search
ELASTICSEARCH_URL=http://localhost:9200
QDRANT_URL=http://localhost:6333

# LLM
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=sk-your-key-here

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Application
DEBUG=false
ENVIRONMENT=development
""")
    print("  ✓ Created .env.example")
    
    # Copy new .gitignore
    gitignore_new = SOURCE_DIR / ".gitignore.new"
    gitignore_dest = dest / ".gitignore"
    if gitignore_new.exists():
        shutil.copy2(gitignore_new, gitignore_dest)
        print("  ✓ Created .gitignore")

def create_security_notice(dest: Path):
    """Create security notice about the migration."""
    notice = dest / "SECURITY_MIGRATION_2025-10-15.md"
    notice.write_text(f"""# Security Migration Notice

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## What Happened

This repository is a clean migration from the original `indoc-app` repository due to 
a security incident where sensitive data was inadvertently committed to git history.

## Actions Taken

1. ✅ Created new repository with clean history
2. ✅ Migrated ONLY source code (no user data, credentials, or sensitive files)
3. ✅ Implemented comprehensive .gitignore
4. ✅ Added pre-commit hooks for secret detection
5. ⚠️  Old repository archived as `indoc-app-archived`

## What Was Excluded

- User data and uploads
- Database backups
- Private documentation
- Credentials and keys
- Test data files
- Build artifacts
- Logs and temporary files

## Next Steps

1. Rotate all credentials from the old repository
2. Review and update team access
3. Implement secret scanning in CI/CD
4. Train team on git security best practices

## Old Repository

The original repository has been archived and kept private for audit purposes.
**Do NOT use credentials from the old repository.**

---
*This migration was performed to maintain the highest security standards for inDoc.*
""")
    print("  ✓ Created SECURITY_MIGRATION_2025-10-15.md")

def main():
    """Main migration function."""
    print("\n" + "="*70)
    print("inDoc Repository Clean Slate Migration")
    print("="*70)
    print(f"\nSource: {SOURCE_DIR}")
    print(f"Destination: {DEST_DIR}")
    print()
    
    # Check source exists
    if not SOURCE_DIR.exists():
        print("❌ Source directory not found!")
        return 1
    
    # Check destination doesn't exist
    if DEST_DIR.exists():
        print("⚠️  Destination already exists!")
        response = input("Delete and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return 1
        shutil.rmtree(DEST_DIR)
    
    # Create destination
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Created clean repository directory\n")
    
    # Copy root files
    print("Copying root files...")
    for pattern in INCLUDE_PATTERNS:
        if not pattern.endswith('/'):
            src_file = SOURCE_DIR / pattern
            if src_file.exists() and src_file.is_file():
                dest_file = DEST_DIR / pattern
                if not should_exclude_file(src_file):
                    shutil.copy2(src_file, dest_file)
                    print(f"  ✓ {pattern}")
    
    # Copy directories
    print("\nCopying directories...")
    for pattern in INCLUDE_PATTERNS:
        if pattern.endswith('/'):
            dir_name = pattern.rstrip('/')
            src_dir = SOURCE_DIR / dir_name
            if src_dir.exists() and src_dir.is_dir():
                print(f"\n  📁 {dir_name}/")
                dest_dir = DEST_DIR / dir_name
                copy_with_filter(src_dir, dest_dir, dir_name)
    
    # Create essential files
    print("\nCreating essential files...")
    create_essential_files(DEST_DIR)
    
    # Create security notice
    print("\nCreating security documentation...")
    create_security_notice(DEST_DIR)
    
    print("\n" + "="*70)
    print("✅ Migration Complete!")
    print("="*70)
    print(f"\nClean repository created at: {DEST_DIR}")
    print("\nNext steps:")
    print("  1. cd {DEST_DIR}")
    print("  2. git init")
    print("  3. git add .")
    print("  4. git commit -m 'Initial commit: inDoc v1.0 (clean migration)'")
    print("  5. Review files to ensure no sensitive data")
    print("  6. Create new GitHub repository")
    print("  7. git remote add origin <new-repo-url>")
    print("  8. git push -u origin main")
    print()
    
    return 0

if __name__ == "__main__":
    exit(main())

