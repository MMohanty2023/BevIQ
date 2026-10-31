import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR
DB_DIR = BASE_DIR / "db_storage"
INDEX_DIR = BASE_DIR / "vector_indices"
REPORTS_DIR = BASE_DIR / "generated_reports"

# Load .env file if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

# Ensure directories exist
DB_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Database Configurations
# Primary Target: MySQL on localhost:3307 (as requested for DBeaver)
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3307))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")  # Loaded from .env or environment
MYSQL_DB = os.getenv("MYSQL_DB", "beverage_db")

# High-Performance Local SQLite Fallback & Cache (Works 100% offline with zero setup)
SQLITE_PATH = DB_DIR / "beverage_data.sqlite3"

# Ollama / LLM Configurations
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# CSV File Mappings
CSV_FILES = {
    "all_brands": {
        "file": "$ALLBrand_202610291524.csv",
        "delimiter": "|",
        "table": "all_brands",
        "upc_col": "UPCCode",
        "alt_upc_col": "AlternateUPCCode",
        "brand_col": "BrandName",
        "supplier_col": "SupplierName",
        "category_col": "ProductCategory"
    },
    "suppliers": {
        "file": "$Supplier_202610291521.csv",
        "delimiter": "|",
        "table": "suppliers",
        "upc_col": None,
        "alt_upc_col": None,
        "brand_col": None,
        "supplier_col": "SupplierName",
        "category_col": None
    },
    "ai_master": {
        "file": "AIMasterBrandData.csv",
        "delimiter": "|",
        "table": "ai_master",
        "upc_col": "UPCCode",
        "alt_upc_col": "AlternateUPCCode",
        "brand_col": "BrandName",
        "supplier_col": "SupplierName",
        "category_col": "ProductCategory"
    },
    "cat_beer": {
        "file": "Categorization 2026 - Beer.csv",
        "delimiter": ",",
        "table": "cat_beer",
        "upc_col": "UPC 13 digit",
        "alt_upc_col": None,
        "brand_col": "Beer Brands Value",
        "supplier_col": "Beer Vendors Value",
        "category_col": "Beer Category Value"
    },
    "cat_rtd": {
        "file": "Categorization 2026 - RTDs.csv",
        "delimiter": ",",
        "table": "cat_rtd",
        "upc_col": "UPC 13 digit",
        "alt_upc_col": None,
        "brand_col": "Brands Value",
        "supplier_col": None,
        "category_col": "RTD Category Value"
    },
    "cat_spirits": {
        "file": "Categorization 2026 - Spirits.csv",
        "delimiter": ",",
        "table": "cat_spirits",
        "upc_col": "UPC 13 digit",
        "alt_upc_col": None,
        "brand_col": "Spirits Brands Value",
        "supplier_col": "Spirits Suppliers Value",
        "category_col": "Spirits Category Value"
    },
    "cat_wine": {
        "file": "Categorization 2026 - Wine.csv",
        "delimiter": ",",
        "table": "cat_wine",
        "upc_col": "UPC 13 digit",
        "alt_upc_col": None,
        "brand_col": "Brands Value",
        "supplier_col": "Wine Suppliers Value",
        "category_col": "Categories Value"
    }
}

