import sqlite3
from datetime import datetime, timedelta
import os
import json


def log_scrape(db_path="search_log.db", filters=None):
    """
    Logs a search scrape event to an SQLite database.

    Parameters:
    - db_path (str): Path to the SQLite database file.
    - filters (dict): Dictionary of filter parameters used in the search.
    - result_count (int): Number of results returned by the scrape.
    """

    # Ensure filters is a dict (or fallback to empty)
    filters = filters or {}

    # Serialize filters as sorted JSON to ensure consistent comparisons
    filters_str = json.dumps(filters, sort_keys=True, separators=(',', ':'))

    # Connect to database (will create if not exists)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the search_log table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filters TEXT NOT NULL,
            searched_at TEXT NOT NULL
        );
    """)

    # Insert the log entry
    cursor.execute("""
        INSERT INTO search_log (filters, searched_at)
        VALUES (?, ?);
    """, (filters_str, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def isInLog(db_path="search_log.db", filters=None):
    if filters is None:
        return False

    filters_str = json.dumps(filters, sort_keys=True, separators=(',', ':'))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1 FROM search_log
        WHERE filters = ?
        LIMIT 1;
    """, (filters_str,))

    result = cursor.fetchone()
    conn.close()

    return result is not None


def is_subset_search(current_filters, existing_filters):
    """
    Check if current search is a subset of an existing search.
    Returns True if current search can be satisfied by filtering existing results.
    """
    if not existing_filters:
        return False
    
    # Compare each filter parameter
    for key, current_value in current_filters.items():
        if key == "sort" or not current_value:
            continue
            
        existing_value = existing_filters.get(key)
        if not existing_value:
            # If existing search doesn't have this filter, it's broader (good)
            continue
            
        # Convert to appropriate types for comparison
        if key in ["min_price", "max_price", "min_size", "max_size", "min_rooms", "max_rooms"]:
            try:
                current_num = float(current_value)
                existing_num = float(existing_value)
                
                if key.startswith("min_"):
                    # Current min should be >= existing min (more restrictive is ok)
                    if current_num < existing_num:
                        return False
                elif key.startswith("max_"):
                    # Current max should be <= existing max (more restrictive is ok)
                    if current_num > existing_num:
                        return False
            except (ValueError, TypeError):
                continue
        else:
            # For categorical filters (type, location), must match exactly
            if current_value != existing_value:
                return False
    
    return True


def find_recent_compatible_search(db_path="search_log.db", filters=None, hours_limit=24):
    """
    Find a recent search that could satisfy the current search requirements.
    Returns the compatible filters if found, None otherwise.
    """
    if filters is None:
        return None
    
    # Remove sort parameter for comparison
    search_filters = {k: v for k, v in filters.items() if k != "sort" and v}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get recent searches within the time limit
    cutoff_time = (datetime.now() - timedelta(hours=hours_limit)).isoformat()
    
    cursor.execute("""
        SELECT filters, searched_at FROM search_log
        WHERE searched_at > ?
        ORDER BY searched_at DESC
    """, (cutoff_time,))
    
    recent_searches = cursor.fetchall()
    conn.close()
    
    for filters_str, searched_at in recent_searches:
        try:
            existing_filters = json.loads(filters_str)
            # Remove sort and None values for comparison
            existing_search_filters = {k: v for k, v in existing_filters.items() if k != "sort" and v}
            
            if is_subset_search(search_filters, existing_search_filters):
                return existing_filters
        except (json.JSONDecodeError, TypeError):
            continue
    
    return None


def should_scrape(db_path="search_log.db", filters=None, hours_limit=24):
    """
    Determine if we should scrape new data or use existing data.
    Returns (should_scrape: bool, compatible_filters: dict or None)
    """
    compatible_search = find_recent_compatible_search(db_path, filters, hours_limit)
    
    if compatible_search:
        return False, compatible_search
    else:
        return True, None


