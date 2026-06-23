"""
Toscee Buying Plan App - Streamlit Frontend
=============================================
Browse inventory from Toscee buying plan Excel, select products,
and generate buying plan Excel with images.
"""
import streamlit as st
import io
import os
import sys
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from buying_plan_utils import (
    load_inventory, get_inventory_brands,
    get_inventory_products, get_inventory_summary,
    generate_buying_plan_excel, scrape_brand_by_url
)
from load_buying_plan_excel import get_categories, get_sub_categories

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
    .product-card {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .image-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
        background: #f8f9fa;
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "inventory_data" not in st.session_state:
    st.session_state.inventory_data = load_inventory()
    data = st.session_state.inventory_data
    st.session_state.total_products = data.get("total_inventory", 0)
    st.session_state.products = data.get("products", [])
    print(f"Loaded {st.session_state.total_products} products from Excel")

if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = None

# --- Helper Functions ---
def render_product_card(product, idx):
    """Render a product selection card with image from URL and details."""
    with st.container():
        col_img, col_info, col_qty = st.columns([2, 3, 1])
        
        with col_img:
            image_url = product.get("image_url", "")
            image_displayed = False
            
            if image_url:
                try:
                    st.image(image_url, width=250, use_container_width=True)
                    image_displayed = True
                except Exception as e:
                    pass
            
            if not image_displayed:
                st.markdown(
                    '<div style="width:250px;height:200px;background:#f0f0f0;'
                    'display:flex;align-items:center;justify-content:center;'
                    'border-radius:8px;color:#999;">No Image</div>',
                    unsafe_allow_html=True
                )
        
        with col_info:
            brand = product.get("brand", "N/A")
            category = product.get("category", "")
            sub_category = product.get("sub_category", "")
            product_title = product.get("product_title", "N/A")
            style_code = product.get("style_code", "")
            color = product.get("color", "")
            size = product.get("size", "")
            mrp = product.get("mrp")
            material = product.get("material", "")
            gender = product.get("gender", "")
            
            st.write(f"**{product_title}**")
            st.write(f"**Brand:** {brand}")
            if category:
                st.write(f"**Group:** {category}" + (f" > {sub_category}" if sub_category else ""))
            st.write(f"**MRP:** ₹{mrp:,.2f}" if mrp else "**MRP:** N/A")
            if style_code:
                st.write(f"**SKU:** {style_code}")
            if color:
                st.write(f"**Color:** {color}")
            if size:
                st.write(f"**Size:** {size}")
            if material:
                st.write(f"**Material:** {material}")
            if gender:
                st.write(f"**Gender:** {gender}")
        
        with col_qty:
            qty = st.number_input(
                "Qty", min_value=0, max_value=100, value=0,
                key=f"qty_{idx}_{product.get('product_title', '')[:20]}"
            )
            product["quantity"] = qty
            if qty > 0:
                if st.button("➕ Add to Plan", key=f"add_{idx}", type="primary"):
                    st.session_state.selected_items.append(product.copy())
                    st.success(f"Added {qty} x {product.get('product_title', '')[:30]}")
        
        st.divider()

# --- Main App ---
st.markdown('<div class="main-header">📦 Toscee Buying Plan</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Inventory", "🌐 Scrape Brand", "📊 Buying Plan"])

# --- Tab 1: Inventory ---
with tab1:
    st.header("Inventory Browser")
    inventory = st.session_state.inventory_data
    total_products = st.session_state.total_products
    products = st.session_state.products

    st.write(f"**Total Products:** {total_products}")

    if not products:
        st.warning("No inventory data found. Ensure `Toscee_buying_plan.xlsx` exists in the app directory.")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            brands = get_inventory_brands(inventory)
            selected_brand = st.selectbox("Filter by Brand", ["All"] + brands)
        with col2:
            if selected_brand != "All":
                cats = get_categories(inventory, selected_brand)
                selected_cat = st.selectbox("Filter by Group", ["All"] + cats)
            else:
                cats = get_categories(inventory)
                selected_cat = st.selectbox("Filter by Group", ["All"] + cats)
        with col3:
            if selected_brand != "All" and selected_cat != "All":
                subs = get_sub_categories(inventory, selected_brand, selected_cat)
                selected_sub = st.selectbox("Filter by Sub Group", ["All"] + subs)
            else:
                selected_sub = "All"
        
        search_term = st.text_input("🔍 Search products", placeholder="Search by name or SKU...")

        # Filter products
        filtered = products
        if selected_brand != "All":
            filtered = [p for p in filtered if (p.get("brand") or "").lower() == selected_brand.lower()]
        if selected_cat != "All":
            filtered = [p for p in filtered if (p.get("category") or "").lower() == selected_cat.lower()]
        if selected_sub != "All":
            filtered = [p for p in filtered if (p.get("sub_category") or "").lower() == selected_sub.lower()]
        if search_term:
            search_lower = search_term.lower()
            filtered = [
                p for p in filtered
                if search_lower in (p.get("product_title") or "").lower()
                or search_lower in (p.get("style_code") or "").lower()
            ]

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
        total_value = 0
        for item in st.session_state.selected_items:
            qty = item.get("quantity", 0) or 0
            mrp = item.get("mrp") or 0
            total_qty += qty
            total_value += mrp * qty
            summary_data.append({
                "Product": item.get("product_title", ""),
                "Brand": item.get("brand", ""),
                "Group": item.get("category", ""),
                "MRP": mrp,
                "Qty": qty,
                "Total": mrp * qty,
            })
        st.dataframe(summary_data, use_container_width=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"**Total Quantity:** {total_qty}")
        with col_b:
            st.write(f"**Total Value:** ₹{total_value:,.2f}")

        # Budget input
        col1, col2 = st.columns(2)
        with col1:
            total_budget = st.number_input("Total Budget (INR)", min_value=0, value=max(total_value, 100000), step=1000)
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