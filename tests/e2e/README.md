# inDoc Enterprise-Grade E2E Testing Suite 🧪

This comprehensive end-to-end testing suite validates all tier-1, tier-2, security, and compliance features of the inDoc platform using Playwright.

## 🎯 What Gets Tested

### ✅ Tier 1: Authentication & Security
- User registration and login
- Multi-factor authentication (MFA) enrollment and verification
- Token-based authentication (JWT)
- Token revocation and refresh
- Auth lockout mechanisms
- Session management
- Secure logout

### ✅ Tier 2: Role-Based Access Control (RBAC)
- Admin role capabilities
- Manager role capabilities  
- Analyst role capabilities
- Manager-Analyst hierarchy
- Role-based page access restrictions
- Permission enforcement

### ✅ Tier 3: Document Management
- Document upload (all supported formats)
- Virus scanning integration
- Document processing pipeline
- Document classification (ABAC: Public, Internal, Restricted, Confidential)
- Document scope enforcement
- Field-level encryption
- Document metadata management
- Multi-tenant document isolation

### ✅ Tier 4: Hybrid Search
- Elasticsearch keyword search
- Weaviate semantic/vector search
- Combined hybrid search results
- Search filtering and pagination
- Role-based search scoping

### ✅ Tier 5: Chat & Conversations
- Multi-document conversations
- Conversation persistence
- Message history
- Context-aware responses
- Real-time chat (WebSocket support)
- Conversation management

### ✅ Tier 6: Enterprise Features
- Comprehensive audit logging
- User management (Admin only)
- Team management (Manager)
- Settings configuration
- Multi-tenancy isolation
- Compliance reporting
- Data retention policies

### ✅ Tier 7: All User Pages
- Dashboard
- Documents page
- Upload page
- Document Processing/Pipeline
- Chat page
- Team management
- User/Role management
- Audit Trail
- Settings

## 🚀 Quick Start

### Prerequisites

1. **Install Dependencies**
   ```bash
   npm install
   npm run playwright:install
   ```

2. **Start the Application**
   
   Option A - Full stack with make:
   ```bash
   make local-e2e
   ```
   
   Option B - Manual start:
   ```bash
   # Terminal 1: Start backend
   conda run -n indoc uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Terminal 2: Start frontend
   cd frontend && npm run dev
   
   # Terminal 3: Start Celery worker (for document processing)
   conda run -n indoc celery -A app.core.celery_app worker --loglevel=info
   
   # Terminal 4: Start Celery beat (for scheduled tasks)
   conda run -n indoc celery -A app.core.celery_app beat --loglevel=info
   ```

3. **Ensure Services are Running**
   - PostgreSQL (default: localhost:5432)
   - Redis (default: localhost:6379)
   - Elasticsearch (optional but recommended: localhost:9200)
   - Weaviate (optional but recommended: localhost:8080)

### Running Tests

#### 🔥 Quick Smoke Test (1 minute)
Validates critical paths only - great for quick checks:
```bash
npm run test:smoke
```

#### 🏆 Full Production Validation (3-5 minutes)
Comprehensive test of all enterprise features:
```bash
npm run test:production
```

#### 🎨 Interactive UI Mode
Debug and watch tests in Playwright's UI:
```bash
npm run test:e2e:ui
```

#### 👀 Headed Mode
Watch the browser as tests run:
```bash
npm run test:e2e:headed
```

#### 🐛 Debug Mode
Step through tests with debugger:
```bash
npm run test:e2e:debug
```

#### 📊 View Test Report
After running tests, view the HTML report:
```bash
npm run test:report
```

## 📁 Test Structure

```
tests/e2e/
├── README.md                              # This file
├── fixtures.ts                            # Reusable test fixtures
├── indoc-production-validation.spec.ts    # Full production validation
├── quick-smoke-test.spec.ts               # Quick smoke test
└── helpers/
    ├── api-helpers.ts                     # API interaction utilities
    └── page-objects.ts                    # Page object models
```

## 🎭 Test Features

### Page Object Model
Clean, maintainable test code using page objects:
```typescript
import { test } from './fixtures';

test('example', async ({ loginPage, dashboardPage }) => {
  await loginPage.goto();
  await loginPage.login('user@example.com', 'password');
  await dashboardPage.expectToBeVisible();
});
```

### API Helpers
Direct API access for setup/teardown:
```typescript
test('example', async ({ apiHelper }) => {
  const token = await apiHelper.login('user@example.com', 'password');
  const doc = await apiHelper.uploadDocument(token, 'test.txt', 'content');
});
```

### Rich Reporting
- HTML report with screenshots
- JSON report for CI/CD integration
- Video recording on failure
- Trace files for debugging

## 🔧 Configuration

Edit `playwright.config.ts` to customize:

```typescript
// Change base URLs
baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
apiURL: process.env.E2E_API_URL || 'http://localhost:8000',

// Adjust timeouts
timeout: 120 * 1000,  // 2 minutes per test

// Enable parallel execution
workers: 4,  // Run 4 tests in parallel
```

### Environment Variables

```bash
# Custom URLs
export E2E_BASE_URL=https://staging.indoc.example.com
export E2E_API_URL=https://api-staging.indoc.example.com

# Skip auto-starting servers (use when servers already running)
export SKIP_WEBSERVER=true

# CI mode (more retries, stricter)
export CI=true
```

## 📊 Understanding Test Results

### ✅ Success Output
```
🎉 PRODUCTION VALIDATION COMPLETE!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All enterprise-grade features tested and validated
✅ Authentication, RBAC, Documents, Chat, Search, Audit all working
✅ inDoc is production-ready! 🔒
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### ❌ Failure Output
When tests fail, Playwright generates:
- **Screenshots** at point of failure
- **Videos** of the entire test
- **Trace files** for time-travel debugging
- **Detailed logs** with error messages

View with: `npm run test:report`

## 🐛 Troubleshooting

### Tests Timing Out
- Increase timeout in `playwright.config.ts`
- Check if backend services are running
- Verify database is accessible

### Can't Find Elements
- Check if frontend build is up to date
- Verify selectors in `page-objects.ts`
- Run in headed mode to see what's happening: `npm run test:e2e:headed`

### Backend Errors
- Check backend logs: `tail -f tmp/backend.out`
- Verify database migrations: `alembic upgrade head`
- Ensure all environment variables are set

### Network Issues
- Check Redis is running: `redis-cli ping`
- Check PostgreSQL: `psql -U postgres -c "SELECT 1"`
- Check Elasticsearch: `curl localhost:9200`

## 🔐 Security Considerations

### Test Data
- Tests create users with predictable emails (e2e-*@indoc.test)
- Test data should be cleaned up automatically
- Never run tests against production!

### Credentials
- Test credentials are hardcoded for E2E testing only
- In CI/CD, consider using environment variables
- Rotate any credentials that may have been exposed

## 🚀 CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: npm ci
      
      - name: Install Playwright
        run: npm run playwright:install
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Run E2E tests
        run: npm run test:e2e
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## 📈 Performance Benchmarks

Expected test execution times on standard hardware:

| Test Suite | Duration | What's Tested |
|------------|----------|---------------|
| Smoke Test | ~30s | Critical paths only |
| Production Validation | ~3-5 min | All enterprise features |
| Full Suite (future) | ~10-15 min | All tests including edge cases |

## 🎯 Best Practices

1. **Run smoke tests frequently** - Quick validation during development
2. **Run full validation before releases** - Comprehensive pre-deployment check
3. **Keep page objects updated** - When UI changes, update selectors
4. **Use headed mode for debugging** - See what's happening in real-time
5. **Review test reports** - Screenshots and videos reveal issues quickly

## 📚 Additional Resources

- [Playwright Documentation](https://playwright.dev)
- [Page Object Model Pattern](https://playwright.dev/docs/pom)
- [Best Testing Practices](https://playwright.dev/docs/best-practices)
- [inDoc API Documentation](../../docs/api-reference.md)

## 🤝 Contributing

When adding new features to inDoc:

1. Add corresponding E2E test coverage
2. Update page objects if new UI components added
3. Document any new test utilities
4. Ensure tests pass before submitting PR

## 📝 Test Coverage Report

After running tests, generate a coverage report:

```bash
npm run test:e2e
npm run test:report
```

Look for:
- ✅ **Pass Rate**: Should be 100%
- ⏱️ **Performance**: Tests should complete in reasonable time
- 📸 **Artifacts**: Screenshots/videos only on failures

---

**Made with ❤️ for inDoc Enterprise Platform**

*Ensuring production-grade quality with comprehensive E2E testing* 🚀🔒


