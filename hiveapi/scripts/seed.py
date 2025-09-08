#!/usr/bin/env python3
"""
Seed script for DayZ HiveAPI.

This script creates initial data for testing and development:
- Tenant
- Cluster
- Server with RSA keypair
- Player
- Character

Usage:
    python -m scripts.seed
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.deps import SessionLocal
from app.db.models import Tenant, Cluster, Server, Player, Character, Event


def generate_rsa_keypair():
    """Generate RSA keypair for testing."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem


def seed_database(db: Session):
    """Seed the database with initial data."""
    print("Seeding database...")
    
    # Generate RSA keypair for server
    private_pem, public_pem = generate_rsa_keypair()
    
    # Create tenant
    tenant_id = str(uuid.uuid4())
    tenant = Tenant(
        id=tenant_id,
        name="Demo Tenant",
        owner_id="admin",
        settings_json={"description": "Demo tenant for development"}
    )
    db.add(tenant)
    db.flush()
    print(f"Created tenant: {tenant_id}")
    
    # Create cluster
    cluster_id = str(uuid.uuid4())
    cluster = Cluster(
        id=cluster_id,
        tenant_id=tenant_id,
        name="Demo Cluster",
        policy_json={"description": "Demo cluster for development"}
    )
    db.add(cluster)
    db.flush()
    print(f"Created cluster: {cluster_id}")
    
    # Create server
    server_id = str(uuid.uuid4())
    server = Server(
        id=server_id,
        cluster_id=cluster_id,
        name="Demo Server",
        host_fingerprint="demo:fingerprint:123",
        public_key_pem=public_pem,
        status="active",
        created_at=datetime.utcnow()
    )
    db.add(server)
    db.flush()
    print(f"Created server: {server_id}")
    
    # Save private key to file for testing
    keys_dir = Path(__file__).parent.parent / "keys" / "servers"
    keys_dir.mkdir(parents=True, exist_ok=True)
    
    with open(keys_dir / f"{server_id}_private.pem", "w") as f:
        f.write(private_pem)
    
    with open(keys_dir / f"{server_id}_public.pem", "w") as f:
        f.write(public_pem)
    
    print(f"Saved server keys to {keys_dir}")
    
    # Create player
    player_id = str(uuid.uuid4())
    player = Player(
        id=player_id,
        platform_uid="steam:76561198012345678",
        reputation=0,
        meta={"created_by": "seed.py"}
    )
    db.add(player)
    db.flush()
    print(f"Created player: {player_id}")
    
    # Create character
    character_id = str(uuid.uuid4())
    character = Character(
        id=character_id,
        player_id=player_id,
        cluster_id=cluster_id,
        owned_by_server=server_id,
        life_state="alive",
        position={"x": 100, "y": 50, "z": 200},
        stats_json={"health": 100, "blood": 5000, "water": 100, "energy": 100},
        last_seen_at=datetime.utcnow()
    )
    db.add(character)
    db.flush()
    print(f"Created character: {character_id}")
    
    # Create event for character creation
    event_id = str(uuid.uuid4())
    event = Event(
        id=event_id,
        type="character_created",
        actor="seed.py",
        object_id=character_id,
        server_id=server_id,
        payload_json={"method": "seed", "position": character.position}
    )
    db.add(event)
    db.flush()
    print(f"Created event: {event_id}")
    
    # Commit all changes
    db.commit()
    
    # Print summary
    print("\nSeed data created successfully:")
    print(f"  Tenant ID:    {tenant_id}")
    print(f"  Cluster ID:   {cluster_id}")
    print(f"  Server ID:    {server_id}")
    print(f"  Player ID:    {player_id}")
    print(f"  Character ID: {character_id}")
    print("\nFor testing, you can use:")
    print(f"  Server Login: curl -X POST http://localhost:8000/v1/auth/server-login -H \"Content-Type: application/json\" -d '{{\"server_id\":\"{server_id}\",\"proof\":\"<base64_signature>\"}}'\n")


def main():
    """Main entry point."""
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
