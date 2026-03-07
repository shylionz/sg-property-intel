"""
Database configuration and SQLAlchemy models.
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime, Text, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "property_data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Transaction(Base):
    """URA sale transaction record."""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255), nullable=False, index=True)
    street_name = Column(String(255))
    postal_district = Column(String(10))
    market_segment = Column(String(50))
    property_type = Column(String(100))
    tenure = Column(String(100))
    sale_type = Column(String(50))
    sale_date = Column(String(20))  # "Feb-26"
    sale_date_parsed = Column(Date)  # parsed to YYYY-MM-01
    transacted_price = Column(Integer)
    nett_price = Column(Integer)
    area_sqft = Column(Float)  # exact or midpoint
    area_sqft_band = Column(String(50))
    area_sqm = Column(Float)
    price_psf = Column(Integer)
    price_psm = Column(Integer)
    floor_band = Column(String(50))
    number_of_units = Column(Integer)
    size_band = Column(String(20))
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_txn_project", "project_name"),
        Index("idx_txn_district", "postal_district"),
        Index("idx_txn_date", "sale_date_parsed"),
        Index("idx_txn_size_band", "project_name", "size_band"),
    )


class Rental(Base):
    """URA rental contract record."""
    __tablename__ = "rentals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255), nullable=False, index=True)
    street_name = Column(String(255))
    postal_district = Column(String(10))
    property_type = Column(String(100))
    bedrooms = Column(Integer)
    monthly_rent = Column(Integer)
    area_sqft_band = Column(String(50))
    area_sqm_band = Column(String(50))
    area_sqft_midpoint = Column(Float)
    lease_date = Column(String(20))  # "Jan-26"
    lease_date_parsed = Column(Date)
    size_band = Column(String(20))
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_rent_project", "project_name"),
        Index("idx_rent_district", "postal_district"),
        Index("idx_rent_date", "lease_date_parsed"),
        Index("idx_rent_size_band", "project_name", "size_band"),
    )


class IngestionLog(Base):
    """Track data ingestion for caching."""
    __tablename__ = "ingestion_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_type = Column(String(20), nullable=False)  # "transactions" | "rentals"
    project_name = Column(String(255))
    postal_district = Column(String(10))
    fetched_at = Column(DateTime, default=datetime.utcnow)
    record_count = Column(Integer)
    status = Column(String(20))  # "success" | "error"


# Database engine and session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()