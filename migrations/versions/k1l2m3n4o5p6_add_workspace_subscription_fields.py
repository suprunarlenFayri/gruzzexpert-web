"""Add workspace subscription fields

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-05-27 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'k1l2m3n4o5p6'
down_revision = 'j0k1l2m3n4o5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('admin_limit', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_column('expires_at')
        batch_op.drop_column('admin_limit')
