#!/bin/bash
# Comprehensive Project Cleanup Script for inDoc SaaS
# Removes temporary, deprecated, and unused files

set -e

echo "🧹 inDoc Project Cleanup - Removing Pollution"
echo "=============================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
REMOVED_COUNT=0
SAVED_SPACE=0

# Function to safely remove files/directories
safe_remove() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        local size=$(du -sk "$path" 2>/dev/null | cut -f1 || echo "0")
        rm -rf "$path"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
        SAVED_SPACE=$((SAVED_SPACE + size))
        echo -e "   ${GREEN}✅ Removed:${NC} $description"
    fi
}

echo -e "${BLUE}1️⃣ Removing Python cache files...${NC}"
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
echo "   ✅ Python cache cleaned"

echo -e "\n${BLUE}2️⃣ Removing temporary files...${NC}"
# Temporary Python scripts in tmp/
safe_remove "./tmp/fix_all_syntax_errors.py" "Syntax fix script"
safe_remove "./tmp/final_syntax_fix.py" "Final syntax fix script"
safe_remove "./tmp/ensure_admin_and_login.py" "Admin login script"
safe_remove "./tmp/fix_backend_start.sh" "Backend start fix script"
safe_remove "./tmp/quick_fix_and_test_login.sh" "Quick login test script"
safe_remove "./tmp/EMERGENCY_RESTORE.md" "Emergency restore documentation"

# Temporary data files with tmp in name
safe_remove "./app/data/storage/aa71ce80-31f3-4225-9569-e182860b239c/ee87ce0ea32ff54eec2689b676aa8711d8ec593c69273bfce3fa53c9883dabb5_tmp8zhon1plREADME.md" "Temp README file"
safe_remove "./app/data/storage/aa71ce80-31f3-4225-9569-e182860b239c/ee87ce0ea32ff54eec2689b676aa8711d8ec593c69273bfce3fa53c9883dabb5_tmpgfo24qpzREADME.md" "Temp README file"
safe_remove "./app/data/storage/aa71ce80-31f3-4225-9569-e182860b239c/ee87ce0ea32ff54eec2689b676aa8711d8ec593c69273bfce3fa53c9883dabb5_tmpl0oeu5muREADME.md" "Temp README file"
safe_remove "./app/data/storage/aa71ce80-31f3-4225-9569-e182860b239c/ee87ce0ea32ff54eec2689b676aa8711d8ec593c69273bfce3fa53c9883dabb5_tmppv372ui5README.md" "Temp README file"

echo -e "\n${BLUE}3️⃣ Removing duplicate/redundant files...${NC}"
# Duplicate celery schedule files
safe_remove "./app/celerybeat-schedule.db" "Duplicate celery schedule (app)"
safe_remove "./backend/celerybeat-schedule.db" "Duplicate celery schedule (backend)"
safe_remove "./backend/celerybeat-schedule" "Duplicate celery schedule (backend)"

# Duplicate alembic directories (keep main one)
safe_remove "./backend/alembic" "Duplicate alembic directory"

# Duplicate requirements
safe_remove "./backend/requirements.txt" "Duplicate requirements file"

echo -e "\n${BLUE}4️⃣ Removing test artifacts...${NC}"
safe_remove "./.pytest_cache" "Pytest cache"
safe_remove "./backend/.pytest_cache" "Backend pytest cache"
safe_remove "./.coverage" "Coverage data file"
safe_remove "./htmlcov" "HTML coverage report"

echo -e "\n${BLUE}5️⃣ Removing temporary documentation...${NC}"
safe_remove "./FINAL_ANALYSIS_SUMMARY.md" "Temporary analysis document"
safe_remove "./scripts/production-cleanup.sh" "Production cleanup script (no longer needed)"

echo -e "\n${BLUE}6️⃣ Cleaning log files (keeping recent)...${NC}"
# Keep current logs but remove old/duplicate ones
safe_remove "./tmp/backend_clean.out" "Old backend log"
safe_remove "./tmp/backend_clean.pid" "Old backend PID"
safe_remove "./tmp/backend_fixed.out" "Old backend log"

# Keep these as they're current:
# - tmp/backend.out (current)
# - tmp/backend.pid (current)
# - tmp/celery_*.out (current)
# - tmp/celery_*.pid (current)
# - tmp/frontend.out (current)
# - tmp/frontend.pid (current)

echo -e "\n${BLUE}7️⃣ Removing empty directories...${NC}"
find . -type d -empty -not -path "./node_modules/*" -not -path "./.git/*" -delete 2>/dev/null || true

echo -e "\n${BLUE}8️⃣ Checking .gitignore compliance...${NC}"
# Files that should be ignored but might exist
SHOULD_BE_IGNORED=(
    "*.log"
    "*.db"
    "*.sqlite"
    "tmp/*.py"
    "tmp/*.sh"
    "tmp/*.md"
    "keys/"
    "uploads/*"
)

for pattern in "${SHOULD_BE_IGNORED[@]}"; do
    if find . -name "$pattern" -not -path "./node_modules/*" | grep -q .; then
        echo -e "   ${YELLOW}⚠️ Found files matching ignored pattern: $pattern${NC}"
        find . -name "$pattern" -not -path "./node_modules/*" | head -3
    fi
done

echo -e "\n${GREEN}🎉 CLEANUP COMPLETED!${NC}"
echo "========================================"
echo -e "${GREEN}Files removed:${NC} $REMOVED_COUNT"
echo -e "${GREEN}Space saved:${NC} ~$((SAVED_SPACE / 1024))MB"
echo ""
echo -e "${BLUE}📁 Clean project structure:${NC}"
echo "   app/           - Primary application"
echo "   frontend/      - React frontend"
echo "   backend/       - Data storage only"
echo "   tmp/           - Current runtime files only"
echo "   private-docs/  - Important documentation"
echo ""
echo -e "${GREEN}✅ Project is now clean and production-ready!${NC}"
