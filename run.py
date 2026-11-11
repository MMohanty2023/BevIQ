import os
import sys
from pathlib import Path
from config import INDEX_DIR, MYSQL_HOST, MYSQL_PORT, MYSQL_DB, SQLITE_PATH, CSV_FILES
from data_ingestion.loader import ingest_all_to_sqlite, ingest_csv_to_sqlite
import sqlite3
from engines.vector_engine import vector_engine

def setup_environment():
    print("=" * 65)
    print("              BEVIQ - INITIALIZATION SEQUENCE")
    print("=" * 65)

    # 1. Check if SQLite cache exists and has records
    db_needs_init = not SQLITE_PATH.exists() or SQLITE_PATH.stat().st_size < 1000000

    if db_needs_init:
        print("[*] Local database not found or incomplete. Ingesting configured CSV files...")
        print("[*] Performing UPC recovery, leading zero preservation, and schema indexing...")
        stats = ingest_all_to_sqlite()
        print("[+] Ingestion complete:", stats)
    else:
        print(f"[+] Local SQLite database verified: {SQLITE_PATH} ({SQLITE_PATH.stat().st_size / (1024*1024):.2f} MB)")
        with sqlite3.connect(str(SQLITE_PATH)) as conn:
            trained_table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (CSV_FILES['trained_brands']['table'],),
            ).fetchone()
        if not trained_table_exists:
            print("[*] TrainedBrandsData table missing; ingesting the existing trained sheet...")
            ingest_csv_to_sqlite('trained_brands', CSV_FILES['trained_brands'])

    # 2. Check if vector index exists
    index_file = INDEX_DIR / "beverage_vector_index.pkl"
    if not index_file.exists():
        print("[*] Building persistent local semantic vector index...")
        count = vector_engine.build_from_database(limit_per_table=10000)
        print(f"[+] Vector index built successfully with {count:,} semantic documents.")
    else:
        print(f"[+] Vector index verified: {index_file}")

    print("=" * 65)
    print("  Application ready! Starting Flask Web Server on http://127.0.0.1:5000")
    print(f"  Primary database: MySQL on {MYSQL_HOST}:{MYSQL_PORT} (Database: {MYSQL_DB})")
    print("=" * 65)

if __name__ == '__main__':
    setup_environment()
    from app import app
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
