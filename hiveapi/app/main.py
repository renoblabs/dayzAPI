"""
Main FastAPI application for DayZ HiveAPI.

This module initializes the FastAPI application, configures logging,
sets up Prometheus metrics, and includes all routers.
"""

import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import prometheus_client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DayZ HiveAPI",
    description="API for DayZ server cluster synchronization",
    version="0.1.0",
    docs_url="/docs" if settings.ADMIN_ENABLED else None,
    redoc_url="/redoc" if settings.ADMIN_ENABLED else None,
)

# Define Prometheus metrics
if settings.PROMETHEUS_METRICS:
    REQUEST_COUNT = Counter(
        "hiveapi_requests_total",
        "Total count of requests by method and path",
        ["method", "path", "status_code"]
    )
    REQUEST_LATENCY = Histogram(
        "hiveapi_request_duration_seconds",
        "Request duration in seconds by method and path",
        ["method", "path"]
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware for Prometheus metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Record metrics if enabled
    if settings.PROMETHEUS_METRICS:
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(
            method=request.method, 
            path=request.url.path
        ).observe(duration)
        REQUEST_COUNT.labels(
            method=request.method, 
            path=request.url.path,
            status_code=response.status_code
        ).inc()
    
    return response

# Root endpoint
@app.get("/", response_class=JSONResponse)
async def root():
    """
    Root endpoint returning API name and version.
    """
    return {
        "name": "DayZ HiveAPI",
        "version": "0.1.0",
        "status": "operational"
    }

# Health check endpoint
@app.get("/health", response_class=JSONResponse)
async def health():
    """
    Health check endpoint for monitoring systems.
    """
    # In a more complex implementation, we would check database and Redis connectivity
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# Metrics endpoint for Prometheus
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    if not settings.PROMETHEUS_METRICS:
        return PlainTextResponse(
            content="Metrics collection is disabled",
            status_code=404
        )
    
    return PlainTextResponse(
        content=generate_latest().decode(),
        media_type=CONTENT_TYPE_LATEST
    )

# -------------------------------------------------
# Dynamically import and register routers
# -------------------------------------------------

def _include_router(module_name: str, prefix: str, tag: str) -> None:
    """
    Helper to import a router module safely and register it
    if the import succeeds. Logs a warning otherwise.
    """
    try:
        module = __import__(f"{__package__}.routers.{module_name}", fromlist=["router"])
        router = getattr(module, "router", None)
        if router is None:  # pragma: no cover
            logger.warning(f"Router not found in module '{module_name}'")
            return
        app.include_router(router, prefix=prefix, tags=[tag])
        logger.debug(f"Registered router '{module_name}' at prefix '{prefix}'")
    except ImportError as exc:  # pragma: no cover
        logger.warning(f"Could not import router '{module_name}': {exc}")

# Core routers
_include_router("auth", "/v1/auth", "auth")
_include_router("characters", "/v1/characters", "characters")
_include_router("inventory", "/v1/inventory", "inventory")

# Admin router (optional)
if settings.ADMIN_ENABLED:
    _include_router("admin", "/v1/admin", "admin")

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts.
    """
    logger.info("Starting DayZ HiveAPI")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application shuts down.
    """
    logger.info("Shutting down DayZ HiveAPI")

# If this module is run directly, start the application with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
