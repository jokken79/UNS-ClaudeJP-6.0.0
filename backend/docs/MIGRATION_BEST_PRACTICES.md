# Migration Best Practices - Alembic Guide

## Overview

This project uses Alembic 1.17.0 for database migrations with SQLAlchemy 2.0.36 ORM.

## Standard Migration Pattern

### Creating Migrations

```bash
# Access backend container
docker exec -it uns-claudejp-backend bash

# Auto-generate migration from model changes
cd /app
alembic revision --autogenerate -m "Add new field to candidates table"

# Manually create migration for complex changes
alembic revision -m "Create index on candidates.status"
```

### Generated Migration Template

All migrations follow this pattern:

```python
from alembic import op
import sqlalchemy as sa

# Revision identifiers (auto-generated)
revision = 'abc123def456'
down_revision = 'xyz789uvw012'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade database schema"""
    op.add_column('candidates',
        sa.Column('new_field', sa.String(255), nullable=True)
    )

def downgrade() -> None:
    """Downgrade database schema"""
    op.drop_column('candidates', 'new_field')
```

## Best Practices

### 1. One Migration Per Feature

❌ BAD:
```python
def upgrade():
    # Add column to candidates
    op.add_column(...)
    # Modify employees table
    op.add_column(...)
    # Create new table
    op.create_table(...)
```

✅ GOOD: Create 3 separate migrations
```python
# Migration 1: candidates
def upgrade():
    op.add_column('candidates', ...)

# Migration 2: employees
def upgrade():
    op.add_column('employees', ...)

# Migration 3: new_table
def upgrade():
    op.create_table(...)
```

### 2. Nullable Columns for Existing Tables

When adding columns to tables with existing data, make them nullable:

```python
# ✅ GOOD: nullable=True for existing tables
op.add_column('candidates',
    sa.Column('new_field', sa.String(255), nullable=True)
)
```

### 3. Add Indexes on Foreign Keys

Always index foreign key columns for query performance:

```python
op.create_index('idx_candidates_factory_id', 'candidates', ['factory_id'])
```

### 4. Use Constraints for Data Integrity

```python
# Add NOT NULL with CHECK constraint
op.add_column('candidates',
    sa.Column('status', sa.String(50),
        nullable=False,
        server_default='active'
    )
)
```

### 5. Reversible Migrations

Every upgrade must have a corresponding downgrade:

```python
def upgrade():
    op.add_column('candidates',
        sa.Column('photo_url', sa.String(500), nullable=True)
    )
    op.create_index('idx_candidates_photo', 'candidates', ['photo_url'])

def downgrade():
    op.drop_index('idx_candidates_photo')
    op.drop_column('candidates', 'photo_url')
```

## Migration Workflow

### Development

```bash
# Create model in models.py
# Run auto-generate
alembic revision --autogenerate -m "Add model_name"

# Review generated migration
cat alembic/versions/abc123_add_model_name.py

# Apply migration
alembic upgrade head

# Verify
alembic current  # Show current revision
alembic history  # Show all revisions
```

### Testing

```bash
# Test upgrade path
alembic upgrade head

# Test downgrade path
alembic downgrade -1
alembic upgrade head
```

### Production

```bash
# Show pending migrations
alembic current
alembic heads

# Apply with safety checks
alembic upgrade head  # Docker handles this in init

# Verify
docker exec db psql -U uns_admin -d uns_claudejp -c "\d candidates"
```

## Common Migration Patterns

### Adding a Column with Default

```python
def upgrade():
    op.add_column('candidates',
        sa.Column('hire_date',
            sa.Date,
            nullable=False,
            server_default='2025-01-01'
        )
    )

def downgrade():
    op.drop_column('candidates', 'hire_date')
```

### Renaming a Column

```python
def upgrade():
    op.alter_column('candidates', 'old_name', new_column_name='new_name')

def downgrade():
    op.alter_column('candidates', 'new_name', new_column_name='old_name')
```

### Creating a New Table

```python
def upgrade():
    op.create_table(
        'candidate_qualifications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('candidate_id', sa.Integer, sa.ForeignKey('candidates.id')),
        sa.Column('qualification', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    op.create_index('idx_candidate_qualifications_candidate_id',
        'candidate_qualifications', ['candidate_id']
    )

def downgrade():
    op.drop_index('idx_candidate_qualifications_candidate_id')
    op.drop_table('candidate_qualifications')
```

### Adding Foreign Key

```python
def upgrade():
    op.create_foreign_key(
        'fk_candidates_factory_id',
        'candidates', 'factories',
        ['factory_id'], ['id']
    )

def downgrade():
    op.drop_constraint('fk_candidates_factory_id', 'candidates')
```

## Consistent Naming Conventions

### Table Names
- Lowercase, snake_case
- Plural: `candidates`, `employees`, `factories`

### Column Names
- Lowercase, snake_case
- Foreign keys: `table_id` (e.g., `factory_id`, `candidate_id`)
- Timestamps: `created_at`, `updated_at`
- Booleans: `is_active`, `is_deleted`

### Index Names
- Format: `idx_{table}_{column}`
- Example: `idx_candidates_factory_id`

### Constraint Names
- Format: `fk_{table}_{referenced_table}`
- Example: `fk_candidates_factories`

## Verification Checklist

Before committing a migration:

- [ ] Migration has clear, descriptive name
- [ ] Both `upgrade()` and `downgrade()` are implemented
- [ ] All new columns specify `nullable` explicitly
- [ ] Foreign keys have corresponding indexes
- [ ] Migration tested locally (up and down)
- [ ] No breaking changes without migration path
- [ ] Default values provided for required columns
- [ ] Comments explain complex changes

## Troubleshooting

### "Can't find revision identified by 'xyz'"
- Check revision ID matches in file header
- Ensure file is in `alembic/versions/` directory

### "No downgrade specified"
- Implement `downgrade()` function
- Must reverse all changes from `upgrade()`

### Migration fails in production
- Check server defaults for NULL columns
- Verify foreign key constraints exist
- Check for circular dependencies

### Alembic out of sync
```bash
# Reset to clean state (development only!)
rm alembic/versions/*.py
git checkout alembic/versions/
alembic stamp head
```

## Performance Considerations

### Large Table Alterations

Adding columns to large tables can lock tables:
```python
# For large tables, add nullable column first
op.add_column('candidates',
    sa.Column('new_field', sa.String(255), nullable=True)
)

# Then later, update defaults and make NOT NULL
op.execute('UPDATE candidates SET new_field = DEFAULT')
op.alter_column('candidates', 'new_field', existing_nullable=True, nullable=False)
```

### Indexing Strategy

Always index before foreign keys:
```python
op.create_index('idx_candidates_factory_id', 'candidates', ['factory_id'])
op.create_foreign_key(..., columns=['factory_id'], ...)
```

## Monitoring

Track migration status:

```bash
# Current state
alembic current

# Pending upgrades
alembic upgrade --sql head

# All history
alembic history --verbose
```

## CI/CD Integration

Migrations run automatically on startup:
```bash
# In docker-compose.yml importer service:
python scripts/manage_db.py migrate
```

Database health check validates migrations:
```bash
healthcheck:
  test: ["CMD", "alembic", "current"]
  interval: 30s
  timeout: 10s
```
