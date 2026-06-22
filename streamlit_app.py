"""
Toscee Buying Plan App - Streamlit Frontend
=============================================
3 tabs: Brands, Add Brand, Download
Uses inventory_with_images.json as the product catalog (766 items with images).
"""
import streamlit as st
import pandas as pd
from buying_plan_utils import (
    load_catalog, get_brand_list,
    load_inventory, get_inventory_brands, get_inventory_departments,
    get_inventory_products, get_inventory_summary,
    CATEGORY_MAP, ALL_SUBCATEGORIES,
    get_subcategory_for_product, get_category_for_subcategory,
    product_matches_subcategory, scrape_brand_by_url,
    generate_buying_plan_excel,
)

st.set_page_config(
    page_title="Toscee - Buying Plan Generator",
    page_icon="🛍️",
    layout="wide",
)

# ── Custom CSS for Product Cards & Tables ──────────────────────────────────────
st.markdown("""
<style>
.product-card {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 16px;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    transition: box-shadow 0.2s;
    height: 100%;
    display: flex;
    flex-direction: column;
}
.product-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}
.product-card img {
    width: 100%;
    height: 150px;
    object-fit: cover;
    border-radius: 8px;
    margin-bottom: 10px;
}
.product-card .product-name {
    font-size: 13px;
    font-weight: 600;
    color: #1a202c;
    margin-bottom: 4px;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.product-card .product-price {
    font-size: 15px;
    font-weight: 700;
    color: #2d3748;
    margin-bottom: 4px;
}
.product-card .product-brand {
    font-size: 11px;
    color: #718096;
    margin-bottom: 8px;
}
.product-card .qty-row {
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid #edf2f7;
}
.edit-plan-table {
    width: 100%;
    border-collapse: collapse;
}
.edit-plan-table th {
    background: #667EEA;
    color: white;
    padding: 10px 12px;
    text-align: left;
    font-size: 13px;
}
.edit-plan-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
    font-size: 13px;
}
.edit-plan-table tr:hover {
    background: #f7fafc;
}
</style>
""", unsafe_allow_html=True)

# ── Password Protection ──────────────────────────────────────────────────────
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "toscee@1234")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 120px auto 0;
        padding: 40px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.1);
        text-align: center;
    }
    .login-logo { font-size: 48px; margin-bottom: 10px; }
    .login-title { font-size: 24px; font-weight: 700; color: #2d3748; margin-bottom: 6px; }
    .login-subtitle { font-size: 14px; color: #718096; margin-bottom: 24px; }
    </style>
    <div class="login-container">
        <div class="login-logo">🛍️</div>
        <div class="login-title">Toscee</div>
        <div class="login-subtitle">Buying Plan Generator · Enter password to continue</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            password_input = st.text_input(
                "Password", type="password", placeholder="Enter password",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("🔓 Unlock", type="primary", use_container_width=True)
            if submitted:
                if password_input == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Try again.")
    st.stop()

# ── Session State ────────────────────────────────────────────────────────────
if "inventory" not in st.session_state:
    st.session_state.inventory = load_inventory()
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "gen_excel" not in st.session_state:
    st.session_state.gen_excel = None
if "gen_filename" not in st.session_state:
    st.session_state.gen_filename = None
if "last_scrape_result" not in st.session_state:
    st.session_state.last_scrape_result = None
if "scrape_in_progress" not in st.session_state:
    st.session_state.scrape_in_progress = False

inventory = st.session_state.inventory

# ── Helper Functions ─────────────────────────────────────────────────────────

def get_all_brand_names():
    return get_inventory_brands(inventory)

def find_brand_data(brand_name):
    """Get summary info for a brand from inventory."""
    return get_inventory_summary(inventory, brand_name)

def reset_selection():
    st.session_state.selected_items = []
    st.session_state.gen_excel = None
    st.session_state.gen_filename = None

# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.markdown("## 🛍️ Toscee")
st.sidebar.markdown("### Buying Plan Generator")
st.sidebar.markdown("---")

brands_list = get_all_brand_names()
total_inv = inventory.get("total_inventory", 0)
st.sidebar.metric("Brands Available", len(brands_list))
st.sidebar.metric("Total Products", total_inv)

if st.session_state.selected_items:
    total_qty = sum(item.get("quantity", 0) for item in st.session_state.selected_items)
    st.sidebar.metric("Plan Items Selected", len(st.session_state.selected_items))
    st.sidebar.metric("Plan Total Units", total_qty)

st.sidebar.markdown("---")
st.sidebar.caption("🔒 Password protected")

# ── Header ───────────────────────────────────────────────────────────────────

st.title("🛍️ Toscee - Buying Plan Generator")
st.markdown("Gulshan Mall, Noida")

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_brands, tab_add, tab_download = st.tabs([
    "📋 Brands", "➕ Add Brand", "📥 Download"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Browse Brands — Product Grid with Quantity Picker & Buying Plan
# ═══════════════════════════════════════════════════════════════════════════════

with tab_brands:
    st.subheader("Browse Inventory Products")
    all_brands = get_all_brand_names()
    if not all_brands:
        st.info("No inventory data found. Check the inventory_with_images.json file.")
    else:
        col_brand, col_cat = st.columns([2, 1])
        with col_brand:
            selected_brand = st.selectbox("Select a brand:", all_brands, key="browse_brand_select")
        with col_cat:
            brand_departments = get_inventory_departments(inventory, selected_brand)
            dept_options = ["All Departments"] + brand_departments
            selected_dept_filter = st.selectbox("Filter by department:", dept_options, key="browse_dept_filter")

        brand_summary = find_brand_data(selected_brand)
        if brand_summary:
            col1, col2, col3 = st.columns(3)
            col1.metric("Brand", selected_brand)
            col2.metric("Departments", len(brand_summary.get("departments", [])))
            col3.metric("Products", brand_summary["products_scraped"])
            st.markdown(f"**Departments:** {', '.join(brand_summary.get('departments', []))}")
            st.markdown("---")

            # Get products
            products = get_inventory_products(inventory, selected_brand)
            if not products:
                st.warning("No products found for this brand.")
            else:
                # Filter by department
                if selected_dept_filter and selected_dept_filter != "All Departments":
                    products = [p for p in products if (p.get("department", "") or "").lower() == selected_dept_filter.lower()]

                st.subheader(f"Products ({len(products)}) — Set quantities below")

                # ── Product Grid with Qty Inputs ──
                with st.form(key="brand_qty_form"):
                    cols_per_row = 4
                    selections = {}
                    for row_start in range(0, len(products), cols_per_row):
                        row_products = products[row_start:row_start + cols_per_row]
                        cols = st.columns(cols_per_row)
                        for idx, p in enumerate(row_products):
                            pname = p.get("item_name", p.get("matched_product", ""))
                            price = p.get("mrp", 0) or 0
                            img_url = p.get("image_url", "") or ""
                            style_code = p.get("item_code", "")
                            color = p.get("category_3", "")
                            dept = p.get("department", "")
                            global_idx = row_start + idx
                            with cols[idx]:
                                img_html = f'<img src="{img_url}" alt="{pname}" onerror="this.style.display=\'none\'">' if img_url else '<div style="height:150px;background:#f7fafc;border-radius:8px;margin-bottom:10px;display:flex;align-items:center;justify-content:center;color:#a0aec0;font-size:40px;">📦</div>'
                                card_html = f"""
                                <div class="product-card">
                                    {img_html}
                                    <div class="product-name" title="{pname}">{pname[:80]}{'…' if len(pname) > 80 else ''}</div>
                                    <div class="product-price">₹{float(price):,.0f}</div>
                                    <div class="product-brand">{dept}{' · ' + color if color else ''}</div>
                                    <div class="qty-row">
                                </div>
                                """
                                st.markdown(card_html, unsafe_allow_html=True)
                                qty_val = st.number_input("Qty", min_value=0, max_value=999, value=0, key=f"qty_card_{selected_brand}_{global_idx}", label_visibility="collapsed")
                                selections[global_idx] = {"qty": qty_val, "product": p, "department": dept}

                    add_cols = st.columns([1, 3])
                    with add_cols[0]:
                        submitted = st.form_submit_button("✅ Add Selected to Plan", type="primary", use_container_width=True)

                if submitted:
                    added_count = 0
                    for gidx, sel in selections.items():
                        if sel["qty"] > 0:
                            p = sel["product"]
                            dept = sel["department"]
                            # Check if this item already exists in the plan (by item_code)
                            existing_idx = None
                            for ei, item in enumerate(st.session_state.selected_items):
                                if item.get("item_code") == p.get("item_code", ""):
                                    existing_idx = ei
                                    break
                            if existing_idx is not None:
                                st.session_state.selected_items[existing_idx]["quantity"] += sel["qty"]
                            else:
                                p_copy = dict(p)
                                p_copy["quantity"] = sel["qty"]
                                p_copy["matched_brand"] = selected_brand
                                st.session_state.selected_items.append(p_copy)
                            added_count += 1
                    if added_count > 0:
                        st.success(f"✅ Added {added_count} product(s) to the buying plan!")
                        st.session_state.gen_excel = None
                        st.session_state.gen_filename = None
                        st.rerun()
                    else:
                        st.warning("No products selected (all quantities were 0).")

        # ── Current Plan Section ──
        st.markdown("---")
        if st.session_state.selected_items:
            st.subheader(f"📋 Current Buying Plan ({len(st.session_state.selected_items)} items)")
            st.markdown("**Edit quantities below, then click 'Update Quantities' to save changes.**")

            with st.form(key="edit_plan_form"):
                header_cols = st.columns([0.3, 1.2, 1.5, 2.5, 1, 1, 0.8])
                header_cols[0].markdown("**#**")
                header_cols[1].markdown("**Image**")
                header_cols[2].markdown("**Brand**")
                header_cols[3].markdown("**Product**")
                header_cols[4].markdown("**Price**")
                header_cols[5].markdown("**Dept**")
                header_cols[6].markdown("**Qty**")

                st.markdown("<hr style='margin:2px 0;border-color:#667EEA;'>", unsafe_allow_html=True)

                remove_items = []
                for idx, item in enumerate(st.session_state.selected_items):
                    cols = st.columns([0.3, 1.2, 1.5, 2.5, 1, 1, 0.8])
                    cols[0].write(f"{idx+1}")
                    img_url = item.get("image_url", "")
                    if img_url:
                        cols[1].markdown(f'<a href="{img_url}" target="_blank"><img src="{img_url}" style="width:45px;height:45px;object-fit:cover;border-radius:6px;" onerror="this.style.display=\'none\'"></a>', unsafe_allow_html=True)
                    else:
                        cols[1].markdown("📦")
                    cols[2].write(item.get("matched_brand", ""))
                    pname = item.get("item_name", item.get("matched_product", ""))
                    cols[3].write(pname[:50])
                    mrp = float(item.get("mrp", 0) or 0)
                    cols[4].write(f"₹{mrp:,.0f}" if mrp else "N/A")
                    cols[5].write(item.get("department", ""))
                    new_qty = cols[6].number_input("", min_value=0, max_value=999, value=item.get("quantity", 0), key=f"edit_qty_{idx}", label_visibility="collapsed")

                    if new_qty != item.get("quantity", 0):
                        item["quantity"] = new_qty
                    if new_qty == 0:
                        remove_items.append(idx)

                st.markdown("---")
                update_cols = st.columns([1, 1, 3])
                with update_cols[0]:
                    save_clicked = st.form_submit_button("💾 Update Quantities", type="primary", use_container_width=True)
                with update_cols[1]:
                    clear_clicked = st.form_submit_button("🗑️ Clear All", type="secondary", use_container_width=True)

            if save_clicked:
                if remove_items:
                    for idx in reversed(remove_items):
                        if idx < len(st.session_state.selected_items):
                            st.session_state.selected_items.pop(idx)
                    st.success(f"Removed {len(remove_items)} item(s) with quantity 0.")
                st.session_state.gen_excel = None
                st.session_state.gen_filename = None
                st.rerun()

            if clear_clicked:
                reset_selection()
                st.rerun()

            total_qty = sum(item.get("quantity", 0) for item in st.session_state.selected_items)
            st.metric("Total Units in Plan", total_qty)
        else:
            st.info("No items in buying plan yet. Select a brand above, set quantities on products, and click **Add Selected to Plan**.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Add Brand
# ═══════════════════════════════════════════════════════════════════════════════

with tab_add:
    st.subheader("Scrape a Brand (Experimental)")
    st.markdown("Enter a brand website URL to scrape its products. *(Legacy feature — main catalog comes from inventory data.)*")
    col1, col2 = st.columns([3, 1])
    with col1:
        brand_url = st.text_input("Brand Website URL", placeholder="e.g. https://brandname.com", key="add_url")
    with col2:
        brand_name_override = st.text_input("Brand Name (optional)", placeholder="Auto-detected", key="add_name")

    if st.button("🔍 Scrape Brand", type="primary", disabled=st.session_state.scrape_in_progress):
        if not brand_url:
            st.error("Please enter a URL.")
        else:
            st.session_state.scrape_in_progress = True
            with st.spinner("Scraping products... This may take up to 30 seconds."):
                result = scrape_brand_by_url(brand_url.strip(), brand_name=brand_name_override.strip() or None)
                st.session_state.last_scrape_result = result
                if result["products_scraped"] > 0:
                    bn = result["brand_name"]
                    st.success(f"✅ Scraped **{bn}** — {result['products_scraped']} products found ({result['scrape_method']})")
                    subcat_counts = {}
                    for p in result["products"]:
                        sc = get_subcategory_for_product(p)
                        subcat_counts[sc] = subcat_counts.get(sc, 0) + 1 if sc else subcat_counts.get("Unmatched", 0) + 1
                    with st.expander(f"📦 Product breakdown for {bn}", expanded=True):
                        for sc, count in sorted(subcat_counts.items()):
                            st.write(f"- **{sc}**: {count} products")
                        st.write(f"**Total**: {result['products_scraped']} products")
                else:
                    st.error("⚠️ Could not extract products from this website.")
            st.session_state.scrape_in_progress = False

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Download
# ═══════════════════════════════════════════════════════════════════════════════

with tab_download:
    st.subheader("Download Buying Plan Excel")
    if not st.session_state.selected_items:
        st.info("No items in the buying plan yet. Go to the **Brands** tab to select products and set quantities.")
    else:
        total_qty = sum(item.get("quantity", 0) for item in st.session_state.selected_items)
        st.metric("Items in Plan", len(st.session_state.selected_items))
        st.metric("Total Units", total_qty)
        st.markdown("### Plan Summary by Brand")
        brand_summary = {}
        for item in st.session_state.selected_items:
            bn = item.get("matched_brand", item.get("brand", "Unknown"))
            if bn not in brand_summary:
                brand_summary[bn] = {"items": 0, "qty": 0}
            brand_summary[bn]["items"] += 1
            brand_summary[bn]["qty"] += item.get("quantity", 0)
        for bn, info in sorted(brand_summary.items()):
            st.write(f"- **{bn}**: {info['items']} products, {info['qty']} units")
        total_budget = st.number_input("Total Budget (for display in Excel):", min_value=1, max_value=99999, value=max(total_qty, 4000), key="dl_budget")
        if st.button("📥 Generate & Download Excel", type="primary"):
            with st.spinner("Generating Excel..."):
                excel_bytes, filename = generate_buying_plan_excel(st.session_state.selected_items, total_budget)
                st.session_state.gen_excel = excel_bytes
                st.session_state.gen_filename = filename
                st.success(f"✅ Excel generated: {filename}")
        if st.session_state.gen_excel:
            st.download_button(label="⬇️ Click to Download Excel", data=st.session_state.gen_excel, file_name=st.session_state.gen_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
            st.info("The Excel contains:\n- **Buying Plan** sheet — Master overview with all columns\n" f"- **{len(brand_summary)} brand sheet(s)** — One per brand")
            if st.button("🔄 Reset & Start New Plan"):
                reset_selection()
                st.rerun()
