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

An enterprise-grade, locally running, 100% offline AI Assistant and Data Comparison Engine built with **Flask**, **Pandas**, **MySQL Connector/Python**, **SQLite WAL**, and **Local Vector Search**, specifically designed for large-scale beverage company data management (over **702,000+ product records** across 7 CSV files).

Uses **MySQL as the primary database** (default `127.0.0.1:3306`) with SQLite as a fallback, and supports local **Ollama** LLMs (e.g., `llama3.2`, `mistral`, `phi3`).

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

5. **DBeaver & MySQL Integration**:
   - Configured to use the local MySQL Server (default **port 3306**) and the `beverage_db` database. Set `MYSQL_PORT` in `.env` to override the port.
   - Built-in fallback to high-performance local SQLite (`beverage_data.sqlite3`), ensuring instant operation even before configuring MySQL credentials.

6. **Interactive Web Dashboard & CSV Reports**:
   - Modern, responsive Flask UI with chat interface, quick-prompt pills, live comparison filters, and one-click CSV report exports.

7. **Conversation-scoped Document RAG**:
   - Attach PDF, DOCX, TXT/MD, CSV, XLSX, or image files directly in chat.
   - Ask follow-up questions against uploaded documents with page/sheet source references.
   - Image chat uses the local CPU-only vision model, so photos do not need to contain text.
   - Ask for a detailed description, a caption, or a poem inspired by the image. Follow-ups such as "Make it shorter" reuse the image while that image is the conversation topic.
   - Image uploads stay under `generated_reports/uploads/images/` and are scoped to their chat session. PDF/DOCX/text extraction keeps its existing document flow.

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

### MySQL connection
MySQL is the primary backend. The default local target is `127.0.0.1:3306`.
Set `MYSQL_PASSWORD` in the project `.env` file to the password for the configured
MySQL user. Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, or `MYSQL_DB` there if
your server uses different connection settings. Do not commit `.env`.

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

## 🐬 Connecting DBeaver to MySQL

The application connects to MySQL directly; DBeaver is a separate desktop
client and does not connect through BevIQ. Both can connect to the configured
MySQL server; the default is `127.0.0.1:3306`. Set the MySQL credentials in
`.env` before starting the app.
If the beverage tables are not yet in MySQL, the migration utility can create
them from the source CSVs. From the project directory, run
`python database\mysql_migrator.py`. The utility checks that all seven CSV
files are available before connecting and will not replace existing tables by
default. To intentionally replace matching tables, back them up and run
`python database\mysql_migrator.py --replace-existing`.

### DBeaver Connection Settings:
- **Database Driver**: `MySQL`
- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `3306` (default; override with `MYSQL_PORT`)
- **Database**: `beverage_db`
- **Username**: `root`
- **Password**: The password configured in `.env` (never shown in the UI)
- **JDBC URL**: `jdbc:mysql://127.0.0.1:3306/beverage_db` (default)

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

## 🤖 Local Chat (Ollama)

Database lookups and reports work without Ollama. Natural, open-ended chat uses
Ollama locally, and the assistant includes recent turns so follow-up questions
can refer to the conversation. Chat data is not sent to a cloud AI service.

1. Install Ollama from [ollama.com](https://ollama.com/).
2. In PowerShell, run the configured model (the default is `llama3.2`):
   ```powershell
   ollama run llama3.2
   ```
   Keep Ollama running while chatting. The first run downloads the model.
3. If you use another model or Ollama host, set `OLLAMA_MODEL` or `OLLAMA_HOST`
   in the project's `.env` file and run that model with Ollama.

If Ollama is unavailable or the configured model is missing, the chat response
shows a setup hint; catalog and document features remain available.

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
│   ├── db_manager.py           # MySQL-primary manager with SQLite fallback
│   └── mysql_migrator.py       # MySQL table builder & data loader
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

## Offline image chat and CPU deployment

Install Ollama on the machine that will run inference. While internet is available, download both models once:

```sh
ollama pull llama3.2
ollama pull qwen3-vl:2b-instruct
```

Start Ollama and this application normally. After the weights are present, ordinary chat and image inference use local Ollama without internet or an API key. Requests explicitly set `num_gpu=0`; no GPU is required. Attaching a photo no longer depends on Tesseract or readable text.

Example: attach a landscape, animal photo, or artwork and ask, "Describe this picture in detail and add a four-line poem inspired by it." Ask "Make it shorter" to refine that response, or explicitly refer to the picture later. Starting an unrelated topic stops implicit image follow-ups from using an old picture.

Settings in `.env` / environment variables:

| Setting | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama address reachable by the Flask backend |
| `OLLAMA_MODEL` | `llama3.2` | Ordinary conversation model |
| `OLLAMA_VISION_MODEL` | `qwen3-vl:2b-instruct` | Local vision model |
| `OLLAMA_VISION_TIMEOUT` | `300` | CPU generation timeout in seconds |
| `OLLAMA_VISION_MAX_TOKENS` | `512` | Maximum image-answer length; larger values take longer |
| `OLLAMA_VISION_IMAGE_SIZE` | `512` | Maximum image edge sent to vision; larger values retain more detail but take longer |

For future deployment:
- Run Ollama on the CPU host, or in a separate CPU service reachable through `OLLAMA_HOST`. Inside a container, `localhost` refers to that container; use the Ollama service name when they are separate.
- Preload models during connected setup and retain Ollama's model directory on persistent storage. Chat requests never download models automatically.
- Persist `db_storage/`, `generated_reports/uploads/`, and the existing catalog/index storage across app restarts. This keeps image ownership and conversation history together.
- Use a production WSGI server and reverse proxy with a request timeout longer than `OLLAMA_VISION_TIMEOUT` (for example 360 seconds). Start with one app worker and bounded concurrency on a small CPU host; the image engine accepts one image-generation request per process at a time.
- Allow RAM for Python, the catalog database and the loaded model, not just the model download size. Validate resources on the target CPU host; low-memory free hosting may not fit. Cold starts and longer answers take more time.
- Offline operation applies to local chat, document/catalog retrieval and image inference. Existing integrations that access internet resources still need their own network connection.

If the image model is missing, the app gives a setup instruction. If Ollama is stopped, times out, or returns an empty reply, the app reports a service error instead of rejecting the photo for having no text.

Local validation on this 8 GB laptop: a real photo request asking for a detailed description plus a four-line poem completed in about 90 seconds, with zero GPU memory used. This is one observed cold-request timing, not a latency guarantee; CPU, available RAM, photo size and answer length change it. The default explicitly uses the instruct variant to avoid spending the answer budget on a thinking-only response.

## General conversation and project-aware answers

The same AI Assistant handles ordinary questions, coding explanations, writing and conversation as well as beverage records and uploaded content. It uses the installed local text model, recent session history and the latest requested English/Hindi/Hinglish style.

Examples:
- General: "Explain why rainbows form" or "Write a Python example for sorting a list".
- Project: "Explain my project architecture", "How does PD Comparison Studio work?" or "mere project ki working batao".
- Follow-up: "What database does it use?" after discussing the project.
- Data: "Find UPC 0852955008021", "Show Master Brand Kingfisher" or a missing-UPC comparison.
- Content: attach a PDF for document questions, or a photo for description/poetry.

Project explanations use the allowlisted `docs/assistant-project-guide.md` plus safe configuration facts and display those source filenames. Update the guide when project architecture changes. The assistant does not recursively index code, read credentials or include `.env` values in project context. Actual record/count requests retain database retrieval; uploaded-document questions retain their document source. A factual local project summary remains available if Ollama is stopped.

This is a local assistant with conversational behavior, not the ChatGPT service or a guarantee of equal capability. Offline models can make mistakes and do not have live internet knowledge. They should say when facts are unavailable rather than claim unperformed browsing, code execution or database access.

## Floating AI Assistant

The top navigation AI Assistant tab opens the full chat page. The floating AI Assistant toggle opens a smaller chat window over the current page. While that window is open, the same toggle docks in its header as Close Assistant without covering chat content. Close it with that toggle or Escape; chat history, draft and selected upload stay in place. There are no separate minimize, maximize or close buttons.

Move the floating window by dragging its header, and resize it from any edge or corner with the mouse or touch. Its size and position are retained while moving between pages or closing and reopening chat, and stay within the viewport after browser resizing. Keyboard users can focus the header and use arrow keys to move it, or focus the bottom-right resize handle and use arrow keys to resize; Shift uses larger steps.

When chat is closed, its floating launcher is also draggable. That launcher's position is saved in browser localStorage across refresh; dragging does not trigger chat open/close. The Dashboard is the initial page. Both themes use a compact header, a readable theme-aware logo, scrollable tables with fixed headings, and responsive desktop/mobile layouts.
