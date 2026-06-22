import json
import pandas as pd

# Load original inventory JSON (has correct images)
with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    original_inv = json.load(f)

# Load Inventory.xlsx (has correct brand names)
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')

# Build lookup by item_code from Excel
excel_brands = {}
for _, row in df.iterrows():
    code = str(row.get('Item Code ', '')).strip()
    brand = str(row.get('Category 1', '')).strip()
    if code:
        excel_brands[code] = brand

# Update original JSON with Excel brand names
updated = 0
for item in original_inv['items']:
    code = item.get('item_code', '').strip()
    if code in excel_brands:
        old_brand = item['matched_brand']
        new_brand = excel_brands[code]
        if old_brand != new_brand:
            item['matched_brand'] = new_brand
            updated += 1

print(f"Updated brand names for {updated} items")
print(f"Total items: {len(original_inv['items'])}")
print(f"Matched with images: {original_inv['matched_with_image']}")

# Show brand distribution
brands = set(item['matched_brand'] for item in original_inv['items'])
print(f"\nTotal brands: {len(brands)}")
print("Brands:")
for b in sorted(brands):
    count = sum(1 for item in original_inv['items'] if item['matched_brand'] == b)
    print(f"  - {b}: {count} items")

# Save
with open('toscee_ai_mirror/data/inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(original_inv, f, indent=2, ensure_ascii=False)

print("\nSaved to inventory_with_images.json")