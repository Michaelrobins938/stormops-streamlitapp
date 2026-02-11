"""
Script to update the database schema to include missing columns in sidebar_actions table
"""
import sqlite3

def update_sidebar_actions_table():
    conn = sqlite3.connect('stormops_cache.db')
    cursor = conn.cursor()
    
    # Check if the approved_at column exists
    cursor.execute("PRAGMA table_info(sidebar_actions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    if 'approved_at' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN approved_at TIMESTAMP")
        print("Added approved_at column")
    
    if 'executed_at' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN executed_at TIMESTAMP")
        print("Added executed_at column")
        
    if 'completed_at' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN completed_at TIMESTAMP")
        print("Added completed_at column")
        
    if 'result_summary' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN result_summary TEXT")
        print("Added result_summary column")
        
    if 'error_message' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN error_message TEXT")
        print("Added error_message column")
        
    if 'approved_by' not in columns:
        cursor.execute("ALTER TABLE sidebar_actions ADD COLUMN approved_by TEXT")
        print("Added approved_by column")
    
    # Check if properties table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties';")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Create the properties table
        cursor.execute("""
            CREATE TABLE properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id TEXT UNIQUE,
                address TEXT,
                zip_code TEXT,
                latitude REAL,
                longitude REAL,
                census_tract_geoid TEXT,
                tenant_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created properties table")
    else:
        # Check if tenant_id column exists in properties table
        cursor.execute("PRAGMA table_info(properties)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'tenant_id' not in columns:
            cursor.execute("ALTER TABLE properties ADD COLUMN tenant_id TEXT")
            print("Added tenant_id column to properties table")
    
    conn.commit()
    conn.close()
    print("Database schema updated successfully!")

if __name__ == "__main__":
    update_sidebar_actions_table()