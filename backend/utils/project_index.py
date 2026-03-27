"""
Project name index utilities for dynamic project discovery.
"""
import os
import json
from typing import List, Optional
from pathlib import Path

# Project index file path
PROJECT_INDEX_FILE = "data/project_index.json"

def load_project_index() -> List[str]:
    """Load project index from file."""
    if not os.path.exists(PROJECT_INDEX_FILE):
        return []
    
    try:
        with open(PROJECT_INDEX_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_project_index(project_names: List[str]) -> None:
    """Save project index to file."""
    os.makedirs(os.path.dirname(PROJECT_INDEX_FILE), exist_ok=True)
    with open(PROJECT_INDEX_FILE, 'w') as f:
        json.dump(project_names, f, indent=2)

def search_projects(query: str, limit: int = 10) -> List[str]:
    """Search projects by partial name."""
    index = load_project_index()
    query = query.upper()
    results = [name for name in index if query in name.upper()]
    return results[:limit]

def is_project_valid(project_name: str) -> bool:
    """Check if a project name is valid (exists in index)."""
    index = load_project_index()
    return project_name.upper() in [name.upper() for name in index]

def update_project_index(project_names: List[str]) -> None:
    """Update the project index with new project names."""
    index = load_project_index()
    index.extend(project_names)
    # Remove duplicates
    index = list(set(index))
    save_project_index(index)