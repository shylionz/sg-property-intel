"""
Caching utilities for project data.
"""
from cachetools import TTLCache
from typing import Dict, Any

# Cache configurations
transaction_cache = TTLCache(maxsize=200, ttl=43200)  # 12 hours
rental_cache = TTLCache(maxsize=200, ttl=86400)  # 24 hours
analytics_cache = TTLCache(maxsize=200, ttl=86400)  # 24 hours
project_cache = TTLCache(maxsize=1000, ttl=86400)  # 24 hours

def get_cached_project_data(project_name: str) -> Dict[str, Any]:
    """Get cached project data."""
    return project_cache.get(project_name)

def set_cached_project_data(project_name: str, data: Dict[str, Any]) -> None:
    """Set cached project data."""
    project_cache[project_name] = data