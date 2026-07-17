import sqlite3
import pandas as pd
from typing import List, Tuple, Any
from src.config import DATABASE_PATH, is_db_ready

class SQLExecutor:
    @staticmethod
    def execute(sql: str, params: List[Any] = None) -> pd.DataFrame:
        """Executes a parameterized SQL query in read-only mode, returning a Pandas DataFrame."""
        if not is_db_ready():
            raise FileNotFoundError("The SQLite database has not been initialized. Please run setup_database.py first.")
            
        if params is None:
            params = []
            
        # Security validation check on write operations (just in case, as a secondary layer)
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE"]
        upper_sql = sql.upper().strip()
        for kw in forbidden_keywords:
            if upper_sql.startswith(kw) or f" {kw} " in upper_sql:
                raise PermissionError("Write or schema modification queries are strictly prohibited.")
                
        # Open in read-only mode using SQLite URI
        # Convert path to absolute URI format
        import urllib.request
        db_uri = f"file:{urllib.request.pathname2url(DATABASE_PATH)}?mode=ro"
        
        try:
            # Connect in read-only mode
            conn = sqlite3.connect(db_uri, uri=True)
            df = pd.read_sql_query(sql, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            # Log error internally and raise user-friendly msg
            print(f"Database execution error: {e}\nQuery: {sql}\nParams: {params}")
            raise RuntimeError(f"An internal error occurred while retrieving data. Details: {e}")
