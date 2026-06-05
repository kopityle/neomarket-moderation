"""fix_uuid_types

Revision ID: 527f4d709529
Revises: 3cc0fe597905
Create Date: 2026-06-05 17:32:32.243504

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '527f4d709529'
down_revision: Union[str, None] = '3cc0fe597905'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Меняем тип колонок с VARCHAR на UUID
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN product_id TYPE UUID USING product_id::uuid')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN seller_id TYPE UUID USING seller_id::uuid')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN category_id TYPE UUID USING category_id::uuid')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN assigned_moderator_id TYPE UUID USING assigned_moderator_id::uuid')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN blocking_reason_id TYPE UUID USING blocking_reason_id::uuid')


def downgrade() -> None:
    # Возвращаем обратно к VARCHAR
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN product_id TYPE VARCHAR(36)')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN seller_id TYPE VARCHAR(36)')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN category_id TYPE VARCHAR(36)')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN assigned_moderator_id TYPE VARCHAR(36)')
    op.execute('ALTER TABLE moderation_tasks ALTER COLUMN blocking_reason_id TYPE VARCHAR(36)')