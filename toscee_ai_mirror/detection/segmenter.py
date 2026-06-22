"""
Segmenter — SAM (Segment Anything Model)
===========================================
Takes bounding boxes from Grounding DINO and produces pixel-perfect
segmentation masks for each detected product.
"""
import logging
import numpy as np
import torch
from PIL import Image
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SAMSegmenter:
    """Wrapper around SAM for product segmentation."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load SAM model from HuggingFace hub."""
        try:
            from transformers import SamModel, SamProcessor
            model_id = "facebook/sam-vit-base"
            logger.info(f"Loading SAM from HuggingFace hub on {self.device}...")
            self.model_hf = SamModel.from_pretrained(model_id).to(self.device)
            self.processor = SamProcessor.from_pretrained(model_id)
            self.model_hf.eval()
            logger.info("SAM loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SAM: {e}")
            raise

    @torch.no_grad()
    def segment(self, image: Image.Image, bboxes: List[List[float]]) -> List[Dict]:
        """
        Segment objects in image given bounding boxes.
        
        Args:
            image: PIL Image (RGB)
            bboxes: List of bounding boxes [x1, y1, x2, y2] in pixels
            
        Returns:
            List of dicts with keys: mask (PIL Image), bbox, score
        """
        if not hasattr(self, 'model_hf') or self.model_hf is None:
            return self._segment_sam(image, bboxes)
        return self._segment_hf(image, bboxes)

    def _segment_hf(self, image: Image.Image, bboxes: List[List[float]]) -> List[Dict]:
        """Segment using HuggingFace SAM implementation."""
        results = []
        for bbox in bboxes:
            inputs = self.processor(
                image, input_boxes=[[bbox]], return_tensors="pt"
            ).to(self.device)
            
            outputs = self.model_hf(**inputs)
            masks = self.processor.post_process_masks(
                outputs.pred_masks, inputs["original_sizes"], inputs["reshaped_input_sizes"]
            )
            
            if len(masks) > 0 and len(masks[0]) > 0:
                mask = masks[0][0].cpu().numpy()
                mask_img = Image.fromarray((mask > 0).astype(np.uint8) * 255)
                results.append({
                    "mask": mask_img,
                    "bbox": bbox,
                    "score": float(outputs.iou_scores[0][0].cpu()),
                })
        return results

    def _segment_sam(self, image: Image.Image, bboxes: List[List[float]]) -> List[Dict]:
        """Fallback: return simple bounding box masks."""
        results = []
        for bbox in bboxes:
            mask_img = Image.new('L', image.size, 0)
            results.append({
                "mask": mask_img,
                "bbox": bbox,
                "score": 1.0,
            })
        return results

    def apply_mask(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        """Apply a segmentation mask to an image (background removed)."""
        img_array = np.array(image)
        mask_array = np.array(mask) > 0
        
        # Create RGBA image with transparent background
        rgba = np.zeros((*img_array.shape[:2], 4), dtype=np.uint8)
        rgba[..., :3] = img_array
        rgba[..., 3] = (mask_array * 255).astype(np.uint8)
        
        return Image.fromarray(rgba)