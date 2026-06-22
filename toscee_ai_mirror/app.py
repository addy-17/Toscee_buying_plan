"""
Toscee AI Personal Shopper Mirror
===================================
A multimodal AI system that watches what a customer is holding/wearing
and suggests matching products from your store catalog.

Tech Stack: Grounding DINO, SAM, CLIP, DINOv2, FAISS, ChromaDB, 
            PyTorch Geometric, pytorch-metric-learning, Gemma/Llama

Usage: streamlit run app.py
"""
import streamlit as st
import logging
from PIL import Image
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import (
    CATALOG_FILE, PRODUCT_EMBEDDINGS_FILE, FAISS_INDEX_FILE,
    ASSETS_DIR, USE_LOCAL_LLM,
)
from utils.catalog_loader import load_catalog, get_all_products, get_product_count, get_brands_list
from utils.image_utils import load_image, resize_image, get_image_from_upload
from detection.object_detector import GroundingDINODetector
from detection.segmenter import SAMSegmenter
from detection.feature_extractor import FeatureExtractor
from embeddings.build_faiss_index import FAISSIndexBuilder
from embeddings.build_chromadb import ChromaDBManager
from embeddings.product_embedder import ProductEmbedder
from style_graph.compatibility_scorer import CompatibilityScorer
from recommender.style_recommender import StyleRecommender
from recommender.query_expander import expand_query, get_compatible_categories
from recommender.llm_generator import LLMGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Toscee AI Personal Shopper",
    page_icon="🪞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State ──────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.detector = None
    st.session_state.segmenter = None
    st.session_state.feature_extractor = None
    st.session_state.faiss = None
    st.session_state.recommender = None
    st.session_state.llm = None
    st.session_state.catalog_loaded = False
    st.session_state.detections = []
    st.session_state.suggestions = []
    st.session_state.message = ""
    st.session_state.uploaded_image = None
    st.session_state.processed = False


# ── Load Resources ────────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    """Load all ML models (cached to avoid reloading)."""
    logger.info("Loading models...")
    status = {"detector": False, "segmenter": False, "features": False, "faiss": False, "catalog": False}

    try:
        st.session_state.detector = GroundingDINODetector()
        status["detector"] = True
    except Exception as e:
        st.warning(f"⚠️ Detection model not loaded: {e}")

    try:
        st.session_state.segmenter = SAMSegmenter()
        status["segmenter"] = True
    except Exception as e:
        st.warning(f"⚠️ Segmentation model not loaded: {e}")

    try:
        st.session_state.feature_extractor = FeatureExtractor()
        status["features"] = True
    except Exception as e:
        st.warning(f"⚠️ Feature extractor not loaded: {e}")

    # Load FAISS index
    try:
        st.session_state.faiss = FAISSIndexBuilder()
        if FAISS_INDEX_FILE.exists():
            st.session_state.faiss.load_index()
            status["faiss"] = True
            logger.info(f"FAISS index loaded: {st.session_state.faiss.total_vectors} vectors")
    except Exception as e:
        st.warning(f"⚠️ FAISS index not loaded: {e}")

    # Load catalog
    if CATALOG_FILE.exists():
        st.session_state.catalog_loaded = True
        status["catalog"] = True
        logger.info("Catalog loaded.")

    # Initialize recommender
    st.session_state.recommender = StyleRecommender(
        detector=st.session_state.detector,
        segmenter=st.session_state.segmenter,
        feature_extractor=st.session_state.feature_extractor,
        faiss_index=st.session_state.faiss,
    )
    if st.session_state.catalog_loaded:
        st.session_state.recommender.load_catalog_data()

    # LLM (optional)
    if USE_LOCAL_LLM:
        try:
            st.session_state.llm = LLMGenerator(use_local=True)
        except Exception as e:
            logger.warning(f"LLM not available: {e}")
            st.session_state.llm = LLMGenerator(use_local=False)
    else:
        st.session_state.llm = LLMGenerator(use_local=False)

    st.session_state.initialized = True
    return status


# ── Check if we have the minimum resources ───────────────────────────────
def check_ready():
    """Check if the app has enough resources to run."""
    if not CATALOG_FILE.exists():
        st.error(f"❌ Catalog file not found: {CATALOG_FILE}")
        st.info("Copy your brand_catalogs.json from the buying_plan_app to the data/ folder.")
        return False
    
    if not FAISS_INDEX_FILE.exists() and not PRODUCT_EMBEDDINGS_FILE.exists():
        st.warning("⚠️ No embeddings or FAISS index found.")
        st.info(
            "Run the setup script first:\n"
            "```bash\n"
            "cd toscee_ai_mirror\n"
            "python scripts/build_all_embeddings.py\n"
            "```"
        )
        return False
    
    return True


# ── UI ────────────────────────────────────────────────────────────────────

def show_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.markdown("## 🪞 Toscee AI")
        st.markdown("### Personal Shopper")
        st.markdown("---")
        
        if st.session_state.catalog_loaded:
            catalog = load_catalog()
            brands = get_brands_list(catalog)
            products = get_all_products(catalog)
            st.metric("Brands in Catalog", len(brands))
            st.metric("Products Available", len(products))
        
        st.markdown("---")
        st.markdown("### How it works")
        st.markdown(
            "1. **Upload** a photo of a product\n"
            "2. AI **detects** what it is\n"
            "3. Finds **similar** products\n"
            "4. Suggests **compatible** items\n"
            "5. **Complete the look** ✨"
        )
        
        st.markdown("---")
        st.caption("🔒 Powered by Grounding DINO + SAM + CLIP + DINOv2 + FAISS + GNN")


def show_upload_section():
    """Show image upload area."""
    st.markdown("### 📸 Upload a Product Photo")
    st.markdown(
        "Upload a photo of a product you like — the AI will detect it and "
        "suggest matching items from our catalog."
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Choose an image...",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
    with col2:
        use_sample = st.checkbox("Use sample image", value=False, help="Use a sample image for demo")
    
    if use_sample:
        # Check for sample images
        sample_dir = Path(__file__).parent / "assets" / "sample_images"
        if sample_dir.exists():
            samples = list(sample_dir.glob("*.[jJ][pP][gG]")) + list(sample_dir.glob("*.[pP][nN][gG]"))
            if samples:
                selected_sample = st.selectbox(
                    "Choose sample:",
                    [s.name for s in samples],
                    key="sample_select",
                )
                if selected_sample:
                    uploaded_file = open(sample_dir / selected_sample, "rb")
    
    return uploaded_file


def show_detection_results(detections):
    """Show what was detected in the image."""
    if not detections:
        st.info("No products detected. Try a different image.")
        return
    
    st.markdown("### 🔍 Detected Products")
    
    cols = st.columns(len(detections))
    for i, det in enumerate(detections):
        with cols[i]:
            label = det.get("label", "Unknown").title()
            score = det.get("score", 0)
            st.markdown(f"**{label}**")
            st.caption(f"Confidence: {score:.0%}")
            
            # Show category expansion
            expansion = expand_query(label)
            if expansion["category"]:
                st.caption(f"Category: {expansion['category']}")
            if expansion["compatible_with"][:3]:
                st.caption(f"Goes with: {', '.join(expansion['compatible_with'][:3])}")


def show_suggestions(suggestions, message):
    """Show recommended products."""
    if not suggestions:
        return
    
    st.markdown("---")
    st.markdown("### ✨ Complete the Look")
    
    # Show AI message
    if message:
        st.success(message)
    
    # Show suggestions as cards
    st.markdown("#### Recommended Products")
    
    cols = st.columns(min(len(suggestions), 4))
    for i, suggestion in enumerate(suggestions):
        with cols[i % 4]:
            name = suggestion.get("product_name", "Product")
            brand = suggestion.get("brand", "Unknown")
            price = suggestion.get("price", 0)
            image_url = suggestion.get("image_url", "")
            reason = suggestion.get("reason", "")
            score = suggestion.get("compatibility_score", suggestion.get("similarity_score", 0))
            
            # Product card
            card_html = f"""
            <div style="border:1px solid #e2e8f0;border-radius:12px;padding:12px;margin-bottom:16px;background:white;box-shadow:0 1px 3px rgba(0,0,0,0.08);height:100%;">
            """
            if image_url:
                card_html += f'<img src="{image_url}" style="width:100%;height:150px;object-fit:cover;border-radius:8px;margin-bottom:8px;" onerror="this.style.display=\'none\'">'
            else:
                card_html += '<div style="height:150px;background:#f7fafc;border-radius:8px;margin-bottom:8px;display:flex;align-items:center;justify-content:center;font-size:40px;">📦</div>'
            
            card_html += f"""
                <div style="font-size:13px;font-weight:600;color:#1a202c;margin-bottom:4px;">{name[:50]}</div>
                <div style="font-size:11px;color:#718096;margin-bottom:4px;">{brand}</div>
                <div style="font-size:14px;font-weight:700;color:#2d3748;margin-bottom:4px;">₹{price:,.0f}</div>
                <div style="font-size:11px;color:#667EEA;">{reason}</div>
            """
            if score > 0:
                card_html += f'<div style="font-size:10px;color:#a0aec0;margin-top:4px;">Score: {score:.2f}</div>'
            card_html += "</div>"
            
            st.markdown(card_html, unsafe_allow_html=True)


def show_similar_products(similar_products):
    """Show visually similar products."""
    if not similar_products:
        return
    
    with st.expander("🔍 Visually Similar Products from Catalog", expanded=False):
        cols = st.columns(min(len(similar_products), 5))
        for i, prod in enumerate(similar_products):
            with cols[i % 5]:
                name = prod.get("product_name", "")
                brand = prod.get("brand", "")
                price = prod.get("price", 0)
                image_url = prod.get("image_url", "")
                
                if image_url:
                    st.image(image_url, width=120)
                st.markdown(f"**{name[:30]}**")
                st.caption(f"{brand} · ₹{price:,.0f}")


def show_catalog_summary():
    """Show catalog overview if no image is uploaded."""
    st.markdown("### 📊 Catalog Overview")
    
    catalog = load_catalog()
    products = get_all_products(catalog)
    brands = get_brands_list(catalog)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Brands", len(brands))
    col2.metric("Total Products", len(products))
    
    # Show brand breakdown
    with st.expander("View Brands"):
        for brand in brands:
            st.write(f"- {brand}")


# ── Main App ──────────────────────────────────────────────────────────────

def main():
    st.title("🪞 Toscee AI Personal Shopper")
    st.markdown("### AI-Powered Style Assistant — Complete the Look")
    
    show_sidebar()
    
    # Check if setup is ready
    if not check_ready():
        st.info("📋 **Setup Required**")
        st.markdown(
            "1. Copy `brand_catalogs.json` from your buying plan app into `data/`\n"
            "2. Install dependencies: `pip install -r requirements.txt`\n"
            "3. Run setup: `python scripts/download_models.py`\n"
            "4. Build embeddings: `python scripts/build_all_embeddings.py`\n"
            "5. Restart this app"
        )
        return
    
    # Load models on first run
    if not st.session_state.initialized:
        with st.spinner("Loading AI models... This may take a minute on first run."):
            status = load_models()
            if any(status.values()):
                st.success("✅ Models loaded!")
            st.rerun()
    
    # Main content area
    tab_upload, tab_browse, tab_about = st.tabs([
        "🪞 Personal Shopper", "📦 Browse Catalog", "ℹ️ About"
    ])
    
    # ── TAB 1: Personal Shopper ──
    with tab_upload:
        uploaded_file = show_upload_section()
        
        if uploaded_file is not None:
            # Load image
            image = get_image_from_upload(uploaded_file)
            
            if image is not None:
                st.session_state.uploaded_image = image
                
                # Display uploaded image
                col_img, col_results = st.columns([1, 1])
                
                with col_img:
                    st.markdown("#### Your Image")
                    st.image(image, use_column_width=True)
                    
                    if st.button("🔍 Analyze & Suggest", type="primary", use_container_width=True):
                        with st.spinner("AI is analyzing your image..."):
                            st.session_state.processed = False
                            
                            # Run recommendation pipeline
                            results = st.session_state.recommender.recommend_from_image(image)
                            
                            st.session_state.detections = results["detected_products"]
                            st.session_state.suggestions = results["suggestions"]
                            
                            # Generate LLM message
                            if st.session_state.llm:
                                message = st.session_state.llm.generate_complete_look_message(
                                    results["detected_products"],
                                    results["suggestions"],
                                )
                            else:
                                message = results["message"]
                            
                            st.session_state.message = message
                            st.session_state.processed = True
                
                with col_results:
                    if st.session_state.processed:
                        show_detection_results(st.session_state.detections)
                        show_suggestions(st.session_state.suggestions, st.session_state.message)
                    else:
                        st.info("Click **Analyze & Suggest** to get AI recommendations.")
                
                # Show similar products below
                if st.session_state.processed and hasattr(st.session_state.recommender, '_find_similar_products'):
                    st.markdown("---")
                    st.markdown("### 🔄 Try Another Look")
                    st.markdown("Upload another image or adjust your selection to explore more combinations.")
    
    # ── TAB 2: Browse Catalog ──
    with tab_browse:
        show_catalog_summary()
    
    # ── TAB 3: About ──
    with tab_about:
        st.markdown("## 🪞 Toscee AI Personal Shopper")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧠 AI Models Used")
            st.markdown("""
            - **Grounding DINO** — Open-vocabulary object detection
            - **SAM (Segment Anything)** — Precise product segmentation
            - **CLIP (OpenCLIP)** — Text-aligned visual embeddings
            - **DINOv2** — Self-supervised visual features
            - **FAISS** — Billion-scale similarity search
            - **ChromaDB** — Metadata vector database
            - **Style GNN** — Product compatibility graph
            - **Metric Learning** — Style embedding space
            - **Gemma / Llama** — Natural language generation
            """)
        
        with col2:
            st.markdown("### 📊 Data Pipeline")
            st.markdown("""
            1. Brand websites scraped → product catalog
            2. Product images → CLIP + DINOv2 embeddings
            3. Embeddings indexed in FAISS for similarity search
            4. Style graph built from embedding relationships
            5. GNN trained to predict product compatibility
            6. User uploads photo → detection → search → suggest
            """)
        
        st.markdown("---")
        st.markdown("*Built for Toscee — Gulshan Mall, Noida*")


if __name__ == "__main__":
    main()