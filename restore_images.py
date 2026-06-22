import json
import pandas as pd

# Load the original inventory JSON (with images) from git history
import subprocess
result = subprocess.run(['git', 'show', 'HEAD~1:toscee_ai_mirror/data/inventory_with_images.json'], 
                       capture_output=True, text=True, cwd='.')
old_inv = json.loads(result.stdout)

# Load current inventory JSON (from Excel, no images)
with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    new_inv = json.load(f)

# Build lookup by item_code from old inventory
old_by_code = {}
for item in old_inv['items']:
    code = item.get('item_code', '').strip()
    if code:
        old_by_code[code] = item

# Merge: copy image data from old inventory into new inventory
matched = 0
for item in new_inv['items']:
    code = item.get('item_code', '').strip()
    if code in old_by_code:
        old_item = old_by_code[code]
        item['has_image'] = old_item.get('has_image', False)
        item['image_url'] = old_item.get('image_url', '')
        item['matched_product'] = old_item.get('matched_product', item['matched_product'])
        item['match_score'] = old_item.get('match_score', 1.0)
        matched += 1

# Update stats
new_inv['matched_with_image'] = matched
new_inv['unmatched'] = new_inv['total_inventory'] - matched
new_inv['match_rate'] = round((matched / new_inv['total_inventory']) * 100, 1) if new_inv['total_inventory'] > 0 else 0.0

# Save
with open('toscee_ai_mirror/data/inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(new_inv, f, indent=2, ensure_ascii=False)

print(f"Restored images for {matched}/{new_inv['total_inventory']} items")
print(f"Match rate: {new_inv['match_rate']}%")