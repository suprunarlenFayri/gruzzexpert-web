"""Add is_group flag to chats

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-24 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chats', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_group', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute("UPDATE chats SET is_group = TRUE WHERE type = 'group'")

    with op.batch_alter_table('chats', schema=None) as batch_op:
        batch_op.alter_column('is_group', server_default=None)


def downgrade():
    with op.batch_alter_table('chats', schema=None) as batch_op:
        batch_op.drop_column('is_group')
