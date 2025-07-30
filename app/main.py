from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager
import logging

from app.routers import expenses
from app import models
from app.database import engine, wait_for_db, get_db # Added get_db import

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- The Lifespan Context Manager ---
# This replaces the old @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    logger.info("Starting up application...")
    if wait_for_db():
        logger.info("Database connection established.")
        # This is a good place to create tables if you aren't using a migration tool like Alembic
        try:
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified.")
        except Exception as e:
            logger.error(f"Could not create database tables: {e}")
    else:
        logger.critical("Could not establish database connection. Application will not start correctly.")
    
    yield # The application runs here

    logger.info("Shutting down application...")


# --- Initialize the App with the Lifespan ---
app = FastAPI(
    title="Expense Tracker API",
    description="API for tracking personal expenses",
    version="1.0.0",
    lifespan=lifespan # Use the new lifespan manager
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routers
app.include_router(expenses.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Expense Tracker API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# --- Improved Health Check ---
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that performs a quick, non-blocking check of the database.
    """
    try:
        # A simple query to confirm the connection is live
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

# Note: The old @app.on_event("startup") function has been removed.