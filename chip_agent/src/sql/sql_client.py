import re
import psycopg
from src.settings import settings

def clean_db_url(url: str) -> str:
    """
    Clean connection URL by replacing postgresql+psycopg:// or similar with postgresql://
    """
    return re.sub(r'^postgresql\+[a-zA-Z0-9_-]+://', 'postgresql://', url)

def execute_read_query(query: str, params: tuple = None, timeout: float = 5.0) -> list[dict]:
    """
    Execute a read-only SQL query using psycopg, applying a statement timeout.
    Returns a list of dictionaries mapping column names to values.
    """
    db_url = clean_db_url(settings.DATABASE_URL)
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Set statement timeout in milliseconds
            timeout_ms = int(timeout * 1000)
            cur.execute(f"SET statement_timeout = {timeout_ms};")
            
            # Execute the actual query
            cur.execute(query, params)
            
            # Map results to dictionaries if description is available
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
            return []
