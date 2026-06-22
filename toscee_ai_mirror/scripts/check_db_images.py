"""Check for images in the database and inventory."""
import sqlite3
import pandas as pd
import os

# Check po_data.db for any image-related data
DB_PATH = r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\database\po_data.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check all tables for image columns
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("=== Checking database for image columns ===")
for t in tables:
    cursor.execute(f"PRAGMA table_info({t[0]})")
    for c in cursor.fetchall():
        if any(x in c[1].lower() for x in ['image', 'img', 'photo', 'url', 'picture', 'path', 'file']):
            print(f"  {t[0]}.{c[1]} ({c[2]})")
print("No image columns found in database.")

# Check the Excel file for image URLs in Description fields
df = pd.read_excel(r"C:\Users\adity\Downloads\invitemlist_20260622144242.xlsx")
print(f"\n=== Excel has {len(df)} items ===")
print(f"Columns: {list(df.columns)}")

# Check Description fields for URLs
for col in ['Description 1', 'Description 2', 'Description 3', 'Description 4', 'Description 5', 'Description 6']:
    if col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) > 0:
            sample = str(non_null.iloc[0])
            print(f"\n{col} sample: {sample[:200]}")
            if 'http' in sample.lower() or 'jpg' in sample.lower() or 'png' in sample.lower() or 'jpeg' in sample.lower():
                print(f"  -> Contains image URL!")
                for v in non_null.head(5):
                    print(f"     {str(v)[:150]}")
        else:
            print(f"\n{col}: all empty")

# Check for image folders
print("\n=== Checking for image folders ===")
possible_paths = [
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\images",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\database\images",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\product_images",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\buying_plan_app\images",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\buying_plan_app\product_images",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\media",
    r"C:\Users\adity\OneDrive\Desktop\work\po-analytics\uploads",
]
for p in possible_paths:
    if os.path.exists(p):
        files = [f for f in os.listdir(p) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        print(f"  {p}: {len(files)} image files")
        if files:
            print(f"    Samples: {files[:5]}")
    else:
        print(f"  {p}: NOT FOUND")

# Also check the po-analytics folder broadly
base = r"C:\Users\adity\OneDrive\Desktop\work\po-analytics"
print(f"\n=== Top-level contents of {base} ===")
for item in os.listdir(base):
    full = os.path.join(base, item)
    if os.path.isdir(full):
        img_count = sum(1 for f in os.listdir(full) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
        if img_count > 0:
            print(f"  📁 {item}/ — {img_count} images")
    elif item.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
        print(f"  🖼️ {item}")

conn.close()