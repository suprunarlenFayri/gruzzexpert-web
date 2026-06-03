"""force_fix_missing_tg_columns

Revision ID: 25f00e4688ba
Revises: x8y9z0a1b2c3
Create Date: 2026-06-03 02:46:49.406598

Идемпотентно добавляет колонки Telegram-фич на живой БД (IF NOT EXISTS).
Без autogenerate-правок clients/birth_date/deadline, которые ломают upgrade.
"""
from alembic import op

revision = '25f00e4688ba'
down_revision = 'x8y9z0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS send_by_enter BOOLEAN NOT NULL DEFAULT true;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_privacy VARCHAR(20) NOT NULL DEFAULT 'contacts';

    ALTER TABLE chat_participants ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false;
    ALTER TABLE chat_participants ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT false;
    ALTER TABLE chat_participants ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMP;

    ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false;
    ALTER TABLE messages ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMP;
    ALTER TABLE messages ADD COLUMN IF NOT EXISTS deleted_for_all BOOLEAN NOT NULL DEFAULT false;
    """)

    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS message_hidden (
        id SERIAL NOT NULL,
        created_at TIMESTAMP,
        user_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE CASCADE,
        CONSTRAINT unique_message_hidden UNIQUE (user_id, message_id)
    );
    CREATE INDEX IF NOT EXISTS ix_message_hidden_user_id ON message_hidden (user_id);
    CREATE INDEX IF NOT EXISTS ix_message_hidden_message_id ON message_hidden (message_id);

    CREATE TABLE IF NOT EXISTS blacklist (
        id SERIAL NOT NULL,
        created_at TIMESTAMP,
        owner_id INTEGER NOT NULL,
        blocked_user_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY(blocked_user_id) REFERENCES users (id) ON DELETE CASCADE,
        CONSTRAINT unique_blacklist_entry UNIQUE (owner_id, blocked_user_id)
    );
    CREATE INDEX IF NOT EXISTS ix_blacklist_owner_id ON blacklist (owner_id);

    CREATE TABLE IF NOT EXISTS user_sessions (
        id SERIAL NOT NULL,
        created_at TIMESTAMP,
        user_id INTEGER NOT NULL,
        device_name VARCHAR(200),
        ip_address VARCHAR(45),
        last_active TIMESTAMP,
        token VARCHAR(100) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS ix_user_sessions_created_at ON user_sessions (created_at);
    CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions (user_id);
    CREATE INDEX IF NOT EXISTS ix_user_sessions_token ON user_sessions (token);
    """)


def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS user_sessions;
    DROP TABLE IF EXISTS blacklist;
    DROP TABLE IF EXISTS message_hidden;

    DROP INDEX IF EXISTS ix_users_username;

    ALTER TABLE messages DROP COLUMN IF EXISTS deleted_for_all;
    ALTER TABLE messages DROP COLUMN IF EXISTS pinned_at;
    ALTER TABLE messages DROP COLUMN IF EXISTS is_pinned;

    ALTER TABLE chat_participants DROP COLUMN IF EXISTS pinned_at;
    ALTER TABLE chat_participants DROP COLUMN IF EXISTS is_hidden;
    ALTER TABLE chat_participants DROP COLUMN IF EXISTS is_pinned;

    ALTER TABLE users DROP COLUMN IF EXISTS phone_privacy;
    ALTER TABLE users DROP COLUMN IF EXISTS send_by_enter;
    ALTER TABLE users DROP COLUMN IF EXISTS username;
    """)
