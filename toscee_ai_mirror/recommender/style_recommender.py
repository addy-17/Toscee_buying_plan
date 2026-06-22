"""
Style Recommender
==================
The main recommendation engine that combines all components:
- Object detection (Grounding DINO)
- Segmentation (SAM)
- Feature extraction (CLIP + DINOv2)
- Similarity search (FAISS)
- Compatibility scoring (GNN + Metric Learning)
- LLM generation

Given an uploaded image, produces "Complete the Look" suggestions.
"""
import logging
import numpy as np
from PIL import Image
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from utils.config import TOP_K_SIMILAR, TOP_K_COMPATIBLE, MAX_SUGGESTIONS
from utils.catalog_loader import load_catalog, get_all_products
from utils.image_utils import load_image, resize_image, crop_to_bbox
from detection.object_detector import GroundingDINODetector
from detection.segmenter import SAMSegmenter
from detection.feature_extractor import FeatureExtractor
from embeddings.build_faiss_index import FAISSIndexBuilder
from embeddings.product_embedder import ProductEmbedder
from style_graph.compatibility_scorer import CompatibilityScorer

logger = logging.getLogger(__name__)


class StyleRecommender:
    """
    Full-stack style recommendation engine.
    
    Pipeline:
    1. Detect products in uploaded image (Grounding DINO)
    2. Segment each product (SAM)
    3. Extract features (CLIP + DINOv2)
    4. Find visually similar products in catalog (FAISS)
    5. Score compatibility with other catalog products (GNN + rules)
    6. Return top suggestions
    """

    def __init__(
        self,
        detector: Optional[GroundingDINODetector] = None,
        segmenter: Optional[SAMSegmenter] = None,
        feature_extractor: Optional[FeatureExtractor] = None,
        faiss_index: Optional[FAISSIndexBuilder] = None,
        scorers: Optional[CompatibilityScorer] = None,
    ):
        self.detector = detector
        self.segmenter = segmenter
        self.feature_extractor = feature_extractor
        self.faiss = faiss_index
        self.scorer = scorers or CompatibilityScorer()
        self.embedder = ProductEmbedder(feature_extractor=self.feature_extractor)

        # Catalog metadata
        self.catalog = None
        self.all_products = None
        self.product_embeddings = None

    def load_catalog_data(self):
        """Load catalog and embeddings."""
        self.catalog = load_catalog()
        self.all_products = get_all_products(self.catalog)

        # Load pre-computed embeddings if available
        emb, meta = self.embedder.load_embeddings()
        if emb is not None:
            self.product_embeddings = emb
            if meta:
                self.all_products = meta
            logger.info(f"Loaded {len(self.all_products)} products with embeddings.")

    def recommend_from_image(
        self,
        image: Image.Image,
        top_k_similar: int = TOP_K_SIMILAR,
        top_k_compatible: int = TOP_K_COMPATIBLE,
        max_suggestions: int = MAX_SUGGESTIONS,
    ) -> Dict:
        """
        Full recommendation pipeline from an uploaded image.
        
        Args:
            image: PIL Image of a person holding/wearing products
            top_k_similar: Number of similar products to retrieve per detection
            top_k_compatible: Number of compatible products per detection
            max_suggestions: Maximum total suggestions
            
        Returns:
            Dict with:
                - detected_products: List of detected items
                - suggestions: List of recommended products
                - similar_products: Visually similar to detected items
                - message: LLM-generated "Complete the look" text
        """
        if self.all_products is None:
            self.load_catalog_data()

        # Step 1: Detect products
        image = resize_image(image, max_size=800)
        detections = self._detect_products(image)

        if not detections:
            return {
                "detected_products": [],
                "suggestions": [],
                "similar_products": [],
                "message": "No products detected in the image. Try a clearer photo.",
            }

        # Step 2: Extract features for each detection
        for det in detections:
            det["embedding"] = self._extract_detection_features(image, det)

        # Step 3: Find similar products in catalog for each detection
        all_similar = []
        for det in detections:
            if det["embedding"] is not None:
                similar = self._find_similar_products(
                    det["embedding"], top_k=top_k_similar
                )
                det["similar_products"] = similar
                all_similar.extend(similar)

        # Step 4: Find compatible products (different category)
        suggestions = self._find_compatible_products(
            detections, all_similar, top_k=top_k_compatible
        )

        # Step 5: Deduplicate and limit suggestions
        suggestions = self._deduplicate(suggestions)[:max_suggestions]

        # Step 6: Generate message (placeholder — LLM integration is separate)
        message = self._generate_message(detections, suggestions)

        return {
            "detected_products": [
                {"label": d["label"], "score": d["score"], "bbox": d["bbox"]}
                for d in detections
            ],
            "suggestions": suggestions,
            "similar_products": all_similar[:top_k_similar * 2],
            "message": message,
        }

    def _detect_products(self, image: Image.Image) -> List[Dict]:
        """Run detection pipeline on image."""
        if self.detector is None:
            logger.warning("Detector not initialized. Using placeholder.")
            return [{"label": "product", "score": 1.0, "bbox": [0, 0, 100, 100]}]

        detections = self.detector.detect(image)
        
        # Filter low-confidence detections
        detections = [d for d in detections if d["score"] > 0.3]
        
        # Limit to top 3 detections
        detections = detections[:3]

        logger.info(f"Detected {len(detections)} products.")
        return detections

    def _extract_detection_features(
        self, image: Image.Image, detection: Dict
    ) -> Optional[np.ndarray]:
        """Extract features for a detected product."""
        if self.feature_extractor is None:
            return None

        try:
            # Crop to bounding box
            bbox = detection["bbox_normalized"] if "bbox_normalized" in detection else detection["bbox"]
            cropped = crop_to_bbox(image, bbox)
            cropped = resize_image(cropped, max_size=224)
            
            # Extract embedding
            embedding = self.feature_extractor.extract_embedding(cropped)
            return embedding
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return None

    def _find_similar_products(
        self, query_embedding: np.ndarray, top_k: int = 5
    ) -> List[Dict]:
        """Find visually similar products using FAISS."""
        if self.faiss is None or not self.faiss.is_loaded:
            logger.warning("FAISS index not loaded.")
            return []

        if self.all_products is None:
            return []

        try:
            distances, indices = self.faiss.search(query_embedding, top_k=top_k)
            
            similar = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.all_products):
                    product = self.all_products[idx]
                    similar.append({
                        "id": int(idx),
                        "product_name": product.get("product_name", ""),
                        "brand": product.get("brand", "Unknown"),
                        "price": product.get("price_mrp", product.get("price", 0)),
                        "image_url": product.get("image_url", ""),
                        "product_url": product.get("product_url", ""),
                        "similarity_score": float(distances[0][i]),
                        "reason": f"Visually similar ({(1 - distances[0][i]) * 100:.0f}%)",
                    })
            return similar
        except Exception as e:
            logger.warning(f"FAISS search failed: {e}")
            return []

    def _find_compatible_products(
        self,
        detections: List[Dict],
        similar_products: List[Dict],
        top_k: int = 4,
    ) -> List[Dict]:
        """Find products compatible with detected items."""
        if self.all_products is None or self.product_embeddings is None:
            return []

        # Get categories of detected products
        detected_categories = set()
        for det in detections:
            cat = self.scorer._guess_category({"product_name": det["label"]})
            detected_categories.add(cat)

        # Score all products for compatibility
        scored_products = []
        for idx, product in enumerate(self.all_products):
            prod_cat = self.scorer._guess_category(product)
            
            # Skip products in same categories as detected items
            if prod_cat in detected_categories:
                continue

            # Skip already-similar products
            if any(s.get("id") == idx for s in similar_products):
                continue

            # Compute compatibility score
            embedding = self.product_embeddings[idx] if idx < len(self.product_embeddings) else None
            score = self.scorer.compute_overall_score(
                {"product_name": detections[0]["label"]},
                product,
                embedding_a=np.zeros(self.product_embeddings.shape[1]) if self.product_embeddings is not None else None,
                embedding_b=embedding,
            )

            scored_products.append({
                "id": int(idx),
                "product_name": product.get("product_name", ""),
                "brand": product.get("brand", "Unknown"),
                "price": product.get("price_mrp", product.get("price", 0)),
                "image_url": product.get("image_url", ""),
                "product_url": product.get("product_url", ""),
                "compatibility_score": score,
                "category": prod_cat,
                "reason": f"Completes your look ({prod_cat})",
            })

        # Sort by compatibility score
        scored_products.sort(key=lambda x: x["compatibility_score"], reverse=True)
        
        # Ensure diversity: pick top from different categories
        selected = []
        seen_categories = set()
        for p in scored_products:
            if p["category"] not in seen_categories and len(selected) < top_k:
                selected.append(p)
                seen_categories.add(p["category"])

        # Fill remaining slots with highest scores
        for p in scored_products:
            if len(selected) >= top_k:
                break
            if p not in selected:
                selected.append(p)

        return selected

    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate products by ID."""
        seen = set()
        unique = []
        for item in items:
            item_id = item.get("id")
            if item_id not in seen:
                seen.add(item_id)
                unique.append(item)
        return unique

    def _generate_message(
        self, detections: List[Dict], suggestions: List[Dict]
    ) -> str:
        """
        Generate a "Complete the look" message.
        Can be replaced with LLM-generated text (Gemma/Llama).
        """
        if not detections:
            return "No products detected."

        detected_names = [d["label"].title() for d in detections]
        detected_text = " and ".join(detected_names)

        if not suggestions:
            return f"I see you're looking at {detected_text}. Try exploring other brands in our catalog!"

        suggestion_names = []
        for s in suggestions[:3]:
            name = s.get("product_name", "")
            brand = s.get("brand", "")
            if name:
                short = name[:30]
                suggestion_names.append(f"**{short}** from {brand}")

        suggestions_text = ", ".join(suggestion_names)

        message = (
            f"✨ **Complete your {detected_text} look!**\n\n"
            f"Pair it with: {suggestions_text}\n\n"
            f"*Want more options? Browse the suggestions below.*"
        )
        return message