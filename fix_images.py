import pandas as pd
import json
from difflib import SequenceMatcher

# Load Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')

# Load brand_catalogs.json
with open('brand_catalogs.json', 'r', encoding='utf-8') as f:
    catalogs = json.load(f)

# Build brand lookup: normalized brand name -> brand data
brand_lookup = {}
for brand in catalogs['brands']:
    key = brand['brand_name'].upper().strip()
    brand_lookup[key] = brand

# Build product lookup per brand: (brand_key, product_name_upper) -> product
product_lookup = {}
for brand in catalogs['brands']:
    brand_key = brand['brand_name'].upper().strip()
    for prod in brand.get('products', []):
        pname = prod.get('product_name', '').upper().strip()
        if pname:
            product_lookup[(brand_key, pname)] = prod

# Function to find best matching product
def find_best_match(item_name, category1, brand_products):
    item_upper = str(item_name).upper().strip()
    if not item_upper or not brand_products:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for prod in brand_products:
        pname = prod.get('product_name', '').upper().strip()
        if not pname:
            continue
        # Use sequence matcher for similarity
        score = SequenceMatcher(None, item_upper, pname).ratio()
        # Also check if key words overlap
        item_words = set(item_upper.split())
        prod_words = set(pname.split())
        overlap = len(item_words & prod_words) / max(len(item_words | prod_words), 1)
        combined_score = max(score, overlap)
        
        if combined_score > best_score:
            best_score = combined_score
            best_match = prod
    
    return best_match, best_score

# Process each item
matched = 0
unmatched = 0
results = []

for _, row in df.iterrows():
    item_code = str(row.get('Item Code ', '')).strip()
    item_name = str(row.get('Item Name', '')).strip()
    category1 = str(row.get('Category 1', '')).strip()
    brand_key = category1.upper().strip()
    
    image_url = ''
    has_image = False
    match_score = 0.0
    
    if brand_key in brand_lookup:
        brand = brand_lookup[brand_key]
        brand_products = brand.get('products', [])
        best_prod, score = find_best_match(item_name, category1, brand_products)
        
        if best_prod and score > 0.3:  # threshold
            image_url = best_prod.get('image_url', '')
            has_image = bool(image_url)
            match_score = round(score, 2)
            matched += 1
        else:
            unmatched += 1
    else:
        unmatched += 1
    
    results.append({
        'item_code': item_code,
        'item_name': item_name,
        'brand': category1,
        'has_image': has_image,
        'image_url': image_url,
        'match_score': match_score
    })

print(f"Matched: {matched}")
print(f"Unmatched: {unmatched}")
print(f"Total: {len(results)}")

# Show some examples
print("\n=== Sample Matches ===")
for r in results[:10]:
    print(f"  {r['brand']} | {r['item_name'][:50]} | score={r['match_score']} | img={r['has_image']}")

# Save results
with open('image_match_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nSaved to image_match_results.json")