"""add profile_picture to users

Revision ID: c77c00177523
Revises: 004
Create Date: 2025-10-16 23:25:25.490037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c77c00177523'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona coluna profile_picture na tabela users
    op.add_column('users', sa.Column('profile_picture', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove coluna profile_picture da tabela users
    op.drop_column('users', 'profile_picture')
