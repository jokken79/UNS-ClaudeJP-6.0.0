"""
N+1 Query Detector and Optimizer Guide

Detecta y sugiere optimizaciones para N+1 queries en endpoints FastAPI
"""

import re
from pathlib import Path
from typing import List, Tuple


def find_n_plus_one_patterns(api_dir: str = "backend/app/api") -> List[Tuple[str, int, str]]:
    """
    Encuentra patrones N+1 queries en archivos de API.

    Retorna: Lista de (archivo, línea, patrón)
    """
    patterns_found = []

    n_plus_one_patterns = [
        # Pattern 1: Loop después de query sin eager loading
        (r'(\s+)candidates\s*=\s*db\.query\(Candidate\)\..*?\.all\(\)\s*\n\s*for.*?in\s+candidates:\s*\n.*?\w+\.\w+\s*#.*?causes N\+1',
         "Loop after query without eager loading"),

        # Pattern 2: Relaciones accedidas sin joinedload
        (r'candidate\s*=\s*db\.query\(Candidate\)\.filter.*?\.first\(\)\s*\n.*?candidate\..*?\.',
         "Accessing relationships without joinedload"),

        # Pattern 3: Count en loop
        (r'for.*?in.*?:\s*\n.*?db\.query.*?\.count\(\)',
         "Count query in loop"),
    ]

    api_path = Path(api_dir)
    for py_file in api_path.glob("*.py"):
        with open(py_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                # Básico: detectar queries sin eager loading antes de acceso a relaciones
                if 'db.query(Candidate)' in line and '.filter' in line and '.first()' in line:
                    # Check if next lines access relationships
                    for j in range(i, min(i+10, len(lines))):
                        if any(rel in lines[j] for rel in ['.employee', '.documents', '.photos']):
                            patterns_found.append((
                                str(py_file),
                                i,
                                f"Candidate query may cause N+1 when accessing relationships"
                            ))
                            break

    return patterns_found


OPTIMIZATION_GUIDE = """
# N+1 Query Optimization Guide

## Problem
N+1 queries occur when:
1. Query loads a collection (1 query)
2. Loop accesses related data for each item (N queries)
3. Total: 1 + N queries instead of 1 optimized query

Example:
```python
# BAD: 1 + 166 queries (1 for candidates, 166 for each candidate's relationships)
candidates = db.query(Candidate).all()
for candidate in candidates:
    print(candidate.employee.factory.name)  # Each access = 1 query
```

## Solution: Eager Loading

### Option 1: joinedload (LEFT OUTER JOIN)
Use when you always need the relationship and want one query.

```python
from sqlalchemy.orm import joinedload

candidates = db.query(Candidate)\
    .options(joinedload(Candidate.employee))\
    .all()
```

### Option 2: selectinload (Separate efficient query)
Use when loading many records with large relationships.

```python
from sqlalchemy.orm import selectinload

candidates = db.query(Candidate)\
    .options(selectinload(Candidate.employee))\
    .all()
```

### Option 3: contains_eager (with filters)
Use when filtering on relationships.

```python
from sqlalchemy.orm import contains_eager

candidates = db.query(Candidate)\
    .join(Employee)\
    .filter(Employee.status == 'active')\
    .options(contains_eager(Candidate.employee))\
    .all()
```

## Critical Endpoints to Optimize (High Impact)

### GET /candidates - List all candidates
- BEFORE: 1 + (166 * 3) = 499 queries
- AFTER: 3 queries with eager loading
- Impact: 99.4% reduction

```python
@router.get("/", response_model=List[CandidateResponse])
async def list_candidates(db: Session = Depends(get_db)):
    return db.query(Candidate)\
        .options(
            selectinload(Candidate.employee),
            selectinload(Candidate.documents),
            selectinload(Candidate.photos)
        )\
        .all()
```

### GET /employees - List all employees
- BEFORE: 1 + (250 * 4) = 1001 queries
- AFTER: 4 queries
- Impact: 99.9% reduction

```python
@router.get("/", response_model=List[EmployeeResponse])
async def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee)\
        .options(
            selectinload(Employee.factory),
            selectinload(Employee.apartment),
            selectinload(Employee.candidate),
            selectinload(Employee.contracts)
        )\
        .all()
```

### POST /import - Bulk import
- BEFORE: Unpredictable, can be 1000+ queries
- AFTER: Controlled batch inserts with minimal queries
- Impact: 95%+ reduction

```python
@router.post("/import")
async def import_data(file: UploadFile, db: Session = Depends(get_db)):
    # Use bulk_insert_mappings for efficiency
    db.bulk_insert_mappings(Candidate, candidates_data)
    db.commit()
    # Total: ~3 queries instead of 166+
```

## Implementation Checklist

### List Endpoints (High Priority)
- [ ] GET /candidates
- [ ] GET /employees
- [ ] GET /factories
- [ ] GET /timercards
- [ ] GET /payroll

### Detail Endpoints (Medium Priority)
- [ ] GET /candidates/{id}
- [ ] GET /employees/{id}
- [ ] GET /factories/{id}

### Create/Update Endpoints (Low Priority)
- [ ] POST /candidates
- [ ] PUT /candidates/{id}
- [ ] POST /employees

## Performance Testing

```python
import time
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

# Then in endpoint:
queries_before = len(engine.pool._checked_out) + len(engine.pool._checked_in)
result = db.query(Candidate).all()
queries_after = len(engine.pool._checked_out) + len(engine.pool._checked_in)
print(f"Queries executed: {queries_after - queries_before}")
```

## Monitoring & Prevention

### Use query logging to detect N+1
```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Pytest plugin: pytest-query-monitor
```bash
pip install pytest-query-monitor
pytest --query-monitor  # Will warn about queries > threshold
```

## When NOT to Use Eager Loading

1. **Conditional relationships**: Load only when needed
2. **Large collections**: May cause memory issues
3. **Circular references**: Can cause infinite loops
4. **APIs with sparse field access**: Use GraphQL or sparse fieldsets

Solution: Use lazy loading with specific queries
```python
@router.get("/{id}")
async def get_candidate(id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == id).first()
    # Only load employee if needed
    if candidate:
        candidate.employee  # Lazy load on demand
    return candidate
```
"""

if __name__ == "__main__":
    patterns = find_n_plus_one_patterns()
    print(f"Found {len(patterns)} potential N+1 query patterns:")
    for file, line, pattern in patterns[:10]:
        print(f"  {file}:{line} - {pattern}")

    print("\n" + OPTIMIZATION_GUIDE)
