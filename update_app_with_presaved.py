"""
Update inventory_with_images.json with ALL brands including pre-mapped ones
"""
import pandas as pd
import json
from pathlib import Path

print('=== UPDATING APP WITH ALL BRANDS (INCLUDING PRE-MAPPED) ===\n')

# Load full inventory
df_inv = pd.read_excel('Inventory.xlsx')
print(f'Total inventory items: {len(df_inv)}')

# Vendor to brand name mapping
vendor_to_brand = {
    'Silkwaves Designs Pvt Ltd : V010': 'Banana Labs',
    'Ekatra Collective Private Limited : V005': 'Ekatra',
    'Niktri Endeavours (OPC) Pvt Ltd : V007': 'Green Hermitage',
    'Inara Rituals : V017': 'Inara Rituals',
    'Inhanss Ventures Private Limited : V012': 'Inhanss',
    'OTD Lifestyle Private Limited : V004': 'Jyotir Gamaya',
    'Migalo Brands : V008': 'Migalo',
    'Sainsisters : V020': 'Sainsisters',
    'Soma Essentials Inc : V011': 'Soma Naturals',
    'Tirmisu Retails private limited : V009': 'Tiramisu',
    'Aranya Earthcraft : V015': 'Aranya Earthcraft',
    'Blank Slate Home : V016': 'Blank Slate Home',
    'Sukoon Online LLP : V013': 'Sukoon',
    'SSN Belts : V019': 'SSN Belts',
    'She Ela Jewel : V018': 'She Ela Jewels',
    'Munn Home Products Private Limited : V014': 'Munn Home',
    'Aura Studio : V021': 'Aura Studio',
    'Neesh Perfumes pvt Ltd : V003': 'Neesh',
    'Boond Fragrances : V002': 'Boond',
    'Kavaish Garments Llp : V001': 'Kavaish',
    'Source4you': 'Source4you',
    'SSN Retail': 'SSN Retail',
}

# Pre-mapped brands from brand_mapped_output/
presaved_brands = ['Favori', 'Munn Home', 'NAAVA', 'She Ela Jewels', 'SSN Belts', 'Sukoon']

all_products = []

# First, load pre-saved mapped brands
for brand in presaved_brands:
    mapped_file = f'brand_mapped_output/{brand}/{brand}_mapped.xlsx'
    if Path(mapped_file).exists():
        df = pd.read_excel(mapped_file)
        print(f'  ✓ {brand}: Pre-mapped ({len(df)} items)')
        
        for _, row in df.iterrows():
            product = {
                'item_code': str(row.get('Item Code ', '')),
                'item_name': str(row.get('Item Name', '')),
                'mrp': float(row['MRP']) if pd.notna(row['MRP']) else 0,
                'brand': brand,
                'vendor': str(row.get('Vendor Name', '')),
                'department': str(row.get('Department', '')),
                'category_1': str(row.get('Category 1', '')),
                'category_2': str(row.get('Category 2', '')),
                'category_3': str(row.get('Category 3', '')),
                'image_file': str(row.get('Matched_Image', '')),
                'match_confidence': float(row.get('Match_Confidence', 0)),
            }
            all_products.append(product)

# Then load OCR-mapped brands
mapped_dir = 'ocr_final_mapped'
for vendor, brand_name in vendor_to_brand.items():
    mapped_file = f'{mapped_dir}/{brand_name}/{brand_name}_Mapped.xlsx'
    
    if Path(mapped_file).exists():
        df = pd.read_excel(mapped_file)
        print(f'  ✓ {brand_name}: OCR-mapped ({len(df)} items)')
    else:
        df = df_inv[df_inv['Vendor Name'] == vendor].copy()
        df['Matched_Image'] = ''
        df['Match_Confidence'] = 0.0
        print(f'  - {brand_name}: Inventory only ({len(df)} items)')
    
    for _, row in df.iterrows():
        product = {
            'item_code': str(row.get('Item Code ', '')),
            'item_name': str(row.get('Item Name', '')),
            'mrp': float(row['MRP']) if pd.notna(row['MRP']) else 0,
            'brand': brand_name,
            'vendor': str(row.get('Vendor Name', '')),
            'department': str(row.get('Department', '')),
            'category_1': str(row.get('Category 1', '')),
            'category_2': str(row.get('Category 2', '')),
            'category_3': str(row.get('Category 3', '')),
            'image_file': str(row.get('Matched_Image', '')),
            'match_confidence': float(row.get('Match_Confidence', 0)),
        }
        all_products.append(product)

print(f'\nTotal products: {len(all_products)}')
print(f'Brands: {len(set(p["brand"] for p in all_products))}')
print(f'Products with images: {sum(1 for p in all_products if p["image_file"])}')

# Save as JSON for the app
output = {
    'total_inventory': len(all_products),
    'last_updated': pd.Timestamp.now().isoformat(),
    'products': all_products
}

with open('inventory_with_images.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f'\n✓ Saved: inventory_with_images.json')