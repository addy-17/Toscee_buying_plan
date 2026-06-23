import os
import json
import pandas as pd

# Create image mapping from ocr_matched_output_v2
image_mappings = {}

def process_brand_folder(brand_path, brand_name):
    """Process a brand folder to extract image mappings."""
    print(f"\nProcessing brand: {brand_name}")
    
    # Find the mapped Excel file
    mapped_file = None
    for file in os.listdir(brand_path):
        if file.endswith("_Mapped.xlsx") or file.endswith("_mapped.xlsx"):
            mapped_file = file
            break
    
    if not mapped_file:
        print(f"  WARNING: No mapped Excel file found")
        return 0
    
    print(f"  Reading: {mapped_file}")
    
    # Find images folder - could be directly in brand_path or in a subfolder
    images_folders = []
    
    # Check for images subfolder
    images_subfolder = os.path.join(brand_path, "images")
    if os.path.exists(images_subfolder):
        images_folders.append(images_subfolder)
    
    # Check if brand_path itself contains images
    img_files = [f for f in os.listdir(brand_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if img_files:
        images_folders.append(brand_path)
    
    # Check for sibling _images folder (e.g., "Banana Labs_images" next to "Banana Labs")
    parent_path = os.path.dirname(brand_path)
    sibling_images = os.path.join(parent_path, f"{brand_name}_images")
    if os.path.exists(sibling_images):
        images_folders.append(sibling_images)
    
    if not images_folders:
        print(f"  WARNING: No images folder found")
        return 0
    
    print(f"  Found images in: {images_folders}")
    
    try:
        df = pd.read_excel(os.path.join(brand_path, mapped_file))
        print(f"  Columns: {df.columns.tolist()}")
        
        # Find the item code and matched image columns
        item_code_col = None
        matched_img_col = None
        
        for col in df.columns:
            col_lower = col.strip().lower()
            if col_lower == "item code":
                item_code_col = col
            if col_lower in ["mapped_image", "matched_image", "matched image", "image"]:
                matched_img_col = col
        
        if not item_code_col or not matched_img_col:
            print(f"  WARNING: Could not find required columns")
            return 0
        
        print(f"  Using: '{item_code_col}' and '{matched_img_col}'")
        
        mapped_count = 0
        for _, row in df.iterrows():
            item_code = str(row[item_code_col]).strip()
            matched_img = row[matched_img_col]
            
            if pd.isna(matched_img) or str(matched_img).strip() in ["", "nan", "NaN"]:
                continue
            
            matched_img = str(matched_img).strip()
            
            # Look for the image in the brand's images folders
            image_found = False
            for images_folder in images_folders:
                image_path = os.path.join(images_folder, matched_img)
                if os.path.exists(image_path):
                    image_mappings[item_code] = {
                        "item_code": item_code,
                        "brand": brand_name,
                        "matched_image": matched_img,
                        "image_path": image_path
                    }
                    mapped_count += 1
                    image_found = True
                    break
            
            if not image_found and mapped_count < 3:  # Only print first few warnings
                print(f"  WARNING: Image not found: {matched_img}")
        
        print(f"  Mapped {mapped_count} images")
        return mapped_count
            
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0

# Process both folder structures
print("=" * 60)
print("PROCESSING OCR_MATCHED_OUTPUT_V2")
print("=" * 60)

base_folder = "ocr_matched_output_v2"

# 1. Process brand_mapped_output subfolder
brand_mapped_folder = os.path.join(base_folder, "brand_mapped_output")
if os.path.exists(brand_mapped_folder):
    print("\n--- Processing brand_mapped_output ---")
    for brand_folder in os.listdir(brand_mapped_folder):
        brand_path = os.path.join(brand_mapped_folder, brand_folder)
        if os.path.isdir(brand_path):
            process_brand_folder(brand_path, brand_folder)

# 2. Process "New folder" structure
new_folder = os.path.join(base_folder, "New folder")
if os.path.exists(new_folder):
    print("\n--- Processing New folder ---")
    for brand_folder in os.listdir(new_folder):
        brand_path = os.path.join(new_folder, brand_folder)
        
        # Skip non-directories and _images folders
        if not os.path.isdir(brand_path):
            continue
        if brand_folder.endswith("_images"):
            continue
        
        # Check if this folder has a _Mapped.xlsx file
        has_mapped_file = any(f.endswith("_Mapped.xlsx") or f.endswith("_mapped.xlsx") 
                             for f in os.listdir(brand_path))
        
        if has_mapped_file:
            # Look for corresponding _images folder
            images_folder = os.path.join(new_folder, f"{brand_folder}_images")
            if os.path.exists(images_folder):
                # Temporarily add images folder to brand_path for processing
                process_brand_folder(brand_path, brand_folder)
            else:
                print(f"\nWARNING: No images folder for {brand_folder}")

# 3. Process direct brand folders in ocr_matched_output_v2
print("\n--- Processing direct brand folders ---")
for brand_folder in os.listdir(base_folder):
    brand_path = os.path.join(base_folder, brand_folder)
    
    # Skip non-directories and special folders
    if not os.path.isdir(brand_path):
        continue
    if brand_folder in ["brand_mapped_output", "New folder"]:
        continue
    
    # Check if this folder has a _Mapped.xlsx file
    has_mapped_file = any(f.endswith("_Mapped.xlsx") or f.endswith("_mapped.xlsx") 
                         for f in os.listdir(brand_path))
    
    if has_mapped_file:
        process_brand_folder(brand_path, brand_folder)

# Save to JSON
output_file = "image_mappings.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(image_mappings, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 60}")
print(f"✓ Saved {len(image_mappings)} mappings to {output_file}")
print(f"{'=' * 60}")
print("\nSample mappings:")
for i, (k, v) in enumerate(list(image_mappings.items())[:5]):
    print(f"  {k} -> {v['image_path']}")