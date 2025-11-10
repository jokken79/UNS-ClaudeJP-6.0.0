"""add_is_corporate_housing_to_all_personnel

Revision ID: add_is_corporate_housing
Revises:
Create Date: 2025-11-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_is_corporate_housing'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """
    Agregar campo is_corporate_housing a todas las tablas de personal
    - employees
    - contract_workers
    - staff
    """
    # 1. Agregar columna a employees
    op.add_column('employees', sa.Column('is_corporate_housing', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_employees_is_corporate_housing'), 'employees', ['is_corporate_housing'], unique=False)

    # 2. Agregar columna a contract_workers
    op.add_column('contract_workers', sa.Column('is_corporate_housing', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_contract_workers_is_corporate_housing'), 'contract_workers', ['is_corporate_housing'], unique=False)

    # 3. Agregar columna a staff
    op.add_column('staff', sa.Column('is_corporate_housing', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_staff_is_corporate_housing'), 'staff', ['is_corporate_housing'], unique=False)

def downgrade() -> None:
    """
    Eliminar campo is_corporate_housing de todas las tablas
    """
    # 1. Eliminar índices de staff
    op.drop_index(op.f('ix_staff_is_corporate_housing'), table_name='staff')
    op.drop_column('staff', 'is_corporate_housing')

    # 2. Eliminar índices de contract_workers
    op.drop_index(op.f('ix_contract_workers_is_corporate_housing'), table_name='contract_workers')
    op.drop_column('contract_workers', 'is_corporate_housing')

    # 3. Eliminar índices de employees
    op.drop_index(op.f('ix_employees_is_corporate_housing'), table_name='employees')
    op.drop_column('employees', 'is_corporate_housing')
