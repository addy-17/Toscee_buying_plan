"""
Toscee AI Personal Shopper — Configuration
============================================
Central config: paths, model names, hyperparameters.
"""
from pathlib import Path

# ── Project Paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
ASSETS_DIR = PROJECT_ROOT / "assets"
SAMPLE_IMAGES_DIR = ASSETS_DIR / "sample_images"

# ── Catalog ────────────────────────────────────────────────────────────────
CATALOG_FILE = DATA_DIR / "brand_catalogs.json"

# ── Inventory with Images (matched from catalog) ──────────────────────────
INVENTORY_WITH_IMAGES_FILE = DATA_DIR / "inventory_with_images.json"

# ── Embeddings ─────────────────────────────────────────────────────────────
EMBEDDINGS_DIR = DATA_DIR / "product_embeddings"
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_EMBEDDINGS_FILE = EMBEDDINGS_DIR / "product_embeddings.npy"
PRODUCT_METADATA_FILE = EMBEDDINGS_DIR / "product_metadata.json"
FAISS_INDEX_FILE = EMBEDDINGS_DIR / "faiss_index.bin"
CHROMADB_DIR = DATA_DIR / "chromadb"

# ── Style Graph ────────────────────────────────────────────────────────────
STYLE_GRAPH_DIR = DATA_DIR / "style_graph"
STYLE_GRAPH_DIR.mkdir(parents=True, exist_ok=True)

COMPATIBILITY_SEED_FILE = STYLE_GRAPH_DIR / "compatibility_seeds.json"
GNN_MODEL_FILE = STYLE_GRAPH_DIR / "gnn_model.pt"
GRAPH_DATA_FILE = STYLE_GRAPH_DIR / "style_graph.pt"
METRIC_LEARNER_FILE = STYLE_GRAPH_DIR / "metric_learner.pt"

# ── Detection ──────────────────────────────────────────────────────────────
DETECTION_TEXT_PROMPT = "clothing item . accessory . jewelry . bag . product . item"
DETECTION_BOX_THRESHOLD = 0.25
DETECTION_TEXT_THRESHOLD = 0.25

# ── Feature Extraction ─────────────────────────────────────────────────────
# ViT-B-32 uses 224x224 input (compatible with DINOv2's 224x224)
# This avoids the "Input height (224) doesn't match model (518)" error
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"
EMBEDDING_DIM = 512  # ViT-B-32 output dimension

# ── FAISS ──────────────────────────────────────────────────────────────────
FAISS_INDEX_TYPE = "IP"  # Inner Product (cosine similarity on normalized vectors)

# ── Style Graph ────────────────────────────────────────────────────────────
GNN_HIDDEN_DIM = 256
GNN_OUTPUT_DIM = 128
GNN_LEARNING_RATE = 0.001
GNN_EPOCHS = 100

# ── Recommendation ─────────────────────────────────────────────────────────
TOP_K_SIMILAR = 5
TOP_K_COMPATIBLE = 4
MAX_SUGGESTIONS = 8

# ── LLM ────────────────────────────────────────────────────────────────────
LLM_MODEL_NAME = "google/gemma-2b-it"
USE_LOCAL_LLM = False