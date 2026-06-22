"""
Feature Extractor — CLIP Only (Stable)
=========================================
Extracts visual features from product images using only CLIP.
DINOv2 excluded to avoid input size incompatibility (vit_large needs 518x518).
"""
import logging
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from typing import List, Optional
from utils.config import CLIP_MODEL_NAME, CLIP_PRETRAINED, EMBEDDING_DIM

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract visual features using CLIP (ViT-B-32, 224x224 input)."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.clip_model = None
        self.clip_preprocess = None
        self.clip_tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load OpenCLIP model."""
        import open_clip
        logger.info(f"Loading OpenCLIP {CLIP_MODEL_NAME}...")
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL_NAME,
            pretrained=CLIP_PRETRAINED,
            device=self.device,
        )
        self.clip_model.eval()
        self.clip_tokenizer = open_clip.get_tokenizer(CLIP_MODEL_NAME)
        logger.info(f"OpenCLIP loaded. Input: 224x224, Output: {EMBEDDING_DIM}")

    @torch.no_grad()
    def extract_clip_embedding(self, image: Image.Image) -> np.ndarray:
        """Extract CLIP embedding (512-dim)."""
        img_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
        embedding = self.clip_model.encode_image(img_tensor)
        return F.normalize(embedding, dim=-1).cpu().numpy().flatten()

    def extract_embedding(self, image: Image.Image) -> np.ndarray:
        """Extract CLIP-only embedding. Returns 512-dim vector."""
        return self.extract_clip_embedding(image)

    def extract_text_embedding(self, text: str) -> np.ndarray:
        """Extract CLIP text embedding."""
        tokens = self.clip_tokenizer([text]).to(self.device)
        embedding = self.clip_model.encode_text(tokens)
        return F.normalize(embedding, dim=-1).cpu().numpy().flatten()

    @property
    def embedding_dim(self) -> int:
        return EMBEDDING_DIM

    def extract_embeddings_batch(self, images: List[Image.Image]) -> np.ndarray:
        embeddings = []
        for img in images:
            embeddings.append(self.extract_embedding(img))
        return np.array(embeddings)