"""
Object Detector — Grounding DINO
===================================
Open-vocabulary object detection to find products in uploaded images.
Detects: clothing, accessories, jewelry, bags, etc.
"""
import logging
import numpy as np
import torch
from PIL import Image, ImageDraw
from typing import List, Dict, Optional, Tuple

from utils.config import (
    DETECTION_TEXT_PROMPT, DETECTION_BOX_THRESHOLD, DETECTION_TEXT_THRESHOLD,
)

logger = logging.getLogger(__name__)


class GroundingDINODetector:
    """Wrapper around Grounding DINO for product detection."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self._load_model()

    def _load_model(self):
        """Load Grounding DINO model and processor."""
        try:
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

            # Use HF hub model if local weights not available
            model_id = "IDEA-Research/grounding-dino-tiny"
            
            logger.info(f"Loading Grounding DINO on {self.device}...")
            self.processor = AutoProcessor.from_pretrained(model_id)
            self.model = AutoModelForZeroShotObjectDetection.from_pretrained(
                model_id, torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            self.model.eval()
            logger.info("Grounding DINO loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Grounding DINO: {e}")
            raise

    @torch.no_grad()
    def detect(
        self,
        image: Image.Image,
        text_prompt: Optional[str] = None,
        box_threshold: float = DETECTION_BOX_THRESHOLD,
        text_threshold: float = DETECTION_TEXT_THRESHOLD,
    ) -> List[Dict]:
        """
        Detect objects in an image.
        
        Args:
            image: PIL Image (RGB)
            text_prompt: Text prompt for detection (e.g., "clothing . jewelry . bag")
            box_threshold: Confidence threshold for boxes
            text_threshold: Confidence threshold for text
            
        Returns:
            List of dicts with keys: label, score, bbox (x1, y1, x2, y2 normalized [0,1])
        """
        if text_prompt is None:
            text_prompt = DETECTION_TEXT_PROMPT

        inputs = self.processor(
            images=image,
            text=text_prompt,
            return_tensors="pt",
        ).to(self.device)

        outputs = self.model(**inputs)

        # Post-process results
        target_size = torch.tensor([image.size[::-1]]).to(self.device)
        results = self.processor.post_process_grounded_object_detection(
            outputs,
            target_sizes=target_size,
            text_threshold=text_threshold,
        )[0]

        detections = []
        scores = results["scores"].cpu().numpy() if hasattr(results["scores"], "cpu") else results["scores"]
        labels = results["labels"]
        boxes = results["boxes"].cpu().numpy() if hasattr(results["boxes"], "cpu") else results["boxes"]

        for i in range(len(scores)):
            if float(scores[i]) < box_threshold:
                continue  # Filter by score after processing
            label = labels[i] if isinstance(labels[i], str) else labels[i]
            detections.append({
                "label": str(label),
                "score": float(scores[i]),
                "bbox": boxes[i].tolist(),  # [x1, y1, x2, y2] in pixels
            })

        # Convert pixel coordinates to normalized [0, 1]
        w, h = image.size
        for det in detections:
            det["bbox_normalized"] = [
                det["bbox"][0] / w,
                det["bbox"][1] / h,
                det["bbox"][2] / w,
                det["bbox"][3] / h,
            ]

        logger.info(f"Detected {len(detections)} objects in image.")
        return detections

    def draw_boxes(
        self, image: Image.Image, detections: List[Dict], show_labels: bool = True
    ) -> Image.Image:
        """Draw bounding boxes on image for visualization."""
        draw_img = image.copy()
        draw = ImageDraw.Draw(draw_img)
        
        for det in detections:
            bbox = det["bbox"]
            label = det["label"]
            score = det["score"]
            
            # Draw rectangle
            draw.rectangle(bbox, outline="red", width=3)
            
            if show_labels:
                text = f"{label} ({score:.2f})"
                # Draw text background
                bbox_width = bbox[2] - bbox[0]
                text_bbox = draw.textbbox((bbox[0], bbox[1]), text)
                draw.rectangle(text_bbox, fill="red")
                draw.text((bbox[0], bbox[1]), text, fill="white")
        
        return draw_img