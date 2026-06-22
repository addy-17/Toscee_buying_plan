import json
import pandas as pd
from difflib import SequenceMatcher

# Load Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')

# Load brand_catalogs.json
with open('brand_catalogs.json', 'r', encoding='utf-8') as f:
    catalogs = json.load(f)

# Build brand lookup
brand_lookup = {}
for brand in catalogs['brands']:
    key = brand['brand_name'].upper().strip()
    brand_lookup[key] = brand

def find_best_match_in_brand(item_name, brand_products):
    item_upper = str(item_name).upper().strip()
    if not item_upper or not brand_products:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for prod in brand_products:
        pname = prod.get('product_name', '').upper().strip()
        if not pname:
            continue
        score = SequenceMatcher(None, item_upper, pname).ratio()
        item_words = set(item_upper.split())
        prod_words = set(pname.split())
        overlap = len(item_words & prod_words) / max(len(item_words | prod_words), 1)
        combined_score = max(score, overlap)
        
        if combined_score > best_score:
            best_score = combined_score
            best_match = prod
    
    return best_match, best_score

# Process each item
results = []
matched = 0
unmatched = 0

for _, row in df.iterrows():
    item_code = str(row.get('Item Code ', '')).strip()
    item_name = str(row.get('Item Name', '')).strip()
    category1 = str(row.get('Category 1', '')).strip()
    brand_key = category1.upper().strip()
    
    matched_brand = category1
    image_url = ''
    has_image = False
    match_score = 0.0
    matched_product = item_name
    
    if brand_key in brand_lookup:
        brand = brand_lookup[brand_key]
        brand_products = brand.get('products', [])
        best_prod, score = find_best_match_in_brand(item_name, brand_products)
        
        if best_prod and score > 0.3:
            image_url = best_prod.get('image_url', '')
            has_image = bool(image_url)
            match_score = round(score, 2)
            matched_product = best_prod.get('product_name', item_name)
            matched += 1
        else:
            unmatched += 1
    else:
        unmatched += 1
    
    results.append({
        "item_code": item_code,
        "barcode": str(row.get('Barcode', '')).strip(),
        "article_name": str(row.get('Article Name', '')).strip(),
        "item_name": item_name,
        "vendor": str(row.get('Vendor Name', '')).strip(),
        "section": str(row.get('Section ', '')).strip(),
        "department": str(row.get('Department', '')).strip(),
        "mrp": float(row.get('MRP', 0)) if pd.notna(row.get('MRP')) else 0.0,
        "category_2": str(row.get('Category 2', '')).strip(),
        "category_3": str(row.get('Category 3', '')).strip(),
        "has_image": has_image,
        "image_url": image_url,
        "matched_product": matched_product,
        "matched_brand": matched_brand,
        "match_score": match_score
    })

# Save
output = {
    "total_inventory": len(results),
    "matched_with_image": matched,
    "unmatched": unmatched,
    "match_rate": round((matched / len(results)) * 100, 1) if results else 0.0,
    "items": results
}

with open('toscee_ai_mirror/data/inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Total: {len(results)} | Matched: {matched} ({output['match_rate']}%) | Unmatched: {unmatched}")
print(f"\nBrands: {len(set(i['matched_brand'] for i in results))}")

# Check for duplicates
from collections import defaultdict
brand_images = defaultdict(set)
for item in results:
    if item['has_image']:
        brand_images[item['matched_brand']].add(item['image_url'])

print("\n=== Duplicate Check ===")
for brand in sorted(brand_images.keys()):
    items_count = sum(1 for i in results if i['matched_brand'] == brand)
    unique_count = len(brand_images[brand])
    if items_count > 1:
        status = "✓" if unique_count == items_count else "⚠️"
        print(f"{status} {brand}: {items_count} items, {unique_count} unique images")