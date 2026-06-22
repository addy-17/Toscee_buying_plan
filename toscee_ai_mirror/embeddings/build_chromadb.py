"""
ChromaDB Builder
=================
Stores product metadata in ChromaDB for fast retrieval.
Enables filtering by brand, category, price range, etc.
"""
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

from utils.config import CHROMADB_DIR, PRODUCT_METADATA_FILE

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manage ChromaDB collection for product metadata."""

    def __init__(self, collection_name: str = "products"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._init_client()

    def _init_client(self):
        """Initialize ChromaDB client."""
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
            logger.info(f"ChromaDB client initialized at {CHROMADB_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def create_collection(self, overwrite: bool = False):
        """Create or get the products collection."""
        try:
            if overwrite:
                try:
                    self.client.delete_collection(self.collection_name)
                except Exception:
                    pass  # Collection may not exist yet
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Toscee product catalog metadata"},
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' ready.")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def add_products(self, metadata: List[Dict]):
        """Add product metadata to ChromaDB."""
        if self.collection is None:
            self.create_collection()

        ids = [str(m["id"]) for m in metadata]
        documents = [self._format_document(m) for m in metadata]
        metadatas = [
            {
                "brand": m["brand"],
                "product_name": m["product_name"],
                "price": m.get("price", 0),
                "category": m.get("category", ""),
            }
            for m in metadata
        ]

        # Add in batches of 100
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end],
            )
        logger.info(f"Added {len(ids)} products to ChromaDB.")

    def _format_document(self, metadata: Dict) -> str:
        """Format product metadata as a searchable document."""
        return (
            f"{metadata.get('product_name', '')} "
            f"{metadata.get('brand', '')} "
            f"{metadata.get('category', '')} "
            f"{metadata.get('description', '')}"
        ).strip()

    def query_by_text(self, query_text: str, n_results: int = 10) -> List[Dict]:
        """Search products by text query."""
        if self.collection is None:
            self.create_collection()
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        return self._format_results(results)

    def query_by_filter(self, filter_dict: Dict, n_results: int = 100) -> List[Dict]:
        """Query products by metadata filter."""
        if self.collection is None:
            self.create_collection()
        
        results = self.collection.query(
            query_texts=[""],
            n_results=n_results,
            where=filter_dict,
        )
        return self._format_results(results)

    def _format_results(self, results) -> List[Dict]:
        """Format ChromaDB results into usable dicts."""
        formatted = []
        if not results or not results["ids"]:
            return formatted
        
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return formatted

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Get a product by its ID."""
        if self.collection is None:
            self.create_collection()
        
        results = self.collection.get(ids=[product_id])
        if results and results["ids"]:
            return {
                "id": results["ids"][0],
                "metadata": results["metadatas"][0] if results["metadatas"] else {},
            }
        return None

    def count(self) -> int:
        """Get total product count in ChromaDB."""
        if self.collection is None:
            return 0
        return self.collection.count()