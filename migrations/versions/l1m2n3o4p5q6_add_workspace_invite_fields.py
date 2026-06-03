"""Add workspace invite_key and share_token

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-05-27 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'l1m2n3o4p5q6'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invite_key', sa.String(length=23), nullable=True))
        batch_op.add_column(sa.Column('share_token', sa.String(length=50), nullable=True))
        batch_op.create_unique_constraint('uq_workspaces_invite_key', ['invite_key'])
        batch_op.create_unique_constraint('uq_workspaces_share_token', ['share_token'])


def downgrade():
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_constraint('uq_workspaces_share_token', type_='unique')
        batch_op.drop_constraint('uq_workspaces_invite_key', type_='unique')
        batch_op.drop_column('share_token')
        batch_op.drop_column('invite_key')
