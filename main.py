# main.py

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes import router
from config import settings
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {getattr(settings, 'ENVIRONMENT', 'development')}")
    logger.info(f"Allowed origins: {getattr(settings, 'ALLOWED_ORIGINS', [])}")
    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="A minimal FastAPI backend with proper logging",
    lifespan=lifespan,
)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses"""
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.debug(f"Request headers: {dict(request.headers)}")

    try:
        response = await call_next(request)
        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code}"
        )
        return response
    except Exception as e:
        logger.error(
            f"Request failed: {request.method} {request.url.path} - "
            f"Error: {str(e)}",
            exc_info=True,
        )
        raise


# CORS Middleware (uncomment and configure as needed)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500, content={"message": "Internal server error", "status": "error"}
    )


# Include routers
app.include_router(router, prefix="/api/v1")
logger.info("API routes registered at /api/v1")


@app.get("/")
def root():
    """Root endpoint"""
    logger.debug("Root endpoint accessed")
    return {"message": "Welcome to FastAPI", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    logger.debug("Health check endpoint accessed")
    return {
        "message": "Application is running.",
        "status": "healthy",
        "app_name": settings.APP_NAME,
    }
