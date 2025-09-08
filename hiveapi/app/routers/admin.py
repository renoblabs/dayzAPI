"""
Admin router for DayZ HiveAPI.

This module provides endpoints for administrative functions:
- Overview (counts of entities)
- Events listing and streaming
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_db
from ..db.models import Player, Character, Server, Event
from ..services.events import get_recent_events

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """
    Get overview counts for players, characters, servers, and recent events.
    """
    # Get counts from database
    player_count = db.query(func.count(Player.id)).scalar()
    character_count = db.query(func.count(Character.id)).scalar()
    server_count = db.query(func.count(Server.id)).scalar()
    
    # Get recent events count (last 24 hours)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    recent_events_count = db.query(func.count(Event.id)).filter(
        Event.ts >= one_day_ago
    ).scalar()
    
    return {
        "players": player_count,
        "characters": character_count,
        "servers": server_count,
        "recent_events": recent_events_count,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/events")
async def get_events(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    server_id: Optional[str] = None,
    object_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get recent events with optional filtering.
    
    Args:
        limit: Maximum number of events to return
        event_type: Filter by event type
        server_id: Filter by server ID
        object_id: Filter by object ID (e.g., character ID)
    """
    events = get_recent_events(
        db=db,
        limit=limit,
        event_type=event_type,
        server_id=server_id,
        object_id=object_id
    )
    
    # Convert to dict for JSON response
    return [
        {
            "id": event.id,
            "type": event.type,
            "timestamp": event.ts.isoformat(),
            "server_id": event.server_id,
            "actor": event.actor,
            "object_id": event.object_id,
            "payload": event.payload_json
        }
        for event in events
    ]

async def event_generator(request: Request, db: Session) -> AsyncGenerator[str, None]:
    """
    Generate SSE events by polling the database.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Yields:
        SSE formatted event data
    """
    # Track the latest event ID we've seen
    latest_event_id = None
    
    # Keep track of when we last queried
    last_query_time = datetime.utcnow()
    
    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.debug("Client disconnected from SSE stream")
                break
            
            # Get events since last query
            query = db.query(Event).order_by(Event.ts.desc())
            
            if latest_event_id:
                # Get events newer than the latest we've seen
                latest_event = db.query(Event).filter(Event.id == latest_event_id).first()
                if latest_event:
                    query = query.filter(Event.ts > latest_event.ts)
                else:
                    # If we can't find the latest event, use timestamp
                    query = query.filter(Event.ts > last_query_time)
            
            # Limit to reasonable batch size
            new_events = query.limit(100).all()
            
            # Update latest event ID if we got events
            if new_events:
                latest_event_id = new_events[0].id
                last_query_time = datetime.utcnow()
                
                # Send each event as SSE
                for event in reversed(new_events):  # Oldest first
                    event_data = {
                        "id": event.id,
                        "type": event.type,
                        "timestamp": event.ts.isoformat(),
                        "server_id": event.server_id,
                        "actor": event.actor,
                        "object_id": event.object_id,
                        "payload": event.payload_json
                    }
                    
                    # Format as SSE
                    yield f"data: {json.dumps(event_data)}\n\n"
            
            # Wait before polling again
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Error in event stream: {str(e)}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@router.get("/events/stream")
async def stream_events(request: Request, db: Session = Depends(get_db)):
    """
    Stream events as Server-Sent Events (SSE).
    
    Polls the database every 2 seconds for new events and sends them to the client.
    """
    return StreamingResponse(
        event_generator(request, db),
        media_type="text/event-stream"
    )
