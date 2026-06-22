"""
Query Expander
===============
Expands detected product labels into broader search queries
for finding compatible products across categories.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


# Mapping from detected labels to expanded search terms
EXPANSION_MAP = {
    "kurta": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "bangles", "necklace", "bag", "potli",
            "stole", "scarf", "dupatta", "jutti", "mojari",
        ],
        "style_keywords": ["ethnic", "traditional", "festive"],
    },
    "kurti": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "bangles", "necklace", "bag",
            "stole", "scarf", "dupatta",
        ],
        "style_keywords": ["ethnic", "casual", "western"],
    },
    "saree": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "necklace", "bangles", "potli",
            "blouse", "heel", "sandals", "clutch",
        ],
        "style_keywords": ["ethnic", "traditional", "bridal", "festive"],
    },
    "sari": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "necklace", "bangles", "potli",
            "blouse", "heel", "sandals", "clutch",
        ],
        "style_keywords": ["ethnic", "traditional", "bridal", "festive"],
    },
    "dress": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "necklace", "bracelet", "bag",
            "clutch", "heel", "belt", "watch",
        ],
        "style_keywords": ["western", "party", "casual"],
    },
    "gown": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "necklace", "bracelet", "clutch",
            "heel", "hair accessory",
        ],
        "style_keywords": ["western", "party", "bridal"],
    },
    "lehenga": {
        "category": "Apparel",
        "compatible_with": [
            "earrings", "necklace", "maang tikka", "bangles",
            "potli", "dupatta", "heel",
        ],
        "style_keywords": ["ethnic", "bridal", "festive"],
    },
    "earring": {
        "category": "Jewellery",
        "compatible_with": [
            "necklace", "bracelet", "ring", "maang tikka",
            "saree", "kurta", "dress",
        ],
        "style_keywords": ["matching set", "daily wear", "festive"],
    },
    "jhumka": {
        "category": "Jewellery",
        "compatible_with": [
            "necklace", "bangles", "saree", "kurta",
            "lehenga", "ethnic wear",
        ],
        "style_keywords": ["traditional", "festive", "bridal"],
    },
    "necklace": {
        "category": "Jewellery",
        "compatible_with": [
            "earrings", "bracelet", "ring", "maang tikka",
            "saree", "kurta", "dress",
        ],
        "style_keywords": ["matching set", "statement", "daily wear"],
    },
    "bangle": {
        "category": "Jewellery",
        "compatible_with": [
            "earrings", "necklace", "bracelet", "saree",
            "kurta", "dress",
        ],
        "style_keywords": ["traditional", "daily wear"],
    },
    "bracelet": {
        "category": "Accessories",
        "compatible_with": [
            "watch", "earrings", "necklace", "dress", "kurta",
        ],
        "style_keywords": ["western", "casual", "party"],
    },
    "bag": {
        "category": "Bags",
        "compatible_with": [
            "saree", "kurta", "dress", "ethnic wear",
            "jewellery", "perfume",
        ],
        "style_keywords": ["matching", "daily wear", "party"],
    },
    "clutch": {
        "category": "Bags",
        "compatible_with": [
            "saree", "dress", "gown", "lehenga",
            "jewellery", "perfume",
        ],
        "style_keywords": ["party", "bridal", "evening"],
    },
    "potli": {
        "category": "Bags",
        "compatible_with": [
            "saree", "kurta", "lehenga", "ethnic wear",
            "jewellery",
        ],
        "style_keywords": ["ethnic", "traditional", "festive"],
    },
    "perfume": {
        "category": "Fragrances",
        "compatible_with": [
            "candle", "gift set", "body lotion",
        ],
        "style_keywords": ["floral", "woody", "fresh"],
    },
    "candle": {
        "category": "Home Decor",
        "compatible_with": [
            "perfume", "diffuser", "gift set",
            "vase", "sculpture",
        ],
        "style_keywords": ["scented", "decorative", "gift"],
    },
    "scarf": {
        "category": "Accessories",
        "compatible_with": [
            "bag", "kurta", "dress", "coat",
            "earrings",
        ],
        "style_keywords": ["winter", "casual", "ethnic"],
    },
    "stole": {
        "category": "Accessories",
        "compatible_with": [
            "saree", "kurta", "dress",
            "earrings", "bangles",
        ],
        "style_keywords": ["ethnic", "traditional", "winter"],
    },
    "shoe": {
        "category": "Footwear",
        "compatible_with": [
            "saree", "kurta", "dress", "jeans",
            "bag",
        ],
        "style_keywords": ["daily wear", "party", "formal"],
    },
    "watch": {
        "category": "Accessories",
        "compatible_with": [
            "bracelet", "dress", "kurta",
            "bag",
        ],
        "style_keywords": ["daily wear", "formal", "casual"],
    },
    "ring": {
        "category": "Jewellery",
        "compatible_with": [
            "earrings", "necklace", "bracelet",
            "saree", "dress",
        ],
        "style_keywords": ["daily wear", "festive", "engagement"],
    },
    "flower": {
        "category": "Gifting",
        "compatible_with": [
            "perfume", "candle", "gift set",
            "vase",
        ],
        "style_keywords": ["gift", "decoration", "wedding"],
    },
}


def expand_query(detected_label: str) -> Dict:
    """
    Expand a detected product label into compatible categories and search terms.
    
    Args:
        detected_label: The label detected by Grounding DINO
        
    Returns:
        Dict with category, compatible_with list, and style keywords
    """
    label_lower = detected_label.lower().strip()
    
    # Direct match
    if label_lower in EXPANSION_MAP:
        return EXPANSION_MAP[label_lower]
    
    # Partial match
    for key, value in EXPANSION_MAP.items():
        if key in label_lower or label_lower in key:
            return value
    
    # Default
    return {
        "category": "Other",
        "compatible_with": ["accessories", "jewellery", "bags", "fragrances"],
        "style_keywords": [],
    }


def get_compatible_categories(detected_labels: List[str]) -> List[str]:
    """
    Get all compatible categories given a list of detected labels.
    Returns categories not already in the detection list.
    """
    detected_categories = set()
    all_compatible = set()

    for label in detected_labels:
        expansion = expand_query(label)
        detected_categories.add(expansion["category"])
        all_compatible.update(expansion["compatible_with"])

    return list(all_compatible - detected_categories)


def get_search_queries(detected_labels: List[str]) -> List[str]:
    """
    Generate search queries for finding compatible products.
    """
    queries = []
    for label in detected_labels:
        expansion = expand_query(label)
        for compatible in expansion["compatible_with"][:3]:
            queries.append(f"{compatible} {expansion['category']}".strip())
    return queries