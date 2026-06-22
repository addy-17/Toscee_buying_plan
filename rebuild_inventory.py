import pandas as pd
import json
from datetime import datetime

# Read Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')
print(f"Loaded {len(df)} items from Inventory.xlsx")

# Build new inventory JSON from Excel
items = []
for _, row in df.iterrows():
    item = {
        "item_code": str(row.get('Item Code ', '')).strip(),
        "barcode": str(row.get('Barcode', '')).strip(),
        "article_name": str(row.get('Article Name', '')).strip(),
        "item_name": str(row.get('Item Name', '')).strip(),
        "vendor": str(row.get('Vendor Name', '')).strip(),
        "section": str(row.get('Section ', '')).strip(),
        "department": str(row.get('Department', '')).strip(),
        "mrp": float(row.get('MRP', 0)) if pd.notna(row.get('MRP')) else 0.0,
        "category_2": str(row.get('Category 2', '')).strip(),
        "category_3": str(row.get('Category 3', '')).strip(),
        "has_image": False,
        "image_url": "",
        "matched_product": str(row.get('Item Name', '')).strip(),
        "matched_brand": str(row.get('Category 1', '')).strip(),
        "match_score": 1.0
    }
    items.append(item)

# Create new inventory structure
new_inventory = {
    "total_inventory": len(items),
    "matched_with_image": 0,
    "unmatched": len(items),
    "match_rate": 0.0,
    "items": items
}

# Count unique brands
brands = set(item['matched_brand'] for item in items if item['matched_brand'])
print(f"Total brands: {len(brands)}")
print("Brands:")
for b in sorted(brands):
    print(f"  - {b}")

# Save to inventory_with_images.json
output_path = 'toscee_ai_mirror/data/inventory_with_images.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(new_inventory, f, indent=2, ensure_ascii=False)

print(f"\nSaved to {output_path}")
print(f"Total items: {len(items)}")