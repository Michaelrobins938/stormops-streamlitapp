"""
Script to fix column name mismatches in the database schema
"""
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

def fix_column_name_mismatches():
    # Connect to the database
    conn = sqlite3.connect('stormops_cache.db')
    
    # Check if zip_code column exists and zip doesn't
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(markov_zip_states)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'zip_code' in columns and 'zip' not in columns:
        # We need to create a new table with the correct column name, migrate data, and replace the old table
        print("Fixing column name mismatch in markov_zip_states table...")
        
        # Get all data from the current table
        df = pd.read_sql_query("SELECT * FROM markov_zip_states", conn)
        
        # Rename the column
        df = df.rename(columns={'zip_code': 'zip'})
        
        # Close the connection
        conn.close()
        
        # Create a backup of the original database
        import shutil
        shutil.copy('stormops_cache.db', 'stormops_cache_backup.db')
        print("Backup created as stormops_cache_backup.db")
        
        # Recreate the database with the correct schema
        engine = create_engine('sqlite:///stormops_cache.db')
        
        # Drop the old table and recreate with correct column name
        with engine.connect() as sql_conn:
            sql_conn.execute("DROP TABLE markov_zip_states")
            
            # Create the table with the correct column name
            sql_conn.execute("""
                CREATE TABLE markov_zip_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    storm_id TEXT NOT NULL,
                    zip TEXT NOT NULL,
                    current_state TEXT DEFAULT 'pre_event',
                    prob_to_recovery REAL DEFAULT 0,
                    estimated_tam_usd REAL DEFAULT 0,
                    state_entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transitions_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert the data back with the correct column name
            df.to_sql('markov_zip_states', con=sql_conn, if_exists='append', index=False)
            sql_conn.commit()
        
        print("Fixed column name mismatch: zip_code -> zip in markov_zip_states table")
    
    else:
        conn.close()
        print("No column name mismatch found in markov_zip_states table")

if __name__ == "__main__":
    fix_column_name_mismatches()