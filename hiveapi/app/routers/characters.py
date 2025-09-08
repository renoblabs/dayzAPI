"""
Characters router for DayZ HiveAPI.

This module provides endpoints for character lifecycle management.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..db.models import Player, Character, Server, Cluster
from ..services.events import record_character_event

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Define request and response models
class ClaimRequest(BaseModel):
    platform_uid: str
    cluster_id: str
    server_id: str
    position: Optional[Dict[str, float]] = None
    stats: Optional[Dict[str, Any]] = None

class HeartbeatRequest(BaseModel):
    character_id: str
    server_id: str
    position: Optional[Dict[str, float]] = None
    stats: Optional[Dict[str, Any]] = None

class CharacterResponse(BaseModel):
    id: str
    player_id: str
    cluster_id: str
    owned_by_server: Optional[str] = None
    life_state: str
    position: Optional[Dict[str, float]] = None
    stats: Optional[Dict[str, Any]] = None
    inventory_checksum: Optional[str] = None
    last_seen_at: Optional[datetime] = None

def get_server_id(
    authorization: Optional[str] = Header(None),
    server_id: Optional[str] = None,
):
    """
    Get server ID from various sources.
    
    In production, this would extract server_id from JWT.
    For development, when REQUEST_SIGNATURE_REQUIRED is False,
    it accepts server_id directly.
    """
    if not settings.REQUEST_SIGNATURE_REQUIRED:
        if server_id:
            return server_id
        # In a real implementation, we'd extract from the JWT
        return None
    
    # In production, validate JWT and extract server_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )

@router.post("/claim", response_model=CharacterResponse)
async def claim_character(
    request: ClaimRequest,
    db: Session = Depends(get_db),
    server_id: str = Depends(get_server_id),
):
    """
    Claim a character for a player in a specific cluster.
    
    If the player doesn't exist, it will be created.
    If the character doesn't exist, it will be created.
    """
    # Verify server exists
    server = db.query(Server).filter(Server.id == request.server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    # Verify cluster exists
    cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    # Find or create player
    player = db.query(Player).filter(Player.platform_uid == request.platform_uid).first()
    if not player:
        player = Player(
            id=str(uuid.uuid4()),
            platform_uid=request.platform_uid,
            reputation=0,
            meta={"created_by": "api"},
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow()
        )
        db.add(player)
        db.flush()
        logger.info(f"Created new player: {player.id} for platform_uid: {request.platform_uid}")
    else:
        # Update last seen
        player.last_seen_at = datetime.utcnow()
    
    # Find or create character
    character = db.query(Character).filter(
        Character.player_id == player.id,
        Character.cluster_id == request.cluster_id,
        Character.life_state == "alive"
    ).first()
    
    if not character:
        # Create new character
        character = Character(
            id=str(uuid.uuid4()),
            player_id=player.id,
            cluster_id=request.cluster_id,
            owned_by_server=request.server_id,
            life_state="alive",
            position=request.position or {"x": 0, "y": 0, "z": 0},
            stats_json=request.stats or {"health": 100, "blood": 5000, "water": 100, "energy": 100},
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow()
        )
        db.add(character)
        
        # Record event
        record_character_event(
            db=db,
            character_id=character.id,
            server_id=request.server_id,
            event_type="character_created",
            payload={"position": character.position}
        )
        
        logger.info(f"Created new character: {character.id} for player: {player.id}")
    else:
        # Update existing character
        character.owned_by_server = request.server_id
        character.last_seen_at = datetime.utcnow()
        
        if request.position:
            character.position = request.position
        
        if request.stats:
            # Merge stats
            if character.stats_json:
                character.stats_json = {**character.stats_json, **request.stats}
            else:
                character.stats_json = request.stats
        
        # Record event
        record_character_event(
            db=db,
            character_id=character.id,
            server_id=request.server_id,
            event_type="character_claimed",
            payload={"position": character.position}
        )
        
        logger.info(f"Claimed existing character: {character.id} for player: {player.id}")
    
    # Commit changes
    db.commit()
    
    # Return character info
    return CharacterResponse(
        id=character.id,
        player_id=character.player_id,
        cluster_id=character.cluster_id,
        owned_by_server=character.owned_by_server,
        life_state=character.life_state,
        position=character.position,
        stats=character.stats_json,
        inventory_checksum=character.inventory_checksum,
        last_seen_at=character.last_seen_at
    )

@router.post("/heartbeat", response_model=CharacterResponse)
async def character_heartbeat(
    request: HeartbeatRequest,
    db: Session = Depends(get_db),
    server_id: str = Depends(get_server_id),
):
    """
    Update character heartbeat to keep it alive.
    """
    # Find character
    character = db.query(Character).filter(Character.id == request.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    # Check if server owns the character
    if character.owned_by_server != request.server_id:
        logger.warning(f"Server {request.server_id} attempted heartbeat for character {character.id} owned by {character.owned_by_server}")
        
        # For development, allow any server to update
        if not settings.REQUEST_SIGNATURE_REQUIRED:
            logger.info(f"Allowing heartbeat due to REQUEST_SIGNATURE_REQUIRED=False")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Server does not own this character"
            )
    
    # Update character
    character.last_seen_at = datetime.utcnow()
    
    if request.position:
        character.position = request.position
    
    if request.stats:
        # Merge stats
        if character.stats_json:
            character.stats_json = {**character.stats_json, **request.stats}
        else:
            character.stats_json = request.stats
    
    # Record event
    record_character_event(
        db=db,
        character_id=character.id,
        server_id=request.server_id,
        event_type="character_heartbeat",
        payload={"position": character.position}
    )
    
    # Commit changes
    db.commit()
    
    # Return character info
    return CharacterResponse(
        id=character.id,
        player_id=character.player_id,
        cluster_id=character.cluster_id,
        owned_by_server=character.owned_by_server,
        life_state=character.life_state,
        position=character.position,
        stats=character.stats_json,
        inventory_checksum=character.inventory_checksum,
        last_seen_at=character.last_seen_at
    )
