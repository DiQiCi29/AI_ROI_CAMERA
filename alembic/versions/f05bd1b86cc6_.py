"""empty message

Revision ID: f05bd1b86cc6
Revises: ff8622ea77ea
Create Date: 2026-05-23 01:27:21.769301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f05bd1b86cc6'
down_revision: Union[str, Sequence[str], None] = 'ff8622ea77ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
