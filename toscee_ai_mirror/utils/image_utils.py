"""
Image Utilities
===============
Download, resize, preprocess images for the detection pipeline.
"""
import logging
import requests
import numpy as np
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


def download_image(url: str, timeout: int = 30) -> Optional[Image.Image]:
    """Download an image from URL and return as PIL Image."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, verify=False)  # Disable SSL verification to avoid handshake issues
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        return img.convert("RGB")
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None


def load_image(path: str) -> Optional[Image.Image]:
    """Load an image from a local file path or URL."""
    path = str(path)
    if path.startswith(("http://", "https://")):
        return download_image(path)
    p = Path(path)
    if p.exists():
        img = Image.open(p)
        return img.convert("RGB")
    logger.warning(f"Image not found: {path}")
    return None


def resize_image(image: Image.Image, max_size: int = 800) -> Image.Image:
    """Resize image while maintaining aspect ratio, max dimension = max_size."""
    w, h = image.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.LANCZOS)
    return image


def pad_to_square(image: Image.Image, fill: int = 255) -> Image.Image:
    """Pad image to square with white background."""
    return ImageOps.pad(image, (max(image.size), max(image.size)), color=fill, centering=(0.5, 0.5))


def image_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array (H, W, C)."""
    return np.array(image)


def numpy_to_image(arr: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image."""
    return Image.fromarray(arr)


def crop_to_bbox(image: Image.Image, bbox: Tuple[float, float, float, float]) -> Image.Image:
    """
    Crop image to bounding box.
    bbox: (x1, y1, x2, y2) in normalized coordinates [0, 1].
    """
    w, h = image.size
    x1, y1, x2, y2 = bbox
    left, top, right, bottom = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
    # Ensure valid crop region
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)
    return image.crop((left, top, right, bottom))


def get_image_from_upload(uploaded_file) -> Optional[Image.Image]:
    """Convert a Streamlit UploadedFile to PIL Image."""
    if uploaded_file is None:
        return None
    try:
        img = Image.open(uploaded_file)
        return img.convert("RGB")
    except Exception as e:
        logger.error(f"Failed to load uploaded file: {e}")
        return None