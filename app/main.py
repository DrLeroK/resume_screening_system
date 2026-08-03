"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
from loguru import logger
import sys

from .config import settings
from .core.exceptions import ScreeningSystemException
from .api.routes import upload, match, search, bias, jobs
from .models.database import init_database

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup/shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    # START THE TASK MANAGER - CRITICAL FIX
    logger.info("Starting task manager...")
    try:
        from .core.task_manager import task_manager
        await task_manager.start()
        logger.info(f"Task manager started with {settings.background_workers} workers")
    except Exception as e:
        logger.error(f"Failed to start task manager: {str(e)}")
        raise
    
    # Pre-load models
    logger.info("Pre-loading ML models...")
    try:
        from .services.embedder import TextEmbedder
        from .services.extractor import InformationExtractor
        
        # Initialize models
        embedder = TextEmbedder()
        extractor = InformationExtractor()
        
        logger.info(f"Models loaded. Embedding dimension: {embedder.get_embedding_dimension()}")
    except Exception as e:
        logger.warning(f"Failed to pre-load models: {str(e)}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Stop task manager
    try:
        from .core.task_manager import task_manager
        await task_manager.stop()
        logger.info("Task manager stopped")
    except Exception as e:
        logger.error(f"Error stopping task manager: {str(e)}")
    
    # Cleanup resources if needed
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI-Powered Resume & Applicant Screening System
    
    Features:
    - Parse resumes from PDF and DOCX files
    - Extract skills, experience, education using NLP
    - Match candidates to job descriptions
    - Semantic search across resumes
    - Bias detection and fairness metrics
    
    ## Endpoints
    
    ### Resume Management
    - **POST /resumes/upload** - Upload and process a resume
    - **GET /resumes/** - List all resumes
    - **GET /resumes/{id}** - Get parsed resume details
    
    ### Matching
    - **POST /matches/real-time** - Real-time candidate matching
    - **POST /matches/async** - Async batch matching
    - **GET /matches/{id}** - Get match results
    
    ### Search
    - **POST /search** - Semantic search across resumes
    
    ### Bias Analysis
    - **POST /bias/analyze** - Analyze bias for protected attributes
    - **GET /bias/report** - Generate comprehensive bias report
    """,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(ScreeningSystemException)
async def screening_exception_handler(request: Request, exc: ScreeningSystemException):
    logger.error(f"Screening exception: {exc.message}, details: {exc.details}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else None
        }
    )

# Include routers
app.include_router(upload.router)
app.include_router(match.router)
app.include_router(search.router)
app.include_router(bias.router)
app.include_router(jobs.router)

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    from .services.searcher import FAISSSearcher
    
    searcher = FAISSSearcher(384)  # Temporary dimension
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "connected",
            "search_index": f"loaded with {searcher.get_index_size()} vectors",
            "api": "running",
            "task_manager": "running"
        }
    }

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }