"""
Singapore Property Transaction Intelligence Tool - Backend
FastAPI application entry point.
"""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db
from api import project, district

# Create database on startup
init_db()

app = FastAPI(
    title="Singapore Property Intelligence API",
    description="URA transaction and rental data with yield analytics",
    version="1.0.0"
)

# CORS - allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(project.router)
app.include_router(district.router)


@app.get("/")
def root():
    return {
        "message": "Singapore Property Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "transactions": "/project/{project_name}/transactions",
            "rentals": "/project/{project_name}/rentals",
            "analytics": "/project/{project_name}/analytics",
            "yield": "/project/{project_name}/yield",
            "district_projects": "/district/{district_code}/projects",
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
