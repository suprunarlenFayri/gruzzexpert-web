"""Normalize chat participant roles (creator/admin/member)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-24 20:00:00.000000

"""
from alembic import op


revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE chat_participants
        SET role_in_chat = 'creator'
        WHERE role_in_chat = 'admin'
          AND chat_id IN (SELECT id FROM chats WHERE is_group = TRUE OR type = 'group')
          AND user_id IN (
              SELECT cp.user_id
              FROM chat_participants cp
              JOIN chats c ON c.id = cp.chat_id
              WHERE (c.is_group = TRUE OR c.type = 'group')
                AND cp.created_at = (
                    SELECT MIN(cp2.created_at)
                    FROM chat_participants cp2
                    WHERE cp2.chat_id = cp.chat_id
                )
          )
    """)


def downgrade():
    op.execute("""
        UPDATE chat_participants
        SET role_in_chat = 'admin'
        WHERE role_in_chat = 'creator'
    """)
