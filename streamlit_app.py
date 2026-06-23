"""
Toscee Buying Plan App - Streamlit Frontend
=============================================
3
Main app for browsing inventory, selecting products, and generating buying plans.
"""
import streamlit as st
import json
import io
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from buying_plan_utils import (
    load_inventory, get_inventory_brands, get_inventory_departments,
    get_inventory_products, get_inventory_summary,
    generate_buying_plan_excel, scrape_brand_by_url,
    CATEGORY_MAP, ALL_SUBCATEGORIES
)

# --- Page Config ---
st.set_page_config(
    page_title="Toscee Buying Plan",
    page_icon="📦",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a202c;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "inventory_data" not in st.session_state:
    st.session_state.inventory_data = load_inventory()
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = None

# --- Helper Functions ---
def get_category_for_product(product):
    """Determine category from product data."""
    text = ((product.get("product_name") or "") + " " +
            (product.get("category") or "") + " " +
            (product.get("description") or "")).lower()
    tags = product.get("tags", [])
    text += " " + (" ".join(tags).lower() if isinstance(tags, list) else str(tags or "").lower())
    for subcat_name, pattern in ALL_SUBCATEGORIES.items():
        if pattern and __import__('re').search(pattern, text):
            return subcat_name
    return "Other"

def render_product_card(product, idx):
    """Render a product selection card."""
    with st.container():
        # Image column - wider and more prominent
        col_img, col_info, col_qty = st.columns([2, 3, 1])
        
        with col_img:
            # Try multiple image sources
            image_displayed = False
            
            # First try image_file from local extracted_images folder
            image_file = product.get("image_file", "")
            if image_file and image_file not in ["", "nan", "NaN"]:
                brand = product.get("brand", "")
                # Try different possible paths
                possible_paths = [
                    f"extracted_images/{brand}/{image_file}",
                    f"Images/{brand} x Toscee.xlsx/{image_file}",
                    f"ocr_extracted_data/{brand}_images/{image_file}",
                ]
                for img_path in possible_paths:
                    try:
                        st.image(img_path, width=250, use_container_width=True)
                        image_displayed = True
                        break
                    except:
                        continue
            
            # Fallback to image_url if available
            if not image_displayed and product.get("image_url"):
                try:
                    st.image(product["image_url"], width=250, use_container_width=True)
                    image_displayed = True
                except:
                    pass
            
            # Show placeholder if no image
            if not image_displayed:
                st.markdown(
                    '<div style="width:250px;height:200px;background:#f0f0f0;'
                    'display:flex;align-items:center;justify-content:center;'
                    'border-radius:8px;color:#999;">No Image</div>',
                    unsafe_allow_html=True
                )
        
        with col_info:
            st.write(f"**{product.get('product_name', 'N/A')}**")
            st.write(f"**Brand:** {product.get('brand', 'N/A')}")
            st.write(f"**Dept:** {product.get('department', 'N/A')}")
            mrp = product.get("mrp", "N/A")
            st.write(f"**MRP:** ₹{mrp}" if mrp != "N/A" else f"**MRP:** {mrp}")
            subcat = get_category_for_product(product)
            st.write(f"**Category:** {subcat}")
            if image_file and image_file not in ["", "nan", "NaN"]:
                st.caption(f"📁 {image_file}")
        
        with col_qty:
            qty = st.number_input(
                "Qty", min_value=0, max_value=100, value=0,
                key=f"qty_{idx}_{product.get('product_name', '')[:20]}"
            )
            product["quantity"] = qty
            if qty > 0:
                if st.button("➕ Add", key=f"add_{idx}", type="primary"):
                    st.session_state.selected_items.append(product.copy())
                    st.success(f"Added {qty} x {product.get('product_name', '')[:30]}")
        
        st.divider()

# --- Main App ---
st.markdown('<div class="main-header">📦 Toscee Buying Plan</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Inventory", "🌐 Scrape Brand", "📊 Buying Plan"])

# --- Tab 1: Inventory ---
with tab1:
    st.header("Inventory Browser")
    inventory = st.session_state.inventory_data
    total_products = inventory.get("total_inventory", 0)
    products = inventory.get("products", [])

    st.write(f"**Total Products:** {total_products}")

    if not products:
        st.warning("No inventory data found. Please ensure `inventory_with_images.json` exists.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            brands = get_inventory_brands(inventory)
            selected_brand = st.selectbox("Filter by Brand", ["All"] + brands)
        with col2:
            if selected_brand != "All":
                depts = get_inventory_departments(inventory, selected_brand)
                selected_dept = st.selectbox("Filter by Department", ["All"] + depts)
            else:
                selected_dept = "All"
        with col3:
            search_term = st.text_input("🔍 Search products", placeholder="Search by name...")

        # Filter products
        filtered = products
        if selected_brand != "All":
            filtered = [p for p in filtered if (p.get("brand") or "").lower() == selected_brand.lower()]
        if selected_dept != "All":
            filtered = [p for p in filtered if (p.get("department") or "").lower() == selected_dept.lower()]
        if search_term:
            filtered = [p for p in filtered if search_term.lower() in (p.get("product_name") or "").lower()]

        st.write(f"Showing **{len(filtered)}** products")

        # Display products
        for idx, product in enumerate(filtered):
            render_product_card(product, idx)

# --- Tab 2: Scrape Brand ---
with tab2:
    st.header("Scrape New Brand")
    st.write("Enter a brand website URL to scrape product data.")

    with st.form("scrape_form"):
        brand_url = st.text_input("Website URL", placeholder="https://example.com")
        brand_name_override = st.text_input("Brand Name (optional)", placeholder="Auto-detected from URL")
        submitted = st.form_submit_button("🔍 Scrape Website")

        if submitted and brand_url:
            with st.spinner(f"Scraping {brand_url}..."):
                result = scrape_brand_by_url(brand_url, brand_name_override or None)
                st.session_state.scrape_results = result

    if st.session_state.scrape_results:
        result = st.session_state.scrape_results
        st.subheader(f"Results: {result.get('brand_name', 'Unknown')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", result.get("scrape_status", "unknown"))
        with col2:
            st.metric("Products Found", result.get("products_scraped", 0))
        with col3:
            st.metric("Method", result.get("scrape_method", "none"))

        if result.get("products"):
            st.write("### Scraped Products Preview")
            for p in result["products"][:10]:
                st.write(f"- {p.get('product_name', 'N/A')} | Price: {p.get('price_mrp', 'N/A')}")

# --- Tab 3: Buying Plan ---
with tab3:
    st.header("Buying Plan Generator")
    st.write(f"**Selected Items:** {len(st.session_state.selected_items)}")

    if st.session_state.selected_items:
        # Summary table
        st.write("### Selected Products")
        summary_data = []
        total_qty = 0
        for item in st.session_state.selected_items:
            qty = item.get("quantity", 0)
            total_qty += qty
            summary_data.append({
                "Product": item.get("product_name", ""),
                "Brand": item.get("matched_brand", item.get("brand", "")),
                "MRP": item.get("mrp", ""),
                "Qty": qty,
            })
        st.dataframe(summary_data, use_container_width=True)
        st.write(f"**Total Quantity:** {total_qty}")

        # Budget input
        col1, col2 = st.columns(2)
        with col1:
            total_budget = st.number_input("Total Budget (INR)", min_value=0, value=100000, step=1000)
        with col2:
            st.write("")
            st.write("")
            generate_btn = st.button("📥 Generate Excel", type="primary")

        if generate_btn:
            with st.spinner("Generating Excel file..."):
                excel_data, filename = generate_buying_plan_excel(
                    st.session_state.selected_items, total_budget
                )
                st.download_button(
                    label="📥 Download Buying Plan Excel",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success(f"Excel generated: {filename}")

        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_items = []
            st.rerun()
    else:
        st.info("No products selected yet. Go to the **Inventory** tab to select products.")

# --- Footer ---
st.divider()
st.caption("Toscee Buying Plan App | Powered by Streamlit")