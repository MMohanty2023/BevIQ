# BevIQ project guide

## Purpose and architecture
BevIQ is a Python/Flask application for general conversation and beverage-data analysis. The backend is defined in app.py and the web interface in templates/index.html. The browser sends chat messages and optional uploads to POST /api/chat. engines/rag_orchestrator.py routes requests and maintains recent conversation context per session.

General questions, coding explanations, writing and follow-up conversation use the local Ollama text model. Project explanations use this guide and safe runtime configuration. Product and identifier questions use database retrieval; retrieved records are the evidence for data answers.

## Database, datasets and audit
database/db_manager.py prefers configured MySQL and falls back to local SQLite when MySQL is unavailable. GET /api/db-status and the app UI report the active backend; configuration alone does not prove MySQL is connected. DBeaver is an optional database client, not the database engine or an app runtime dependency. These files do not prove whether someone previously used DBeaver.

The project works with AllBrand, Supplier, AI Master Brand, Beer, RTD, Spirits, Wine and trained-brand datasets configured in config.py. engines/sql_engine.py handles catalog searches; data_ingestion/loader.py handles ingestion and data_ingestion/normalizer.py normalizes identifiers/UPCs. engines/comparison_engine.py compares datasets. engines/upc_match_engine.py performs UPC-first review and conservative product matching. Original CSVs/master data are not overwritten by review reports. Do not infer live row counts or product facts from this guide; use the actual database/query result.

## Interface and reports
Untrained Dataset selects rows labelled New or NeedToVerify in the category sheets. Its Dataset Records card counts unique brand/category pairs and its Unique Brands card counts distinct brand names before the 250-row display limit; both follow the brand search. Repeated brand/category pairs are shown once even across source rows, while the same brand in a different category remains a separate row. Brand matching ignores case and outer spaces; the first matching source row supplies the displayed name and source. This view does not compare trained records or UPCs.

The AI Assistant navigation tab opens the full chat page. Its floating toggle (bottom-right by default) opens a smaller window over the current page. Drag the window header to move it, or drag any edge or corner to resize it. The same toggle docks inside the window header as Close Assistant; use it or Escape to close floating chat. There are no separate minimize, maximize or close controls. The window size/position, chat history, draft and selected attachment remain in place when closing and reopening it or changing pages. When chat is closed, drag its launcher to reposition it; that launcher position is remembered in this browser across refresh. The Dashboard is the initial page. Both themes use a compact header and readable logo; dataset tables have fixed headings and layouts adapt to mobile screens.

The navigation exposes Dashboard, Supplier Overview, AI Assistant, Product Details (Master Brand Search), Trained/Untrained Dataset views, and PD Comparison Studio. PD Comparison Studio presents cross-dataset comparisons and audit results. Reports can be exported as CSV through app endpoints. Dashboard data comes from backend queries; generated reports are stored under generated_reports/.

## Uploaded documents and photos
document_rag.py ingests supported PDFs, DOCX, text, CSV and spreadsheets into session-scoped document retrieval with source references. Text extraction from a PDF depends on readable text in the PDF; scanned PDF pages are not automatically equivalent to the photo-vision path.

engines/image_chat.py validates photos, normalizes pixels, saves images per session and sends the actual picture to the local vision model. Photos do not need readable writing. A user can ask for visible details, a caption or a poem, then ask follow-up questions. Image analysis runs with num_gpu=0. Document attachments and catalog queries keep their own routes rather than reusing an unrelated old photo.

## Offline operation and future deployment
Ollama must be running, with text and vision model weights downloaded once during connected setup. After that, local general conversation, catalog/document retrieval and image inference work without an internet connection or a cloud API key. Both model request paths explicitly use num_gpu=0. Offline generation does not provide live internet facts or guarantee ChatGPT-level accuracy or response speed.

OLLAMA_HOST points from the Flask backend to Ollama. For separate deployment containers, use the internal Ollama service address rather than assuming localhost reaches another container. Keep database, uploads, indexes and model weights on persistent storage and allow sufficient RAM and request timeouts. See README.md for setup and environment settings. CPU photo analysis on the current 8 GB laptop was measured around 75–90 seconds, depending on the request; this is an observation, not a deployment guarantee.

## Conversation behavior and boundaries
Answer in the latest requested language/style: English, Hindi or Hinglish. Use recent session messages to understand follow-ups. Respond naturally to unrelated general questions instead of forcing beverage content into them. Be clear when a project detail, record or external fact is not available. Chat replies do not themselves edit project files, execute suggested commands or browse the internet. Configuration credentials and secret environment values are not included in project knowledge.
