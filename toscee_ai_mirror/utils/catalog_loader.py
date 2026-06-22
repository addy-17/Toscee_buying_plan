"""
Catalog Loader
==============
Loads brand_catalogs.json and provides product-level access.
"""
import json
import logging
from typing import List, Dict, Optional
from utils.config import CATALOG_FILE

logger = logging.getLogger(__name__)


def load_catalog() -> Dict:
    """Load the brand catalog JSON."""
    if not CATALOG_FILE.exists():
        logger.warning(f"Catalog file not found: {CATALOG_FILE}")
        return {"brands": [], "total_brands_with_data": 0, "total_products_scraped": 0}
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_products(catalog: Dict) -> List[Dict]:
    """Flatten all products from all brands into a single list."""
    products = []
    for brand in catalog.get("brands", []):
        brand_name = brand.get("brand_name", "Unknown")
        for product in brand.get("products", []):
            product["_brand"] = brand_name
            product["_brand_website"] = brand.get("website", "")
            products.append(product)
    return products


def get_product_by_id(products: List[Dict], product_id: int) -> Optional[Dict]:
    """Get a product by its index in the flattened list."""
    if 0 <= product_id < len(products):
        return products[product_id]
    return None


def get_brands_list(catalog: Dict) -> List[str]:
    """Return sorted list of brand names."""
    return sorted(set(b["brand_name"] for b in catalog.get("brands", [])))


def get_products_by_brand(catalog: Dict, brand_name: str) -> List[Dict]:
    """Get all products for a specific brand."""
    for brand in catalog.get("brands", []):
        if brand["brand_name"] == brand_name:
            return brand.get("products", [])
    return []


def get_product_count(catalog: Dict) -> int:
    """Get total product count across all brands."""
    return sum(len(b.get("products", [])) for b in catalog.get("brands", []))