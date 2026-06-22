"""
FAISS Index Builder
=====================
Builds a FAISS index for fast similarity search over product embeddings.
Uses Inner Product (cosine similarity on normalized vectors).
"""
import logging
import numpy as np
import faiss
from typing import Optional, List
from pathlib import Path

from utils.config import FAISS_INDEX_FILE, FAISS_INDEX_TYPE, PRODUCT_EMBEDDINGS_FILE

logger = logging.getLogger(__name__)


class FAISSIndexBuilder:
    """Build and manage FAISS index for product similarity search."""

    def __init__(self):
        self.index = None
        self.dimension = None

    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build a FAISS index from embeddings.
        
        Args:
            embeddings: numpy array of shape (n_products, embedding_dim)
            
        Returns:
            FAISS index
        """
        n_products, dim = embeddings.shape
        self.dimension = dim
        
        logger.info(f"Building FAISS index for {n_products} products (dim={dim})...")

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        if FAISS_INDEX_TYPE == "IP":
            # Inner Product on normalized vectors = cosine similarity
            self.index = faiss.IndexFlatIP(dim)
        else:
            # L2 distance
            self.index = faiss.IndexFlatL2(dim)

        self.index.add(embeddings.astype(np.float32))
        logger.info(f"FAISS index built with {self.index.ntotal} vectors.")
        return self.index

    def save_index(self, path: Optional[Path] = None):
        """Save FAISS index to disk."""
        save_path = path or FAISS_INDEX_FILE
        if self.index is None:
            logger.warning("No index to save.")
            return
        faiss.write_index(self.index, str(save_path))
        logger.info(f"FAISS index saved to {save_path}")

    def load_index(self, path: Optional[Path] = None) -> Optional[faiss.Index]:
        """Load FAISS index from disk."""
        load_path = path or FAISS_INDEX_FILE
        if not load_path.exists():
            logger.warning(f"FAISS index not found at {load_path}")
            return None
        
        self.index = faiss.read_index(str(load_path))
        self.dimension = self.index.d
        logger.info(f"FAISS index loaded with {self.index.ntotal} vectors.")
        return self.index

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> tuple:
        """
        Search for nearest neighbors.
        
        Args:
            query_embedding: Query vector (1D or 2D array)
            top_k: Number of nearest neighbors to return
            
        Returns:
            (distances, indices) tuples
        """
        if self.index is None:
            raise RuntimeError("FAISS index not loaded. Call load_index() first.")

        # Ensure 2D and float32
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)
        faiss.normalize_L2(query_embedding)

        distances, indices = self.index.search(query_embedding, top_k)
        return distances, indices

    @property
    def is_loaded(self) -> bool:
        """Check if index is loaded."""
        return self.index is not None

    @property
    def total_vectors(self) -> int:
        """Get number of vectors in index."""
        return self.index.ntotal if self.index else 0