# 🛍️ Startsida Buying Plan Generator

Streamlit web app to generate buying plan Excel files for Startsida store.

## Features

- **📋 Browse Brands** — View all brands and their products from the catalog
- **➕ Add Brand** — Enter any brand URL, scrape products (Shopify API + HTML fallback)
- **🛒 Create Buying Plan** — Select brands → Category → Subcategory → Pick products + quantities
- **📥 Download Excel** — Generate formatted Excel with master sheet + one sheet per brand

## How to Deploy (Streamlit Cloud — Free, Always-On)

### Step 1: Create a GitHub Account
1. Go to [github.com](https://github.com) and sign up (free)
2. Verify your email

### Step 2: Create a Repository
1. Click the **+** icon (top right) → **New repository**
2. Repository name: `startsida-buying-plan`
3. Set visibility: **Public** (required for free Streamlit Cloud)
4. Click **Create repository**

### Step 3: Upload Files
Upload these 4 files to the repository:
- `streamlit_app.py`
- `utils.py`
- `requirements.txt`
- `brand_catalogs.json`

**How to upload:**
1. In your new GitHub repo, click **Add file** → **Upload files**
2. Drag & drop the 4 files from `po-analytics/buying_plan_app/` folder
3. Click **Commit changes**

### Step 4: Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **New app**
4. Select: `your-username/startsida-buying-plan`
5. Branch: `main`
6. Main file path: `streamlit_app.py`
7. Click **Deploy**

Wait 2-3 minutes. Your app will be live at:
`https://your-username-startsida-buying-plan.streamlit.app`

### Step 5: Share with Your Colleague
Send them the URL above. They open it in any browser — no installation needed.

## How to Update the Catalog Data

When you run your pipeline and update `brand_catalogs.json`:

1. Download the latest `brand_catalogs.json` from your GitHub repo
2. Replace it with your updated file
3. Upload back to the repo (Add file → Upload files → replace existing)
4. Streamlit Cloud auto-redeploys within seconds

## Running Locally (for testing)

```bash
cd po-analytics/buying_plan_app
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Category Structure

| Category | Subcategories |
|---|---|
| **Apparel** | Sarees, Dresses, Kurta Sets, Tops, Co-ord Sets, Kaftans, Ethnic Wear |
| **Jewellery** | Earrings, Necklaces, Bracelets & Bangles, Rings, Maang Tikka |
| **Fragrances** | Perfumes, Candles, Incense |
| **Bags** | Bags |
| **Home Decor** | Bowls & Dips, Plates & Platters, Mugs, Coasters, Vases & Sculptures, Table Runners |
| **Accessories** | Belts, Scarves & Stoles |
| **Gifting** | Gift Sets, Stationery |