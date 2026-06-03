"""Add logistics tracking fields to task assignments

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-23 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('en_route_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('started_working_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('finished_working_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.drop_column('finished_working_at')
        batch_op.drop_column('started_working_at')
        batch_op.drop_column('en_route_at')
