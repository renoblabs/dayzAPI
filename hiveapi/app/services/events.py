"""
Events service for DayZ HiveAPI.

This module provides utilities for recording and retrieving events
for auditing and monitoring purposes.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID

from ..db.models import Event

logger = logging.getLogger(__name__)

def append_event(
    db: Session,
    type: str,
    server_id: Optional[str] = None,
    actor: Optional[str] = None,
    object_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Event:
    """
    Append a new event to the events log.
    
    Args:
        db: Database session
        type: Event type identifier (e.g., 'character_claimed', 'logout_intent')
        server_id: UUID of the server that triggered the event
        actor: Identifier of the actor (e.g., platform_uid, admin username)
        object_id: UUID of the object this event relates to (e.g., character_id)
        payload: Additional data related to the event
        
    Returns:
        The created Event object
    """
    try:
        # Create payload dict if None
        if payload is None:
            payload = {}
        
        # Create event
        event = Event(
            type=type,
            actor=actor,
            object_id=object_id,
            server_id=server_id,
            payload_json=payload,
            ts=datetime.utcnow()
        )
        
        # Add to session
        db.add(event)
        
        # Log at debug level
        logger.debug(f"Event recorded: {type} for object {object_id} by server {server_id}")
        
        return event
        
    except Exception as e:
        logger.error(f"Failed to record event {type}: {str(e)}")
        # Don't raise exception - events should be non-blocking
        return None

def get_recent_events(
    db: Session,
    limit: int = 100,
    event_type: Optional[str] = None,
    server_id: Optional[str] = None,
    object_id: Optional[str] = None
) -> List[Event]:
    """
    Get recent events, optionally filtered by type, server, or object.
    
    Args:
        db: Database session
        limit: Maximum number of events to return
        event_type: Filter by event type
        server_id: Filter by server ID
        object_id: Filter by object ID
        
    Returns:
        List of Event objects
    """
    query = db.query(Event)
    
    if event_type:
        query = query.filter(Event.type == event_type)
    
    if server_id:
        query = query.filter(Event.server_id == server_id)
    
    if object_id:
        query = query.filter(Event.object_id == object_id)
    
    return query.order_by(desc(Event.ts)).limit(limit).all()

def record_character_event(
    db: Session,
    character_id: str,
    server_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None
) -> Event:
    """
    Convenience function to record a character-related event.
    
    Args:
        db: Database session
        character_id: UUID of the character
        server_id: UUID of the server
        event_type: Event type identifier
        payload: Additional data related to the event
        
    Returns:
        The created Event object
    """
    return append_event(
        db=db,
        type=event_type,
        server_id=server_id,
        object_id=character_id,
        payload=payload
    )

def record_inventory_event(
    db: Session,
    character_id: str,
    server_id: str,
    event_type: str,
    checksum: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Event:
    """
    Convenience function to record an inventory-related event.
    
    Args:
        db: Database session
        character_id: UUID of the character
        server_id: UUID of the server
        event_type: Event type identifier
        checksum: Inventory checksum
        payload: Additional data related to the event
        
    Returns:
        The created Event object
    """
    if payload is None:
        payload = {}
    
    if checksum:
        payload["checksum"] = checksum
    
    return append_event(
        db=db,
        type=event_type,
        server_id=server_id,
        object_id=character_id,
        payload=payload
    )

def record_security_event(
    db: Session,
    event_type: str,
    server_id: Optional[str] = None,
    actor: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Event:
    """
    Record a security-related event (authentication, authorization).
    
    Args:
        db: Database session
        event_type: Event type identifier
        server_id: UUID of the server
        actor: Identifier of the actor
        payload: Additional data related to the event
        
    Returns:
        The created Event object
    """
    return append_event(
        db=db,
        type=f"security_{event_type}",
        server_id=server_id,
        actor=actor,
        payload=payload
    )
