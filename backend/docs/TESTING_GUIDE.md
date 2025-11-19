# Testing Guide - Critical Module Testing

## Overview

This guide provides comprehensive testing strategies for critical modules in the UNS-ClaudeJP backend. Proper testing is essential for maintaining code quality, preventing regressions, and ensuring critical features work correctly.

## Test Structure

### Directory Layout

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── fixtures/                      # Reusable fixture data
│   │   ├── __init__.py
│   │   ├── candidates.py              # Candidate fixtures
│   │   ├── employees.py               # Employee fixtures
│   │   └── ...
│   ├── test_auth.py                   # Authentication tests
│   ├── test_candidates_api.py          # Candidate API tests
│   ├── test_employees_api.py           # Employee API tests
│   ├── test_ai_budget_limits.py       # AI Budget tests (critical)
│   ├── test_file_validation.py        # File validation tests (FIX 10)
│   ├── test_migrations.py             # Migration tests (FIX 14)
│   └── ...
└── pytest.ini                         # Pytest configuration
```

## Critical Module Tests

### 1. Authentication & Authorization

**Test File:** `backend/tests/test_auth.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.models.models import User, UserRole

@pytest.fixture
def auth_user(db_session) -> User:
    """Create a test user with admin role."""
    user = User(
        username="testadmin",
        email="admin@test.com",
        hashed_password="hashed_password",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_token(auth_user) -> str:
    """Generate JWT token for test user."""
    return create_access_token(
        data={"sub": auth_user.username, "user_id": auth_user.id}
    )

def test_login_success(client: TestClient):
    """Test successful login."""
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_protected_endpoint_without_token(client: TestClient):
    """Test protected endpoint without authentication token."""
    response = client.get("/api/candidates/")
    assert response.status_code == 401

def test_protected_endpoint_with_token(client: TestClient, auth_token: str):
    """Test protected endpoint with valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/candidates/", headers=headers)
    assert response.status_code == 200
```

### 2. Candidates Module (履歴書)

**Test File:** `backend/tests/test_candidates_api.py`

**Critical Tests:**

```python
import pytest
import io
from fastapi.testclient import TestClient

@pytest.fixture
def valid_pdf_file() -> bytes:
    """Create a minimal valid PDF file."""
    return b'%PDF-1.4\n%minimal pdf content\nendobj\n%%EOF'

@pytest.fixture
def invalid_pdf_file() -> bytes:
    """Create an invalid PDF (spoofed extension)."""
    return b'This is actually a text file, not PDF'

def test_create_candidate(client: TestClient, auth_token: str):
    """Test creating a new candidate."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    candidate_data = {
        "full_name_roman": "Taro Yamada",
        "full_name_kanji": "山田太郎",
        "date_of_birth": "1990-01-15",
        "email": "taro@example.com",
        "phone": "09012345678"
    }
    response = client.post(
        "/api/candidates/",
        json=candidate_data,
        headers=headers
    )
    assert response.status_code == 201
    assert response.json()["full_name_roman"] == "Taro Yamada"

def test_upload_resume_validation(client: TestClient, auth_token: str,
                                   valid_pdf_file: bytes):
    """Test file validation on resume upload (FIX 10)."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Create a candidate first
    candidate_id = 1  # Assume candidate exists

    # Upload valid PDF
    response = client.post(
        f"/api/candidates/{candidate_id}/upload",
        files={"file": ("resume.pdf", valid_pdf_file, "application/pdf")},
        headers=headers
    )
    assert response.status_code == 200

    # Try to upload spoofed file (exe renamed as pdf)
    exe_content = b'MZ\x90\x00\x03'  # EXE magic bytes
    response = client.post(
        f"/api/candidates/{candidate_id}/upload",
        files={"file": ("malware.pdf", exe_content, "application/pdf")},
        headers=headers
    )
    # Should fail validation
    assert response.status_code in [400, 422]
    assert "validation" in response.json()["detail"].lower()

def test_candidate_search_n_plus_one_prevention(client: TestClient,
                                                 auth_token: str,
                                                 db_session):
    """Test that candidate list doesn't have N+1 query problem."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Create multiple candidates with relationships
    for i in range(10):
        candidate = Candidate(
            full_name_roman=f"User{i}",
            full_name_kanji=f"ユーザー{i}",
            email=f"user{i}@test.com"
        )
        db_session.add(candidate)
    db_session.commit()

    # Query should use eager loading (joinedload/selectinload)
    with QueryCounter() as counter:
        response = client.get("/api/candidates/", headers=headers)
        assert response.status_code == 200

        # Should be ~3 queries (not 11 = 1 for list + 10 for relationships)
        assert counter.count <= 5, f"Too many queries: {counter.count}"

def test_get_candidate_by_id(client: TestClient, auth_token: str):
    """Test retrieving single candidate."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/candidates/1", headers=headers)
    assert response.status_code in [200, 404]  # 404 if doesn't exist

def test_update_candidate(client: TestClient, auth_token: str):
    """Test updating candidate information."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    updated_data = {
        "full_name_roman": "Updated Name",
        "email": "newemail@test.com"
    }
    response = client.put(
        "/api/candidates/1",
        json=updated_data,
        headers=headers
    )
    assert response.status_code in [200, 404]

def test_delete_candidate(client: TestClient, auth_token: str):
    """Test candidate deletion."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.delete("/api/candidates/1", headers=headers)
    assert response.status_code in [200, 204, 404]
```

### 3. AI Budget Service (Critical Fix #9 - Atomic Operations)

**Test File:** `backend/tests/test_ai_budget_atomic.py`

```python
import pytest
from concurrent.futures import ThreadPoolExecutor
from app.services.ai_budget_service import AIBudgetService
from app.models.models import AIBudget, User

@pytest.fixture
def ai_budget_service(db_session) -> AIBudgetService:
    """Create AIBudgetService instance."""
    return AIBudgetService(db_session)

@pytest.fixture
def test_user(db_session) -> User:
    """Create test user."""
    user = User(username="budgetuser", email="budget@test.com")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_budget(db_session, test_user) -> AIBudget:
    """Create test AI budget."""
    budget = AIBudget(
        user_id=test_user.id,
        monthly_limit=1000.0,
        spent_this_month=0.0,
        spent_today=0.0,
        daily_limit=100.0
    )
    db_session.add(budget)
    db_session.commit()
    return budget

def test_atomic_budget_spend_no_race_condition(
    ai_budget_service: AIBudgetService,
    test_user: User,
    test_budget: AIBudget
):
    """Test atomic spending to prevent race conditions (FIX 9)."""

    def concurrent_spend(amount: float):
        """Simulate concurrent spending."""
        ai_budget_service.record_spending(test_user.id, amount)

    # Simulate 10 concurrent requests spending $5 each = $50 total
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(concurrent_spend, 5.0) for _ in range(10)]
        for future in futures:
            future.result()

    # Verify final spent amount is exactly $50 (no lost updates)
    budget = ai_budget_service.get_budget(test_user.id)
    assert budget.spent_this_month == 50.0, \
        f"Expected 50.0, got {budget.spent_this_month} - race condition detected!"

def test_pessimistic_locking_prevents_overdraft(
    ai_budget_service: AIBudgetService,
    test_user: User,
    test_budget: AIBudget
):
    """Test that pessimistic locking prevents budget overdraft."""

    # Try to spend $1500 when limit is $1000
    with pytest.raises(Exception) as exc_info:
        ai_budget_service.validate_spending(test_user.id, 1500.0)

    assert "exceeds" in str(exc_info.value).lower() or \
           "limit" in str(exc_info.value).lower()

def test_daily_reset_works_correctly(
    ai_budget_service: AIBudgetService,
    test_user: User,
    db_session
):
    """Test daily budget reset mechanism."""
    budget = AIBudget(
        user_id=test_user.id,
        daily_limit=100.0,
        spent_today=80.0,
        last_reset_date=datetime.now().date() - timedelta(days=1)
    )
    db_session.add(budget)
    db_session.commit()

    # After spending, daily limit should reset if day changed
    ai_budget_service.record_spending(test_user.id, 20.0)

    # Should succeed even though 80+20=100 > daily limit
    # because day changed and spent_today should be reset
    budget = ai_budget_service.get_budget(test_user.id)
    assert budget.spent_today == 20.0  # Reset and new charge
```

### 4. File Validation (Critical Fix #10)

**Test File:** `backend/tests/test_file_validation.py`

```python
import pytest
from app.core.file_validator import FileValidator, FileValidationError, validate_upload

class TestFileValidation:
    """Test file validation with magic bytes (FIX 10)."""

    @staticmethod
    def get_pdf_magic_bytes() -> bytes:
        """Return PDF magic bytes."""
        return b'%PDF-1.4\n%Comment\n1 0 obj<</Type/Catalog>>endobj\nxref\ntrailer<</Size 2/Root 1 0 R>>startxref\n%%EOF'

    @staticmethod
    def get_jpeg_magic_bytes() -> bytes:
        """Return JPEG magic bytes."""
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'

    @staticmethod
    def get_png_magic_bytes() -> bytes:
        """Return PNG magic bytes."""
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'

    @staticmethod
    def get_exe_magic_bytes() -> bytes:
        """Return EXE magic bytes."""
        return b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00'

    def test_valid_pdf(self):
        """Test valid PDF validation."""
        pdf_content = self.get_pdf_magic_bytes()
        is_valid, error = FileValidator.validate_file_type(
            pdf_content,
            "document.pdf",
            ["pdf"]
        )
        assert is_valid
        assert error is None

    def test_valid_jpeg(self):
        """Test valid JPEG validation."""
        jpeg_content = self.get_jpeg_magic_bytes()
        is_valid, error = FileValidator.validate_file_type(
            jpeg_content,
            "photo.jpg",
            ["jpg", "jpeg"]
        )
        assert is_valid
        assert error is None

    def test_spoofed_file_detected(self):
        """Test that spoofed files are detected (exe renamed as pdf)."""
        exe_content = self.get_exe_magic_bytes()
        is_valid, error = FileValidator.validate_file_type(
            exe_content,
            "malware.pdf",
            ["pdf"]
        )
        assert not is_valid
        assert "mismatch" in error.lower() or "invalid" in error.lower()

    def test_empty_file_rejected(self):
        """Test that empty files are rejected."""
        is_valid, error = FileValidator.validate_file_type(
            b"",
            "empty.pdf",
            ["pdf"]
        )
        assert not is_valid
        assert "empty" in error.lower()

    def test_extension_not_allowed(self):
        """Test that disallowed extensions are rejected."""
        is_valid, error = FileValidator.validate_file_type(
            self.get_exe_magic_bytes(),
            "script.exe",
            ["pdf", "jpg"]  # exe not allowed
        )
        assert not is_valid
        assert "not allowed" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_upload_async(self):
        """Test async validation wrapper."""
        pdf_content = self.get_pdf_magic_bytes()

        # Should not raise
        await validate_upload(
            pdf_content,
            "valid.pdf",
            ["pdf"],
            check_pdf=True
        )

    @pytest.mark.asyncio
    async def test_validate_upload_fails(self):
        """Test async validation failure."""
        exe_content = self.get_exe_magic_bytes()

        with pytest.raises(FileValidationError):
            await validate_upload(
                exe_content,
                "malware.pdf",
                ["pdf"],
                check_pdf=True
            )
```

### 5. Database Migrations (Critical Fix #14)

**Test File:** `backend/tests/test_migrations.py`

```python
import pytest
from alembic.command import upgrade, downgrade
from alembic.config import Config

@pytest.fixture
def alembic_config() -> Config:
    """Provide Alembic config for migration tests."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")
    return config

def test_migration_upgrade(alembic_config: Config):
    """Test that all migrations can be applied successfully."""
    upgrade(alembic_config, "head")
    # If we get here without exception, upgrade succeeded

def test_migration_downgrade(alembic_config: Config):
    """Test that migrations can be rolled back."""
    # Upgrade to head
    upgrade(alembic_config, "head")

    # Downgrade one step
    downgrade(alembic_config, "-1")
    # If we get here without exception, downgrade succeeded

def test_migration_creates_tables(alembic_config: Config):
    """Test that migrations create all required tables."""
    upgrade(alembic_config, "head")

    # Get database connection
    from sqlalchemy import create_engine, inspect
    engine = create_engine("sqlite:///:memory:")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Verify critical tables exist
    required_tables = [
        "users", "candidates", "employees", "factories",
        "timer_cards", "salary_calculations", "ai_budget"
    ]
    for table in required_tables:
        assert table in tables, f"Table {table} not created by migrations"

def test_migration_consistency():
    """Test that migration files follow naming conventions."""
    from pathlib import Path

    migrations_dir = Path("backend/alembic/versions")
    for migration_file in migrations_dir.glob("*.py"):
        if migration_file.name == "__pycache__":
            continue

        # Verify file naming convention: xxx_descriptive_name.py
        parts = migration_file.stem.split("_", 1)
        assert len(parts) == 2, f"Migration {migration_file} doesn't follow naming convention"
        assert parts[0].isalnum(), f"Revision ID in {migration_file} is not alphanumeric"
        assert len(parts[1]) > 0, f"Description in {migration_file} is empty"
```

## Common Test Patterns

### 1. Database Fixtures

```python
@pytest.fixture
def db_session(db):
    """Provide database session for tests."""
    yield db.session
    db.session.rollback()

@pytest.fixture
def sample_user(db_session):
    """Create sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        role=UserRole.EMPLOYEE
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_candidate(db_session, sample_user):
    """Create sample candidate."""
    candidate = Candidate(
        full_name_roman="Test User",
        full_name_kanji="テスト ユーザー",
        email="candidate@test.com",
        created_by_user_id=sample_user.id
    )
    db_session.add(candidate)
    db_session.commit()
    return candidate
```

### 2. Mocking External Services

```python
@pytest.fixture
def mock_azure_ocr(monkeypatch):
    """Mock Azure OCR service."""
    def mock_analyze(*args, **kwargs):
        return {
            "readResult": [{
                "lines": [{
                    "text": "Sample OCR text"
                }]
            }]
        }

    monkeypatch.setattr("app.services.ocr.azure.analyze", mock_analyze)
    return mock_analyze

@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service."""
    emails_sent = []

    def mock_send(to: str, subject: str, body: str):
        emails_sent.append({
            "to": to,
            "subject": subject,
            "body": body
        })
        return True

    monkeypatch.setattr("app.services.email.send", mock_send)
    return emails_sent
```

### 3. Performance Testing

```python
import time

def test_endpoint_performance(client: TestClient, auth_token: str):
    """Test that endpoint responds within acceptable time."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    start = time.time()
    response = client.get("/api/candidates/", headers=headers)
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 1.0, f"Endpoint took {elapsed}s, expected < 1s"

class QueryCounter:
    """Context manager to count database queries."""

    def __init__(self):
        self.count = 0

    def __enter__(self):
        # Hook into SQLAlchemy event system to count queries
        from sqlalchemy import event
        from app.core.database import engine

        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            self.count += 1

        event.listen(engine, "before_cursor_execute", receive_before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        from sqlalchemy import event
        from app.core.database import engine
        event.remove(engine, "before_cursor_execute")
```

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage report
pytest backend/tests/ --cov=app --cov-report=html

# Run specific test file
pytest backend/tests/test_candidates_api.py -v

# Run tests matching pattern
pytest -k "test_atomic" -v

# Run tests with markers
pytest -m "not slow" -v
```

### Run Specific Module Tests

```bash
# Authentication tests
pytest backend/tests/test_auth.py -v

# Candidates API tests
pytest backend/tests/test_candidates_api.py -v

# AI Budget tests (atomic operations)
pytest backend/tests/test_ai_budget_atomic.py -v

# File validation tests
pytest backend/tests/test_file_validation.py -v

# Migration tests
pytest backend/tests/test_migrations.py -v
```

### Run with Logging

```bash
# Show print statements and logs
pytest -s -v backend/tests/test_candidates_api.py

# Run with different log levels
pytest --log-cli-level=DEBUG backend/tests/
```

## Test Coverage Requirements

### Minimum Coverage by Module

| Module | Minimum Coverage |
|--------|------------------|
| Authentication | 90% |
| Candidates API | 85% |
| Employees API | 85% |
| AI Budget Service | 95% (critical for race conditions) |
| File Validation | 95% (security-critical) |
| Database Models | 80% |
| Services | 85% |
| Utilities | 80% |

### Run Coverage Report

```bash
# Generate coverage report
pytest backend/tests/ --cov=app --cov-report=html --cov-report=term-missing

# Check coverage for specific module
pytest backend/tests/ --cov=app.services.ai_budget --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest backend/tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

### ✅ DO

1. **Write descriptive test names** that explain what is being tested
   ```python
   def test_upload_resume_with_invalid_mime_type_rejected():
       # Clear what's being tested
   ```

2. **Use fixtures for reusable setup**
   ```python
   @pytest.fixture
   def authenticated_client(client, auth_token):
       client.headers["Authorization"] = f"Bearer {auth_token}"
       return client
   ```

3. **Test both success and failure paths**
   ```python
   def test_create_candidate_success():
       # success case

   def test_create_candidate_invalid_data():
       # failure case
   ```

4. **Use context managers for resource management**
   ```python
   with QueryCounter() as counter:
       response = client.get(...)
       assert counter.count < 5
   ```

5. **Test critical business logic thoroughly**
   - All authentication/authorization paths
   - Budget calculations and limits
   - File validation and security
   - Data consistency and race conditions

### ❌ DON'T

1. **Avoid test interdependencies**
   ```python
   # ❌ BAD: Test B depends on Test A
   def test_a_create():
       # creates data

   def test_b_uses_a_data():  # Fails if test_a doesn't run
       # uses data from test_a

   # ✅ GOOD: Each test is independent
   def test_a_create():
       candidate = create_candidate()
       assert candidate.id

   def test_b_uses_its_own_data():
       my_candidate = create_candidate()
       assert my_candidate.id
   ```

2. **Avoid slow tests**
   - Mock external services (Azure, EasyOCR)
   - Use in-memory databases for unit tests
   - Use integration tests only for critical paths

3. **Avoid hardcoded values**
   ```python
   # ❌ BAD
   def test_salary():
       assert calculate_salary(100) == 10000

   # ✅ GOOD
   def test_salary():
       hourly_rate = 100
       hours_worked = 100
       expected = hourly_rate * hours_worked
       assert calculate_salary(hourly_rate, hours_worked) == expected
   ```

4. **Avoid skipping tests without reason**
   ```python
   # ❌ BAD
   @pytest.mark.skip
   def test_important_feature():
       pass

   # ✅ GOOD - Always document why
   @pytest.mark.skip(reason="Waiting for FIX-123 to be implemented")
   def test_important_feature():
       pass
   ```

## Critical Test Checklist

Before merging any changes, ensure:

- [ ] All new code has corresponding tests
- [ ] Critical modules have 95%+ coverage
- [ ] File validation tests include spoofed file scenarios
- [ ] AI budget tests verify atomic operations (no race conditions)
- [ ] Migration tests verify upgrade/downgrade paths
- [ ] Authentication tests cover all role-based access scenarios
- [ ] API endpoint tests include both success and error cases
- [ ] Performance tests verify N+1 queries are prevented
- [ ] All tests pass locally with `pytest backend/tests/ -v`
- [ ] Coverage report shows no critical code is untested
- [ ] No hardcoded test data in test files
- [ ] Mocked external services (Azure OCR, etc.)

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **FastAPI testing guide**: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- **SQLAlchemy testing**: https://docs.sqlalchemy.org/en/20/orm/extensions/hybrid.html
- **Alembic testing**: https://alembic.sqlalchemy.org/en/latest/

## Troubleshooting

### Tests Fail with "Database locked"

This typically means multiple tests are trying to write to the same database. Solution:

```python
@pytest.fixture
def db_session(db):
    """Provide isolated database session."""
    session = db.Session()
    yield session
    session.rollback()
    session.close()
```

### "N+1 Query Problem" Not Detected

Add query counting:

```python
with QueryCounter() as counter:
    response = client.get("/api/candidates/")
    print(f"Queries executed: {counter.count}")
    assert counter.count <= 5
```

### Performance Test Timeout

Increase timeout or check for infinite loops:

```python
@pytest.mark.timeout(30)  # 30 second timeout
def test_slow_operation():
    # test code
    pass
```

### Mocked Service Not Being Used

Verify monkeypatch target matches actual import:

```python
# If service imported as:
from app.services.ocr import azure_ocr

# Monkeypatch:
monkeypatch.setattr("app.services.ocr.azure_ocr", mock_function)
```

---

**Last Updated:** 2025-11-19
**Version:** 1.0.0
**Status:** Production-Ready
