"""
Style Graph Builder
====================
Builds a product→product compatibility graph.
Nodes = products, Edges = "goes well with" relationships.
The graph is seeded with hand-crafted compatibility pairs and then
propagates via GNN to discover new relationships.
"""
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from utils.config import (
    COMPATIBILITY_SEED_FILE, GRAPH_DATA_FILE,
    STYLE_GRAPH_DIR,
)
from utils.catalog_loader import load_catalog, get_all_products

logger = logging.getLogger(__name__)


class StyleGraphBuilder:
    """
    Builds the style compatibility graph.
    
    Graph structure:
    - Nodes: Each product in catalog (node_id = product index)
    - Edges: Compatibility relationships between products
    - Edge types:
        "same_look" -> products that form a complete outfit together
        "similar_style" -> products with similar visual style
        "complementary" -> products that complement each other
    - Edge weights: 0.0 to 1.0 (learned via metric learning)
    """

    def __init__(self):
        self.products = []
        self.product_map = {}  # product_id -> product dict
        self.adjacency = defaultdict(dict)  # node_id -> {neighbor_id: weight}
        self.edge_types = defaultdict(dict)  # (node_id, neighbor_id) -> type
        self.node_features = None
        self.seed_pairs = []

    def load_products(self, catalog: Optional[Dict] = None):
        """Load products from catalog."""
        if catalog is None:
            catalog = load_catalog()
        self.products = get_all_products(catalog)
        self.product_map = {i: p for i, p in enumerate(self.products)}
        logger.info(f"Loaded {len(self.products)} products for graph.")

    def build_from_embeddings_only(self):
        """
        Build the graph purely from product embeddings.
        No hardcoded rules — compatibility is determined by
        visual similarity and category complementarity in embedding space.
        """
        logger.info("Building style graph from embeddings only (no seed data).")
        # This is a placeholder — the graph will be populated by
        # add_similarity_edges() and add_category_edges() calls.
        pass

    def add_edge(self, node_a: int, node_b: int, weight: float, edge_type: str = "same_look"):
        """Add an edge between two product nodes."""
        self.adjacency[node_a][node_b] = weight
        self.adjacency[node_b][node_a] = weight
        self.edge_types[(node_a, node_b)] = edge_type
        self.edge_types[(node_b, node_a)] = edge_type

    def add_similarity_edges(
        self,
        embedding_matrix: np.ndarray,
        threshold: float = 0.8,
        top_k: int = 3,
    ):
        """
        Add edges between visually similar products.
        Uses embedding cosine similarity to find similar-looking products.
        """
        if embedding_matrix is None:
            logger.warning("No embeddings provided for similarity edges.")
            return

        n = embedding_matrix.shape[0]
        # Normalize embeddings
        norms = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-8
        normalized = embedding_matrix / norms

        # Compute cosine similarity matrix
        sim_matrix = normalized @ normalized.T

        # Add edges for highly similar products
        edges_added = 0
        for i in range(n):
            # Get top-k most similar (excluding self)
            sim_scores = sim_matrix[i]
            sim_scores[i] = 0  # Exclude self
            top_indices = np.argsort(-sim_scores)[:top_k]

            for j in top_indices:
                score = float(sim_scores[j])
                if score >= threshold and j not in self.adjacency[i]:
                    self.add_edge(i, j, score, "similar_style")
                    edges_added += 1

        logger.info(f"Added {edges_added} similarity-based edges (threshold={threshold}).")

    def add_category_edges(self):
        """
        Add edges between products from complementary categories.
        e.g., Saree ↔ Earrings, Kurta ↔ Bag, Perfume ↔ Candle
        """
        # Define complementary category pairs
        complementary_pairs = [
            ("Saree", "Earrings"),
            ("Saree", "Necklaces"),
            ("Saree", "Bracelets & Bangles"),
            ("Kurta", "Earrings"),
            ("Kurta", "Bags"),
            ("Kurta", "Scarves & Stoles"),
            ("Dress", "Bags"),
            ("Dress", "Earrings"),
            ("Dress", "Bracelets & Bangles"),
            ("Perfumes", "Candles"),
            ("Perfumes", "Gift Sets"),
            ("Candles", "Gift Sets"),
            ("Bags", "Scarves & Stoles"),
            ("Ethnic Wear", "Maang Tikka"),
            ("Ethnic Wear", "Earrings"),
        ]

        # Extract subcategory from product (simple heuristic)
        def get_subcategory(product):
            name = product.get("product_name", "").lower()
            category = product.get("category", "").lower()
            text = name + " " + category

            subcat_keywords = {
                "Saree": ["saree", "sari"],
                "Earrings": ["earring", "jhumka"],
                "Necklaces": ["necklace", "choker", "pendant"],
                "Bracelets & Bangles": ["bracelet", "bangle"],
                "Bags": ["bag", "tote", "clutch", "potli"],
                "Scarves & Stoles": ["scarf", "stole"],
                "Perfumes": ["perfume", "attar", "fragrance"],
                "Candles": ["candle"],
                "Gift Sets": ["gift set", "gift box", "hamper"],
                "Dress": ["dress", "gown"],
                "Kurta": ["kurta", "kurti"],
                "Maang Tikka": ["tikka", "maang tikka"],
                "Ethnic Wear": ["lehenga", "dupatta", "ethnic"],
            }

            for subcat, keywords in subcat_keywords.items():
                if any(kw in text for kw in keywords):
                    return subcat
            return None

        # Get subcategories for each product
        product_subcats = {}
        for i, product in enumerate(self.products):
            subcat = get_subcategory(product)
            if subcat:
                product_subcats[i] = subcat

        # Add edges for complementary pairs
        edges_added = 0
        for cat_a, cat_b in complementary_pairs:
            products_a = [i for i, sc in product_subcats.items() if sc == cat_a]
            products_b = [i for i, sc in product_subcats.items() if sc == cat_b]

            for pa in products_a[:5]:  # Limit to 5 per category to avoid explosion
                for pb in products_b[:5]:
                    if pb not in self.adjacency[pa]:
                        self.add_edge(pa, pb, 0.5, "complementary")
                        edges_added += 1

        logger.info(f"Added {edges_added} category-based complementary edges.")

    def _find_product(self, product_name: str) -> Optional[int]:
        """Find a product index by name (case-insensitive partial match)."""
        product_name = product_name.lower().strip()
        for i, product in enumerate(self.products):
            name = product.get("product_name", "").lower()
            if product_name in name or name in product_name:
                return i
        # Try harder: match first few words
        for i, product in enumerate(self.products):
            name = product.get("product_name", "").lower()
            if product_name.split()[0] in name.split():
                return i
        logger.warning(f"Could not find product: {product_name}")
        return None

    def get_graph_data(self) -> Dict:
        """Get graph data for saving/training."""
        return {
            "num_nodes": len(self.products),
            "edges": [
                {
                    "source": int(s),
                    "target": int(t),
                    "weight": float(w),
                    "type": self.edge_types.get((s, t), "unknown"),
                }
                for s, neighbors in self.adjacency.items()
                for t, w in neighbors.items()
                if s < t  # Store each edge once
            ],
            "product_ids": list(self.product_map.keys()),
        }

    def save_graph(self, filepath: Optional[str] = None):
        """Save graph data to JSON."""
        path = filepath or str(GRAPH_DATA_FILE)
        data = self.get_graph_data()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Graph saved to {path} ({len(data['edges'])} edges).")

    def load_graph(self, filepath: Optional[str] = None):
        """Load graph data from JSON."""
        path = filepath or str(GRAPH_DATA_FILE)
        if not path.exists():
            logger.warning(f"Graph file not found: {path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.adjacency.clear()
        self.edge_types.clear()
        for edge in data["edges"]:
            self.add_edge(
                edge["source"], edge["target"],
                edge["weight"], edge["type"],
            )
        logger.info(f"Graph loaded from {path} ({len(data['edges'])} edges).")

    @property
    def num_nodes(self) -> int:
        """Get number of nodes (products)."""
        return len(self.products)

    @property
    def num_edges(self) -> int:
        """Get number of undirected edges."""
        return sum(1 for s in self.adjacency for t in self.adjacency[s] if s < t)

    @property
    def density(self) -> float:
        """Get graph density."""
        n = self.num_nodes
        if n < 2:
            return 0.0
        max_edges = n * (n - 1) / 2
        return self.num_edges / max_edges if max_edges > 0 else 0.0