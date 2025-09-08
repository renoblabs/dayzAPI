"""
Dependency injection for DayZ HiveAPI.

This module provides dependency injection functions for database and Redis connections.
"""

import logging
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from redis.asyncio import Redis, from_url

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,  # Check connection before using from pool
    pool_size=10,        # Default connection pool size
    max_overflow=20,     # Allow up to 20 connections beyond pool_size
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Import models to ensure they're registered with Base
from .db import models  # noqa

def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Get a Redis client.
    
    Yields:
        Redis client
    """
    redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield redis
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        raise
    finally:
        await redis.close()
