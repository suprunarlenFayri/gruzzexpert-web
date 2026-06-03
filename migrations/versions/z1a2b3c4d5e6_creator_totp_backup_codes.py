"""TOTP-секрет создателя и резервные коды восстановления."""

from alembic import op
import sqlalchemy as sa


revision = 'z1a2b3c4d5e6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=512), nullable=True))

    op.create_table(
        'user_backup_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_backup_codes_user_id', 'user_backup_codes', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_user_backup_codes_user_id', table_name='user_backup_codes')
    op.drop_table('user_backup_codes')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('totp_secret')
