"""Add task address and rename deadline to execution_date

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('address', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('execution_date', sa.Date(), nullable=True))

    op.execute("""
        UPDATE tasks
        SET execution_date = date(deadline)
        WHERE deadline IS NOT NULL
    """)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('deadline')


def downgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deadline', sa.DateTime(), nullable=True))

    op.execute("""
        UPDATE tasks
        SET deadline = datetime(execution_date)
        WHERE execution_date IS NOT NULL
    """)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('execution_date')
        batch_op.drop_column('address')
