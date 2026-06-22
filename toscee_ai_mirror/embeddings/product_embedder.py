"""
Product Embedder
=================
Generates and stores embeddings for all products in the catalog.
Uses CLIP + DINOv2 ensemble features.
"""
import json
import logging
import numpy as np
from pathlib import Path
from PIL import Image
from typing import List, Dict, Optional
from tqdm import tqdm

from utils.config import (
    PRODUCT_EMBEDDINGS_FILE, PRODUCT_METADATA_FILE,
    EMBEDDINGS_DIR,
)
from utils.catalog_loader import load_catalog, get_all_products
from utils.image_utils import download_image, resize_image
from detection.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class ProductEmbedder:
    """Generate and manage product embeddings."""

    def __init__(self, feature_extractor: Optional[FeatureExtractor] = None):
        self.feature_extractor = feature_extractor or FeatureExtractor()

    def embed_all_products(
        self,
        catalog: Optional[Dict] = None,
        save: bool = True,
    ) -> tuple:
        """
        Generate embeddings for all products in the catalog.
        
        Args:
            catalog: Catalog dict (loaded if not provided)
            save: Whether to save embeddings to disk
            
        Returns:
            (embeddings_array, metadata_list)
        """
        if catalog is None:
            catalog = load_catalog()
        
        products = get_all_products(catalog)
        logger.info(f"Generating embeddings for {len(products)} products...")

        embeddings = []
        metadata = []
        failed = 0

        for idx, product in enumerate(tqdm(products, desc="Embedding products")):
            image_url = product.get("image_url", "")
            if not image_url:
                failed += 1
                continue

            # Download image
            img = download_image(image_url)
            if img is None:
                failed += 1
                continue

            try:
                img = resize_image(img, max_size=512)
                embedding = self.feature_extractor.extract_embedding(img)
                embeddings.append(embedding)

                metadata.append({
                    "id": idx,
                    "product_name": product.get("product_name", ""),
                    "brand": product.get("_brand", "Unknown"),
                    "price": product.get("price_mrp", 0),
                    "category": product.get("category", ""),
                    "image_url": image_url,
                    "product_url": product.get("product_url", ""),
                    "description": product.get("description", "")[:200],
                })
            except Exception as e:
                logger.warning(f"Failed to embed product {idx}: {e}")
                failed += 1

        embeddings = np.array(embeddings)
        logger.info(f"Embedded {len(embeddings)} products ({failed} failed).")

        if save:
            self.save_embeddings(embeddings, metadata)

        return embeddings, metadata

    def save_embeddings(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Save embeddings and metadata to disk."""
        np.save(str(PRODUCT_EMBEDDINGS_FILE), embeddings)
        with open(PRODUCT_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(embeddings)} embeddings to {PRODUCT_EMBEDDINGS_FILE}")

    def load_embeddings(self) -> tuple:
        """Load pre-computed embeddings and metadata."""
        if not PRODUCT_EMBEDDINGS_FILE.exists():
            logger.warning("No embeddings file found.")
            return None, None
        
        embeddings = np.load(str(PRODUCT_EMBEDDINGS_FILE))
        with open(PRODUCT_METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        logger.info(f"Loaded {len(embeddings)} embeddings.")
        return embeddings, metadata