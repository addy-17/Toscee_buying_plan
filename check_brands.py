import pandas as pd
import json

# Read Category 1 from Inventory.xlsx
df = pd.read_excel('Inventory.xlsx', sheet_name='Data')
excel_brands_orig = df['Category 1'].dropna().astype(str).str.strip().unique()
excel_brands_upper = set(b.upper() for b in excel_brands_orig)

# Read inventory JSON brands
with open('toscee_ai_mirror/data/inventory_with_images.json', 'r', encoding='utf-8') as f:
    inv = json.load(f)
inv_brands_orig = set(item['matched_brand'] for item in inv['items'] if item.get('matched_brand'))
inv_brands_upper = set(b.upper() for b in inv_brands_orig)

# Case-insensitive matching
print('=== Case-insensitive brand matching ===')
print(f'Excel brands (upper): {sorted(excel_brands_upper)}')
print(f'JSON brands (upper): {sorted(inv_brands_upper)}')

matched_upper = excel_brands_upper & inv_brands_upper
print(f'\nMatched (case-insensitive): {len(matched_upper)}')
for b in sorted(matched_upper):
    excel_ver = [x for x in excel_brands_orig if x.upper() == b][0]
    json_ver = [x for x in inv_brands_orig if x.upper() == b][0]
    print(f'  Excel: "{excel_ver}"  <->  JSON: "{json_ver}"')

missing_upper = excel_brands_upper - inv_brands_upper
print(f'\nTruly missing from JSON: {len(missing_upper)}')
for b in sorted(missing_upper):
    excel_ver = [x for x in excel_brands_orig if x.upper() == b][0]
    print(f'  - {excel_ver}')