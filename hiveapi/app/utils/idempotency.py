"""
Idempotency utilities for DayZ HiveAPI.

This module provides functions to ensure idempotent operations using Redis as primary
storage and database as fallback. Idempotency is critical for preventing duplicate
processing of requests in distributed systems.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from redis.asyncio import Redis
from typing import Optional

from ..db.models import IdempotencyKey
from ..config import settings

logger = logging.getLogger(__name__)

async def ensure_idempotent(key: str, server_id: str, redis: Redis, db: Session) -> bool:
    """
    Ensure idempotent processing by checking if the key has already been used.
    If the key is new, it's stored in Redis with TTL and in the database for persistence.
    
    Args:
        key: Idempotency key to check
        server_id: UUID of the server making the request
        redis: Redis client
        db: Database session
        
    Returns:
        bool: True if the key is new and was stored, False if it already exists
        
    Example:
        ```python
        if not await ensure_idempotent(idempotency_key, server_id, redis, db):
            return {"message": "Request already processed", "idempotent": True}
        # Continue with request processing
        ```
    """
    # Normalize key for storage
    redis_key = f"idem:{key}"
    
    # Check if key exists in Redis (fast path)
    if await redis.exists(redis_key):
        logger.debug(f"Idempotency key already exists in Redis: {key}")
        return False
    
    # Check if key exists in database (fallback)
    db_key = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if db_key:
        # Key exists in DB but not in Redis, restore it to Redis
        logger.debug(f"Idempotency key found in DB but not Redis, restoring: {key}")
        await redis.set(
            redis_key, 
            server_id,
            ex=settings.IDEMPOTENCY_TTL_SECONDS
        )
        return False
    
    # Key is new, store it in Redis with TTL
    try:
        await redis.set(
            redis_key,
            server_id,
            ex=settings.IDEMPOTENCY_TTL_SECONDS
        )
        
        # Store in database for persistence
        db_key = IdempotencyKey(
            key=key,
            server_id=server_id,
            created_at=datetime.utcnow()
        )
        db.add(db_key)
        db.commit()
        
        logger.debug(f"New idempotency key stored: {key}")
        return True
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error storing idempotency key: {str(e)}")
        # If DB storage fails but Redis succeeded, we still consider it stored
        return True
    except Exception as e:
        logger.error(f"Error ensuring idempotency: {str(e)}")
        # On any other error, we try to delete the Redis key to be safe
        await redis.delete(redis_key)
        return False

async def check_idempotent(key: str, redis: Redis, db: Session) -> Optional[str]:
    """
    Check if an idempotency key exists without storing it.
    
    Args:
        key: Idempotency key to check
        redis: Redis client
        db: Database session
        
    Returns:
        Optional[str]: Server ID associated with the key if it exists, None otherwise
    """
    redis_key = f"idem:{key}"
    
    # Check Redis first
    server_id = await redis.get(redis_key)
    if server_id:
        return server_id
    
    # Check database as fallback
    db_key = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if db_key:
        # Restore to Redis
        await redis.set(
            redis_key,
            db_key.server_id,
            ex=settings.IDEMPOTENCY_TTL_SECONDS
        )
        return db_key.server_id
    
    return None

async def remove_idempotency_key(key: str, redis: Redis, db: Session) -> bool:
    """
    Remove an idempotency key from both Redis and database.
    Useful for cleaning up after errors or for testing.
    
    Args:
        key: Idempotency key to remove
        redis: Redis client
        db: Database session
        
    Returns:
        bool: True if key was found and removed, False otherwise
    """
    redis_key = f"idem:{key}"
    removed = False
    
    # Remove from Redis
    if await redis.exists(redis_key):
        await redis.delete(redis_key)
        removed = True
    
    # Remove from database
    try:
        db_key = db.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
        if db_key:
            db.delete(db_key)
            db.commit()
            removed = True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error removing idempotency key: {str(e)}")
    
    return removed

async def cleanup_expired_keys(redis: Redis, db: Session) -> int:
    """
    Cleanup expired idempotency keys from the database.
    This is a maintenance function that should be called periodically.
    
    Args:
        redis: Redis client
        db: Database session
        
    Returns:
        int: Number of keys removed
    """
    try:
        # Calculate expiration threshold
        expiration = datetime.utcnow() - timedelta(seconds=settings.IDEMPOTENCY_TTL_SECONDS)
        
        # Delete expired keys
        result = db.query(IdempotencyKey).filter(
            IdempotencyKey.created_at < expiration
        ).delete()
        
        db.commit()
        return result
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error cleaning up expired idempotency keys: {str(e)}")
        return 0
