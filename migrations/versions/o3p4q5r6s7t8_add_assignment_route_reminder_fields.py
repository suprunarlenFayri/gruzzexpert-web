"""Add route reminder timer fields to task_assignments

Revision ID: o3p4q5r6s7t8
Revises: n2o3p4q5r6s7
Create Date: 2026-05-27 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'o3p4q5r6s7t8'
down_revision = 'n2o3p4q5r6s7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('route_reminder_stage', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('route_deadline_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.drop_column('route_deadline_at')
        batch_op.drop_column('route_reminder_stage')
