"""Make ai_chats.task_id ON DELETE SET NULL

Revision ID: 6a8d3b0a5f11
Revises: e7b82706bb80
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a8d3b0a5f11'
down_revision: Union[str, Sequence[str], None] = 'e7b82706bb80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('ai_chats_task_id_fkey', 'ai_chats', type_='foreignkey')
    op.create_foreign_key(
        'ai_chats_task_id_fkey',
        'ai_chats',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ai_chats_task_id_fkey', 'ai_chats', type_='foreignkey')
    op.create_foreign_key(
        'ai_chats_task_id_fkey',
        'ai_chats',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='NO ACTION',
    )
