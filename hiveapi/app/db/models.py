"""
SQLAlchemy models for DayZ HiveAPI.

This module defines the database schema using SQLAlchemy ORM.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create Base class for models
Base = declarative_base()

def generate_uuid():
    """Generate a UUID string for use as a primary key."""
    return str(uuid.uuid4())

class Tenant(Base):
    """Tenant model for multi-tenant support."""
    
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)
    settings_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clusters = relationship("Cluster", back_populates="tenant", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_tenants_owner_id", "owner_id"),
    )

class Cluster(Base):
    """Cluster model representing a group of DayZ servers."""
    
    __tablename__ = "clusters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    policy_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="clusters")
    servers = relationship("Server", back_populates="cluster", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="cluster")
    
    # Indices
    __table_args__ = (
        Index("ix_clusters_tenant_id", "tenant_id"),
    )

class Server(Base):
    """Server model representing a DayZ game server."""
    
    __tablename__ = "servers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    cluster_id = Column(String, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    host_fingerprint = Column(String, nullable=False, unique=True)
    public_key_pem = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="inactive")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    
    # Relationships
    cluster = relationship("Cluster", back_populates="servers")
    owned_characters = relationship("Character", back_populates="owning_server", foreign_keys="Character.owned_by_server")
    events = relationship("Event", back_populates="server")
    
    # Indices
    __table_args__ = (
        Index("ix_servers_cluster_id", "cluster_id"),
        Index("ix_servers_host_fingerprint", "host_fingerprint"),
        Index("ix_servers_status", "status"),
    )

class Player(Base):
    """Player model representing a DayZ player."""
    
    __tablename__ = "players"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    platform_uid = Column(String, nullable=False, unique=True)
    reputation = Column(Integer, nullable=False, default=0)
    meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    
    # Relationships
    characters = relationship("Character", back_populates="player", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_players_platform_uid", "platform_uid"),
    )

class Character(Base):
    """Character model representing a player's character in DayZ."""
    
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    player_id = Column(String, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    cluster_id = Column(String, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False)
    owned_by_server = Column(String, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    life_state = Column(String, nullable=False, default="alive")
    position = Column(JSONB, nullable=True)
    stats_json = Column(JSONB, nullable=False, default=dict)
    inventory_json = Column(JSONB, nullable=True)
    inventory_checksum = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    
    # Relationships
    player = relationship("Player", back_populates="characters")
    cluster = relationship("Cluster", back_populates="characters")
    owning_server = relationship("Server", back_populates="owned_characters", foreign_keys=[owned_by_server])
    
    # Indices
    __table_args__ = (
        Index("ix_characters_player_id", "player_id"),
        Index("ix_characters_cluster_id", "cluster_id"),
        Index("ix_characters_owned_by_server", "owned_by_server"),
        Index("ix_characters_life_state", "life_state"),
    )

class Event(Base):
    """Event model for audit logging."""
    
    __tablename__ = "events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    type = Column(String, nullable=False)
    actor = Column(String, nullable=True)
    object_id = Column(String, nullable=True)
    server_id = Column(String, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    payload_json = Column(JSONB, nullable=False, default=dict)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="events")
    
    # Indices
    __table_args__ = (
        Index("ix_events_type", "type"),
        Index("ix_events_object_id", "object_id"),
        Index("ix_events_server_id", "server_id"),
        Index("ix_events_ts", "ts"),
    )

class IdempotencyKey(Base):
    """Idempotency key model for ensuring idempotent operations."""
    
    __tablename__ = "idempotency_keys"
    
    key = Column(String, primary_key=True)
    server_id = Column(String, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indices
    __table_args__ = (
        Index("ix_idempotency_keys_server_id", "server_id"),
        Index("ix_idempotency_keys_created_at", "created_at"),
    )

class MoveTicket(Base):
    """Move ticket model for character server transfers."""
    
    __tablename__ = "move_tickets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    character_id = Column(String, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    source_server_id = Column(String, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    target_server_id = Column(String, ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default="issued")
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    redeemed_at = Column(DateTime, nullable=True)
    
    # Indices
    __table_args__ = (
        Index("ix_move_tickets_character_id", "character_id"),
        Index("ix_move_tickets_source_server_id", "source_server_id"),
        Index("ix_move_tickets_target_server_id", "target_server_id"),
        Index("ix_move_tickets_status", "status"),
        Index("ix_move_tickets_expires_at", "expires_at"),
    )
