# BevIQ (Offline RAG & Beverage Comparison Engine)

## Current runtime behavior

- MySQL is the primary backend after a successful connection/configuration.
- SQLite is the automatic local fallback when MySQL is unavailable or has not
  been configured. The active backend is shown in the UI and `/api/db-status`.
- Search runs against indexed database tables; the application does not reload
  full CSV files for every question.
- Original CSV files are never overwritten. Use
  `python tools/optimize_csv.py SOURCE.csv OUTPUT.csv --columns ... --dedupe ...`
  to create a separate smaller derivative for offline exchange or Power BI.

## Dashboard and Power BI

The Dashboard tab reads live values from the active backend. Power BI can use
these read-only endpoints or import a CSV export:

- `GET /api/dashboard/overview`
- `GET /api/dashboard/categories`
- `GET /api/dashboard/missing-upc?limit=500`
- `GET /api/dashboard/export/<dataset>?limit=50000`

Export dataset names are `all_brands`, `suppliers`, `ai_master`, `cat_beer`,
`cat_rtd`, `cat_spirits`, and `cat_wine`.

## Complete ID lookup

Questions such as `Find details for ID 10245` or `Find UPC 0852955008021`
search exact identifiers, UPCs, alternate UPCs, and related dataset records.
Results include available database fields, source filenames, and source row
references. Unknown identifiers return a clear not-found response.

An enterprise-grade, locally running, 100% offline AI Assistant and Data Comparison Engine built with **Flask**, **Pandas**, **PyMySQL**, **SQLite WAL**, and **Local Vector Search**, specifically designed for large-scale beverage company data management (over **702,000+ product records** across 7 CSV files).

Supports integration with **DBeaver** on **MySQL localhost:3307** and local **Ollama** LLMs (e.g., `llama3.2`, `mistral`, `phi3`).

---

## 🌟 Key Capabilities

1. **100% Offline & Private**:
   - Zero external cloud APIs (no OpenAI, no cloud databases, no external network calls).
   - All models, databases, vector indexes, and query caches run strictly on your local computer.

2. **Smart UPC Recovery & Integrity Engine**:
   - Handles corrupted Excel scientific notation (e.g. `6.19947E+11`) by automatically extracting authentic 13-digit UPCs from the `Product` text column.
   - Strips `UPC=` prefixes, handles alternate barcodes, and preserves leading zeros (stored strictly as strings).

3. **Natural Language Question Answering (English & Hinglish)**:
   - Understands standard English and colloquial Hinglish (e.g., *"kya ye UPC 0852955008021 master data me hai?"*, *"Beer sheet me missing brands dikhao"*).
   - Routes queries automatically to exact SQL lookups, cross-sheet comparison engines, or semantic vector retrieval.

4. **Multi-Dataset Comparison Studio**:
   - Compares **AIMasterBrandData** against Categorization sheets (**Beer**, **RTDs**, **Spirits**, **Wine**).
   - Compares **AllBrand Master** against **Supplier Master Sheet** (`$Supplier_202610291521.csv`).
   - Validates **Beer vs. RTD** cross-categorization (identifying FABs, hard seltzers, and `NON RTD` tags).
   - Classifies every record into the 6 standard statuses:
     - 🟢 **Exact Match**
     - 🟡 **Partial Match**
     - 🔴 **Mismatch**
     - ⚪ **Missing Record**
     - 🟣 **Duplicate Record**
     - 🟠 **Requires Verification**
   - Shows source filename and original CSV row number for every match and mismatch.

5. **DBeaver & MySQL 3307 Integration**:
   - Pre-configured to sync all 7 datasets into MySQL Server on **port 3307** into the `beverage_db` database.
   - Built-in fallback to high-performance local SQLite (`beverage_data.sqlite3`), ensuring instant operation even before configuring MySQL credentials.

6. **Interactive Web Dashboard & CSV Reports**:
   - Modern, responsive Flask UI with chat interface, quick-prompt pills, live comparison filters, and one-click CSV report exports.

7. **Conversation-scoped Document RAG**:
   - Attach PDF, DOCX, TXT/MD, CSV, XLSX, or image files directly in chat.
   - Ask follow-up questions against uploaded documents with page/sheet source references.
   - Image OCR uses local Tesseract when installed; files stay under `generated_reports/uploads/`.

8. **Conservative Missing-UPC Product Matching**:
   - Checks AllBrand against Beer, RTD, Spirits, and Wine using brand/product/size similarity after exact and alternate UPC checks.
   - Runs UPC-first review across the categorization sheets, reports every bounded/full-review row, and exports review-only CSV data with suggested alternate UPCs; it never changes source data automatically.
   - Reports suggested UPCs with confidence and source rows; it never overwrites master data automatically.

---

## 📂 Dataset Profile (702,207 Total Records)

| File Name | Size | Total Rows | Columns | Primary Key / UPC Column |
| :--- | :--- | :--- | :--- | :--- |
| **`$ALLBrand_202610291524.csv`** | 113.3 MB | 189,619 | 45 | `UPCCode`, `AlternateUPCCode` |
| **`$Supplier_202610291521.csv`** | 2.0 MB | 16,784 | 11 | `SupplierCode`, `SupplierName` |
| **`AIMasterBrandData.csv`** | 46.0 MB | 189,752 | 22 | `UPCCode`, `AlternateUPCCode` |
| **`Categorization 2026 - Beer.csv`** | 11.6 MB | 50,441 | 16 | `UPC 13 digit` (recovered from `Product`) |
| **`Categorization 2026 - RTDs.csv`** | 23.4 MB | 153,026 | 10 | `UPC 13 digit` (recovered from `Product`) |
| **`Categorization 2026 - Spirits.csv`** | 8.4 MB | 41,554 | 16 | `UPC 13 digit` (recovered from `Product`) |
| **`Categorization 2026 - Wine.csv`** | 13.0 MB | 61,031 | 18 | `UPC 13 digit` (recovered from `Product`) |

---

## 🚀 Quick Start Guide

### 1. Requirements & Dependencies
Ensure Python 3.10+ is installed. Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Simply run the startup script:
```bash
python run.py
```
This automatically:
1. Validates or initializes the local SQLite database (`db_storage/beverage_data.sqlite3`).
2. Cleans and normalizes all 702k+ records and creates lookup indexes.
3. Builds the persistent local semantic vector index (`vector_indices/beverage_vector_index.pkl`).
4. Starts the web application on **http://127.0.0.1:5000**.

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🐬 Connecting DBeaver to MySQL Port 3307

The tool connects directly to MySQL running on `127.0.0.1:3307`.

### Method A: Through the Web Interface
1. Open the web app and click the **DBeaver & MySQL 3307** tab.
2. Enter your MySQL `root` password in the password field.
3. Click **"Test Connection"** or **"Migrate All 700k+ Records to MySQL 3307"**.

### Method B: Via Command Line Script
Run the migrator directly:
```bash
python database/mysql_migrator.py <YOUR_MYSQL_PASSWORD>
```

### DBeaver Connection Settings:
- **Database Driver**: `MySQL`
- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `3307`
- **Database**: `beverage_db`
- **Username**: `root`
- **Password**: `<your_root_password>`
- **JDBC URL**: `jdbc:mysql://127.0.0.1:3307/beverage_db`

**Tables Created for DBeaver Inspection**:
- `all_brands`
- `suppliers`
- `ai_master`
- `cat_beer`
- `cat_rtd`
- `cat_spirits`
- `cat_wine`

Each table includes indexed columns: `clean_upc`, `norm_brand`, `norm_supplier`, `source_file`, and `original_row`.

---

## 🤖 Local LLM (Ollama) Integration (Optional)

The application features a built-in **Deterministic Semantic Synthesis Engine** that operates with 100% precision without needing Ollama.

If you also wish to enable generative conversational answers:
1. Download Ollama from [ollama.com](https://ollama.com/).
2. Pull your model of choice:
   ```bash
   ollama run llama3.2
   ```
3. The application will automatically detect Ollama running on `http://localhost:11434` and update the status indicator to **Online**.

---

## 💬 Example Natural Language Queries

| Query Category | Example Prompt |
| :--- | :--- |
| **Exact UPC Lookup** | `"Find UPC 0852955008021 in master data"` |
| **Hinglish Availability** | `"kya ye UPC 0852955008021 master data me hai?"` |
| **Cross-File Comparison** | `"Compare Master Data with Beer categorization"` |
| **Supplier Audit** | `"Compare All Brand Sheet with Supplier Sheet"` |
| **Category Gap Analysis** | `"Find all UPCs available in Master but missing in Beer"` |
| **Beer vs. RTD Validation** | `"Compare Beer and RTD categorization"` |
| **Duplicate Audit** | `"Show duplicate UPCs across all files"` |
| **Product Match / Alternate UPC** | `"Check products where brand flavour size match but UPC is missing; suggest alternate UPC"` |
| **Category Aggregation** | `"Count total products in each category"` |
| **Brand Inquiry** | `"Show all products belonging to brand Michelob Ultra"` |
| **Supplier Inquiry** | `"Find all products with supplier Gallo"` |

---

## 🏗️ Architecture & Project Structure

```
beverage_db/
├── app.py                      # Flask Application & REST API
├── run.py                      # One-click startup & initialization script
├── config.py                   # Central configurations & dataset registry
├── requirements.txt            # Dependency specifications
├── README.md                   # Complete documentation
│
├── data_ingestion/
│   ├── normalizer.py           # UPC 13-digit recovery, prefix stripper & text cleaning
│   └── loader.py               # Streaming chunked CSV ingestion & SQLite WAL builder
│
├── database/
│   ├── db_manager.py           # Dual-backend manager (MySQL 3307 + SQLite)
│   └── mysql_migrator.py       # DBeaver MySQL 3307 table builder & data loader
│
├── engines/
│   ├── comparison_engine.py    # Multi-dataset comparison & mismatch classifier
│   ├── sql_engine.py           # Exact UPC, brand, supplier, and aggregation engine
│   ├── vector_engine.py        # Local persistent semantic vector index (BM25/TF-IDF)
│   └── rag_orchestrator.py     # Intent classification, context builder & synthesis
│
├── db_storage/
│   └── beverage_data.sqlite3   # High-speed local database with 702,207 indexed records
├── vector_indices/
│   └── beverage_vector_index.pkl # Persistent semantic search index
├── generated_reports/          # Exported CSV comparison reports
│
├── templates/
│   └── index.html              # Responsive HTML5 / Bootstrap 5 / Marked.js UI
└── static/                     # Custom styles and scripts
```

