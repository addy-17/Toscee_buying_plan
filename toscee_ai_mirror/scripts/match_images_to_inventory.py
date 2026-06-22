"""
Match Inventory Products to Catalog Images
============================================
Takes product names from the inventory Excel and matches them 
to products in brand_catalogs.json to find images.
Uses fuzzy name matching.
"""
import json
import pandas as pd
import logging
from pathlib import Path
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
EXCEL_PATH = r"C:\Users\adity\Downloads\invitemlist_20260622144242.xlsx"
CATALOG_PATH = Path(__file__).parent.parent / "data" / "brand_catalogs.json"
# Fallback to original location
if not CATALOG_PATH.exists():
    CATALOG_PATH = Path(__file__).parent.parent.parent / "brand_catalogs.json"

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "inventory_with_images.json"

def load_inventory():
    """Load inventory from Excel."""
    df = pd.read_excel(EXCEL_PATH)
    items = []
    for _, row in df.iterrows():
        items.append({
            "item_code": str(row.get("Item Code ", "")).strip(),
            "barcode": str(row.get("Barcode", "")).strip(),
            "article_name": str(row.get("Article Name", "")).strip(),
            "item_name": str(row.get("Item Name", "")).strip(),
            "short_name": str(row.get("Short Name", "")).strip() if pd.notna(row.get("Short Name")) else "",
            "vendor": str(row.get("Vendor Name", "")).strip() if pd.notna(row.get("Vendor Name")) else "",
            "section": str(row.get("Section ", "")).strip(),
            "department": str(row.get("Department", "")).strip(),
            "mrp": float(row.get("MRP", 0)) if pd.notna(row.get("MRP")) else 0,
            "category_1": str(row.get("Category 1", "")).strip(),
            "category_2": str(row.get("Category 2", "")).strip(),
            "category_3": str(row.get("Category 3", "")).strip(),
        })
    logger.info(f"Loaded {len(items)} inventory items from Excel")
    return items

def load_catalog_products():
    """Load products with images from brand_catalogs.json."""
    if not CATALOG_PATH.exists():
        logger.error(f"Catalog not found at {CATALOG_PATH}")
        return []
    
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    
    products = []
    for brand in catalog.get("brands", []):
        brand_name = brand.get("brand_name", "Unknown")
        for product in brand.get("products", []):
            name = (product.get("product_name") or "").strip()
            if name and product.get("image_url"):
                products.append({
                    "name": name.lower(),
                    "original_name": name,
                    "brand": brand_name,
                    "image_url": product.get("image_url", ""),
                    "price": product.get("price_mrp", 0),
                    "product_url": product.get("product_url", ""),
                    "description": (product.get("description") or "")[:100],
                })
    
    logger.info(f"Loaded {len(products)} catalog products with images")
    return products

def name_similarity(name1, name2):
    """Compute similarity between two product names."""
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    return SequenceMatcher(None, n1, n2).ratio()

def find_best_match(inventory_name, catalog_products, threshold=0.3):
    """
    Find the best matching catalog product for an inventory item.
    Uses multiple strategies:
    1. Direct substring match
    2. Fuzzy ratio
    3. Word overlap
    """
    inv_name_lower = inventory_name.lower().strip()
    inv_words = set(inv_name_lower.split())
    
    best_match = None
    best_score = 0
    
    for prod in catalog_products:
        cat_name = prod["name"]
        
        # Strategy 1: Direct substring
        if inv_name_lower in cat_name or cat_name in inv_name_lower:
            score = 0.9
            if best_score < score:
                best_score = score
                best_match = prod
                continue
        
        # Strategy 2: Fuzzy ratio
        ratio = name_similarity(inv_name_lower, cat_name)
        if ratio > best_score:
            best_score = ratio
            best_match = prod
        
        # Strategy 3: Word overlap
        cat_words = set(cat_name.split())
        if inv_words and cat_words:
            overlap = len(inv_words & cat_words) / max(len(inv_words), len(cat_words))
            if overlap > 0.5 and overlap > best_score:
                best_score = overlap
                best_match = prod
    
    if best_score >= threshold:
        return best_match, best_score
    return None, 0

def main():
    logger.info("=" * 60)
    logger.info("Matching Inventory Products to Catalog Images")
    logger.info("=" * 60)
    
    inventory = load_inventory()
    catalog_products = load_catalog_products()
    
    if not catalog_products:
        logger.error("No catalog products found. Make sure brand_catalogs.json exists.")
        return
    
    # Build search names from inventory
    # Use article_name, item_name, short_name, category_2 as search terms
    matched = 0
    unmatched = 0
    results = []
    
    for item in inventory:
        # Build search terms from available names
        search_terms = []
        if item["article_name"]:
            search_terms.append(item["article_name"])
        if item["item_name"]:
            search_terms.append(item["item_name"])
        if item["short_name"]:
            search_terms.append(item["short_name"])
        
        # Also try individual words from category
        if item["category_2"]:
            search_terms.append(item["category_2"])
        
        best_overall_match = None
        best_overall_score = 0
        
        for term in search_terms:
            if not term:
                continue
            match, score = find_best_match(term, catalog_products)
            if match and score > best_overall_score:
                best_overall_match = match
                best_overall_score = score
        
        # Build result
        result = {
            "item_code": item["item_code"],
            "barcode": item["barcode"],
            "article_name": item["article_name"],
            "item_name": item["item_name"],
            "vendor": item["vendor"],
            "section": item["section"],
            "department": item["department"],
            "mrp": item["mrp"],
            "category_2": item["category_2"],
            "category_3": item["category_3"],
            "has_image": False,
            "image_url": "",
            "matched_product": "",
            "matched_brand": "",
            "match_score": 0,
        }
        
        if best_overall_match and best_overall_score >= 0.3:
            result["has_image"] = True
            result["image_url"] = best_overall_match["image_url"]
            result["matched_product"] = best_overall_match["original_name"]
            result["matched_brand"] = best_overall_match["brand"]
            result["match_score"] = round(best_overall_score, 3)
            matched += 1
        else:
            unmatched += 1
        
        results.append(result)
    
    # Save results
    output = {
        "total_inventory": len(inventory),
        "matched_with_image": matched,
        "unmatched": unmatched,
        "match_rate": round(matched / len(inventory) * 100, 1) if inventory else 0,
        "items": results,
    }
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nResults:")
    logger.info(f"  Total inventory items: {len(inventory)}")
    logger.info(f"  Matched with images: {matched} ({output['match_rate']}%)")
    logger.info(f"  Unmatched: {unmatched}")
    logger.info(f"\nSaved to: {OUTPUT_PATH}")
    
    # Show sample matches
    logger.info("\nSample matches:")
    shown = 0
    for r in results:
        if r["has_image"] and shown < 10:
            logger.info(f"  {r['article_name'][:40]:40s} → {r['matched_product'][:40]:40s} (score: {r['match_score']})")
            shown += 1
    
    logger.info("\nSample unmatched:")
    shown = 0
    for r in results:
        if not r["has_image"] and shown < 5:
            logger.info(f"  {r['article_name'][:50]}")
            shown += 1

if __name__ == "__main__":
    main()