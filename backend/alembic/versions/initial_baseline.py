"""initial_baseline

Revision ID: initial_baseline
Revises:
Create Date: 2025-10-16

Crea todas las tablas iniciales del sistema usando SQLAlchemy metadata.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData


# revision identifiers, used by Alembic.
revision: str = 'initial_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Importar los modelos para que SQLAlchemy los registre
    from app.models import models

    # Obtener el engine actual de Alembic
    connection = op.get_bind()

    # Crear todas las tablas definidas en los modelos
    models.Base.metadata.create_all(bind=connection)


def downgrade() -> None:
    # Importar los modelos
    from app.models import models

    # Obtener el engine actual de Alembic
    connection = op.get_bind()

    # Eliminar todas las tablas
    models.Base.metadata.drop_all(bind=connection)
