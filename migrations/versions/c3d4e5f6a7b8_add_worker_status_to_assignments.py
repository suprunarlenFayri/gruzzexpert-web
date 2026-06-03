"""Add worker_status to task assignments

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('worker_status', sa.String(length=20), nullable=False, server_default='assigned')
        )
        batch_op.create_index(batch_op.f('ix_task_assignments_worker_status'), ['worker_status'], unique=False)

    op.execute("""
        UPDATE task_assignments
        SET worker_status = CASE
            WHEN finished_working_at IS NOT NULL THEN 'completed'
            WHEN started_working_at IS NOT NULL THEN 'on_site'
            WHEN en_route_at IS NOT NULL THEN 'en_route'
            ELSE 'assigned'
        END
    """)


def downgrade():
    with op.batch_alter_table('task_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_task_assignments_worker_status'))
        batch_op.drop_column('worker_status')
