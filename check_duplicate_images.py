import json

with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    inv = json.load(f)

# Check for duplicate images within each brand
from collections import defaultdict

brand_images = defaultdict(set)
brand_items = defaultdict(list)

for item in inv['items']:
    brand = item['matched_brand']
    img = item['image_url']
    brand_images[brand].add(img)
    brand_items[brand].append(item['item_name'][:50])

print("=== Image Duplication Check ===\n")
for brand in sorted(brand_images.keys()):
    unique_imgs = len(brand_images[brand])
    total_items = len(brand_items[brand])
    print(f"{brand}:")
    print(f"  Items: {total_items}")
    print(f"  Unique images: {unique_imgs}")
    if unique_imgs == 1 and total_items > 1:
        print(f"  ⚠️  ALL ITEMS HAVE SAME IMAGE!")
        print(f"  Image: {list(brand_images[brand])[0][:80]}")
    elif unique_imgs < total_items:
        print(f"  ⚠️  Some items share images")
    else:
        print(f"  ✓ All items have unique images")
    print()