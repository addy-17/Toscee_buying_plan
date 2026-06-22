"""Check the po_data.db schema."""
import sqlite3

DB_PATH = r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\database\po_data.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}")

# Get schema for each table
for t in tables:
    name = t[0]
    print(f"\n--- {name} ---")
    cursor.execute(f"PRAGMA table_info({name})")
    cols = cursor.fetchall()
    for col in cols:
        print(f"  {col[1]:30s} {col[2]:20s} nullable={not col[3]} default={col[4]}")
    
    # Show first 3 rows
    cursor.execute(f"SELECT * FROM {name} LIMIT 3")
    rows = cursor.fetchall()
    if rows:
        print(f"  Sample rows:")
        for row in rows:
            print(f"    {row}")

conn.close()