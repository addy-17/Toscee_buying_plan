import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
import time

# Load Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')

# Load brand_catalogs.json for website URLs
with open('brand_catalogs.json', 'r', encoding='utf-8') as f:
    catalogs = json.load(f)

# Build brand -> website mapping
brand_websites = {}
for brand in catalogs['brands']:
    name = brand['brand_name']
    website = brand.get('website', '')
    if website:
        brand_websites[name.upper()] = website

# Load current inventory
with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    inventory = json.load(f)

# Create lookup by item_code
inv_by_code = {item['item_code']: item for item in inventory['items']}

# Process each brand
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
    
    if brand_key not in brand_websites:
        continue
    
    website = brand_websites[brand_key]
    
    # Try to search on the brand's website
    try:
        # Most Shopify sites have /search?q= endpoint
        search_url = f"{website}/search?q={quote_plus(item_name)}"
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find product images
            # Common patterns: .product-card img, .product-item img, etc.
            product_imgs = soup.select('.product-card img, .product-item img, [class*="product"] img')
            
            if product_imgs:
                # Get first product image
                img_url = product_imgs[0].get('src', '')
                if img_url and not img_url.startswith('http'):
                    img_url = urljoin(website, img_url)
                
                if img_url:
                    if item_code in inv_by_code:
                        inv_by_code[item_code]['image_url'] = img_url
                        inv_by_code[item_code]['has_image'] = True
                        updated += 1
                        print(f"✓ {category1} | {item_name[:50]} → {img_url[:60]}")
        
        time.sleep(0.5)  # Be polite
        
    except Exception as e:
        errors.append(f"{item_code}: {str(e)}")

# Save updated inventory
inventory['items'] = list(inv_by_code.values())
inventory['matched_with_image'] = sum(1 for item in inventory['items'] if item['has_image'])
inventory['unmatched'] = inventory['total_inventory'] - inventory['matched_with_image']
inventory['match_rate'] = round((inventory['matched_with_image'] / inventory['total_inventory']) * 100, 1)

with open('toscee_ai_mirror/data/inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False)

print(f"\n=== Results ===")
print(f"Updated: {updated}")
print(f"Total matched: {inventory['matched_with_image']}/{inventory['total_inventory']} ({inventory['match_rate']}%)")
print(f"Errors: {len(errors)}")

if errors:
    print("\nSample errors:")
    for e in errors[:5]:
        print(f"  {e}")