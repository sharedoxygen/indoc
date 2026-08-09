# Bulk Upload Guide

Complete guide for bulk uploading seed documents and distributing them among users for demo and analytics purposes.

## 📋 Overview

The bulk upload tool allows you to:
- Upload 1500+ documents reliably
- Distribute documents equitably among managers and analysts
- Maintain multi-tenant isolation
- Track upload progress and statistics
- Test with dry-run mode before actual upload

## 🚀 Quick Start

### Basic Bulk Upload
```bash
# Upload all documents from a directory
make bulk-upload SOURCE=/path/to/seed/documents

# Or use the script directly
python tools/bulk_seed_upload.py --source /path/to/seed/documents
```

### Dry Run (Test Without Uploading)
```bash
# Simulate the upload to see what would happen
make bulk-upload-dry-run SOURCE=/path/to/seed/documents
```

### Role-Specific Upload
```bash
# Upload only to managers
make bulk-upload-managers SOURCE=/path/to/seed/documents

# Upload only to analysts
make bulk-upload-analysts SOURCE=/path/to/seed/documents
```

## 📁 Supported File Types

The tool automatically detects and uploads:
- **Documents**: PDF, DOC, DOCX, TXT, MD
- **Spreadsheets**: XLS, XLSX, CSV
- **Presentations**: PPT, PPTX
- **Images**: JPG, JPEG, PNG, GIF

System files (starting with `.`) are automatically excluded.

## 🎯 Distribution Strategy

### Equitable Round-Robin Distribution

The tool uses **round-robin distribution** to ensure fair allocation:

1. **Collects** all files from source directory
2. **Shuffles** files randomly for variety
3. **Distributes** using round-robin:
   ```
   File 1 → User 1
   File 2 → User 2
   File 3 → User 3
   ...
   File N → User (N mod total_users)
   ```

### Example Distribution

For 1500 files and 18 managers + 79 analysts (97 total users):
- Each user gets: ~15-16 files
- Managers: 18 users × ~15 files = ~270 files
- Analysts: 79 users × ~15 files = ~1230 files

## 🔧 Usage Examples

### Example 1: Full Bulk Upload
```bash
cd /Users/Collins/iDo/Projects/indoc

# Start the stack if not running
make dev

# Upload all seed documents
make bulk-upload SOURCE=./app/data/storage
```

**Output:**
```
[1/4] Collecting files...
  Collected 1523 files from ./app/data/storage

[2/4] Getting target users...
  Found 97 target users for upload

[3/4] Distributing files...
  === Distribution Summary ===
  Manager         :  18 users,   274 files (avg: 15.2 per user)
  Analyst         :  79 users,  1249 files (avg: 15.8 per user)

[4/4] Uploading files...
  [1/97] Uploading 16 files for darrell.ferguson@enterprise-sys.com (Manager)...
  ✓ Success: 16, Failed: 0, Duplicate: 0
  ...
```

### Example 2: Dry Run First
```bash
# Test before actual upload
make bulk-upload-dry-run SOURCE=./app/data/storage

# Review the output, then run for real
make bulk-upload SOURCE=./app/data/storage
```

### Example 3: Manager-Only Upload
```bash
# Upload 500 files to managers only
make bulk-upload-managers SOURCE=./seed_data/manager_docs
```

### Example 4: Progressive Upload
```bash
# Upload in batches for monitoring
make bulk-upload SOURCE=./seed_data/batch1
# Wait and monitor...
make bulk-upload SOURCE=./seed_data/batch2
# Wait and monitor...
make bulk-upload SOURCE=./seed_data/batch3
```

## 📊 Monitoring Progress

### Real-Time Monitoring

```bash
# Terminal 1: Run the upload
make bulk-upload SOURCE=/path/to/docs

# Terminal 2: Watch document counts
watch -n 5 'psql -h localhost -U indoc_user -d indoc_db -c "
  SELECT status, COUNT(*) 
  FROM documents 
  GROUP BY status;"'

# Terminal 3: Monitor Celery worker
tail -f tmp/celery_worker.out
```

### Check Final Stats
```bash
# After upload completes
python -c "
from app.db.session import SessionLocal
from app.models.document import Document
from sqlalchemy import func

db = SessionLocal()
stats = db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()

print('Document Status Summary:')
for status, count in stats:
    print(f'  {status:20} : {count:5}')
db.close()
"
```

## ⚠️ Important Notes

### Prerequisites
1. **Stack Running**: Ensure `make dev` is running
2. **Services Healthy**: Check Elasticsearch, Qdrant, Redis, PostgreSQL
3. **Celery Active**: Verify Celery worker is processing

### Performance Considerations

- **Upload Speed**: ~5-10 documents/second per user
- **1500 files**: Expect ~15-30 minutes total
- **Celery Queues**: Monitor with `docker exec indoc-redis redis-cli llen document_processing`

### Error Handling

The tool automatically handles:
- ✅ Duplicate files (skips with warning)
- ✅ Invalid file types (skips)
- ✅ Upload failures (logs and continues)
- ✅ Tenant isolation (validates user tenants)

### Troubleshooting

**Problem**: Upload seems stuck
```bash
# Check Celery is processing
ps aux | grep celery

# Check queue depth
docker exec indoc-redis redis-cli llen document_processing

# Restart Celery if needed
make stop
make dev
```

**Problem**: Many duplicates
```bash
# Clear existing documents first (CAREFUL!)
python -c "
from app.db.session import SessionLocal
from app.models.document import Document
db = SessionLocal()
db.query(Document).delete()
db.commit()
"

# Then re-upload
make bulk-upload SOURCE=/path/to/docs
```

**Problem**: Files not distributing evenly
- This is expected! Round-robin ensures near-equal distribution
- Variance of ±1-2 files per user is normal

## 🔍 Advanced Usage

### Custom Script Usage
```bash
# Direct script with all options
python tools/bulk_seed_upload.py \
  --source /path/to/documents \
  --dry-run \
  --managers-only

# Get help
python tools/bulk_seed_upload.py --help
```

### Programmatic Usage
```python
from tools.bulk_seed_upload import BulkSeedUploader
import asyncio

uploader = BulkSeedUploader(
    source_path=Path('/path/to/docs'),
    dry_run=False
)
asyncio.run(uploader.run(role_filter='managers'))
```

## 📈 Analytics & Reporting

### User Document Distribution
```sql
SELECT 
    u.email,
    u.role,
    COUNT(d.id) as document_count,
    SUM(d.file_size) as total_size_bytes
FROM users u
LEFT JOIN documents d ON d.uploaded_by = u.id
WHERE u.role IN ('Manager', 'Analyst')
GROUP BY u.id, u.email, u.role
ORDER BY document_count DESC;
```

### Upload Statistics
```sql
-- Documents by status
SELECT status, COUNT(*) 
FROM documents 
GROUP BY status;

-- Upload timeline
SELECT 
    DATE(created_at) as upload_date,
    COUNT(*) as docs_uploaded
FROM documents
GROUP BY DATE(created_at)
ORDER BY upload_date DESC;

-- Top uploaders
SELECT 
    uploaded_by,
    COUNT(*) as uploads
FROM documents
GROUP BY uploaded_by
ORDER BY uploads DESC
LIMIT 10;
```

## ✅ Best Practices

1. **Always dry-run first** to verify distribution
2. **Monitor Celery** during large uploads
3. **Upload in batches** for very large sets (>5000 files)
4. **Check disk space** before bulk upload
5. **Backup database** before major uploads
6. **Use meaningful filenames** for better searchability
7. **Verify counts** after upload completes

## 🎓 Demo & Testing Scenarios

### Scenario 1: Sales Demo
```bash
# Upload 500 diverse documents to all users
make bulk-upload SOURCE=./demo_data/sales_materials
```

### Scenario 2: Analytics Testing
```bash
# Managers get strategic docs
make bulk-upload-managers SOURCE=./demo_data/strategic

# Analysts get operational docs
make bulk-upload-analysts SOURCE=./demo_data/operational
```

### Scenario 3: Performance Testing
```bash
# Upload 5000 files to stress-test
make bulk-upload SOURCE=./performance_test_data
```

## 📝 Maintenance

### Cleanup After Testing
```bash
# Remove all test documents
python -c "
from app.db.session import SessionLocal
from app.models.document import Document
from datetime import datetime, timedelta

db = SessionLocal()

# Delete documents uploaded in last hour (test uploads)
cutoff = datetime.utcnow() - timedelta(hours=1)
db.query(Document).filter(Document.created_at > cutoff).delete()
db.commit()
print('Test documents cleaned up')
"
```

### Verify Data Integrity
```bash
# Check all documents have required fields
python tools/data_integrity_check.py --fix
```

## 🆘 Support

For issues or questions:
1. Check logs: `tail -f tmp/celery_worker.out`
2. Review this guide
3. Check document status in database
4. Restart stack: `make stop && make dev`

---

**Ready to upload?** Start with a dry run:
```bash
make bulk-upload-dry-run SOURCE=/path/to/your/seed/documents
```

