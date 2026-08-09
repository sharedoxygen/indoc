#!/usr/bin/env python3
"""
Bulk Seed Document Upload Tool

Uploads seed documents and distributes them equitably among managers and analysts
for demo and analytics purposes.

Usage:
    python tools/bulk_seed_upload.py --source /path/to/seed/documents
    python tools/bulk_seed_upload.py --source /path/to/seed/documents --dry-run
    python tools/bulk_seed_upload.py --source /path/to/seed/documents --managers-only
    python tools/bulk_seed_upload.py --source /path/to/seed/documents --analysts-only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import random
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.user import User
from app.services.bulk_upload_service import BulkUploadService
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BulkSeedUploader:
    """Handles bulk upload and equitable distribution of seed documents"""
    
    def __init__(self, source_path: Path, dry_run: bool = False):
        self.source_path = source_path
        self.dry_run = dry_run
        self.db = SessionLocal()
        self.stats = defaultdict(int)
        
    def get_target_users(self, role_filter: str = None) -> List[User]:
        """Get managers and analysts for document distribution"""
        query = select(User).where(
            User.is_active == True,
            User.tenant_id != None  # Only users with tenants
        )
        
        if role_filter == 'managers':
            query = query.where(User.role == 'Manager')
        elif role_filter == 'analysts':
            query = query.where(User.role == 'Analyst')
        else:
            # Both managers and analysts
            query = query.where(User.role.in_(['Manager', 'Analyst']))
            
        result = self.db.execute(query)
        users = list(result.scalars().all())
        
        logger.info(f"Found {len(users)} target users for upload")
        return users
    
    def collect_files(self) -> List[Path]:
        """Recursively collect all files from source directory"""
        if not self.source_path.exists():
            raise ValueError(f"Source path does not exist: {self.source_path}")
            
        if self.source_path.is_file():
            return [self.source_path]
            
        # Supported file types
        extensions = [
            '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', 
            '*.ppt', '*.pptx', '*.txt', '*.md', '*.jpg', 
            '*.jpeg', '*.png', '*.gif', '*.csv'
        ]
        
        files = []
        for ext in extensions:
            files.extend(self.source_path.rglob(ext))
            
        # Filter out system files
        files = [f for f in files if not f.name.startswith('.') and not '/.' in str(f)]
        
        logger.info(f"Collected {len(files)} files from {self.source_path}")
        return sorted(files)
    
    def distribute_files(self, files: List[Path], users: List[User]) -> Dict[User, List[Path]]:
        """Distribute files equitably among users using round-robin"""
        distribution = defaultdict(list)
        
        # Shuffle files for random distribution
        shuffled_files = files.copy()
        random.shuffle(shuffled_files)
        
        # Round-robin distribution
        for idx, file_path in enumerate(shuffled_files):
            user = users[idx % len(users)]
            distribution[user].append(file_path)
            
        # Log distribution stats
        logger.info("\n=== Distribution Summary ===")
        role_counts = defaultdict(lambda: {'users': 0, 'files': 0})
        
        for user, user_files in distribution.items():
            role = str(user.role).split('.')[-1]  # Extract role name
            role_counts[role]['users'] += 1
            role_counts[role]['files'] += len(user_files)
            
        for role, counts in sorted(role_counts.items()):
            avg_files = counts['files'] / counts['users'] if counts['users'] > 0 else 0
            logger.info(f"  {role:15} : {counts['users']:3} users, {counts['files']:5} files (avg: {avg_files:.1f} per user)")
            
        return distribution
    
    async def upload_for_user(self, user: User, files: List[Path]) -> Dict[str, int]:
        """Upload files for a specific user"""
        service = BulkUploadService(self.db)
        results = {
            'success': 0,
            'failed': 0,
            'duplicate': 0
        }
        
        for file_path in files:
            try:
                if self.dry_run:
                    logger.info(f"  [DRY-RUN] Would upload: {file_path.name} for {user.email}")
                    results['success'] += 1
                    continue
                    
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                # Create upload file object
                from io import BytesIO
                file_obj = BytesIO(file_content)
                file_obj.name = file_path.name
                
                # Upload via service
                result = await service.upload_single_file(
                    file=file_obj,
                    filename=file_path.name,
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    metadata=None
                )
                
                if result.get('status') == 'success':
                    results['success'] += 1
                    self.stats['total_success'] += 1
                elif result.get('status') == 'duplicate':
                    results['duplicate'] += 1
                    self.stats['total_duplicate'] += 1
                else:
                    results['failed'] += 1
                    self.stats['total_failed'] += 1
                    logger.warning(f"  Failed: {file_path.name} - {result.get('message')}")
                    
            except Exception as e:
                results['failed'] += 1
                self.stats['total_failed'] += 1
                logger.error(f"  Error uploading {file_path.name}: {e}")
                
        return results
    
    async def run(self, role_filter: str = None):
        """Execute the bulk upload"""
        try:
            logger.info("=" * 80)
            logger.info("BULK SEED DOCUMENT UPLOAD")
            logger.info("=" * 80)
            logger.info(f"Source: {self.source_path}")
            logger.info(f"Dry Run: {self.dry_run}")
            logger.info(f"Role Filter: {role_filter or 'All (Managers + Analysts)'}")
            logger.info("=" * 80)
            
            # Step 1: Collect files
            logger.info("\n[1/4] Collecting files...")
            files = self.collect_files()
            if not files:
                logger.error("No files found to upload!")
                return
                
            # Step 2: Get target users
            logger.info("\n[2/4] Getting target users...")
            users = self.get_target_users(role_filter)
            if not users:
                logger.error("No target users found!")
                return
                
            # Step 3: Distribute files
            logger.info("\n[3/4] Distributing files...")
            distribution = self.distribute_files(files, users)
            
            # Step 4: Upload
            logger.info("\n[4/4] Uploading files...")
            if self.dry_run:
                logger.info("DRY RUN MODE - No actual uploads will occur")
                
            total_users = len(distribution)
            completed_users = 0
            
            for user, user_files in distribution.items():
                completed_users += 1
                logger.info(f"\n[{completed_users}/{total_users}] Uploading {len(user_files)} files for {user.email} ({user.role})...")
                
                results = await self.upload_for_user(user, user_files)
                
                logger.info(f"  ✓ Success: {results['success']}, Failed: {results['failed']}, Duplicate: {results['duplicate']}")
                
            # Final summary
            logger.info("\n" + "=" * 80)
            logger.info("UPLOAD COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total Files Processed: {len(files)}")
            logger.info(f"Total Users: {total_users}")
            logger.info(f"Successfully Uploaded: {self.stats['total_success']}")
            logger.info(f"Failed: {self.stats['total_failed']}")
            logger.info(f"Duplicates Skipped: {self.stats['total_duplicate']}")
            logger.info("=" * 80)
            
        finally:
            self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Bulk upload seed documents and distribute among managers/analysts'
    )
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help='Source directory or file containing seed documents'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate upload without actually uploading'
    )
    parser.add_argument(
        '--managers-only',
        action='store_true',
        help='Only upload to managers'
    )
    parser.add_argument(
        '--analysts-only',
        action='store_true',
        help='Only upload to analysts'
    )
    
    args = parser.parse_args()
    
    # Determine role filter
    role_filter = None
    if args.managers_only:
        role_filter = 'managers'
    elif args.analysts_only:
        role_filter = 'analysts'
        
    # Run bulk upload
    uploader = BulkSeedUploader(args.source, args.dry_run)
    asyncio.run(uploader.run(role_filter))


if __name__ == '__main__':
    main()

