"""create initial schema

Revision ID: 004
Revises:
Create Date: 2025-10-09 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Cria o schema inicial completo do banco"""
    user_role_enum = sa.Enum('admin', 'user', name='userrole')
    schedule_status_enum = sa.Enum(
        'pending', 'processing', 'completed', 'failed', 'cancelled', name='schedulestatus'
    )
    log_level_enum = sa.Enum('debug', 'info', 'warning', 'error', 'critical', name='loglevel')

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('account_quota', sa.Integer(), nullable=False, server_default='-1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )

    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('key_hash', name='uq_api_keys_key_hash')
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])

    op.create_table(
        'tiktok_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cookies_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('total_uploads', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_upload', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('account_name', name='uq_tiktok_accounts_account_name')
    )
    op.create_index('ix_tiktok_accounts_account_name', 'tiktok_accounts', ['account_name'])

    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_path', sa.String(length=500), nullable=False),
        sa.Column('video_title', sa.String(length=255), nullable=True),
        sa.Column('video_description', sa.Text(), nullable=True),
        sa.Column('video_tags', sa.JSON(), nullable=True),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', schedule_status_enum, nullable=False, server_default='pending'),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tiktok_url', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_schedules_user_id', 'schedules', ['user_id'])
    op.create_index('ix_schedules_scheduled_time', 'schedules', ['scheduled_time'])
    op.create_index('ix_schedules_status', 'schedules', ['status'])
    op.create_index('ix_schedules_account_name', 'schedules', ['account_name'])

    op.create_table(
        'posting_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('time_slot', sa.String(length=5), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['tiktok_accounts.id'], ondelete='CASCADE')
    )
    op.create_index('ix_posting_schedules_account_id', 'posting_schedules', ['account_id'])
    op.create_index('ix_posting_schedules_time_slot', 'posting_schedules', ['time_slot'])
    op.create_index('ix_posting_schedules_is_active', 'posting_schedules', ['is_active'])
    op.create_index(
        'ix_posting_schedules_account_active',
        'posting_schedules',
        ['account_id', 'is_active']
    )

    op.create_table(
        'video_upload_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['schedule_id'], ['schedules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_video_upload_logs_schedule_id', 'video_upload_logs', ['schedule_id'])
    op.create_index('ix_video_upload_logs_user_id', 'video_upload_logs', ['user_id'])

    op.create_table(
        'system_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('account_name', sa.String(length=100), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('level', log_level_enum, nullable=False, server_default='info'),
        sa.Column('module', sa.String(length=100), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_system_logs_user_id', 'system_logs', ['user_id'])
    op.create_index('ix_system_logs_account_name', 'system_logs', ['account_name'])
    op.create_index('ix_system_logs_level', 'system_logs', ['level'])
    op.create_index('ix_system_logs_created_at', 'system_logs', ['created_at'])

    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(length=20), nullable=False, server_default='dark'),
        sa.Column('accent_color', sa.String(length=20), nullable=False, server_default='#0ea5e9'),
        sa.Column('notifications', sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('timezone', sa.String(length=100), nullable=False,
                  server_default='America/Sao_Paulo'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_preferences_user_id')
    )
    op.create_index('ix_user_preferences_user_id', 'user_preferences', ['user_id'])


def downgrade():
    """Remove o schema inicial completo"""
    op.drop_index('ix_user_preferences_user_id', table_name='user_preferences')
    op.drop_table('user_preferences')

    op.drop_index('ix_system_logs_created_at', table_name='system_logs')
    op.drop_index('ix_system_logs_level', table_name='system_logs')
    op.drop_index('ix_system_logs_account_name', table_name='system_logs')
    op.drop_index('ix_system_logs_user_id', table_name='system_logs')
    op.drop_table('system_logs')

    op.drop_index('ix_video_upload_logs_user_id', table_name='video_upload_logs')
    op.drop_index('ix_video_upload_logs_schedule_id', table_name='video_upload_logs')
    op.drop_table('video_upload_logs')

    op.drop_index('ix_posting_schedules_account_active', table_name='posting_schedules')
    op.drop_index('ix_posting_schedules_is_active', table_name='posting_schedules')
    op.drop_index('ix_posting_schedules_time_slot', table_name='posting_schedules')
    op.drop_index('ix_posting_schedules_account_id', table_name='posting_schedules')
    op.drop_table('posting_schedules')

    op.drop_index('ix_schedules_account_name', table_name='schedules')
    op.drop_index('ix_schedules_status', table_name='schedules')
    op.drop_index('ix_schedules_scheduled_time', table_name='schedules')
    op.drop_index('ix_schedules_user_id', table_name='schedules')
    op.drop_table('schedules')

    op.drop_index('ix_tiktok_accounts_account_name', table_name='tiktok_accounts')
    op.drop_table('tiktok_accounts')

    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')

    bind = op.get_bind()
    log_level_enum = sa.Enum(name='loglevel')
    schedule_status_enum = sa.Enum(name='schedulestatus')
    user_role_enum = sa.Enum(name='userrole')

    log_level_enum.drop(bind, checkfirst=True)
    schedule_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
