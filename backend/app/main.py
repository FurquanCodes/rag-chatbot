"""
FastAPI Application Entry Point
Main configuration and initialization of the RAG Chatbot backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

# Import configuration and utilities
from app.utils.config import settings, print_startup_info
from app.utils.logger import get_logger
from app.utils.constants import API_V1_PREFIX

# Initialize logger
logger = get_logger(__name__)


# ============ LIFESPAN EVENTS ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown logic
    """
    # STARTUP
    try:
        print_startup_info()
        logger.info(f"🚀 Starting RAG Chatbot Backend")
        logger.info(f"Environment: {settings.api_env}")
        logger.info(f"API running on {settings.api_host}:{settings.api_port}")
        yield
    # SHUTDOWN
    finally:
        logger.info("🛑 Shutting down RAG Chatbot Backend")


# ============ CREATE FASTAPI APP ============
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan
)


# ============ CORS MIDDLEWARE ============
# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ ROOT ENDPOINT ============
@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - Welcome message
    """
    return {
        "message": "Welcome to RAG Chatbot API",
        "version": settings.api_version,
        "docs": f"http://{settings.api_host}:{settings.api_port}/docs"
    }


# ============ HEALTH CHECK ENDPOINT ============
@app.get(f"{API_V1_PREFIX}/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns application status and service availability
    """
    return {
        "status": "healthy",
        "environment": settings.api_env,
        "version": settings.api_version,
        "services": {
            "api": "running",
            "gemini": "configured" if settings.google_api_key else "not_configured",
            "faiss": "ready"
        }
    }


# ============ PLACEHOLDER ROUTES ============
# These will be replaced with actual route imports later

@app.post(f"{API_V1_PREFIX}/upload", tags=["Documents"])
async def upload_documents():
    """
    Upload documents endpoint (placeholder)
    Will be implemented in Step 2
    """
    return {
        "status": "coming_soon",
        "message": "Document upload will be implemented in Step 2"
    }


@app.post(f"{API_V1_PREFIX}/chat", tags=["Chat"])
async def chat():
    """
    Chat endpoint (placeholder)
    Will be implemented in Step 2
    """
    return {
        "status": "coming_soon",
        "message": "Chat functionality will be implemented in Step 2"
    }


@app.get(f"{API_V1_PREFIX}/documents", tags=["Documents"])
async def list_documents():
    """
    List documents endpoint (placeholder)
    Will be implemented in Step 2
    """
    return {
        "status": "coming_soon",
        "message": "Document listing will be implemented in Step 2"
    }


# ============ ERROR HANDLERS ============
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler
    Catches all unhandled exceptions and returns proper error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if settings.api_env == "development" else "An error occurred"
        }
    )


# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_env == "development",
        log_level=settings.log_level.lower()
    )