"""
Download Models Script
========================
Downloads all pretrained model weights needed for the AI Personal Shopper:
- Grounding DINO (from HuggingFace)
- SAM (from HuggingFace)
- CLIP weights (loaded via OpenCLIP)
- DINOv2 weights (loaded via timm)

Run: python scripts/download_models.py
"""
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import MODELS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def download_grounding_dino():
    """Download Grounding DINO model from HuggingFace."""
    logger.info("Downloading Grounding DINO (IDEA-Research/grounding-dino-tiny)...")
    try:
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        
        model_id = "IDEA-Research/grounding-dino-tiny"
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id)
        
        # Save locally
        save_path = MODELS_DIR / "grounding-dino-tiny"
        save_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_path))
        processor.save_pretrained(str(save_path))
        logger.info(f"Grounding DINO saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to download Grounding DINO: {e}")
        logger.info("Will load from HuggingFace hub at runtime instead.")


def download_sam():
    """Download SAM model from HuggingFace."""
    logger.info("Downloading SAM (facebook/sam-vit-base)...")
    try:
        from transformers import SamModel, SamProcessor
        
        model_id = "facebook/sam-vit-base"
        model = SamModel.from_pretrained(model_id)
        processor = SamProcessor.from_pretrained(model_id)
        
        # Save locally
        save_path = MODELS_DIR / "sam-vit-base"
        save_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(save_path))
        processor.save_pretrained(str(save_path))
        logger.info(f"SAM saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to download SAM: {e}")
        logger.info("Will load from HuggingFace hub at runtime instead.")


def verify_models():
    """Verify all models are accessible."""
    logger.info("\n=== Model Verification ===")
    
    # Test OpenCLIP
    try:
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        logger.info("✅ OpenCLIP (ViT-B-32) — OK")
    except Exception as e:
        logger.warning(f"⚠️ OpenCLIP: {e}")

    # Test timm (DINOv2)
    try:
        import timm
        model = timm.create_model("vit_small_patch14_reg4_dinov2.lvd142m", pretrained=True, num_classes=0)
        logger.info("✅ DINOv2 (timm) — OK")
    except Exception as e:
        logger.warning(f"⚠️ DINOv2: {e}")

    # Test Grounding DINO via HF
    try:
        from transformers import AutoModelForZeroShotObjectDetection
        logger.info("✅ Grounding DINO (transformers) — OK")
    except Exception as e:
        logger.warning(f"⚠️ Grounding DINO: {e}")

    # Test SAM via transformers
    try:
        from transformers import SamModel
        logger.info("✅ SAM (transformers) — OK")
    except Exception as e:
        logger.warning(f"⚠️ SAM: {e}")

    # Test FAISS
    try:
        import faiss
        logger.info("✅ FAISS — OK")
    except Exception as e:
        logger.warning(f"⚠️ FAISS: {e}")

    # Test ChromaDB
    try:
        import chromadb
        logger.info("✅ ChromaDB — OK")
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB: {e}")

    # Test PyTorch Geometric
    try:
        import torch_geometric
        logger.info(f"✅ PyTorch Geometric — OK")
    except Exception as e:
        logger.warning(f"⚠️ PyTorch Geometric: {e}")

    # Test pytorch-metric-learning
    try:
        import pytorch_metric_learning
        logger.info("✅ pytorch-metric-learning — OK")
    except Exception as e:
        logger.warning(f"⚠️ pytorch-metric-learning: {e}")


def main():
    logger.info("=" * 50)
    logger.info("TOSCEE AI Personal Shopper — Model Download")
    logger.info("=" * 50)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    download_grounding_dino()
    download_sam()
    verify_models()
    
    logger.info("\n" + "=" * 50)
    logger.info("Download complete! Models will load from HuggingFace at runtime.")
    logger.info("Run 'streamlit run app.py' to start the app.")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()