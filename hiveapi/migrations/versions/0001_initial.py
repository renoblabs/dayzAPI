"""
Initial database migration for DayZ HiveAPI.

Creates all tables for the application:
- tenants
- clusters
- servers
- players
- characters
- events
- idempotency_keys
- move_tickets

Revision ID: 0001_initial
Revises: 
Create Date: 2023-09-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime


# revision identifiers, used by Alembic
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def generate_uuid():
    """Generate a UUID string for use as a primary key."""
    return str(uuid.uuid4())


def upgrade():
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_owner_id', 'tenants', ['owner_id'])

    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('policy_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clusters_tenant_id', 'clusters', ['tenant_id'])

    # Create servers table
    op.create_table(
        'servers',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('cluster_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('host_fingerprint', sa.String(), nullable=False, unique=True),
        sa.Column('public_key_pem', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='inactive'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_servers_cluster_id', 'servers', ['cluster_id'])
    op.create_index('ix_servers_host_fingerprint', 'servers', ['host_fingerprint'])
    op.create_index('ix_servers_status', 'servers', ['status'])

    # Create players table
    op.create_table(
        'players',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('platform_uid', sa.String(), nullable=False, unique=True),
        sa.Column('reputation', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_players_platform_uid', 'players', ['platform_uid'])

    # Create characters table
    op.create_table(
        'characters',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('player_id', sa.String(), nullable=False),
        sa.Column('cluster_id', sa.String(), nullable=False),
        sa.Column('owned_by_server', sa.String(), nullable=True),
        sa.Column('life_state', sa.String(), nullable=False, server_default='alive'),
        sa.Column('position', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('stats_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('inventory_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('inventory_checksum', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owned_by_server'], ['servers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_characters_player_id', 'characters', ['player_id'])
    op.create_index('ix_characters_cluster_id', 'characters', ['cluster_id'])
    op.create_index('ix_characters_owned_by_server', 'characters', ['owned_by_server'])
    op.create_index('ix_characters_life_state', 'characters', ['life_state'])

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('actor', sa.String(), nullable=True),
        sa.Column('object_id', sa.String(), nullable=True),
        sa.Column('server_id', sa.String(), nullable=True),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ts', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_events_type', 'events', ['type'])
    op.create_index('ix_events_object_id', 'events', ['object_id'])
    op.create_index('ix_events_server_id', 'events', ['server_id'])
    op.create_index('ix_events_ts', 'events', ['ts'])

    # Create idempotency_keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('key', sa.String(), primary_key=True),
        sa.Column('server_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index('ix_idempotency_keys_server_id', 'idempotency_keys', ['server_id'])
    op.create_index('ix_idempotency_keys_created_at', 'idempotency_keys', ['created_at'])

    # Create move_tickets table
    op.create_table(
        'move_tickets',
        sa.Column('id', sa.String(), primary_key=True, default=generate_uuid),
        sa.Column('character_id', sa.String(), nullable=False),
        sa.Column('source_server_id', sa.String(), nullable=True),
        sa.Column('target_server_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='issued'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('redeemed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_server_id'], ['servers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_server_id'], ['servers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_move_tickets_character_id', 'move_tickets', ['character_id'])
    op.create_index('ix_move_tickets_source_server_id', 'move_tickets', ['source_server_id'])
    op.create_index('ix_move_tickets_target_server_id', 'move_tickets', ['target_server_id'])
    op.create_index('ix_move_tickets_status', 'move_tickets', ['status'])
    op.create_index('ix_move_tickets_expires_at', 'move_tickets', ['expires_at'])


def downgrade():
    # Drop all tables in reverse order to avoid foreign key constraint violations
    op.drop_table('move_tickets')
    op.drop_table('idempotency_keys')
    op.drop_table('events')
    op.drop_table('characters')
    op.drop_table('players')
    op.drop_table('servers')
    op.drop_table('clusters')
    op.drop_table('tenants')
