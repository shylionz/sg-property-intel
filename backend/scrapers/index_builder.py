"""Build project name index from URA transaction data."""
import time
import json
import os
from sqlalchemy.orm import sessionmaker
from models.database import SessionLocal, Transaction, Rental

def build_project_index_from_db():
    """Build project index from existing database data."""
    print("Building project index from existing database...")
    
    db = SessionLocal()
    try:
        # Get all unique project names from transactions
        transaction_projects = db.query(Transaction.project_name).distinct().all()
        
        # Get all unique project names from rentals
        rental_projects = db.query(Rental.project_name).distinct().all()
        
        # Combine and deduplicate
        all_names = set()
        
        for project in transaction_projects:
            if project[0]:  # Check if not None/empty
                all_names.add(project[0].upper())
        
        for project in rental_projects:
            if project[0]:  # Check if not None/empty
                all_names.add(project[0].upper())
        
        names = sorted(list(all_names))
        os.makedirs("data", exist_ok=True)
        with open("data/project_index.json", "w") as f:
            json.dump(names, f, indent=2)
        
        print(f"Done! {len(names)} projects indexed from database.")
        return names
        
    except Exception as e:
        print(f"Error building index from database: {e}")
        return []
    finally:
        db.close()

if __name__ == "__main__":
    build_project_index_from_db()