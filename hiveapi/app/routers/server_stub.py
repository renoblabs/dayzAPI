"""
Server stub router for DayZ HiveAPI.

This module provides endpoints for testing without a real DayZ server.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from ..deps import get_db
from ..db.models import Tenant, Cluster, Server, Event

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Define response models
class PingResponse(BaseModel):
    ok: bool = True

class BootstrapResponse(BaseModel):
    tenant_id: str
    cluster_id: str
    server_id: str

def generate_rsa_keypair():
    """Generate RSA keypair for testing."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return public_pem

@router.get("/ping", response_model=PingResponse)
async def ping():
    """
    Simple ping endpoint for testing connectivity.
    """
    return PingResponse(ok=True)

@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap(db: Session = Depends(get_db)):
    """
    Ensure that a tenant, cluster, and server exist for testing.
    This is idempotent - if entities already exist, returns their IDs.
    """
    # Check if tenant exists
    tenant = db.query(Tenant).first()
    if not tenant:
        # Create tenant
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name="Test Tenant",
            owner_id="server-stub",
            settings_json={"description": "Created by server-stub"}
        )
        db.add(tenant)
        db.flush()
        logger.info(f"Created test tenant: {tenant_id}")
    
    # Check if cluster exists
    cluster = db.query(Cluster).filter(Cluster.tenant_id == tenant.id).first()
    if not cluster:
        # Create cluster
        cluster_id = str(uuid.uuid4())
        cluster = Cluster(
            id=cluster_id,
            tenant_id=tenant.id,
            name="Test Cluster",
            policy_json={"description": "Created by server-stub"}
        )
        db.add(cluster)
        db.flush()
        logger.info(f"Created test cluster: {cluster_id}")
    
    # Check if server exists
    server = db.query(Server).filter(Server.cluster_id == cluster.id).first()
    if not server:
        # Generate RSA public key
        public_pem = generate_rsa_keypair()
        
        # Create server
        server_id = str(uuid.uuid4())
        server = Server(
            id=server_id,
            cluster_id=cluster.id,
            name="Test Server",
            host_fingerprint=f"stub:fingerprint:{server_id}",
            public_key_pem=public_pem,
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(server)
        db.flush()
        logger.info(f"Created test server: {server_id}")
        
        # Record event
        event = Event(
            id=str(uuid.uuid4()),
            type="server_created",
            actor="server-stub",
            object_id=server_id,
            server_id=server_id,
            payload_json={"method": "bootstrap", "source": "server-stub"}
        )
        db.add(event)
    
    # Commit changes
    db.commit()
    
    # Return IDs
    return BootstrapResponse(
        tenant_id=tenant.id,
        cluster_id=cluster.id,
        server_id=server.id
    )
