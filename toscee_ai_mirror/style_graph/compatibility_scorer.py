"""
Compatibility Scorer
=====================
Scores compatibility between products using the trained Style GNN
and metric learning model. Used by the recommender to find
"what goes with what."
"""
import logging
import numpy as np
import torch
from typing import List, Dict, Optional

from utils.config import GNN_MODEL_FILE, METRIC_LEARNER_FILE
from embeddings.build_faiss_index import FAISSIndexBuilder

logger = logging.getLogger(__name__)


class CompatibilityScorer:
    """
    Score compatibility between products.
    
    Combines multiple signals:
    1. Graph-based compatibility (GNN)
    2. Visual similarity (FAISS/embeddings)
    3. Category complementarity
    4. Price harmony
    """

    def __init__(
        self,
        gnn_model: Optional[torch.nn.Module] = None,
        faiss_index: Optional[FAISSIndexBuilder] = None,
    ):
        self.gnn_model = gnn_model
        self.faiss = faiss_index

    def score_by_category_complementarity(
        self,
        product_a: Dict,
        product_b: Dict,
    ) -> float:
        """
        Score based on how well categories complement each other.
        e.g., Saree + Earrings = high, Saree + Saree = low.
        """
        complementary_pairs = {
            ("Saree", "Earrings"): 0.9,
            ("Saree", "Necklaces"): 0.8,
            ("Saree", "Bracelets & Bangles"): 0.7,
            ("Saree", "Bags"): 0.6,
            ("Kurta", "Earrings"): 0.9,
            ("Kurta", "Bags"): 0.8,
            ("Kurta", "Scarves"): 0.7,
            ("Dress", "Bags"): 0.8,
            ("Dress", "Earrings"): 0.7,
            ("Dress", "Bracelets"): 0.6,
            ("Perfumes", "Candles"): 0.8,
            ("Perfumes", "Gift Sets"): 0.7,
            ("Bags", "Scarves"): 0.6,
        }

        cat_a = self._guess_category(product_a)
        cat_b = self._guess_category(product_b)

        if cat_a == cat_b:
            return 0.2  # Same category = low complementarity

        # Check both orderings
        score = complementary_pairs.get((cat_a, cat_b))
        if score is not None:
            return score
        score = complementary_pairs.get((cat_b, cat_a))
        if score is not None:
            return score

        return 0.3  # Default moderate score

    def score_by_price_harmony(self, product_a: Dict, product_b: Dict) -> float:
        """
        Score based on price compatibility.
        Products in similar price ranges go better together.
        """
        price_a = product_a.get("price_mrp", 0) or 0
        price_b = product_b.get("price_mrp", 0) or 0

        if price_a == 0 and price_b == 0:
            return 0.5  # Unknown prices = neutral

        if price_a == 0 or price_b == 0:
            return 0.4  # Partially known = slightly penalize

        # Log-scale price ratio: closer ratio = higher score
        ratio = min(price_a, price_b) / max(price_a, price_b)
        return float(ratio)  # 0.0 to 1.0

    def score_by_gnn(
        self,
        embedding_a: np.ndarray,
        embedding_b: np.ndarray,
    ) -> float:
        """Score using GNN-based compatibility."""
        if self.gnn_model is None:
            return 0.0

        self.gnn_model.eval()
        with torch.no_grad():
            emb_a = torch.tensor(embedding_a, dtype=torch.float32).unsqueeze(0)
            emb_b = torch.tensor(embedding_b, dtype=torch.float32).unsqueeze(0)

            # Pass through GNN
            if hasattr(self.gnn_model, 'predict_compatibility'):
                score = self.gnn_model.predict_compatibility(emb_a, emb_b)
                return float(score.item())
            else:
                # Simple cosine similarity on GNN output
                out_a = self.gnn_model(emb_a, torch.zeros((2, 0), dtype=torch.long))
                out_b = self.gnn_model(emb_b, torch.zeros((2, 0), dtype=torch.long))
                sim = torch.cosine_similarity(out_a, out_b)
                return float(sim.item())

    def score_by_visual_similarity(
        self,
        embedding_a: np.ndarray,
        embedding_b: np.ndarray,
    ) -> float:
        """Score based on visual embedding similarity."""
        if embedding_a is None or embedding_b is None:
            return 0.0
        
        # Cosine similarity
        a_norm = embedding_a / (np.linalg.norm(embedding_a) + 1e-8)
        b_norm = embedding_b / (np.linalg.norm(embedding_b) + 1e-8)
        similarity = float(np.dot(a_norm, b_norm))
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, (similarity + 1) / 2))

    def _guess_category(self, product: Dict) -> str:
        """Simple category guessing from product name."""
        name = (product.get("product_name", "") + " " + 
                product.get("category", "")).lower()
        
        category_keywords = {
            "Saree": ["saree", "sari"],
            "Earrings": ["earring", "jhumka"],
            "Necklaces": ["necklace", "choker", "pendant"],
            "Bracelets & Bangles": ["bracelet", "bangle"],
            "Rings": ["ring"],
            "Bags": ["bag", "tote", "clutch", "potli", "handbag"],
            "Kurta": ["kurta", "kurti"],
            "Dress": ["dress", "gown"],
            "Perfumes": ["perfume", "attar", "fragrance"],
            "Candles": ["candle"],
            "Gift Sets": ["gift set", "gift box"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in name for kw in keywords):
                return category
        return "Other"

    def compute_overall_score(
        self,
        product_a: Dict,
        product_b: Dict,
        embedding_a: Optional[np.ndarray] = None,
        embedding_b: Optional[np.ndarray] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute overall compatibility score between two products.
        
        Weights: category=0.3, price=0.2, visual=0.3, gnn=0.2
        """
        if weights is None:
            weights = {
                "category": 0.3,
                "price": 0.2,
                "visual": 0.3,
                "gnn": 0.2,
            }

        cat_score = self.score_by_category_complementarity(product_a, product_b)
        price_score = self.score_by_price_harmony(product_a, product_b)

        visual_score = 0.0
        if embedding_a is not None and embedding_b is not None:
            visual_score = self.score_by_visual_similarity(embedding_a, embedding_b)

        gnn_score = 0.0
        if embedding_a is not None and embedding_b is not None:
            gnn_score = self.score_by_gnn(embedding_a, embedding_b)

        total = (
            weights["category"] * cat_score +
            weights["price"] * price_score +
            weights["visual"] * visual_score +
            weights["gnn"] * gnn_score
        )

        return min(1.0, max(0.0, total))