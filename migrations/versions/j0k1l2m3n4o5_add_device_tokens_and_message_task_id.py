"""Add device session tokens to users and task_id to messages

Revision ID: j0k1l2m3n4o5
Revises: 41049cd0a899
Create Date: 2026-05-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'j0k1l2m3n4o5'
down_revision = '41049cd0a899'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_desktop_token', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('current_mobile_token', sa.String(length=100), nullable=True))

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_messages_task_id_tasks',
            'tasks',
            ['task_id'],
            ['id'],
        )
        batch_op.create_index(batch_op.f('ix_messages_task_id'), ['task_id'], unique=False)


def downgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_task_id'))
        batch_op.drop_constraint('fk_messages_task_id_tasks', type_='foreignkey')
        batch_op.drop_column('task_id')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('current_mobile_token')
        batch_op.drop_column('current_desktop_token')
