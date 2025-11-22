# 🚀 AGENT EXECUTION GUIDE - How to Deploy Specialized Agents

## Quick Start

Este documento te enseña cómo desplegar y coordinar los 25 agentes especializados para mejorar toda la aplicación.

---

## 🎯 PHASE 1: CRITICAL IMPROVEMENTS (Week 1-2)

### STEP 1: Logging Standardization
**Agent**: `logging-standardization-agent`
**Duration**: 2-3 hours
**Priority**: CRITICAL (do first!)

```bash
# Invocation
claude-task logging-standardization-agent --priority critical \
  --scope "all backend services" \
  --config "structured JSON logging" \
  --output "/backend/app/core/logging_config.py"

# What it does:
# 1. Replaces 65 print() statements with logger calls
# 2. Implements context middleware for request tracking
# 3. Adds structured JSON output
# 4. Creates logging documentation
```

**Expected Output**:
- ✅ `/backend/app/core/logging_config.py` - Logging configuration
- ✅ All `.py` files updated with logger calls
- ✅ `LOGGING.md` - Logging guidelines
- ✅ New logging context middleware

**Verification**:
```python
# After: All logs should look like
logger.info("action_performed", extra={"user_id": 123, "entity": "candidate"})
# Not: print("User 123 did action")
```

---

### STEP 2-4: Parallel Service Refactoring (3 Agents, Run in Parallel)

**Duration**: 4-6 hours each (6-8 hours total in parallel)
**Priority**: CRITICAL (depends on logging)

#### STEP 2a: Assignment Service Refactor
**Agent**: `assignment-service-refactor-agent`

```bash
claude-task assignment-service-refactor-agent \
  --source "/backend/app/services/assignment_service.py" \
  --target-size 20KB \
  --split-into 4 \
  --output "/backend/app/services/assignment/"
```

**Current Structure** (55KB):
- Apartment assignment logic
- Validation rules
- Notifications
- Deductions

**Target Structure** (4 separate services):
```
/backend/app/services/assignment/
├── __init__.py
├── models.py          # Data models
├── assignment.py      # Core assignment logic (~12KB)
├── validation.py      # Validation rules (~8KB)
├── notifications.py   # Notification system (~8KB)
└── deductions.py      # Deduction management (~10KB)
```

#### STEP 2b: Yukyu Service Refactor
**Agent**: `yukyu-service-refactor-agent`

```bash
claude-task yukyu-service-refactor-agent \
  --source "/backend/app/services/yukyu_service.py" \
  --target-size 20KB \
  --split-into 3 \
  --output "/backend/app/services/yukyu/"
```

**Target Structure**:
```
/backend/app/services/yukyu/
├── __init__.py
├── balance.py          # Balance management (~15KB)
├── requests.py         # Request workflows (~15KB)
└── notifications.py    # Notifications (~10KB)
```

#### STEP 2c: Payroll Service Refactor
**Agent**: `payroll-service-refactor-agent`

```bash
claude-task payroll-service-refactor-agent \
  --source "/backend/app/services/payroll_service.py" \
  --target-size 20KB \
  --split-into 3 \
  --output "/backend/app/services/payroll/"
```

**Target Structure**:
```
/backend/app/services/payroll/
├── __init__.py
├── calculator.py       # Calculation logic (~15KB)
├── deductions.py       # Deduction rules (~12KB)
└── reports.py          # Report generation (~13KB)
```

**Verification** (after all 3 refactors):
```bash
# Check no service > 25KB
find /backend/app/services -name "*.py" -exec wc -l {} \; | sort -rn | head -5

# All should be < 600 lines
# Expected: All services < 25KB
```

---

### STEP 5-6: TODO Resolution (2 Agents, Sequential)

#### STEP 5: Capacity Verification
**Agent**: `capacity-verification-agent`

```bash
claude-task capacity-verification-agent \
  --file "/backend/app/services/apartment_service.py" \
  --line 142 \
  --issue "implement apartment capacity verification"
```

**Task Details**:
```python
# Line 142 - Current TODO:
# TODO: Add apartment capacity verification when assigning residents

# What needs to happen:
1. Add capacity_constraint to Apartment model
2. Check occupied_count < total_capacity in assignment
3. Raise ValidationError if overcapacity
4. Add tests for capacity logic
```

**Expected Implementation**:
```python
def validate_apartment_capacity(apartment_id: int, new_residents: int):
    apartment = db.query(Apartment).get(apartment_id)
    occupied = db.query(Assignment).filter(
        Assignment.apartment_id == apartment_id,
        Assignment.status == "active"
    ).count()

    if occupied + new_residents > apartment.capacity:
        raise CapacityExceededError(f"Apartment capacity is {apartment.capacity}")
```

#### STEP 6: Permission System Completion
**Agent**: `permission-system-completion-agent`

```bash
claude-task permission-system-completion-agent \
  --file "/backend/app/core/rate_limiter.py" \
  --todos 4 \
  --issue "move rate limiting to database"
```

**Task Details**:
```python
# Line 45 - TODO: Move to database-backed store
# Line 78 - TODO: Add admin rate limit overrides
# Line 112 - TODO: Add rate limit analytics
# Line 156 - TODO: Add exponential backoff

# Implementation:
1. Create RateLimitStore service using DB
2. Replace memory-based RedisStore
3. Add admin override mechanism
4. Add analytics tracking
5. Implement exponential backoff
```

**Expected Structure**:
```
/backend/app/services/rate_limiter_service.py
├── RateLimitStore        # Database-backed store
├── RateLimitAnalytics    # Tracking
├── AdminOverrides        # Permission overrides
└── ExponentialBackoff    # Backoff logic
```

---

## 🟠 PHASE 2: HIGH PRIORITY (Week 2-3)

### STEP 7-9: Security Enhancement (3 Agents, Parallel)

#### STEP 7: File Upload Security
**Agent**: `file-upload-security-agent`

```bash
claude-task file-upload-security-agent \
  --target "/backend/app/api/candidates.py" \
  --target "/backend/app/api/employees.py" \
  --validations "mime-type|file-size|virus-scan" \
  --output "/backend/app/services/file_security_service.py"
```

**Implementation**:
```python
# Create FileSecurityValidator service
class FileSecurityValidator:
    ALLOWED_MIME_TYPES = {
        "image/jpeg", "image/png",
        "application/pdf",
        "application/vnd.openxmlformats"
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def validate_upload(file: UploadFile):
        # 1. Check MIME type
        # 2. Check file size
        # 3. Scan with ClamAV
        # 4. Store securely
```

#### STEP 8: Audit Trail Completion
**Agent**: `audit-trail-completion-agent`

```bash
claude-task audit-trail-completion-agent \
  --database "postgresql" \
  --scope "sensitive-operations" \
  --output "/backend/migrations/"
```

**Creates**:
- Database triggers for INSERT/UPDATE/DELETE on sensitive tables
- New audit table columns
- Audit query API endpoints
- Audit report generation

#### STEP 9: Secrets Management
**Agent**: `secrets-management-agent`

```bash
claude-task secrets-management-agent \
  --audit-scope "all .env usage" \
  --implement "rotation-policies" \
  --documentation "secrets-access.md"
```

---

### STEP 10-12: Performance Optimization (3 Agents, Parallel)

#### STEP 10: Database Indexing
**Agent**: `database-indexing-agent`

```bash
claude-task database-indexing-agent \
  --database "postgresql" \
  --analyze-queries 100 \
  --create-indexes "composite|partial" \
  --output "/backend/migrations/new_indexes.py"
```

**Expected Indexes** (~8-10):
```sql
-- Composite index for common filters
CREATE INDEX idx_employees_factory_status
  ON employees(factory_id, status)
  WHERE is_deleted = false;

-- Partial index for soft deletes
CREATE INDEX idx_candidates_pending
  ON candidates(created_at DESC)
  WHERE status = 'pending' AND is_deleted = false;

-- For yukyu queries
CREATE INDEX idx_assignments_apartment_active
  ON assignments(apartment_id, status)
  WHERE status = 'active';
```

**Performance Impact**:
- Query performance: +30-50%
- Slow query count: -80%

#### STEP 11: OCR Parallelization
**Agent**: `ocr-parallelization-agent`

```bash
claude-task ocr-parallelization-agent \
  --current-latency "5-10s" \
  --target-latency "1-2s" \
  --implementation "celery|async" \
  --output "/backend/tasks/"
```

**Architecture**:
```
User uploads file
    ↓
API returns immediately with task_id (no wait)
    ↓
Celery worker processes OCR async
    ↓
Client polls /api/ocr/{task_id}/status
    ↓
Result returned when ready
```

**Creates**:
- `/backend/tasks/ocr_tasks.py` - Celery OCR tasks
- `/backend/api/ocr.py` - Polling endpoints
- `/backend/core/ocr_queue.py` - Task queue management

#### STEP 12: N+1 Query Optimization
**Agent**: `n-plus-one-query-agent`

```bash
claude-task n-plus-one-query-agent \
  --identify-queries \
  --scope "all endpoints" \
  --fix-pattern "joinedload|selectinload" \
  --verify "before-after"
```

**Fixes** (~15+ endpoints):
```python
# BEFORE: N+1 queries
candidates = db.query(Candidate).all()
for candidate in candidates:
    print(candidate.documents)  # N additional queries!

# AFTER: Single query with eager loading
from sqlalchemy.orm import joinedload
candidates = db.query(Candidate).options(
    joinedload(Candidate.documents)
).all()
```

---

### STEP 13-14: Frontend Optimization (2 Agents)

#### STEP 13: Code Splitting
**Agent**: `frontend-code-splitting-agent`

```bash
claude-task frontend-code-splitting-agent \
  --framework "next.js" \
  --analyze-bundle \
  --target-reduction "20%" \
  --output "/frontend/next.config.js"
```

**Implementation**:
```typescript
// Dynamic imports for heavy components
export default dynamic(
  () => import('@/components/HeavyChart'),
  { loading: () => <LoadingSpinner /> }
);

// Route-based code splitting
const payrollRoute = dynamic(() => import('@/app/payroll'));
```

#### STEP 14: State Management Consistency
**Agent**: `state-management-consistency-agent`

```bash
claude-task state-management-consistency-agent \
  --audit-stores \
  --framework "zustand" \
  --create-guidelines "STORE_PATTERNS.md"
```

---

## 🟡 PHASE 3: MEDIUM PRIORITY (Week 3-4)

### STEP 15-17: Testing Improvements (3 Agents, Parallel)

#### STEP 15: Integration Tests
**Agent**: `integration-test-agent`

```bash
claude-task integration-test-agent \
  --test-workflows 4 \
  --workflows "candidate-to-employee|payroll-calculation|apartment-assignment|ocr-processing" \
  --output "/backend/tests/integration/"
```

**Test Workflows**:
```python
# 1. test_candidate_to_employee_workflow()
#    - Create candidate
#    - Interview (passed)
#    - Approve
#    - Create NYUUSHA
#    - Fill employee data
#    - Approve NYUUSHA
#    - Verify employee created
#    - Verify data sync

# 2. test_payroll_calculation_flow()
# 3. test_apartment_assignment_flow()
# 4. test_ocr_processing_flow()
```

#### STEP 16: OCR Integration Tests
**Agent**: `ocr-integration-test-agent`

```bash
claude-task ocr-integration-test-agent \
  --providers "azure|gemini|easyocr|tesseract" \
  --test-scenarios "single-provider|fallback|accuracy|performance" \
  --output "/backend/tests/ocr/"
```

#### STEP 17: E2E Expansion
**Agent**: `e2e-expansion-agent`

```bash
claude-task e2e-expansion-agent \
  --framework "playwright" \
  --test-journeys 15 \
  --include "accessibility|performance|error-cases" \
  --output "/frontend/e2e/"
```

---

### STEP 18-19: Documentation Team (2 Agents)

#### STEP 18: API Documentation
**Agent**: `api-documentation-agent`

```bash
claude-task api-documentation-agent \
  --generate "openapi|postman" \
  --complete-descriptions \
  --add-examples \
  --output "/docs/api/"
```

#### STEP 19: Changelog Generation
**Agent**: `changelog-generator-agent`

```bash
claude-task changelog-generator-agent \
  --analyze-commits \
  --generate-changelog \
  --document-breaking-changes \
  --output "/CHANGELOG.md"
```

---

### STEP 20: Real-time Features

#### STEP 20: WebSocket Notifications
**Agent**: `websocket-notifications-agent`

```bash
claude-task websocket-notifications-agent \
  --implement "notifications|presence|sync" \
  --framework "fastapi-websockets" \
  --output "/backend/services/notification_service.py"
```

---

## 🔵 PHASE 4: NICE-TO-HAVE (Week 4+)

### STEP 21-25: Advanced Features (5 Agents, Sequential)

#### STEP 21: Analytics
**Agent**: `advanced-analytics-agent`
- Create analytics dashboard
- Payroll analytics
- Hiring analytics
- Retention analytics

#### STEP 22: Reporting Engine
**Agent**: `reporting-engine-agent`
- Scheduled report generation
- PDF export
- Email delivery
- Custom report builder

#### STEP 23: Multi-Language Support
**Agent**: `multi-language-support-agent`
- i18n framework
- Translation files (EN/JA/ES)
- Language switcher

#### STEP 24: Monitoring & Observability
**Agent**: `monitoring-observability-agent`
- OpenTelemetry complete
- Prometheus metrics
- Grafana dashboards
- Alerting rules

#### STEP 25: Backup & Recovery
**Agent**: `backup-recovery-agent`
- Automated backups
- Recovery procedures
- Disaster recovery plan

---

## 📊 MONITORING & VERIFICATION

### Phase 1 Verification Checklist
```bash
# After all Phase 1 agents complete
✅ All services < 25KB
   find /backend/app/services -name "*.py" -exec wc -c {} \; | awk '$1 > 25000'

✅ All logging standardized
   grep -r "print(" /backend/app | grep -v "test" | wc -l  # Should be 0

✅ All TODOs resolved
   grep -r "TODO\|FIXME" /backend --include="*.py" | wc -l  # Should be 0

✅ Tests passing
   pytest /backend/tests -v

✅ No broken imports
   python -m py_compile /backend/app/**/*.py
```

### Phase 2 Verification
```bash
# Performance improvements
✅ Database query performance +30%
✅ OCR latency < 2 seconds
✅ Frontend bundle -20%
✅ File uploads secured with validation
```

### Phase 3 Verification
```bash
✅ Integration test coverage: 50+ tests
✅ E2E coverage: 15+ user journeys
✅ API documentation: 100%
✅ WebSocket notifications: Functional
```

### Phase 4 Verification
```bash
✅ Advanced analytics: Complete
✅ Multi-language: 3 languages
✅ Monitoring: Full observability
✅ Backup: Automated & tested
```

---

## 🎯 PARALLEL EXECUTION STRATEGY

### Day 1
```
logging-standardization-agent
  ↓ (blocks others)
```

### Days 2-3
```
assignment-service-refactor    ↓
yukyu-service-refactor         ↓ (parallel)
payroll-service-refactor       ↓
capacity-verification          ↓
permission-system              ↓
```

### Days 4-5
```
file-upload-security           ↓
audit-trail-completion         ↓ (parallel)
database-indexing              ↓
ocr-parallelization            ↓
n-plus-one-query               ↓
frontend-code-splitting        ↓
state-management-consistency   ↓
```

### Days 6-8
```
integration-test               ↓
ocr-integration-test          ↓ (parallel)
e2e-expansion                 ↓
api-documentation             ↓
changelog-generator           ↓
websocket-notifications       ↓
```

### Days 9+
```
analytics                      ↓
reporting-engine              ↓ (sequential)
multi-language                ↓
monitoring                    ↓
backup-recovery               ↓
```

---

## ⚠️ ROLLBACK PROCEDURE

If any agent's work causes issues:

```bash
# 1. Git reset to before agent
git reset --hard <commit-before-agent>

# 2. Identify issue
pytest -x  # Stop on first failure

# 3. Create issue ticket
# 4. Rerun agent with fixes
```

---

## 📞 AGENT COMMUNICATION PROTOCOL

**Between Agents**:
- Logging agent output → used by all others
- Refactored services → consumed by testing agents
- Performance optimizations → verified by testing agents
- Security implementations → verified by integration tests

**Handoff Pattern**:
```
Agent A completes
  ↓
Creates verification report
  ↓
Agent B consumes report
  ↓
Builds on previous work
```

---

## 🎓 LEARNING & IMPROVEMENT

As agents work, they should:
1. Document patterns discovered
2. Create reusable templates
3. Build agent library
4. Improve future agent performance

**Example**: After logging-standardization-agent completes:
- Create `/backend/LOGGING_STANDARDS.md`
- This becomes input for next logging-related agents
- Improves consistency and speed

---

**Ready to deploy?** Start with Phase 1 Day 1:

```bash
claude-task logging-standardization-agent --priority critical
```

Good luck! 🚀
