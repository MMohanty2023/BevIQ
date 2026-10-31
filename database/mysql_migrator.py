import os
import re
import pymysql
import pandas as pd
import logging
from config import CSV_FILES, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
from data_ingestion.normalizer import normalize_upc
from data_ingestion.loader import clean_column_name

logger = logging.getLogger("MySQLMigrator")

def migrate_data_to_mysql(password=None, host=None, port=None, user=None, db_name=None, progress_callback=None):
    """
    Ingests all beverage CSV files directly into MySQL server on port 3307.
    Enables viewing in DBeaver immediately.
    """
    host = host or MYSQL_HOST
    port = port or MYSQL_PORT
    user = user or MYSQL_USER
    password = password if password is not None else MYSQL_PASSWORD
    db_name = db_name or MYSQL_DB

    # 1. Connect and create database
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=10
        )
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
    except Exception as e:
        return False, f"Failed to connect to MySQL on {host}:{port}: {e}"

    # 2. Connect to the created database
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name,
        charset='utf8mb4'
    )

    results = {}

    try:
        for key, config_entry in CSV_FILES.items():
            fname = config_entry["file"]
            delimiter = config_entry["delimiter"]
            table_name = config_entry["table"]
            upc_col = config_entry.get("upc_col")
            alt_upc_col = config_entry.get("alt_upc_col")
            brand_col = config_entry.get("brand_col")
            supplier_col = config_entry.get("supplier_col")

            if not os.path.exists(fname):
                continue

            # Read sample to define columns
            df_sample = pd.read_csv(fname, sep=delimiter, nrows=5, dtype=str)
            raw_cols = df_sample.columns.tolist()
            sql_cols = [clean_column_name(c) for c in raw_cols] + ['_source_file', '_original_row', 'clean_upc', 'clean_alt_upc', 'norm_brand', 'norm_supplier']
            
            # Deduplicate sql_cols preserving order
            unique_cols = []
            for col in sql_cols:
                if col not in unique_cols:
                    unique_cols.append(col)

            # Drop old table
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS `{table_name}`")
                
                # Build CREATE TABLE
                col_defs = []
                for c in unique_cols:
                    if c in ['clean_upc', 'clean_alt_upc']:
                        col_defs.append(f"`{c}` VARCHAR(64)")
                    elif c in ['norm_brand', 'norm_supplier', 'BrandName', 'SupplierName']:
                        col_defs.append(f"`{c}` VARCHAR(255)")
                    elif c == '_original_row':
                        col_defs.append(f"`{c}` INT")
                    elif c == '_source_file':
                        col_defs.append(f"`{c}` VARCHAR(128)")
                    else:
                        col_defs.append(f"`{c}` TEXT")
                
                create_sql = f"CREATE TABLE `{table_name}` (\n  " + ",\n  ".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
                cur.execute(create_sql)
                conn.commit()

            # Insert in chunks
            chunksize = 10000
            total_rows = 0
            row_offset = 1

            for chunk in pd.read_csv(fname, sep=delimiter, chunksize=chunksize, dtype=str, on_bad_lines='skip'):
                chunk_len = len(chunk)
                chunk['_source_file'] = os.path.basename(fname)
                chunk['_original_row'] = list(range(row_offset, row_offset + chunk_len))
                row_offset += chunk_len

                prod_series = chunk['Product'] if 'Product' in chunk.columns else (chunk['ProductName'] if 'ProductName' in chunk.columns else None)
                if upc_col and upc_col in chunk.columns:
                    if prod_series is not None:
                        chunk['clean_upc'] = [normalize_upc(u, p) for u, p in zip(chunk[upc_col], prod_series)]
                    else:
                        chunk['clean_upc'] = [normalize_upc(u) for u in chunk[upc_col]]
                else:
                    chunk['clean_upc'] = ""

                if alt_upc_col and alt_upc_col in chunk.columns:
                    chunk['clean_alt_upc'] = [normalize_upc(u) for u in chunk[alt_upc_col]]
                else:
                    chunk['clean_alt_upc'] = ""

                if brand_col and brand_col in chunk.columns:
                    chunk['norm_brand'] = chunk[brand_col].fillna("").astype(str).str.strip().str.upper()
                else:
                    chunk['norm_brand'] = ""

                if supplier_col and supplier_col in chunk.columns:
                    chunk['norm_supplier'] = chunk[supplier_col].fillna("").astype(str).str.strip().str.upper()
                else:
                    chunk['norm_supplier'] = ""

                chunk.columns = [clean_column_name(c) for c in chunk.columns]
                
                # Keep only columns present in table definition
                insert_df = chunk.reindex(columns=unique_cols).fillna("")
                
                # Bulk insert
                placeholders = ", ".join(["%s"] * len(unique_cols))
                col_names_sql = ", ".join([f"`{c}`" for c in unique_cols])
                insert_sql = f"INSERT INTO `{table_name}` ({col_names_sql}) VALUES ({placeholders})"
                
                tuples = [tuple(x) for x in insert_df.to_numpy()]
                with conn.cursor() as cur:
                    cur.executemany(insert_sql, tuples)
                conn.commit()

                total_rows += chunk_len
                if progress_callback:
                    progress_callback(key, total_rows)

            # Create Indexes
            with conn.cursor() as cur:
                try:
                    cur.execute(f"CREATE INDEX `idx_{table_name}_upc` ON `{table_name}`(clean_upc(32))")
                    cur.execute(f"CREATE INDEX `idx_{table_name}_brand` ON `{table_name}`(norm_brand(64))")
                    conn.commit()
                except Exception as ex:
                    logger.warning(f"MySQL index creation notice: {ex}")

            results[key] = total_rows

        conn.close()
        return True, f"Successfully migrated {sum(results.values()):,} records into MySQL on port {port} (Database: '{db_name}')"

    except Exception as e:
        conn.close()
        return False, f"Migration error: {e}"

if __name__ == "__main__":
    import sys
    pwd = sys.argv[1] if len(sys.argv) > 1 else MYSQL_PASSWORD
    print(f"Connecting to MySQL on 127.0.0.1:{MYSQL_PORT} with user root...")
    ok, msg = migrate_data_to_mysql(password=pwd)
    print("Result:", ok, msg)

