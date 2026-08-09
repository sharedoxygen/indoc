# inDoc Tools

Python utility scripts for development, operations, and testing.

## 📁 Available Tools

### Database & Initialization

- **`init_db.py`** - Initialize database schema and create default users
- **`seed_data_generator.py`** - Generate realistic test data
- **`realistic_seed_generator.py`** - Generate production-like seed data

**Usage:**
```bash
# Initialize database
conda run -n indoc python tools/init_db.py

# Generate test data
conda run -n indoc python tools/seed_data_generator.py
```

### Testing & Validation

- **`verify_production_readiness.py`** - Comprehensive production readiness validation
- **`e2e_test_runner.py`** - End-to-end API test runner

**Usage:**
```bash
# Run production validation
conda run -n indoc python tools/verify_production_readiness.py

# Run E2E tests
conda run -n indoc python tools/e2e_test_runner.py
```

### Data Management

- **`cleanup_orphaned_data.py`** - Remove orphaned documents and files
- **`auto_process_monitor.py`** - Monitor document processing queue

**Usage:**
```bash
# Clean up orphaned data
conda run -n indoc python tools/cleanup_orphaned_data.py

# Monitor processing
conda run -n indoc python tools/auto_process_monitor.py
```

## 🛠️ Development Guidelines

### Creating New Tools

1. **Place in correct category** - Database, testing, or operations
2. **Add docstring** - Explain purpose and usage
3. **Use argparse** - For command-line arguments
4. **Error handling** - Graceful failures with clear messages
5. **Logging** - Use Python logging module
6. **Update this README** - Document new tools

### Tool Template

```python
#!/usr/bin/env python3
"""
Tool Name
Brief description of what this tool does.

Usage:
    python tools/tool_name.py [options]
"""
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Tool description")
    parser.add_argument("--option", help="Option description")
    args = parser.parse_args()
    
    logger.info("Starting tool...")
    # Your code here
    logger.info("✅ Tool completed successfully")

if __name__ == "__main__":
    main()
```

## 📝 Best Practices

1. **Use conda environment**: Always run with `conda run -n indoc python tools/script.py`
2. **Check prerequisites**: Verify database/services are running
3. **Backup data**: Before running destructive operations
4. **Test in staging**: Don't run untested tools in production
5. **Log operations**: All tools should log their actions

## 🔐 Security Notes

- **Never commit** `.env` files with credentials
- **Use environment variables** for sensitive configuration
- **Validate inputs** to prevent injection attacks
- **Audit tool usage** in production environments

## 🆘 Troubleshooting

**Import errors?**
```bash
# Make sure you're using conda environment
conda activate indoc
python tools/script.py
```

**Database connection errors?**
```bash
# Check PostgreSQL is running
psql -h localhost -U postgres -d indoc -c "SELECT 1;"
```

**Permission errors?**
```bash
# Check file permissions
chmod +x tools/script.py
```

