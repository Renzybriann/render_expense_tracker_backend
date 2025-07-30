from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import expenses
from app import models
from app.database import engine

models.Base.metadata.create_all(bind=engine)

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