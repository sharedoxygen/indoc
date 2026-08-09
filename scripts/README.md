# inDoc Scripts

This directory contains shell scripts for development, setup, and operations.

## 📁 Directory Structure

```
scripts/
├── setup/              # Initial environment setup
├── dev/               # Development helpers
└── ops/               # Operations scripts
```

## 🔧 Setup Scripts (`setup/`)

Scripts for initial environment configuration:

- **`setup-database.sh`** - Initialize PostgreSQL database
- **`setup-local-db.sh`** - Setup local development database
- **`init-search-indices.sh`** - Initialize Elasticsearch/Weaviate indices

**Usage:**
```bash
# First-time setup
./scripts/setup/setup-local-db.sh
./scripts/setup/init-search-indices.sh
```

## 🛠️ Development Scripts (`dev/`)

Scripts for daily development tasks:

- **`start-services.sh`** - Start all development services
- **`stop-services.sh`** - Stop all running services
- **`cleanup.sh`** - Clean up temporary files and containers

**Usage:**
```bash
# Start development environment
./scripts/dev/start-services.sh

# Stop everything
./scripts/dev/stop-services.sh

# Clean up temp files
./scripts/dev/cleanup.sh
```

## ⚙️ Operations Scripts (`ops/`)

Scripts for production operations:

- **`start-saas.sh`** - Start services in SaaS mode
- **`backup-db.sh`** - Backup database
- **`health-check.sh`** - Check service health

**Usage:**
```bash
# Production deployment
./scripts/ops/start-saas.sh

# Backup database
./scripts/ops/backup-db.sh
```

## 📝 Script Conventions

All scripts should follow these conventions:

1. **Shebang**: Start with `#!/bin/bash` or `#!/usr/bin/env bash`
2. **Error handling**: Use `set -euo pipefail`
3. **Documentation**: Include comments explaining what the script does
4. **Exit codes**: Return 0 on success, non-zero on failure
5. **Logging**: Use `echo` with prefixes: `✅`, `❌`, `⚠️`, `🔧`

### Example Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail

# Script: example-script.sh
# Description: Brief description of what this script does
# Usage: ./example-script.sh [options]

echo "🔧 Starting example script..."

# Your code here

echo "✅ Example script completed successfully!"
exit 0
```

## 🚨 Important Notes

- **Always review** scripts before running them
- **Use from project root**: `./scripts/dev/start-services.sh`
- **Check permissions**: Scripts should be executable (`chmod +x script.sh`)
- **Environment variables**: Use `.env` file or export before running

## 🆘 Troubleshooting

**Script not executable?**
```bash
chmod +x scripts/dev/start-services.sh
```

**Script not found?**
```bash
# Make sure you're in project root
cd /path/to/indoc
./scripts/dev/start-services.sh
```

**Permission denied?**
```bash
# Use sudo only if absolutely necessary
sudo ./scripts/ops/backup-db.sh
```

