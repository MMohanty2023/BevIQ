
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ==========================================================
# 1. PROJECT DIRECTORIES
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR
TRAINED_BRANDS_FILE = DATA_DIR / "TrainedBrandsData.csv"
DB_DIR = BASE_DIR / "db_storage"
INDEX_DIR = BASE_DIR / "vector_indices"
REPORTS_DIR = BASE_DIR / "generated_reports"

# ==========================================================
# 2. LOAD ENVIRONMENT VARIABLES
# ==========================================================

def load_env_file():
    """Load .env variables without overriding existing variables."""

    env_path = BASE_DIR / ".env"

    if not env_path.exists():
        logger.info(".env file not found. Using system environment variables.")
        return

    try:
        with open(env_path, "r", encoding="utf-8-sig") as file:
            for line_number, line in enumerate(file, start=1):

                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("export "):
                    line = line[7:].strip()

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                # Remove matching surrounding quotes.
                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ("'", '"')
                ):
                    value = value[1:-1]

                os.environ.setdefault(key, value)

    except OSError as error:
        raise RuntimeError(
            f"Unable to read environment file: {error}"
        ) from error


load_env_file()

# ==========================================================
# 3. CREATE REQUIRED DIRECTORIES
# ==========================================================

for directory in (DB_DIR, INDEX_DIR, REPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# ==========================================================
# 4. MYSQL DATABASE CONFIGURATION
# ==========================================================

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")

try:
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
except ValueError as error:
    raise ValueError("MYSQL_PORT must be a valid integer.") from error

if not 1 <= MYSQL_PORT <= 65535:
    raise ValueError("MYSQL_PORT must be between 1 and 65535.")

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "beverage_db")

# ==========================================================
# 5. SQLITE DATABASE CONFIGURATION
# ==========================================================

SQLITE_PATH = DB_DIR / "beverage_data.sqlite3"

# ==========================================================
# 6. OLLAMA CONFIGURATION
# ==========================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2"
)

# ==========================================================
# 7. CSV FILE CONFIGURATION
# ==========================================================

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


# ==========================================================
# 8. SOURCE FILE VALIDATION
# ==========================================================

def validate_csv_files():
    """Check availability of all seven configured source files."""

    missing_files = []

    for source_name, config in CSV_FILES.items():
        file_path = DATA_DIR / config["file"]

        if not file_path.is_file():
            missing_files.append(str(file_path))

    if missing_files:
        logger.warning("Some source CSV files are missing:")

        for file_path in missing_files:
            logger.warning("Missing: %s", file_path)

        return False

    logger.info("All seven source CSV files are available.")
    return True


if __name__ == "__main__":

    print("=" * 60)
    print("BEVIQ CONFIGURATION CHECK")
    print("=" * 60)

    print("Project directory:", BASE_DIR)
    print("SQLite database:", SQLITE_PATH)
    print("Vector index:", INDEX_DIR)
    print("Reports:", REPORTS_DIR)

    print("MySQL host:", MYSQL_HOST)
    print("MySQL port:", MYSQL_PORT)
    print("MySQL database:", MYSQL_DB)

    print("CSV validation:", validate_csv_files())

    print("=" * 60)
