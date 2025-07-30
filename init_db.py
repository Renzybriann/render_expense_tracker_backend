#!/usr/bin/env python3
"""
Database initialization script.
Run this after deployment to create tables if not using Alembic.
"""

from app.database import engine
from app.models import Base

def init_database():
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")

if __name__ == "__main__":
    init_database()