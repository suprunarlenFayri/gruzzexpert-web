"""Add chat delete_at and task extended fields

Revision ID: a1b2c3d4e5f6
Revises: 309ddacd7043
Create Date: 2026-05-23 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '309ddacd7043'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chats', schema=None) as batch_op:
        batch_op.add_column(sa.Column('delete_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chats_delete_at'), ['delete_at'], unique=False)

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_number', sa.String(length=11), nullable=True))
        batch_op.add_column(sa.Column('execution_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('auto_chat', sa.Boolean(), nullable=True))
        batch_op.create_unique_constraint('uq_tasks_task_number', ['task_number'])


def downgrade():
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('uq_tasks_task_number', type_='unique')
        batch_op.drop_column('auto_chat')
        batch_op.drop_column('execution_time')
        batch_op.drop_column('task_number')

    with op.batch_alter_table('chats', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chats_delete_at'))
        batch_op.drop_column('delete_at')
