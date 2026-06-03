"""users.phone nullable для аккаунта создателя без телефона."""

from alembic import op
import sqlalchemy as sa


revision = 'z0a1b2c3d4e5'
down_revision = 'y9z0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=True)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=False)
