"""Add tasks_muted_until for worker sleep mode

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-05-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'q0r1s2t3u4v5'
down_revision = 'p9q0r1s2t3u4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tasks_muted_until', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('tasks_muted_until')
