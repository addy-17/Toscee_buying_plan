"""
Build All Embeddings Script
=============================
One-time setup script that:
1. Loads the inventory products with matched images
2. Generates CLIP + DINOv2 embeddings for all products
3. Builds FAISS index
4. Populates ChromaDB
5. Builds the style graph

Uses inventory_with_images.json (inventory items matched to catalog images).

Run: python scripts/build_all_embeddings.py
"""
import logging
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import (
    CATALOG_FILE, INVENTORY_WITH_IMAGES_FILE,
    PRODUCT_EMBEDDINGS_FILE, FAISS_INDEX_FILE,
)
from utils.catalog_loader import get_all_products
from detection.feature_extractor import FeatureExtractor
from embeddings.product_embedder import ProductEmbedder
from embeddings.build_faiss_index import FAISSIndexBuilder
from embeddings.build_chromadb import ChromaDBManager
from style_graph.graph_builder import StyleGraphBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_inventory_with_images():
    """Load the matched inventory data."""
    if not INVENTORY_WITH_IMAGES_FILE.exists():
        logger.error(f"Inventory file not found: {INVENTORY_WITH_IMAGES_FILE}")
        logger.error("Run scripts/match_images_to_inventory.py first.")
        sys.exit(1)

    with open(INVENTORY_WITH_IMAGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items_with_images = [item for item in data["items"] if item["has_image"]]
    logger.info(f"Loaded {len(items_with_images)} inventory items with images "
                f"(out of {data['total_inventory']} total, {data['match_rate']}% match rate)")
    return items_with_images


def main():
    logger.info("=" * 60)
    logger.info("TOSCEE AI Personal Shopper — Build All Embeddings")
    logger.info("=" * 60)

    # Step 1: Load inventory with matched images
    logger.info("\n[1/5] Loading inventory with matched images...")
    inventory_items = load_inventory_with_images()

    if not inventory_items:
        logger.error("No inventory items with images. Cannot build embeddings.")
        sys.exit(1)

    # Step 2: Initialize feature extractor
    logger.info("\n[2/5] Initializing Feature Extractor (CLIP: ViT-B-32 + DINOv2)...")
    feature_extractor = FeatureExtractor()
    logger.info(f"Ensemble embedding dimension: {feature_extractor.embedding_dim}")

    # Step 3: Generate product embeddings
    logger.info(f"\n[3/5] Generating embeddings for {len(inventory_items)} products...")
    logger.info("This will download images from URLs. May take a while...")
    
    from tqdm import tqdm
    from utils.image_utils import download_image, resize_image

    embeddings = []
    metadata = []
    failed = 0

    for idx, item in enumerate(tqdm(inventory_items, desc="Embedding")):
        image_url = item.get("image_url", "")
        if not image_url:
            failed += 1
            continue

        img = download_image(image_url)
        if img is None:
            failed += 1
            continue

        try:
            img = resize_image(img, max_size=512)
            embedding = feature_extractor.extract_embedding(img)
            embeddings.append(embedding)

            metadata.append({
                "id": idx,
                "barcode": item.get("barcode", ""),
                "item_code": item.get("item_code", ""),
                "product_name": item.get("article_name", item.get("item_name", "Unknown")),
                "brand": item.get("vendor", "Unknown"),
                "price": item.get("mrp", 0),
                "category": item.get("section", ""),
                "department": item.get("department", ""),
                "image_url": image_url,
                "matched_product": item.get("matched_product", ""),
                "matched_brand": item.get("matched_brand", ""),
                "match_score": item.get("match_score", 0),
            })
        except Exception as e:
            logger.warning(f"Failed to embed product {idx}: {e}")
            failed += 1

    embeddings = [e for e in embeddings if e is not None]
    if not embeddings:
        logger.error("No embeddings generated!")
        sys.exit(1)

    embeddings_array = __import__('numpy').array(embeddings)
    logger.info(f"Generated {len(embeddings_array)} embeddings ({failed} failed).")

    # Save embeddings and metadata
    from embeddings.product_embedder import ProductEmbedder
    embedder = ProductEmbedder(feature_extractor=feature_extractor)
    embedder.save_embeddings(embeddings_array, metadata)

    # Step 4: Build FAISS index
    logger.info("\n[4/5] Building FAISS index...")
    faiss_builder = FAISSIndexBuilder()
    faiss_builder.build_index(embeddings_array)
    faiss_builder.save_index()
    logger.info(f"FAISS index saved with {faiss_builder.total_vectors} vectors.")

    # Step 5: Populate ChromaDB
    logger.info("\n[5/5] Populating ChromaDB...")
    chroma = ChromaDBManager()
    chroma.create_collection(overwrite=True)
    chroma.add_products(metadata)
    logger.info(f"ChromaDB populated with {chroma.count()} products.")

    # Step 6: Build style graph (purely from embeddings)
    logger.info("\n[5/5] Building Style Compatibility Graph from embeddings...")
    graph_builder = StyleGraphBuilder()
    # Use metadata as products
    graph_builder.products = metadata
    graph_builder.product_map = {i: m for i, m in enumerate(metadata)}
    graph_builder.add_similarity_edges(embeddings_array, threshold=0.85, top_k=3)
    graph_builder.save_graph()
    logger.info(f"Style graph built: {graph_builder.num_nodes} nodes, {graph_builder.num_edges} edges")

    logger.info("\n" + "=" * 60)
    logger.info("✅ All embeddings built successfully!")
    logger.info(f"   - {len(embeddings_array)} product embeddings")
    logger.info(f"   - FAISS index: {FAISS_INDEX_FILE}")
    logger.info(f"   - ChromaDB: ready")
    logger.info(f"   - Style graph: {graph_builder.num_edges} edges")
    logger.info("\nRun 'streamlit run app.py' to start the AI Personal Shopper.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()