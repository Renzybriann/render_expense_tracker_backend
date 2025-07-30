from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routers import expenses
from app import models
from app.database import engine, wait_for_db
from sqlalchemy.exc import OperationalError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Don't create tables on startup - use Alembic migrations instead
# models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking personal expenses",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(expenses.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Expense Tracker API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
def health_check():
    """Health check endpoint that verifies database connectivity"""
    try:
        if wait_for_db(max_retries=3, delay=1):
            return {"status": "healthy", "database": "connected"}
        else:
            raise HTTPException(status_code=503, detail="Database connection failed")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("Starting up application...")
    if wait_for_db():
        logger.info("Database connection established")
        # Optionally create tables here if not using migrations
        try:
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.warning(f"Could not create tables: {e}")
    else:
        logger.warning("Could not establish database connection on startup")