"""
Configuration settings for DayZ HiveAPI.

This module provides a Pydantic settings class that reads configuration from
environment variables with sensible defaults.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Settings(BaseModel):
    """Application settings loaded from environment variables with defaults."""
    
    # Database settings
    DB_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/hive",
        description="PostgreSQL connection string"
    )
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # JWT settings
    JWT_ISSUER: str = Field(
        default="hiveapi",
        description="JWT issuer claim"
    )
    JWT_ALGORITHM: str = Field(
        default="RS256",
        description="JWT signing algorithm"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="JWT access token expiration in minutes"
    )
    
    # Security settings
    REQUEST_SIGNATURE_REQUIRED: bool = Field(
        default=True,
        description="Require HTTP signatures for server endpoints"
    )
    ORIGIN_SECRET: Optional[str] = Field(
        default="",
        description="Secret for origin verification with Cloudflare Tunnel"
    )
    
    # TTL settings
    IDEMPOTENCY_TTL_SECONDS: int = Field(
        default=600,
        description="Time-to-live for idempotency keys in seconds"
    )
    MOVE_TICKET_TTL_SECONDS: int = Field(
        default=90,
        description="Time-to-live for move tickets in seconds"
    )
    LOGOUT_GRACE_SECONDS: int = Field(
        default=30,
        description="Grace period for logout intent in seconds"
    )
    SERVER_SWITCH_COOLDOWN_SECONDS: int = Field(
        default=180,
        description="Cooldown period between server switches in seconds"
    )
    
    # Observability settings
    PROMETHEUS_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics collection"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Admin settings
    ADMIN_ENABLED: bool = Field(
        default=True,
        description="Enable admin endpoints"
    )
    ADMIN_USERNAME: str = Field(
        default="admin",
        description="Admin username for Basic Auth"
    )
    ADMIN_PASSWORD: str = Field(
        default="",
        description="Admin password for Basic Auth (empty disables auth)"
    )
    
    # Keys directory for server public keys
    KEYS_DIR: str = Field(
        default="./keys",
        description="Directory containing server keys"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

def get_settings() -> Settings:
    """
    Create settings instance from environment variables.
    
    Returns:
        Settings object with values from environment variables or defaults
    """
    return Settings(
        DB_URL=os.getenv("DB_URL", Settings().DB_URL),
        REDIS_URL=os.getenv("REDIS_URL", Settings().REDIS_URL),
        JWT_ISSUER=os.getenv("JWT_ISSUER", Settings().JWT_ISSUER),
        JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", Settings().JWT_ALGORITHM),
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", Settings().JWT_ACCESS_TOKEN_EXPIRE_MINUTES)),
        REQUEST_SIGNATURE_REQUIRED=os.getenv("REQUEST_SIGNATURE_REQUIRED", "True").lower() in ("true", "1", "t"),
        ORIGIN_SECRET=os.getenv("ORIGIN_SECRET", Settings().ORIGIN_SECRET),
        IDEMPOTENCY_TTL_SECONDS=int(os.getenv("IDEMPOTENCY_TTL_SECONDS", Settings().IDEMPOTENCY_TTL_SECONDS)),
        MOVE_TICKET_TTL_SECONDS=int(os.getenv("MOVE_TICKET_TTL_SECONDS", Settings().MOVE_TICKET_TTL_SECONDS)),
        LOGOUT_GRACE_SECONDS=int(os.getenv("LOGOUT_GRACE_SECONDS", Settings().LOGOUT_GRACE_SECONDS)),
        SERVER_SWITCH_COOLDOWN_SECONDS=int(os.getenv("SERVER_SWITCH_COOLDOWN_SECONDS", Settings().SERVER_SWITCH_COOLDOWN_SECONDS)),
        PROMETHEUS_METRICS=os.getenv("PROMETHEUS_METRICS", "True").lower() in ("true", "1", "t"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", Settings().LOG_LEVEL),
        ADMIN_ENABLED=os.getenv("ADMIN_ENABLED", "True").lower() in ("true", "1", "t"),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", Settings().ADMIN_USERNAME),
        ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", Settings().ADMIN_PASSWORD),
        KEYS_DIR=os.getenv("KEYS_DIR", Settings().KEYS_DIR),
    )

# Create a global settings instance
settings = get_settings()
