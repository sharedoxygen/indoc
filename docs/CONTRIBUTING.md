# Contributing to inDoc

Welcome to inDoc! This guide will help you contribute effectively to the project.

---

## 🌳 Branch Workflow

inDoc uses a **4-branch promotion strategy** to ensure quality and stability:

```
in-progress (local only) → development → publish → main
```

### Branch Purposes:
- **`in-progress`**: Your local working branch (never pushed to remote)
- **`development`**: Integration and testing
- **`publish`**: Pre-production staging
- **`main`**: Production-ready code

---

## 🚀 Quick Start

### 1. Start a New Feature
```bash
# Ensure you're on in-progress and up-to-date
git checkout in-progress
git status
```

### 2. Work on Your Feature
```bash
# Make changes, commit as you go
git add .
git commit -m "feat: your feature description"
```

### 3. Promote Your Changes
```bash
# Use the automated promotion tool
conda run -n indoc python tools/git_promote.py

# Or with auto-commit if you have uncommitted changes
conda run -n indoc python tools/git_promote.py --auto-commit
```

That's it! The tool will:
- ✅ Promote through all branches
- ✅ Push to remote (except `in-progress`)
- ✅ Rebase `in-progress` on `main` to prevent conflicts
- ✅ Return you to `in-progress` for the next feature

---

## 📝 Commit Message Guidelines

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples:
```bash
feat(search): add hybrid search with Elasticsearch and Qdrant
fix(auth): resolve JWT token expiration issue
docs(readme): update installation instructions
test(upload): add integration tests for bulk upload
```

---

## 🛠️ Development Environment

### Prerequisites:
- **Conda**: Python environment management
- **Node.js**: Frontend development
- **PostgreSQL**: Database (via Docker)
- **Elasticsearch**: Keyword search (via Docker)
- **Qdrant**: Semantic search (via Docker)
- **Redis**: Caching and queues (via Docker)

### Setup:
```bash
# Create conda environment
conda env create -f environment.yml
conda activate indoc

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Start services
make local-e2e
```

---

## ✅ Code Quality Standards

### Before Committing:
1. **Run linters**:
   ```bash
   # Python
   black app/ backend/app/
   flake8 app/ backend/app/
   
   # TypeScript
   cd frontend && npm run lint
   ```

2. **Run tests**:
   ```bash
   # Backend tests
   conda run -n indoc pytest tests/
   
   # Frontend tests
   cd frontend && npm test
   
   # E2E tests
   conda run -n indoc pytest tests/e2e/
   ```

3. **Check pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

### Pre-commit Hooks:
The project uses pre-commit hooks to enforce standards:
- No hardcoded colors (use theme tokens)
- Verify imports exist (prevent hallucinations)
- Check hybrid search concurrency
- Validate additive migrations
- Protect private docs

Install hooks:
```bash
pre-commit install
```

---

## 🎨 UI Development

### Theme System:
**Always use theme tokens** from `frontend/src/theme.ts`:

```tsx
// ✅ GOOD
<Box sx={{ bgcolor: 'primary.main', color: 'text.primary' }}>

// ❌ BAD - hardcoded colors
<Box sx={{ bgcolor: '#1976d2', color: '#000' }}>
```

### Theme Context:
Use `ThemeContext` for light/dark mode:

```tsx
import { useTheme } from '../contexts/ThemeContext'

const { mode, toggleTheme } = useTheme()
```

---

## 🔍 Search Architecture

inDoc uses **concurrent hybrid search**:

1. **Elasticsearch**: Keyword/exact match search
2. **Qdrant**: Semantic/vector search
3. **Reranker**: Merges and ranks results

### Authoritative Provider:
Always use `backend/app/mcp/providers/search_provider.py` for search functionality.

**Never create duplicate search services** - extend the existing provider.

---

## 📚 Documentation

### Public Documentation (`docs/`):
- User guides
- API documentation
- Public README
- Installation guides

### Private Documentation (`private-docs/`):
- Architecture details
- Development guides
- Credentials and secrets
- Internal technical docs

### Required Docs:
Follow `private-docs/DOCUMENTATION_POLICY.md` for:
- What goes where
- Master index maintenance
- Archive policy

---

## 🔒 Security & Compliance

### Data Integrity:
- ✅ Use UUIDs for primary keys
- ✅ Foreign key constraints
- ✅ Timestamps (`created_at`, `updated_at`)
- ✅ Additive migrations only (no destructive changes)
- ✅ Transactions for multi-step operations

### RBAC/ABAC:
- ✅ Enforce tenant scope before retrieval
- ✅ Check user permissions at API layer
- ✅ Log all access in audit trail
- ✅ Scope search results by user access

### Testing:
Run enterprise-grade checks:
```bash
# Data integrity
python tools/verify_integrity.py

# Enterprise features
python tools/test_enterprise_grade.py
```

---

## 🐛 Debugging

### Backend Logs:
```bash
# View logs
tail -f tmp/backend.log

# Or use the Admin Log Viewer
# Navigate to: http://localhost:5173/logs (Admin only)
```

### Frontend Logs:
Open browser DevTools (F12) → Console

### Database:
```bash
# Connect to PostgreSQL
make db-shell

# Check tables
\dt

# Query data
SELECT * FROM users WHERE role = 'Admin';
```

---

## 🚨 Troubleshooting

### Merge Conflicts During Promotion:
If you get merge conflicts:

1. **Resolve conflicts** in your editor
2. **Stage and commit**:
   ```bash
   git add .
   git commit
   ```
3. **Continue promotion**:
   ```bash
   python tools/git_promote.py --continue
   ```

### Rebase Conflicts (Expected for WIP):
If `in-progress` rebase has conflicts:

1. **Resolve conflicts** in your editor
2. **Continue rebase**:
   ```bash
   git add .
   git rebase --continue
   ```
3. **Or abort if needed**:
   ```bash
   git rebase --abort
   ```

### Failed Tests:
```bash
# Run specific test
conda run -n indoc pytest tests/test_specific.py -v

# Run with debugging
conda run -n indoc pytest tests/test_specific.py -v -s --pdb
```

---

## 📖 Key Resources

### Architecture:
- **AI Prompt Engineering Guide**: `private-docs/AI_PROMPT_ENGINEERING_GUIDE.md`
- **Git Workflow Fix**: `private-docs/GIT_WORKFLOW_FIX.md`
- **App Structure**: `private-docs/APP_STRUCTURE_README.md`

### Configuration:
- **Backend Config**: `app/core/config.py`
- **Frontend Theme**: `frontend/src/theme.ts`
- **Database**: `alembic/` migrations

### Testing:
- **Unit Tests**: `tests/`
- **Integration Tests**: `tests/integration/`
- **E2E Tests**: `tests/e2e/`

---

## 🤝 Getting Help

### Questions?
1. Check documentation in `docs/` and `private-docs/`
2. Search existing issues on GitHub
3. Ask in project chat/Slack
4. Open a discussion thread

### Found a Bug?
1. Check if it's already reported
2. Gather reproduction steps
3. Include logs and screenshots
4. Open an issue with details

### Feature Request?
1. Check if it's already proposed
2. Describe the use case
3. Propose a solution (optional)
4. Open a feature request issue

---

## ✅ Checklist Before Submitting

- [ ] Code follows project style guidelines
- [ ] Commits follow conventional commits format
- [ ] Tests pass (`pytest`, `npm test`, E2E)
- [ ] Pre-commit hooks pass
- [ ] Documentation updated (if needed)
- [ ] No hardcoded colors (use theme tokens)
- [ ] No new duplicate services (reuse existing)
- [ ] Data integrity checks pass
- [ ] Promoted through all branches
- [ ] `in-progress` rebased on `main`

---

## 🎯 Best Practices

### DO:
- ✅ Use `tools/git_promote.py` for all promotions
- ✅ Write tests for new features
- ✅ Follow the AI Prompt Engineering Guide
- ✅ Use theme tokens for UI
- ✅ Reuse existing services (avoid duplication)
- ✅ Document new APIs and features
- ✅ Check data integrity

### DON'T:
- ❌ Push `in-progress` to remote
- ❌ Work directly on `main`, `publish`, or `development`
- ❌ Skip tests
- ❌ Hardcode colors or styles
- ❌ Create duplicate search/auth/LLM services
- ❌ Skip the rebase after promotion
- ❌ Commit sensitive data (use `.env`)

---

## 📜 License

This project is proprietary. See LICENSE file for details.

---

**Thank you for contributing to inDoc!** 🚀

For more details, see:
- `private-docs/AI_PROMPT_ENGINEERING_GUIDE.md`
- `private-docs/GIT_WORKFLOW_FIX.md`
- `private-docs/WORKING_SYSTEM_GUIDE.md`

