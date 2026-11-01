import os
import re
import csv
import sqlite3
import pandas as pd
import logging
from config import CSV_FILES, SQLITE_PATH
from data_ingestion.normalizer import normalize_upc, clean_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataLoader")

def clean_column_name(col):
    """Normalize CSV column names for safe SQL table column names."""
    col = col.strip()
    col = re.sub(r'[\s\-/\(\)\.\$]+', '_', col)
    col = re.sub(r'_+', '_', col).strip('_')
    if col and col[0].isdigit():
        col = 'col_' + col
    return col or 'unnamed_col'

def ingest_csv_to_sqlite(key, config_entry, progress_callback=None):
    fname = config_entry["file"]
    delimiter = config_entry["delimiter"]
    table_name = config_entry["table"]
    upc_col = config_entry.get("upc_col")
    alt_upc_col = config_entry.get("alt_upc_col")
    brand_col = config_entry.get("brand_col")
    supplier_col = config_entry.get("supplier_col")

    if not os.path.exists(fname):
        logger.error(f"File not found: {fname}")
        return 0

    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = 100000")

    # Drop existing table if refreshing
    conn.execute(f"DROP TABLE IF EXISTS `{table_name}`")
    conn.commit()

    chunksize = 25000
    total_processed = 0
    row_offset = 1

    logger.info(f"Starting ingestion of {fname} into SQLite table '{table_name}'...")

    for chunk in pd.read_csv(fname, sep=delimiter, chunksize=chunksize, dtype=str, on_bad_lines='skip'):
        chunk_len = len(chunk)
        chunk['_source_file'] = os.path.basename(fname)
        chunk['_original_row'] = list(range(row_offset, row_offset + chunk_len))
        row_offset += chunk_len

        # Extract normalized 13-digit UPC
        prod_series = chunk['Product'] if 'Product' in chunk.columns else (chunk['ProductName'] if 'ProductName' in chunk.columns else None)
        
        if upc_col and upc_col in chunk.columns:
            if prod_series is not None:
                chunk['clean_upc'] = [normalize_upc(u, p) for u, p in zip(chunk[upc_col], prod_series)]
            else:
                chunk['clean_upc'] = [normalize_upc(u) for u in chunk[upc_col]]
        else:
            chunk['clean_upc'] = ""

        # Normalize Alternate UPC if present
        if alt_upc_col and alt_upc_col in chunk.columns:
            chunk['clean_alt_upc'] = [normalize_upc(u) for u in chunk[alt_upc_col]]
        else:
            chunk['clean_alt_upc'] = ""

        # Normalize standardized brand and supplier column
        if brand_col and brand_col in chunk.columns:
            chunk['norm_brand'] = chunk[brand_col].fillna("").astype(str).str.strip().str.upper()
        else:
            chunk['norm_brand'] = ""

        if supplier_col and supplier_col in chunk.columns:
            chunk['norm_supplier'] = chunk[supplier_col].fillna("").astype(str).str.strip().str.upper()
        else:
            chunk['norm_supplier'] = ""

        # Clean all column names for SQL safety
        chunk.columns = [clean_column_name(c) for c in chunk.columns]

        # Append to SQLite table
        chunk.to_sql(table_name, conn, if_exists='append', index=False)
        total_processed += chunk_len

        if progress_callback:
            progress_callback(key, total_processed)
        logger.info(f"  {table_name}: Ingested {total_processed:,} records...")

    # Create helpful indexes for lightning-fast queries
    logger.info(f"Creating indexes for table '{table_name}'...")
    try:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_upc ON `{table_name}`(clean_upc)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_brand ON `{table_name}`(norm_brand)")
        if 'norm_supplier' in chunk.columns:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_supp ON `{table_name}`(norm_supplier)")
        conn.commit()
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

    conn.close()
    logger.info(f"Finished '{table_name}': {total_processed:,} records ingested successfully.")
    return total_processed

def ingest_all_to_sqlite(progress_callback=None):
    """Ingest all 7 datasets into SQLite local database."""
    total_all = 0
    stats = {}
    for key, config_entry in CSV_FILES.items():
        count = ingest_csv_to_sqlite(key, config_entry, progress_callback)
        stats[key] = count
        total_all += count
    logger.info(f"ALL DATASETS INGESTED. Total records: {total_all:,}")
    return stats

