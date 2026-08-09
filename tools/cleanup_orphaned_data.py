#!/usr/bin/env python3
"""
Data Integrity Cleanup Tool
Removes orphaned files and fixes referential integrity issues
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.models.audit import AuditLog
from sqlalchemy import select, text

def cleanup_orphaned_files(dry_run=False):
    """Remove files in storage that have no corresponding database records"""
    print("=== ORPHANED FILES CLEANUP ===")
    
    db = SessionLocal()
    
    # Get all document file paths from database
    all_docs = db.execute(select(Document)).scalars().all()
    db_file_hashes = set()
    
    for doc in all_docs:
        file_path = Path(doc.storage_path)
        db_file_hashes.add(file_path.name)
    
    print(f"Database has {len(db_file_hashes)} file references")
    
    # Check storage directories
    storage_dirs = [
        Path("backend/data/storage"),
        Path("data/storage"),
        Path("../data/storage")
    ]
    
    total_removed = 0
    total_size_saved = 0
    
    for storage_dir in storage_dirs:
        if not storage_dir.exists():
            continue
            
        print(f"\nChecking {storage_dir}...")
        
        for file_path in storage_dir.iterdir():
            if file_path.is_file() and file_path.name not in db_file_hashes:
                file_size = file_path.stat().st_size
                total_size_saved += file_size
                
                if dry_run:
                    print(f"  Would remove: {file_path.name} ({file_size:,} bytes)")
                else:
                    file_path.unlink()
                    print(f"  Removed: {file_path.name} ({file_size:,} bytes)")
                
                total_removed += 1
    
    print(f"\n{'DRY RUN: Would remove' if dry_run else 'Removed'} {total_removed:,} orphaned files")
    print(f"{'Would save' if dry_run else 'Saved'} {total_size_saved / (1024*1024):.1f} MB of storage")
    
    db.close()
    return total_removed, total_size_saved

def fix_document_paths():
    """Fix incorrect file paths in document records"""
    print("\n=== FIXING DOCUMENT PATHS ===")
    
    db = SessionLocal()
    all_docs = db.execute(select(Document)).scalars().all()
    
    fixed = 0
    
    for doc in all_docs:
        file_path = Path(doc.storage_path)
        if not file_path.exists():
            # Try to find the file
            possible_paths = [
                Path(f"data/storage/{file_path.name}"),
                Path(f"backend/data/storage/{file_path.name}"),
                Path(f"../data/storage/{file_path.name}")
            ]
            
            for alt_path in possible_paths:
                if alt_path.exists():
                    print(f"  Fixed: {doc.filename} -> {alt_path}")
                    doc.storage_path = str(alt_path)
                    fixed += 1
                    break
    
    if fixed > 0:
        db.commit()
        print(f"✅ Fixed {fixed} document paths")
    else:
        print("✅ All document paths are correct")
    
    db.close()
    return fixed

def verify_foreign_keys():
    """Verify all foreign key relationships"""
    print("\n=== FOREIGN KEY VERIFICATION ===")
    
    db = SessionLocal()
    
    # Check document -> user relationships
    orphaned_docs = db.execute(text('''
        SELECT COUNT(*) as count
        FROM documents d 
        LEFT JOIN users u ON d.uploaded_by = u.id 
        WHERE u.id IS NULL
    ''')).scalar()
    
    # Check audit -> user relationships  
    orphaned_audits = db.execute(text('''
        SELECT COUNT(*) as count
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE u.id IS NULL
    ''')).scalar()
    
    print(f"Orphaned documents: {orphaned_docs}")
    print(f"Orphaned audit logs: {orphaned_audits}")
    
    if orphaned_docs == 0 and orphaned_audits == 0:
        print("✅ All foreign key relationships are valid")
    else:
        print("❌ Foreign key integrity issues found")
    
    db.close()
    return orphaned_docs + orphaned_audits

def main():
    """Run complete data integrity cleanup"""
    print(f"Data Integrity Cleanup - {datetime.now()}")
    
    # 1. Fix document paths
    fixed_paths = fix_document_paths()
    
    # 2. Verify foreign keys
    fk_issues = verify_foreign_keys()
    
    # 3. Show orphaned files (dry run first)
    removed_count, saved_size = cleanup_orphaned_files(dry_run=True)
    
    if removed_count > 0:
        response = input(f"\nFound {removed_count:,} orphaned files ({saved_size/(1024*1024):.1f} MB). Remove them? (y/N): ")
        if response.lower() == 'y':
            cleanup_orphaned_files(dry_run=False)
    
    print(f"\n=== CLEANUP SUMMARY ===")
    print(f"Fixed document paths: {fixed_paths}")
    print(f"Foreign key issues: {fk_issues}")
    print(f"Orphaned files processed: {removed_count:,}")
    
    if fk_issues == 0 and fixed_paths >= 0:
        print("\n✅ Database integrity is now CLEAN")
    else:
        print("\n❌ Some issues remain - manual intervention required")

if __name__ == "__main__":
    main()
