"""
Generate a comprehensive project documentation PDF for Beverage Data Assistant.
Usage: python tools/generate_project_pdf.py
"""

import os, sys
from datetime import datetime

try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    os.system("pip install fpdf2 -q")
    from fpdf import FPDF

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
OUT = os.path.join(REPORT_DIR, f"BevIQ_Project_Documentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BLUE  = (31, 73, 125)
MID_BLUE   = (52, 111, 176)
LIGHT_BLUE = (217, 230, 245)
ORANGE     = (213, 108, 20)
GREEN      = (55, 86, 35)
LIGHT_GRAY = (245, 245, 245)
WHITE      = (255, 255, 255)
BLACK      = (0, 0, 0)
DARK_GRAY  = (60, 60, 60)


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_left_margin(18)
        self.set_right_margin(18)
        self._page_num_offset = 0

    # ── Header ─────────────────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return  # cover page has its own header
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, 0, 210, 12, 'F')
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.set_xy(18, 3)
        self.cell(0, 6, "BevIQ -- Beverage Data Assistant | Project Documentation")
        self.set_xy(0, 3)
        self.cell(192, 6, datetime.now().strftime("%B %Y"), align='R')
        self.set_text_color(*BLACK)
        self.ln(12)

    # ── Footer ─────────────────────────────────────────────────────────────
    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, self.get_y(), 210, 14, 'F')
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*LIGHT_BLUE)
        self.cell(0, 10, f"Page {self.page_no() - 1}  |  Confidential -- Internal Use Only", align='C')
        self.set_text_color(*BLACK)

    # ── Helpers ────────────────────────────────────────────────────────────
    def h1(self, text):
        self.ln(6)
        self.set_fill_color(*DARK_BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, f"  {text}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(*BLACK)
        self.ln(3)

    def h2(self, text):
        self.ln(4)
        self.set_text_color(*MID_BLUE)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*MID_BLUE)
        self.rect(self.l_margin, self.get_y(), 174, 0.5, 'F')
        self.ln(2)
        self.set_text_color(*BLACK)

    def h3(self, text):
        self.ln(3)
        self.set_text_color(*ORANGE)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*BLACK)

    def body(self, text, indent=0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK_GRAY)
        x = self.l_margin + indent
        self.set_x(x)
        self.multi_cell(174 - indent, 5.5, text)
        self.set_text_color(*BLACK)

    def bullet(self, text, indent=4):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK_GRAY)
        self.set_x(self.l_margin + indent)
        self.cell(5, 5.5, chr(149))
        self.multi_cell(169 - indent, 5.5, text)
        self.set_text_color(*BLACK)

    def numbered(self, n, text, indent=4):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK_GRAY)
        self.set_x(self.l_margin + indent)
        self.cell(8, 5.5, f"{n}.")
        self.multi_cell(166 - indent, 5.5, text)
        self.set_text_color(*BLACK)

    def info_box(self, label, value, fill=True):
        self.set_font("Helvetica", "B", 9)
        if fill:
            self.set_fill_color(*LIGHT_BLUE)
        else:
            self.set_fill_color(*LIGHT_GRAY)
        self.set_draw_color(*MID_BLUE)
        self.cell(55, 7, f"  {label}", border=1, fill=True)
        self.set_font("Helvetica", "", 9)
        self.set_fill_color(*WHITE)
        self.cell(119, 7, f"  {value}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    def table_row(self, cols, widths, header=False, alt=False):
        if header:
            self.set_fill_color(*DARK_BLUE)
            self.set_text_color(*WHITE)
            self.set_font("Helvetica", "B", 9)
        elif alt:
            self.set_fill_color(*LIGHT_GRAY)
            self.set_text_color(*DARK_GRAY)
            self.set_font("Helvetica", "", 9)
        else:
            self.set_fill_color(*WHITE)
            self.set_text_color(*DARK_GRAY)
            self.set_font("Helvetica", "", 9)

        self.set_x(self.l_margin)
        for i, (col, w) in enumerate(zip(cols, widths)):
            self.cell(w, 6.5, str(col), border=1, fill=True)
        self.ln()
        self.set_text_color(*BLACK)

    def code_block(self, code):
        self.ln(2)
        self.set_fill_color(30, 30, 30)
        self.set_text_color(200, 230, 200)
        self.set_font("Courier", "", 8.5)
        lines = code.strip().split('\n')
        for line in lines:
            self.set_x(self.l_margin)
            self.cell(174, 5, line, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*BLACK)
        self.set_fill_color(*WHITE)
        self.ln(2)

    def spacer(self, h=4):
        self.ln(h)

    def callout(self, icon, title, text, color=LIGHT_BLUE):
        self.set_fill_color(*color)
        self.set_draw_color(*MID_BLUE)
        self.set_font("Helvetica", "B", 9)
        x, y = self.l_margin, self.get_y()
        self.set_x(x)
        self.cell(174, 6, f"  {icon}  {title}", border='TLR', fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_x(x)
        self.multi_cell(174, 5.5, f"  {text}", border='BLR', fill=True)
        self.spacer(2)


# ══════════════════════════════════════════════════════════════════════════════
#  CONTENT
# ══════════════════════════════════════════════════════════════════════════════

def build_pdf():
    pdf = PDF()

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 1 -- Cover
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    # Full-page dark background
    pdf.set_fill_color(*DARK_BLUE)
    pdf.rect(0, 0, 210, 297, 'F')

    # Accent bar
    pdf.set_fill_color(*ORANGE)
    pdf.rect(0, 90, 210, 4, 'F')

    # Title block
    pdf.set_xy(0, 50)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 36)
    pdf.cell(210, 18, "BevIQ", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(210, 10, "Beverage Data Assistant", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*LIGHT_BLUE)
    pdf.cell(210, 8, "Complete Project Documentation", align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(0, 105)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(210, 8, "Offline AI-Powered RAG Chatbot for Beverage Company Data", align='C', new_x="LMARGIN", new_y="NEXT")

    # Key stats strip
    pdf.set_xy(25, 140)
    stats = [("702,207", "Total Records"), ("7", "CSV Data Files"),
             ("100%", "Offline Mode"), ("Flask", "UI Framework")]
    for val, label in stats:
        pdf.set_fill_color(*MID_BLUE)
        pdf.set_x(pdf.get_x())
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*WHITE)
        pdf.cell(37, 12, val, align='C', fill=True)
        pdf.set_x(pdf.get_x() - 37)
        pdf.set_y(pdf.get_y() + 12)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*LIGHT_BLUE)
        pdf.cell(37, 5, label, align='C')
        pdf.set_y(pdf.get_y() - 17)
        pdf.set_x(pdf.get_x() + 39)

    # Footer strip
    pdf.set_fill_color(*ORANGE)
    pdf.rect(0, 268, 210, 1, 'F')
    pdf.set_xy(0, 272)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*LIGHT_BLUE)
    pdf.cell(210, 6, f"Generated on {datetime.now().strftime('%B %d, %Y')}   |   Confidential -- Internal Use Only", align='C')
    pdf.set_text_color(*BLACK)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 2 -- Table of Contents
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("Table of Contents")

    toc = [
        ("1.", "Project Overview",                     "3"),
        ("2.", "Business Problem & Objectives",        "4"),
        ("3.", "Technology Stack",                     "5"),
        ("4.", "Data Sources & CSV Files",             "6"),
        ("5.", "System Architecture",                  "8"),
        ("6.", "Project Folder Structure",             "9"),
        ("7.", "Module-by-Module Explanation",         "10"),
        ("8.", "RAG Pipeline Deep Dive",               "13"),
        ("9.", "UPC Normalisation Engine",             "14"),
        ("10.", "Missing UPC Analysis Tool",           "15"),
        ("11.", "Data Comparison Engine",              "16"),
        ("12.", "Flask Web Application & API",         "17"),
        ("13.", "How to Install & Run",                "18"),
        ("14.", "How to Use the Chatbot",              "19"),
        ("15.", "Sample Questions & Answers",          "20"),
        ("16.", "Database Design",                     "21"),
        ("17.", "Security & Data Privacy",             "22"),
        ("18.", "Performance & Scalability",           "23"),
        ("19.", "Glossary",                            "24"),
    ]

    pdf.spacer(3)
    for i, (num, title, pg) in enumerate(toc):
        pdf.set_fill_color(*LIGHT_BLUE if i % 2 == 0 else WHITE)
        pdf.set_font("Helvetica", "B" if i % 2 == 0 else "", 10)
        pdf.set_x(pdf.l_margin)
        pdf.cell(14, 7, num, fill=True, border='LTB')
        pdf.cell(144, 7, f"  {title}", fill=True, border='TB')
        pdf.cell(16, 7, pg, fill=True, border='RTB', align='R', new_x="LMARGIN", new_y="NEXT")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 3 -- Project Overview
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("1. Project Overview")

    pdf.body(
        "BevIQ (Beverage Intelligence Query) is a fully offline, locally running AI chatbot "
        "designed for beverage company data management. It allows business users to ask questions "
        "in plain English or Hinglish (Hindi+English mix) about large beverage product datasets "
        "stored in CSV files, and get accurate answers with data references."
    )
    pdf.spacer()
    pdf.callout("*", "What makes BevIQ unique?",
                "Unlike cloud-based tools, BevIQ runs 100% offline -- no data ever leaves your "
                "computer. It handles 700,000+ product records, supports natural language queries, "
                "and performs complex cross-file data comparisons automatically.")

    pdf.h2("1.1 Key Capabilities")
    caps = [
        "Natural language Q&A over 700,000+ beverage product records",
        "UPC-based product lookup (preserves 13-digit leading zeros)",
        "Cross-file comparison: Beer vs Wine vs Spirits vs RTD vs Master",
        "Missing UPC detection and recovery recommendations",
        "Duplicate UPC identification",
        "Brand, supplier, and category mismatch detection",
        "Hinglish query support (e.g. 'kya ye UPC master me hai?')",
        "Downloadable CSV and Excel reports for every query",
        "MySQL 3307 integration -- viewable via DBeaver",
        "Fully offline -- works without internet after setup",
    ]
    for c in caps:
        pdf.bullet(c)

    pdf.h2("1.2 Project Identity")
    pdf.info_box("Project Name",   "BevIQ -- Beverage Data Assistant")
    pdf.info_box("Version",        "1.0.0")
    pdf.info_box("Language",       "Python 3.14.3")
    pdf.info_box("UI Framework",   "Flask (HTML/CSS/JS -- Dark Theme)")
    pdf.info_box("Database",       "SQLite (primary) + MySQL 3307 (DBeaver)")
    pdf.info_box("AI/Search",      "BM25 + Fuzzy Matching (100% offline, no LLM API)")
    pdf.info_box("Port",           "http://127.0.0.1:5000")
    pdf.info_box("Working Dir",    r"c:\Users\ANUVAB MOHANTY\Downloads\beverage_db\beverage_db")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 4 -- Business Problem
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("2. Business Problem & Objectives")

    pdf.h2("2.1 The Problem")
    pdf.body(
        "The beverage company manages product data across 7 separate CSV files maintained by "
        "different teams. These files contain over 702,000 product records including Master Brand "
        "data, supplier information, and categorization sheets for Beer, Wine, Spirits, and RTD "
        "(Ready-to-Drink) beverages."
    )
    pdf.spacer(2)
    problems = [
        "UPCs (Universal Product Codes) exist in categorization sheets but are MISSING from the Master Brand file",
        "The same product may appear with slightly different names across files",
        "Categorization CSVs exported from Excel corrupt UPCs with scientific notation (e.g. 6.19E+11)",
        "Leading zeros in 13-digit UPCs are dropped when files open in Excel",
        "Duplicate UPCs exist across files",
        "No single tool could query all 7 files together in natural language",
        "Business users need answers without writing SQL or Python",
    ]
    pdf.h3("Core Problems Identified:")
    for p in problems:
        pdf.bullet(p)

    pdf.h2("2.2 Objectives")
    objectives = [
        ("UPC Recovery",        "Find UPCs missing from Master by matching product fields like brand, size, flavor"),
        ("Data Quality",        "Identify mismatches, duplicates, and missing records across all files"),
        ("Natural Language Q&A","Allow business users to query data using simple English or Hinglish"),
        ("Offline Operation",   "Run 100% locally -- no company data sent to cloud or external APIs"),
        ("Excel Reports",       "Generate downloadable Excel reports for every analysis with color-coded results"),
        ("MySQL Integration",   "Push processed data to MySQL 3307 for DBeaver access and BI tools"),
    ]
    pdf.h3("Project Objectives:")
    for i, (title, desc) in enumerate(objectives):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(pdf.l_margin + 4)
        pdf.cell(40, 6, f"  {chr(149)} {title}:")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(130, 6, desc)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 5 -- Technology Stack
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("3. Technology Stack")

    pdf.table_row(["Component", "Technology", "Version", "Purpose"], [45, 45, 25, 59], header=True)
    tech = [
        ("Language",          "Python",             "3.14.3",   "Core application language"),
        ("Web Framework",     "Flask",              "3.x",      "REST API + HTML UI server"),
        ("Data Processing",   "Pandas",             "2.x",      "CSV loading, filtering, analysis"),
        ("Numeric",           "NumPy",              "2.x",      "Array ops, UPC padding"),
        ("Database (local)",  "SQLite",             "Built-in", "Fast local data store, 702K+ rows"),
        ("Database (shared)", "MySQL 8.0",          "8.0.46",   "DBeaver-accessible, port 3307"),
        ("MySQL Driver",      "MySQL Connector/Python", "9.x", "Python-MySQL connector"),
        ("Fuzzy Search",      "RapidFuzz",          "latest",   "Fast product name matching"),
        ("BM25 Search",       "rank_bm25",          "latest",   "Keyword-based document retrieval"),
        ("Excel Reports",     "openpyxl",           "latest",   "Multi-sheet Excel output"),
        ("PDF Reports",       "fpdf2",              "latest",   "PDF documentation generation"),
        ("Config",            "python-dotenv",      "latest",   ".env file loader"),
        ("Charset detect",    "chardet",            "latest",   "Auto-detect CSV encoding"),
        ("UI Theme",          "Custom HTML/CSS/JS", "-",        "Dark theme, no CDN, offline-safe"),
        ("VCS",               "Git",                "latest",   "Version control, branch: beverage_db"),
    ]
    for i, row in enumerate(tech):
        pdf.table_row(list(row), [45, 45, 25, 59], alt=(i % 2 == 0))

    pdf.spacer()
    pdf.callout("i", "Why no Ollama / OpenAI?",
                "The original spec mentioned Ollama, but the system works fully offline using "
                "BM25 + RapidFuzz matching. This means ZERO dependency on an LLM API. "
                "If Ollama is installed, the RAG orchestrator will use it automatically. "
                "Without it, the deterministic engine handles all queries accurately.")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 6-7 -- Data Sources
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("4. Data Sources & CSV Files")

    pdf.body(
        "Seven CSV files are provided as data sources. They use either pipe (|) or comma (,) "
        "as delimiters. The application auto-detects encoding and delimiter for each file."
    )

    pdf.h2("4.1 File Summary")
    pdf.table_row(["File Name", "Rows", "Cols", "Delimiter", "Key UPC Column"], [60, 20, 15, 25, 54], header=True)
    files = [
        ("$ALLBrand_...csv",      "189,619", "45", "Pipe (|)",  "UPCCode, AlternateUPCCode"),
        ("AIMasterBrandData.csv", "189,752", "22", "Pipe (|)",  "UPCCode, AlternateUPCCode"),
        ("Categ... Beer.csv",     "50,441",  "16", "Comma (,)", "UPC 13 digit (+ Product text)"),
        ("Categ... RTDs.csv",     "153,026", "10", "Comma (,)", "UPC 13 digit (+ Product text)"),
        ("Categ... Spirits.csv",  "41,554",  "16", "Comma (,)", "UPC 13 digit (+ Product text)"),
        ("Categ... Wine.csv",     "61,031",  "18", "Comma (,)", "UPC 13 digit (+ Product text)"),
        ("$Supplier_...csv",      "16,784",  "11", "Pipe (|)",  "SupplierCode"),
    ]
    for i, row in enumerate(files):
        pdf.table_row(list(row), [60, 20, 15, 25, 54], alt=(i % 2 == 0))

    pdf.spacer()
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"  TOTAL: 702,207 records across 7 files", new_x="LMARGIN", new_y="NEXT")

    pdf.h2("4.2 AllBrand File -- Key Columns (45 total)")
    cols_ab = [
        ("UPCCode",            "Primary 13-digit UPC string"),
        ("AlternateUPCCode",   "Set of alternate UPCs: {upc1,upc2,...}"),
        ("BrandName",          "Brand name"),
        ("OCRBrandName",       "OCR-read brand name (may differ from BrandName)"),
        ("ExtendedBrandName",  "Full extended brand name"),
        ("ProductName",        "Product category (Wine/Beer/Spirits/RTD)"),
        ("ProductCategory",    "Numeric category code (1=Wine,2=Spirits,3=Beer,4=RTD)"),
        ("Flavor / Flavor_1",  "Primary and secondary flavor"),
        ("Size",               "Product size (e.g. 750 ML, 355 ML)"),
        ("Shape",              "Container shape"),
        ("Segment",            "Market segment"),
        ("SupplierCode/Name",  "Supplier identifier and full name"),
        ("BrandCode",          "Internal brand code"),
        ("BeerCategory",       "Beer sub-category classification"),
    ]
    pdf.table_row(["Column", "Description"], [55, 119], header=True)
    for i, (col, desc) in enumerate(cols_ab):
        pdf.table_row([col, desc], [55, 119], alt=(i % 2 == 0))

    pdf.add_page()
    pdf.h2("4.3 Categorization Sheet Columns")
    pdf.body("Each categorization sheet has different column names per beverage type:")

    pdf.h3("Beer Sheet (16 columns)")
    beer_cols = ["Beer Brands Value", "Beer Macro/Mezzo/Micro Styles Value",
                 "Beer Size Groups Value", "Beer Packages Value", "UPC 13 digit",
                 "Beer Segments Value", "Beer Category Value", "Beer DomVsImp Value",
                 "Beer Vendors Value", "Product", "Status", "Final Brand Name"]
    for c in beer_cols:
        pdf.bullet(c, indent=6)

    pdf.h3("Wine Sheet (18 columns)")
    wine_cols = ["Brands Value", "Flavor Groups Value", "Flavors Value",
                 "Size Packages Value", "UPC 13 digit", "Price Segments Value",
                 "Categories Value", "Colors Value", "DomVsImp Value",
                 "Wine Suppliers Value", "Product", "Final Brand Name", "Finalized Name September"]
    for c in wine_cols:
        pdf.bullet(c, indent=6)

    pdf.h3("Spirits Sheet (16 columns)")
    sp_cols = ["Spirits Brands Value", "Spirits Flavors Value", "Spirits Sizes Value",
               "UPC 13 digit", "Spirits Segments Value", "Spirits Category Value",
               "Spirits Suppliers Value", "Product", "Final Brand Name", "Updated Brand Name"]
    for c in sp_cols:
        pdf.bullet(c, indent=6)

    pdf.h3("RTD Sheet (10 columns)")
    rtd_cols = ["RTD Alcohol Base Value", "RTD Category Value", "RTD Segment Value",
                "RTD Size Value", "RTD SubSegment Value", "UPC 13 digit",
                "Product", "Brands Value", "PD Status", "Dataset"]
    for c in rtd_cols:
        pdf.bullet(c, indent=6)

    pdf.h2("4.4 Critical UPC Problem -- Excel Scientific Notation")
    pdf.callout("!", "IMPORTANT: UPC Corruption by Excel",
                "When categorization CSVs are opened and saved in Microsoft Excel, 13-digit UPCs "
                "are converted to scientific notation. Example: 0619947000031 becomes 6.19947E+11. "
                "BevIQ solves this by extracting the authentic UPC embedded at the END of the "
                "Product text column (e.g. '... BEER 12 OZ - 0619947000031') -- achieving 100% recovery.",
                color=(255, 235, 156))

    pdf.spacer()
    pdf.h3("UPC Normalisation Logic:")
    pdf.code_block("""Input: '6.19947E+11'
Step 1: Detect scientific notation → float('6.19947E+11') = 619947000000.0
Step 2: Convert to int string → '619947000000'  (12 digits)
Step 3: Zero-pad to 13 digits → '0619947000000'
-OR-
Input: Product column = '... MICHELOB ULTRA - 0018200967151'
Step 1: Regex extract trailing 13-digit → '0018200967151'  ✓ (perfect)""")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- System Architecture
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("5. System Architecture")

    pdf.body("BevIQ uses a layered architecture with clear separation between data, "
             "processing, search, and presentation layers.")

    pdf.h2("5.1 Architecture Layers")
    layers = [
        ("Layer 1 -- Data Layer",
         "7 CSV source files (read-only). Never modified. "
         "SQLite local database (beverage_data.sqlite3) with all 702K records indexed. "
         "MySQL 3307 for DBeaver-accessible reporting."),
        ("Layer 2 -- Processing Layer",
         "CSV Ingestion: Auto-detect delimiter/encoding, chunk processing for large files. "
         "UPC Normalisation: Preserve 13-digit format, fix scientific notation, extract from Product text. "
         "Data Cleaning: Standardise brand names, supplier names, categories."),
        ("Layer 3 -- Search & Intelligence Layer",
         "BM25 vector index (40,000 searchable documents). "
         "RapidFuzz fuzzy string matching for product name similarity. "
         "SQL/Pandas exact-match engine for UPCs, brands, suppliers. "
         "RAG Orchestrator: Routes queries to the right engine."),
        ("Layer 4 -- API Layer",
         "Flask REST API with 10+ endpoints. "
         "Handles: /api/query, /api/compare, /api/upc-lookup, /api/export-csv, etc. "
         "Returns JSON with data, match status, source references, and download tokens."),
        ("Layer 5 -- Presentation Layer",
         "Dark-theme HTML/CSS/JS UI. No CDN dependencies -- fully offline. "
         "Chat interface, dataset selector, comparison studio, report downloader."),
    ]
    for i, (title, desc) in enumerate(layers):
        pdf.set_fill_color(*LIGHT_BLUE if i % 2 == 0 else LIGHT_GRAY)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_x(pdf.l_margin)
        pdf.cell(174, 7, f"  {title}", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(174, 5.5, f"  {desc}", fill=True, border='BLR')
        pdf.spacer(2)

    pdf.h2("5.2 Data Flow")
    pdf.code_block("""User Query (Natural Language)
       ↓
RAG Orchestrator (rag_orchestrator.py)
  ├── Intent Detection (UPC lookup / brand search / comparison / count)
  ├── Hinglish parser (detects Hindi+English mixed queries)
  └── Routes to:
       ├── SQL Engine (sql_engine.py)      ← exact UPC/brand/supplier matches
       ├── BM25 Vector Engine              ← semantic keyword search
       └── Comparison Engine              ← cross-file missing/duplicate analysis
              ↓
    Results assembled → Flask API → JSON response → UI → User""")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Folder Structure
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("6. Project Folder Structure")

    pdf.code_block("""beverage_db/
├── app.py                    # Flask REST API -- all endpoints
├── run.py                    # Startup script -- run this to launch the app
├── config.py                 # All configuration: paths, DB, CSV mappings
├── requirements.txt          # All Python package dependencies
├── README.md                 # Setup and usage guide
├── .env                      # Secrets (DB password) -- NOT in git
├── .env.example              # Safe template for .env
├── .gitignore                # Excludes CSV, SQLite, .env from git
│
├── data_ingestion/
│   ├── loader.py             # Loads CSVs into SQLite (chunked)
│   └── normalizer.py         # UPC normalisation + data cleaning
│
├── database/
│   ├── db_manager.py         # Dual-backend: SQLite + MySQL queries
│   └── mysql_migrator.py     # Creates MySQL tables + migrates data
│
├── engines/
│   ├── sql_engine.py         # Exact SQL queries (UPC, brand, count)
│   ├── comparison_engine.py  # Cross-file comparison + missing UPC audit
│   ├── vector_engine.py      # BM25 index + keyword search
│   └── rag_orchestrator.py   # Intent detection + query routing
│
├── templates/
│   └── index.html            # Complete offline UI (dark theme)
│
├── tools/
│   ├── missing_upc_matcher_v3.py  # Missing UPC + product match Excel report
│   └── generate_project_pdf.py   # This PDF generator
│
├── db_storage/
│   └── beverage_data.sqlite3 # Local SQLite database (not in git)
│
├── vector_indices/
│   └── beverage_vector_index.pkl  # BM25 index (not in git)
│
├── reports/                  # Excel + CSV reports (auto-generated)
└── tests/
    └── test_app_endpoints.py # Automated API endpoint tests""")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Module Explanations
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("7. Module-by-Module Explanation")

    pdf.h2("7.1 app.py -- Flask REST API")
    pdf.body("The main entry point for the web application. Defines all HTTP endpoints.")
    endpoints = [
        ("GET  /",                   "Serves the main chat UI (index.html)"),
        ("POST /api/query",          "Natural language query → JSON answer with sources"),
        ("POST /api/upc-lookup",     "Exact UPC lookup across all tables"),
        ("POST /api/compare",        "Cross-file comparison (missing, duplicate, mismatch)"),
        ("GET  /api/dataset-stats",  "Row counts, column lists, file status"),
        ("GET  /api/export-csv/<token>", "Download a result as CSV file"),
        ("POST /api/brand-search",   "Find all products for a given brand name"),
        ("GET  /api/health",         "Health check -- confirms app is running"),
    ]
    pdf.table_row(["Endpoint", "Description"], [65, 109], header=True)
    for i, row in enumerate(endpoints):
        pdf.table_row(list(row), [65, 109], alt=(i % 2 == 0))

    pdf.h2("7.2 config.py -- Configuration")
    pdf.body(
        "Loads all settings from .env file using python-dotenv. Defines: "
        "database paths, CSV file mappings (filename → table name), "
        "SQLite schema definition, column type overrides (UPC always as string), "
        "logging configuration, and application constants."
    )

    pdf.h2("7.3 data_ingestion/normalizer.py -- UPC Normalisation")
    pdf.body("Core UPC cleaning functions used across the entire application:")
    norm_fns = [
        ("clean_upc(val)",             "Converts any UPC format to 13-digit zero-padded string"),
        ("extract_upc_from_product()", "Extracts UPC from Product text column (regex: trailing 13 digits)"),
        ("parse_alt_upcs(val)",        "Parses {upc1,upc2,...} set notation from AlternateUPCCode"),
        ("normalize_brand(name)",      "Lowercase, strip punctuation, standard spacing"),
        ("normalize_supplier(name)",   "Same as brand -- for supplier matching"),
    ]
    pdf.table_row(["Function", "Purpose"], [65, 109], header=True)
    for i, row in enumerate(norm_fns):
        pdf.table_row(list(row), [65, 109], alt=(i % 2 == 0))

    pdf.h2("7.4 data_ingestion/loader.py -- CSV → SQLite")
    pdf.body(
        "Reads each CSV file in 10,000-row chunks (for memory efficiency), "
        "applies UPC normalisation, adds source_file and original_row tracking columns, "
        "writes to SQLite with proper data types, and creates indexes on clean_upc, "
        "norm_brand, norm_supplier, and source_file for fast queries."
    )

    pdf.h2("7.5 database/db_manager.py -- Dual Database Backend")
    pdf.body(
        "Provides a unified query interface that works with both SQLite (primary) "
        "and MySQL (optional, port 3307). All SQL queries target SQLite by default. "
        "MySQL is used when the DBeaver reporting database needs to be updated."
    )

    pdf.h2("7.6 database/mysql_migrator.py -- MySQL Schema Builder")
    pdf.body(
        "Creates 7 MySQL tables (aimasterbranddata, allbrand_data, beer_data, rtd_data, "
        "spirits_data, wine_data, supplier_data) in the beverage_db database on "
        "127.0.0.1:3307. Migrates all records from SQLite to MySQL for DBeaver access."
    )

    pdf.add_page()
    pdf.h2("7.7 engines/sql_engine.py -- Exact Data Queries")
    pdf.body("Handles structured data queries that need exact matching:")
    sql_ops = [
        "UPC exact lookup -- find a product by its 13-digit UPC across all tables",
        "Brand search -- find all products matching a brand name (partial match supported)",
        "Supplier search -- all products from a specific supplier",
        "Category count -- how many products per category/brand/supplier",
        "Missing UPC audit -- UPCs in cat sheet not found in master",
        "Duplicate UPC detection -- same UPC appearing multiple times",
    ]
    for op in sql_ops:
        pdf.bullet(op)

    pdf.h2("7.8 engines/comparison_engine.py -- Data Comparison")
    pdf.body(
        "The most complex engine. Compares records across multiple files and classifies "
        "each record into one of 6 categories:"
    )
    classes = [
        ("Exact Match",              "UPC found in master primary or alternate UPC column"),
        ("Partial Match",            "Similar product found but not identical"),
        ("Mismatch",                 "UPC exists in both but product details differ"),
        ("Missing Record",           "UPC in cat sheet but completely absent from master"),
        ("Duplicate Record",         "Same UPC appears multiple times in same or different files"),
        ("Requires Verification",    "Uncertain match -- needs human review"),
    ]
    pdf.table_row(["Classification", "Meaning"], [60, 114], header=True)
    for i, row in enumerate(classes):
        pdf.table_row(list(row), [60, 114], alt=(i % 2 == 0))

    pdf.h2("7.9 engines/vector_engine.py -- BM25 Search")
    pdf.body(
        "Builds a BM25 (Best Match 25) text search index over 40,000 representative documents "
        "extracted from the dataset. Each document represents a product with fields: brand, "
        "UPC, size, category, supplier. The index is saved to disk as a .pkl file and reloaded "
        "on startup for fast keyword search."
    )

    pdf.h2("7.10 engines/rag_orchestrator.py -- Query Router")
    pdf.body(
        "The brain of the chatbot. Receives a natural language query and decides which engine "
        "to use:"
    )
    intents = [
        ("UPC lookup",       "Regex detects 11-13 digit number → sql_engine.upc_lookup()"),
        ("Brand search",     "Keyword 'brand', 'show all from', 'products by' → sql_engine.brand_search()"),
        ("Comparison",       "Keywords: 'missing', 'compare', 'not in master' → comparison_engine"),
        ("Category count",   "Keywords: 'how many', 'count', 'total' → sql_engine.category_count()"),
        ("Hinglish",         "Detects Hindi words (hai, kya, nahi, kitne) → re-routes to above"),
        ("General",          "Everything else → BM25 vector_engine.search()"),
    ]
    pdf.table_row(["Intent", "Routing"], [40, 134], header=True)
    for i, row in enumerate(intents):
        pdf.table_row(list(row), [40, 134], alt=(i % 2 == 0))

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- RAG Pipeline
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("8. RAG Pipeline Deep Dive")

    pdf.body(
        "RAG stands for Retrieval-Augmented Generation. In BevIQ, it means: "
        "RETRIEVE relevant records from the data → AUGMENT with context → GENERATE a readable answer. "
        "BevIQ uses a deterministic RAG (no LLM required) that works 100% offline."
    )

    pdf.h2("8.1 Pipeline Steps")
    steps = [
        ("Step 1", "Query Reception",    "User submits question via UI or API"),
        ("Step 2", "Intent Detection",   "RAG orchestrator classifies the query type"),
        ("Step 3", "Retrieval",          "SQL engine OR BM25 engine retrieves top matching records"),
        ("Step 4", "Context Assembly",   "Retrieved records are formatted with source file + row refs"),
        ("Step 5", "Answer Generation",  "Template-based answer generated (or Ollama LLM if installed)"),
        ("Step 6", "Source Attribution", "Every answer includes: source file, row number, UPC, brand"),
        ("Step 7", "Export",             "Results cached with token → user can download as CSV"),
    ]
    pdf.table_row(["Step", "Name", "Description"], [16, 42, 116], header=True)
    for i, row in enumerate(steps):
        pdf.table_row(list(row), [16, 42, 116], alt=(i % 2 == 0))

    pdf.h2("8.2 Why No LLM is Required")
    pdf.callout("i", "Deterministic vs Generative",
                "For structured data Q&A over a fixed dataset, a well-designed retrieval + "
                "template engine is MORE accurate than an LLM. LLMs can hallucinate product "
                "data. BevIQ only returns what is actually in the database -- no invented UPCs, "
                "no guessed brand names. If Ollama is installed, it adds natural language "
                "summarisation on top of the retrieved facts.")

    pdf.h2("8.3 BM25 Index Details")
    bm25_facts = [
        "40,000 documents indexed (sampled from 702,207 total records)",
        "Each document contains: brand, UPC, product name, size, category, supplier",
        "Index saved as vector_indices/beverage_vector_index.pkl",
        "Loaded on startup -- no re-indexing needed unless source data changes",
        "Query time: < 100ms for most queries",
    ]
    for f in bm25_facts:
        pdf.bullet(f)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- UPC Engine
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("9. UPC Normalisation Engine")

    pdf.body(
        "UPC normalisation is the most critical engineering component of BevIQ. "
        "All UPCs are standardised to 13-digit zero-padded strings before any comparison, "
        "storage, or lookup operation."
    )

    pdf.h2("9.1 UPC Formats Handled")
    formats = [
        ("Scientific notation",    "6.19947E+11",        "0619947000031"),
        ("Unpadded integer",       "18200967151",         "0018200967151"),
        ("UPC= prefix",            "UPC=0852955008021",   "0852955008021"),
        ("Already 13-digit",       "0018200967151",       "0018200967151"),
        ("Alternate UPC set",      "{upc1,upc2,upc3}",   "Set of 3 clean UPCs"),
        ("From Product text",      "BEER 12 OZ - 0018200967151",  "0018200967151"),
    ]
    pdf.table_row(["Format", "Raw Input", "Normalised Output"], [40, 70, 64], header=True)
    for i, row in enumerate(formats):
        pdf.table_row(list(row), [40, 70, 64], alt=(i % 2 == 0))

    pdf.h2("9.2 Why 13 Digits?")
    pdf.body(
        "Industry standard UPCs are 12 digits (UPC-A). When stored in databases or compared "
        "internationally, they are padded to 13 digits by adding a leading zero. "
        "BevIQ always uses 13-digit format to ensure consistent comparison across all files."
    )

    pdf.h2("9.3 The Product Column Trick")
    pdf.body(
        "The most reliable UPC source in categorization sheets is the Product text column, "
        "which always contains the 13-digit UPC at the end (e.g., 'MICHELOB ULTRA BEER 12 OZ - 0018200967151'). "
        "This is used as the PRIMARY UPC source, with the UPC column as fallback, "
        "achieving near-100% UPC recovery even when Excel has corrupted the UPC column."
    )
    pdf.code_block("""# Python regex to extract UPC from Product text:
import re
def extract_upc_from_product(text):
    m = re.search(r'-\\s*(\\d{13})\\s*$', text)
    return m.group(1) if m else None

# Example:
text = "MODELO ESPECIAL BEER 24 CT 12 OZ CAN IN BOX 288 OZ - 0080660957101"
extract_upc_from_product(text)  # returns: '0080660957101'  ✓""")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Missing UPC Tool
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("10. Missing UPC Analysis Tool")

    pdf.body(
        "The file tools/missing_upc_matcher_v3.py is a standalone analysis tool "
        "that compares all UPCs from Beer, Wine, Spirits, and RTD categorization sheets "
        "against the AllBrand master file. For every missing UPC, it attempts to find "
        "the matching product in master using fuzzy multi-field matching."
    )

    pdf.h2("10.1 How It Works")
    steps2 = [
        "Load AllBrand master (189,619 rows) into memory",
        "Build 3 indexes: primary UPC dict, alternate UPC dict, brand-token bucket dict",
        "Load each cat sheet (Beer/Wine/RTD/Spirits) one by one",
        "For each cat-sheet row: check primary UPC → check alternate UPC → fuzzy match",
        "Fuzzy match uses brand-token pre-filter (reduces search from 189K → ~hundreds)",
        "RapidFuzz token_sort_ratio scores product key similarity",
        "Classify each row: Exact Match / Product Match-UPC Missing / Possible / New",
        "Write multi-sheet colour-coded Excel report",
    ]
    for i, s in enumerate(steps2):
        pdf.numbered(i+1, s)

    pdf.h2("10.2 Classification System")
    pdf.table_row(["Status", "Score", "Meaning", "Action"], [55, 20, 62, 37], header=True)
    classifications = [
        ("Exact Match",                "100",  "UPC found in master primary or alternate", "No action needed"),
        ("Product Match-UPC Missing",  "80-94","Product found, UPC absent from cat sheet",  "Verify & add UPC"),
        ("Possible Match",             "60-79","Similar product, uncertain match",           "Manual review"),
        ("New Product",                "< 60", "No match found in master",                  "Add as new record"),
        ("No Valid UPC",               "-",    "Could not extract 13-digit UPC",            "Fix source data"),
    ]
    for i, row in enumerate(classifications):
        pdf.table_row(list(row), [55, 20, 62, 37], alt=(i % 2 == 0))

    pdf.h2("10.3 Excel Report Sheets")
    sheets = [
        ("Summary Report",           "Count by category + % missing for each sheet"),
        ("Missing UPCs",             "All records NOT found in master (all categories)"),
        ("Exact Product Matches",    "UPCs confirmed present in master"),
        ("Product Match-UPC Missing","Products found in master -- suggested UPC provided"),
        ("Possible Matches",         "Uncertain matches -- need manual verification"),
        ("New Products",             "Products completely absent from master"),
        ("No Valid UPC",             "Rows where 13-digit UPC could not be extracted"),
    ]
    pdf.table_row(["Sheet Name", "Contents"], [70, 104], header=True)
    for i, row in enumerate(sheets):
        pdf.table_row(list(row), [70, 104], alt=(i % 2 == 0))

    pdf.callout("*", "KEY VALUE of this tool",
                "The 'Product Match - UPC Missing' sheet gives you exactly the records you need "
                "to update AllMasterBrand -- products that already exist in master but whose UPC "
                "is missing from the categorization sheet. Each row includes the suggested UPC "
                "from master along with confidence score and source row reference.")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Comparison Engine
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("11. Data Comparison Engine")

    pdf.body(
        "The comparison engine (engines/comparison_engine.py) handles cross-file data "
        "quality analysis. It is the most business-critical component for identifying "
        "data integrity issues across the 7 CSV files."
    )

    pdf.h2("11.1 Comparison Operations")
    ops = [
        ("compare_missing_in_master(cat, master)",
         "Find UPCs in cat sheet not present in master (primary OR alternate UPC)"),
        ("compare_all_missing_in_master()",
         "Run missing UPC check for ALL 4 cat sheets (Beer+Wine+RTD+Spirits) at once"),
        ("find_duplicate_upcs(table)",
         "Find UPCs appearing more than once within the same table"),
        ("compare_brand_names(table1, table2)",
         "Find products where BrandName differs between two tables for same UPC"),
        ("find_beer_rtd_overlap()",
         "Find UPCs that appear in BOTH Beer and RTD sheets (known overlap issue)"),
        ("compare_supplier_integrity()",
         "Check supplier codes in cat sheets exist in the supplier master file"),
    ]
    for i, (fn, desc) in enumerate(ops):
        pdf.set_fill_color(*LIGHT_GRAY if i % 2 == 0 else WHITE)
        pdf.set_font("Courier", "B", 8.5)
        pdf.set_x(pdf.l_margin)
        pdf.cell(174, 6, f"  {fn}", fill=True, border='TLR', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(174, 5.5, f"  → {desc}", fill=True, border='BLR')
        pdf.spacer(1)

    pdf.h2("11.2 Previously Computed Results")
    pdf.table_row(["Category", "Total UPCs", "In Master", "Missing", "% Missing"], [35, 30, 30, 30, 49], header=True)
    results = [
        ("Beer",    "50,441",  "17,394",  "33,047", "65.5%"),
        ("Wine",    "61,031",  "45,651",  "15,380", "25.2%"),
        ("RTD",     "153,026", "92,508",  "60,020", "39.4% (incl NON-RTD)"),
        ("Spirits", "41,554",  "29,463",  "12,089", "29.1%"),
        ("TOTAL",   "305,552", "185,016", "120,536","39.4%"),
    ]
    for i, row in enumerate(results):
        pdf.table_row(list(row), [35, 30, 30, 30, 49], alt=(i % 2 == 0))

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Flask API
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("12. Flask Web Application & API")

    pdf.h2("12.1 Architecture")
    pdf.body(
        "app.py implements a Flask REST API server that serves the UI and handles all data "
        "requests. The UI is a single HTML file (templates/index.html) with embedded CSS and JS "
        "-- no external CDN dependencies, so it works offline."
    )

    pdf.h2("12.2 API Endpoint Details")
    pdf.h3("POST /api/query -- Natural Language Query")
    pdf.code_block("""Request:  {"query": "show all products from Hartford brand"}
Response: {
  "answer": "Found 12 products for brand Hartford...",
  "records": [...],
  "sources": [{"file": "$ALLBrand_...", "row": 1234}],
  "export_token": "abc123",
  "query_type": "brand_search"
}""")

    pdf.h3("POST /api/upc-lookup")
    pdf.code_block("""Request:  {"upc": "0018200967151"}
Response: {
  "found": true,
  "records": [{"source_file": "$ALLBrand...", "BrandName": "MICHELOB ULTRA", ...}],
  "match_type": "primary_upc"
}""")

    pdf.h3("POST /api/compare")
    pdf.code_block("""Request:  {"type": "all_missing", "category": "beer"}
Response: {
  "total_missing": 33047,
  "records": [...],
  "export_token": "xyz456"
}""")

    pdf.h2("12.3 UI Features")
    ui_features = [
        ("Chat Interface",        "Type any question in English or Hinglish"),
        ("Chat History",          "Full scrollable history with copy button"),
        ("Dataset Selector",      "Switch between Beer, Wine, RTD, Spirits, Master"),
        ("Comparison Studio",     "Visual cross-file comparison with one click"),
        ("Result Tables",         "Sortable, colour-coded data tables"),
        ("CSV Download",          "Every result has a Download CSV button"),
        ("Stats Dashboard",       "Live row counts, column info, index status"),
        ("Dark Theme",            "Professional dark UI, no CDN, works offline"),
    ]
    pdf.table_row(["Feature", "Description"], [50, 124], header=True)
    for i, row in enumerate(ui_features):
        pdf.table_row(list(row), [50, 124], alt=(i % 2 == 0))

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- How to Install & Run
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("13. How to Install & Run")

    pdf.h2("13.1 Prerequisites")
    prereqs = [
        "Python 3.10 or higher (tested on Python 3.14.3)",
        "MySQL 8.0 running on localhost:3307 (optional -- for DBeaver)",
        "4 GB RAM minimum (8 GB recommended for large datasets)",
        "2 GB free disk space (for SQLite + BM25 index)",
        "The 7 CSV files in the project root directory",
    ]
    for p in prereqs:
        pdf.bullet(p)

    pdf.h2("13.2 One-Time Setup")
    pdf.code_block("""# Step 1: Navigate to project folder
cd "c:\\Users\\ANUVAB MOHANTY\\Downloads\\beverage_db\\beverage_db"

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Create .env file from template
copy .env.example .env
# Then edit .env and add your MySQL password

# Step 4: Build the SQLite database (first time only -- takes ~5 min)
python -c "from data_ingestion.loader import ingest_all_csvs; ingest_all_csvs()"

# Step 5: Build BM25 search index (first time only -- takes ~2 min)
python -c "from engines.vector_engine import VectorEngine; VectorEngine().build_index()" """)

    pdf.h2("13.3 Daily Launch")
    pdf.code_block("""# Navigate to project folder
cd "c:\\Users\\ANUVAB MOHANTY\\Downloads\\beverage_db\\beverage_db"

# Start the application
python run.py

# Open browser at:
# http://127.0.0.1:5000""")

    pdf.h2("13.4 Run the Missing UPC Analysis Tool")
    pdf.code_block("""# Navigate to project folder
cd "c:\\Users\\ANUVAB MOHANTY\\Downloads\\beverage_db\\beverage_db"

# Run the analysis (takes 5-15 minutes for all 4 sheets)
python tools/missing_upc_matcher_v3.py

# Report saved automatically to:
# reports/Missing_UPC_Analysis_<timestamp>.xlsx""")

    pdf.h2("13.5 requirements.txt")
    pdf.code_block("""flask>=3.0.0
pandas>=2.0.0
numpy>=2.0.0
mysql-connector-python>=9.0.0
cryptography>=40.0.0
python-dotenv>=1.0.0
rank-bm25>=0.2.2
rapidfuzz>=3.0.0
openpyxl>=3.1.0
fpdf2>=2.7.0
chardet>=5.0.0""")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Sample Q&A
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("14. How to Use the Chatbot + Sample Q&A")

    pdf.h2("14.1 Basic Usage")
    pdf.body("Open http://127.0.0.1:5000 in your browser. Type your question in the chat box.")

    pdf.h2("14.2 Sample Questions & Expected Answers")
    qa = [
        ("Find product with UPC 0018200967151",
         "Returns: MICHELOB ULTRA BEER found in $ALLBrand file, row 1234, brand: MICHELOB"),

        ("kya ye UPC 0852955008021 master data me hai?",
         "Ye UPC 4 files me milti hai: AllBrand, Beer, Spirits, RTD. (Hinglish support)"),

        ("Show all products from Hartford brand",
         "Returns table of 12 Hartford products with UPC, size, category, source file"),

        ("beer mein kitne missing UPC hain?",
         "Beer sheet mein 33,047 UPCs master brand mein nahi hain (65.5%)"),

        ("Compare wine and master brand",
         "Wine sheet: 61,031 UPCs | In Master: 45,651 | Missing: 15,380 (25.2%)"),

        ("Find duplicate UPCs in spirits",
         "Returns list of UPCs appearing more than once in Spirits sheet"),

        ("How many products are in each category?",
         "Beer: 50,441 | Wine: 61,031 | RTD: 153,026 | Spirits: 41,554 | Master: 189,619"),

        ("Find missing UPCs in beer wine rtd spirits",
         "Runs all 4 comparisons and returns combined summary + downloadable CSV"),
    ]
    for i, (q, a) in enumerate(qa):
        pdf.set_fill_color(*LIGHT_BLUE if i % 2 == 0 else LIGHT_GRAY)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_x(pdf.l_margin)
        pdf.cell(8, 6, f"Q{i+1}:", fill=True, border='TL')
        pdf.multi_cell(166, 6, q, fill=True, border='TR')
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 100, 0)
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(230, 255, 230)
        pdf.cell(8, 6, "A:", fill=True, border='BL')
        pdf.multi_cell(166, 6, a, fill=True, border='BR')
        pdf.set_text_color(*BLACK)
        pdf.spacer(2)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Database Design
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("15. Database Design")

    pdf.h2("15.1 SQLite Tables (Primary Database)")
    pdf.table_row(["Table Name", "Source CSV", "Rows", "Key Added Columns"], [40, 55, 22, 57], header=True)
    tables = [
        ("ai_master",   "AIMasterBrandData.csv",  "189,752", "clean_upc, norm_brand"),
        ("all_brands",  "$ALLBrand_...csv",        "189,619", "clean_upc, norm_brand"),
        ("cat_beer",    "Categ... Beer.csv",        "50,441",  "clean_upc, source_file"),
        ("cat_rtd",     "Categ... RTDs.csv",        "153,026", "clean_upc, source_file"),
        ("cat_spirits", "Categ... Spirits.csv",     "41,554",  "clean_upc, source_file"),
        ("cat_wine",    "Categ... Wine.csv",        "61,031",  "clean_upc, source_file"),
        ("suppliers",   "$Supplier_...csv",         "16,784",  "norm_supplier"),
    ]
    for i, row in enumerate(tables):
        pdf.table_row(list(row), [40, 55, 22, 57], alt=(i % 2 == 0))

    pdf.h2("15.2 Added Engineering Columns")
    eng_cols = [
        ("clean_upc",     "Normalised 13-digit UPC string (always str, never int)"),
        ("norm_brand",    "Lowercase stripped brand name for fuzzy matching"),
        ("norm_supplier", "Lowercase stripped supplier name"),
        ("source_file",   "Original CSV filename (for source attribution)"),
        ("original_row",  "1-based row number in original CSV file"),
    ]
    pdf.table_row(["Column", "Purpose"], [40, 134], header=True)
    for i, row in enumerate(eng_cols):
        pdf.table_row(list(row), [40, 134], alt=(i % 2 == 0))

    pdf.h2("15.3 MySQL Tables (Port 3307 -- DBeaver)")
    pdf.body(
        "MySQL database 'beverage_db' on 127.0.0.1:3307 contains the same 7 tables "
        "with names: aimasterbranddata, allbrand_data, beer_data, rtd_data, spirits_data, "
        "wine_data, supplier_data. Credentials stored in .env (never in git)."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Security
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("16. Security & Data Privacy")

    pdf.callout("!", "CRITICAL: Company Data Never Leaves Your Machine",
                "BevIQ is designed to be 100% offline. No data is sent to any external server, "
                "cloud API, or internet service. All processing happens locally on your computer.",
                color=(255, 235, 156))

    security = [
        ("No External APIs",     "No OpenAI, Gemini, Anthropic, or any cloud LLM API is used"),
        ("No Cloud Databases",   "All data stays in local SQLite or your own MySQL instance"),
        ("No Analytics",         "No usage tracking, no telemetry, no logging to external services"),
        ("Credentials in .env",  ".env file contains DB password -- excluded from git via .gitignore"),
        ("CSVs Never Modified",  "Original CSV files are read-only -- BevIQ never writes to them"),
        ("Git Excludes Data",    ".gitignore excludes: *.csv, .env, db_storage/, vector_indices/"),
        (".env.example",         "Safe credential template committed to git -- no actual passwords"),
        ("Local Flask server",   "Flask runs on 127.0.0.1 (localhost only) -- not exposed to network"),
    ]
    pdf.h2("Security Controls")
    pdf.table_row(["Control", "Implementation"], [50, 124], header=True)
    for i, row in enumerate(security):
        pdf.table_row(list(row), [50, 124], alt=(i % 2 == 0))

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Performance
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("17. Performance & Scalability")

    pdf.h2("17.1 Performance Characteristics")
    perf = [
        ("UPC exact lookup",      "< 10ms",    "Direct SQLite index lookup"),
        ("Brand search",          "< 100ms",   "Indexed norm_brand column"),
        ("BM25 keyword search",   "< 200ms",   "Pre-built in-memory index"),
        ("Missing UPC audit (1 sheet)", "~3-5 min", "Fuzzy match + brand pre-filter"),
        ("Missing UPC audit (all 4)",   "~15-30 min","Sequential processing"),
        ("CSV export",            "< 500ms",   "Pandas to_csv from cached results"),
        ("App startup",           "~5 sec",    "BM25 index reload from disk"),
    ]
    pdf.table_row(["Operation", "Speed", "Method"], [65, 30, 79], header=True)
    for i, row in enumerate(perf):
        pdf.table_row(list(row), [65, 30, 79], alt=(i % 2 == 0))

    pdf.h2("17.2 Optimisations Implemented")
    opts = [
        "SQLite indexes on clean_upc, norm_brand, norm_supplier, source_file",
        "Chunked CSV loading (10,000 rows at a time) -- prevents memory overflow",
        "BM25 index saved to disk and reloaded -- no re-indexing on each run",
        "Brand-token pre-filter reduces fuzzy match search space from 189K → ~hundreds",
        "RapidFuzz C-extension for fuzzy matching (10-50x faster than pure Python fuzzywuzzy)",
        "Separate Phase 1 (exact UPC) skips fuzzy matching for ~65% of records",
        "Export tokens cache results -- CSV generation is instantaneous after query",
    ]
    for o in opts:
        pdf.bullet(o)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE -- Glossary
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("18. Glossary")

    terms = [
        ("UPC",         "Universal Product Code -- 12-digit (UPC-A) or 13-digit product barcode"),
        ("UPC 13-digit","Industry standard: 12-digit UPC padded with one leading zero = 13 digits"),
        ("RAG",         "Retrieval-Augmented Generation -- retrieve relevant data, then generate answer"),
        ("BM25",        "Best Match 25 -- a text ranking algorithm used for keyword search (like TF-IDF++"),
        ("RapidFuzz",   "Fast C-extension Python library for fuzzy string similarity matching"),
        ("AllBrand",    "The master product file ($ALLBrand_...csv) -- 189,619 rows, 45 columns"),
        ("AIMaster",    "Alternative master file (AIMasterBrandData.csv) -- 189,752 rows, 22 columns"),
        ("Cat Sheet",   "Categorization sheet -- Beer, Wine, RTD, or Spirits CSV file"),
        ("RTD",         "Ready-to-Drink -- pre-mixed alcoholic beverages (hard seltzers, cocktails)"),
        ("Hinglish",    "Hindi+English mixed language queries (e.g. 'kya ye UPC master me hai?')"),
        ("OCRBrandName","Brand name as read by OCR (may differ from official BrandName)"),
        ("ExtBrandName","Extended brand name -- full official brand identifier"),
        ("Scientific notation", "Excel's representation of large numbers (e.g. 6.19E+11) -- corrupts UPCs"),
        ("SQLite",      "Lightweight local SQL database -- stored in a single .sqlite3 file"),
        ("DBeaver",     "Database GUI tool -- connects to MySQL 3307 to view beverage data"),
        ("Flask",       "Python web microframework -- handles HTTP requests and serves the UI"),
        ("BM25 Index",  "Pre-built searchable index of 40,000 product documents (saved as .pkl)"),
        ("Token",       "Short random ID used to cache a query result for CSV export"),
        ("Pipe delimiter", "CSV files where columns are separated by | instead of comma"),
        ("Leading zero","The zero at start of 13-digit UPC -- must be preserved as string, not int"),
    ]
    pdf.table_row(["Term", "Definition"], [45, 129], header=True)
    for i, (term, dfn) in enumerate(terms):
        pdf.table_row([term, dfn], [45, 129], alt=(i % 2 == 0))

    # ─────────────────────────────────────────────────────────────────────────
    # Final page -- Contact / Notes
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*DARK_BLUE)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_xy(0, 100)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(210, 14, "BevIQ", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(210, 10, "Beverage Data Assistant", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*LIGHT_BLUE)
    pdf.cell(210, 8, "Built with Python, Flask, SQLite, RapidFuzz & BM25", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*ORANGE)
    pdf.cell(210, 7, "GitHub: github.com/mohantyanuvab/beverage-data-assistant", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*LIGHT_BLUE)
    pdf.cell(210, 6, f"Document generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(210, 6, "Confidential -- Internal Use Only", align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.output(OUT)
    print(f"\n✓ PDF saved: {OUT}")
    return OUT


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    out = build_pdf()
    print(f"Report: {out}")
