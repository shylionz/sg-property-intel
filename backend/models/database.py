"""
Database models and initialization for Singapore Property Intelligence Tool.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sg_property_intel.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Initialize the database."""
    Base.metadata.create_all(bind=engine)

# Database models

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)
    street_name = Column(String)
    postal_district = Column(String)
    market_segment = Column(String)
    property_type = Column(String)
    tenure = Column(String)
    sale_type = Column(String)
    sale_date = Column(String)  # stored as "MMM-YY" e.g. "Feb-26"
    sale_date_parsed = Column(Date)  # parsed to YYYY-MM-01 for querying
    transacted_price = Column(Integer)
    nett_price = Column(Integer)
    area_sqft = Column(Float)  # midpoint of band e.g. 1259.39 (exact from URA)
    area_sqft_band = Column(String)  # original band string if returned as range
    area_sqm = Column(Float)
    price_psf = Column(Integer)
    price_psm = Column(Integer)
    floor_band = Column(String)
    number_of_units = Column(Integer)
    size_band = Column(String)  # normalised: "<600"|"600-900"|"900-1200"|"1200-1600"|"1600-2200"|">2200"
    fetched_at = Column(DateTime, default=func.now())

class Rental(Base):
    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)
    street_name = Column(String)
    postal_district = Column(String)
    property_type = Column(String)
    bedrooms = Column(Integer)
    monthly_rent = Column(Integer)
    area_sqft_band = Column(String)  # e.g. "1,400 to 1,500"
    area_sqft_midpoint = Column(Float)  # computed midpoint
    area_sqm_band = Column(String)
    lease_date = Column(String)  # "Jan-26"
    lease_date_parsed = Column(Date)  # YYYY-MM-01
    size_band = Column(String)  # same normalised bands as transactions
    fetched_at = Column(DateTime, default=func.now())

class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String, nullable=False)  # "transactions" | "rentals"
    project_name = Column(String)
    postal_district = Column(String)
    fetched_at = Column(DateTime, default=func.now())
    record_count = Column(Integer)
    status = Column(String)  # "success" | "error"

# Helper functions

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()