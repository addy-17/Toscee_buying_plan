import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# Load Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')

# Load brand_catalogs.json
with open('brand_catalogs.json', 'r', encoding='utf-8') as f:
    catalogs = json.load(f)

# Build brand -> products mapping
brand_products = {}
for brand in catalogs['brands']:
    key = brand['brand_name'].upper().strip()
    brand_products[key] = brand.get('products', [])

# Load current inventory
with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    inventory = json.load(f)

# Create lookup by item_code
inv_by_code = {item['item_code']: item for item in inventory['items']}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

updated = 0
errors = []

for _, row in df.iterrows():
    item_code = str(row.get('Item Code ', '')).strip()
    item_name = str(row.get('Item Name', '')).strip()
    category1 = str(row.get('Category 1', '')).strip()
    brand_key = category1.upper().strip()
    
    if brand_key not in brand_products:
        continue
    
    products = brand_products[brand_key]
    
    # Try to find matching product by URL or name similarity
    best_match = None
    best_score = 0.0
    
    for prod in products:
        prod_url = prod.get('product_url', '')
        prod_name = prod.get('product_name', '').upper()
        
        # Check if item_name appears in product URL or name
        item_upper = item_name.upper()
        if item_upper in prod_url or item_upper in prod_name:
            score = 1.0
        else:
            # Partial match
            from difflib import SequenceMatcher
            score = SequenceMatcher(None, item_upper, prod_name).ratio()
        
        if score > best_score:
            best_score = score
            best_match = prod
    
    if best_match and best_score > 0.3:
        prod_url = best_match.get('product_url', '')
        img_url = best_match.get('image_url', '')
        
        # If we have a product URL, try to scrape the actual page for better image
        if prod_url and not img_url:
            try:
                response = requests.get(prod_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Try to find main product image
                    img_tag = soup.select_one('.product__media img, .product-featured-image img, [class*="product"] img')
                    if img_tag:
                        img_url = img_tag.get('src', '') or img_tag.get('data-src', '')
                        if img_url and not img_url.startswith('http'):
                            img_url = urljoin(prod_url, img_url)
                time.sleep(0.3)
            except:
                pass
        
        if img_url:
            if item_code in inv_by_code:
                inv_by_code[item_code]['image_url'] = img_url
                inv_by_code[item_code]['has_image'] = True
                inv_by_code[item_code]['matched_product'] = best_match.get('product_name', item_name)
                updated += 1
                print(f"✓ {category1} | {item_name[:50]}")
                print(f"  → {best_match.get('product_name', '')[:50]}")
                print(f"  → {img_url[:70]}")

# Save
inventory['items'] = list(inv_by_code.values())
inventory['matched_with_image'] = sum(1 for item in inventory['items'] if item['has_image'])

with open('toscee_ai_mirror/data/inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False)

print(f"\n=== Results ===")
print(f"Updated: {updated}")
print(f"Total matched: {inventory['matched_with_image']}/{inventory['total_inventory']}")