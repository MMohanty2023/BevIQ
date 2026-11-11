import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import mysql.connector

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from config import (
    CSV_FILES,
    DATA_DIR,
    MYSQL_DB,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)
from data_ingestion.loader import clean_column_name
from data_ingestion.normalizer import normalize_upc

logger = logging.getLogger("MySQLMigrator")
_METADATA_COLUMNS = (
    "source_file",
    "original_row",
    "clean_upc",
    "clean_alt_upc",
    "norm_brand",
    "norm_supplier",
)


def _quote_identifier(identifier):
    """Validate and quote a MySQL database, table, or column identifier."""
    if (
        not isinstance(identifier, str)
        or not identifier
        or len(identifier) > 64
        or "\x00" in identifier
    ):
        raise ValueError(f"Invalid MySQL identifier: {identifier!r}")
    return f"`{identifier.replace('`', '``')}`"


def _prepare_sources(dataset_keys=None):
    """Resolve and validate selected configured CSVs before changing the database."""
    sources = {}
    errors = []

    if dataset_keys is None:
        selected_keys = list(CSV_FILES)
    else:
        selected_keys = list(dataset_keys)
        unknown_keys = [key for key in selected_keys if key not in CSV_FILES]
        if unknown_keys:
            raise ValueError(
                "unknown dataset key(s): " + ", ".join(map(str, unknown_keys))
            )

    for key in selected_keys:
        entry = CSV_FILES[key]
        file_path = DATA_DIR / entry["file"]
        try:
            table_sql = _quote_identifier(entry["table"])
        except ValueError as error:
            errors.append(str(error))
            continue

        if not file_path.is_file():
            errors.append(f"{key}: source file not found: {file_path}")
            continue

        try:
            columns = pd.read_csv(
                file_path,
                sep=entry["delimiter"],
                nrows=0,
                dtype=str,
            ).columns.tolist()
        except (
            OSError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            UnicodeError,
        ) as error:
            errors.append(f"{key}: unable to read CSV header from {file_path}: {error}")
            continue

        sql_columns = [clean_column_name(column) for column in columns]
        sql_columns.extend(_METADATA_COLUMNS)
        if len(sql_columns) != len(set(sql_columns)):
            errors.append(
                f"{key}: CSV columns conflict after SQL name normalization "
                "or with generated metadata columns."
            )
            continue

        try:
            quoted_columns = [_quote_identifier(column) for column in sql_columns]
        except ValueError as error:
            errors.append(f"{key}: {error}")
            continue

        sources[key] = {
            "entry": entry,
            "path": file_path,
            "table_sql": table_sql,
            "columns": sql_columns,
            "columns_sql": quoted_columns,
        }

    if errors:
        raise ValueError("CSV preflight failed:\n" + "\n".join(errors))
    return sources


def migrate_data_to_mysql(
    password=None,
    host=None,
    port=None,
    user=None,
    db_name=None,
    progress_callback=None,
    replace_existing=False,
    dataset_keys=None,
):
    """Migrate all configured beverage CSV files into the configured MySQL database.

    Existing tables are preserved unless ``replace_existing=True`` is explicitly set.
    """
    host = host or MYSQL_HOST
    port = port or MYSQL_PORT
    user = user or MYSQL_USER
    password = MYSQL_PASSWORD if password is None else password
    db_name = db_name or MYSQL_DB

    try:
        db_sql = _quote_identifier(db_name)
        sources = _prepare_sources(dataset_keys)
    except (TypeError, ValueError) as error:
        return False, str(error)

    server_conn = None
    conn = None
    try:
        server_conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connection_timeout=10,
            charset="utf8mb4",
        )
        with server_conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {db_sql} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    except Exception as error:
        return False, f"Failed to connect to MySQL on {host}:{port}: {error}"
    finally:
        if server_conn is not None:
            server_conn.close()

    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            charset="utf8mb4",
            connection_timeout=10,
        )

        existing_tables = []
        with conn.cursor() as cur:
            for source in sources.values():
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = %s",
                    (db_name, source["entry"]["table"]),
                )
                if cur.fetchone()[0]:
                    existing_tables.append(source["entry"]["table"])

        if existing_tables and not replace_existing:
            tables = ", ".join(sorted(existing_tables))
            return (
                False,
                f"Migration stopped: these MySQL tables already exist: {tables}. "
                "Back up any data, then rerun with --replace-existing to replace them.",
            )

        results = {}
        for key, source in sources.items():
            entry = source["entry"]
            table_name = entry["table"]
            table_sql = source["table_sql"]
            columns = source["columns"]
            columns_sql = source["columns_sql"]

            if replace_existing:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {table_sql}")

            column_definitions = []
            for column, column_sql in zip(columns, columns_sql):
                if column == "clean_upc":
                    column_type = "VARCHAR(64)"
                elif column == "clean_alt_upc":
                    column_type = "TEXT"
                elif column in ("norm_brand", "norm_supplier", "BrandName", "SupplierName"):
                    column_type = "VARCHAR(255)"
                elif column == "original_row":
                    column_type = "INT"
                elif column == "source_file":
                    column_type = "VARCHAR(128)"
                else:
                    column_type = "TEXT"
                column_definitions.append(f"{column_sql} {column_type}")

            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE TABLE {table_sql} "
                    f"({', '.join(column_definitions)}) "
                    "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                )
            conn.commit()

            total_rows = 0
            row_offset = 1
            chunks = pd.read_csv(
                source["path"],
                sep=entry["delimiter"],
                chunksize=10000,
                dtype=str,
            )
            for chunk in chunks:
                chunk_len = len(chunk)
                chunk["source_file"] = source["path"].name
                chunk["original_row"] = range(row_offset, row_offset + chunk_len)
                row_offset += chunk_len

                product_column = next(
                    (name for name in ("Product", "ProductName") if name in chunk.columns),
                    None,
                )
                product_values = chunk[product_column] if product_column else None
                upc_column = entry.get("upc_col")
                if upc_column and upc_column in chunk.columns:
                    if product_values is not None:
                        chunk["clean_upc"] = [
                            normalize_upc(upc, product)
                            for upc, product in zip(chunk[upc_column], product_values)
                        ]
                    else:
                        chunk["clean_upc"] = [
                            normalize_upc(upc) for upc in chunk[upc_column]
                        ]
                else:
                    chunk["clean_upc"] = ""

                alt_upc_column = entry.get("alt_upc_col")
                if alt_upc_column and alt_upc_column in chunk.columns:
                    chunk["clean_alt_upc"] = [
                        normalize_upc(upc) for upc in chunk[alt_upc_column]
                    ]
                else:
                    chunk["clean_alt_upc"] = ""

                brand_column = entry.get("brand_col")
                if brand_column and brand_column in chunk.columns:
                    chunk["norm_brand"] = (
                        chunk[brand_column].fillna("").astype(str).str.strip().str.upper()
                    )
                else:
                    chunk["norm_brand"] = ""

                supplier_column = entry.get("supplier_col")
                if supplier_column and supplier_column in chunk.columns:
                    chunk["norm_supplier"] = (
                        chunk[supplier_column].fillna("").astype(str).str.strip().str.upper()
                    )
                else:
                    chunk["norm_supplier"] = ""

                chunk.columns = [clean_column_name(column) for column in chunk.columns]
                insert_df = chunk.reindex(columns=columns).fillna("")
                placeholders = ", ".join(["%s"] * len(columns))
                insert_sql = (
                    f"INSERT INTO {table_sql} ({', '.join(columns_sql)}) "
                    f"VALUES ({placeholders})"
                )
                rows = [tuple(row) for row in insert_df.to_numpy()]
                with conn.cursor() as cur:
                    cur.executemany(insert_sql, rows)
                conn.commit()

                total_rows += chunk_len
                if progress_callback:
                    progress_callback(key, total_rows)

            index_definitions = (
                ("clean_upc", "upc", 32),
                ("clean_alt_upc", "alt_upc", 32),
                ("norm_brand", "brand", 64),
                ("norm_supplier", "supplier", 64),
            )
            for column, suffix, prefix_length in index_definitions:
                if column in columns:
                    try:
                        index_name = _quote_identifier(f"idx_{table_name}_{suffix}")
                        column_sql = _quote_identifier(column)
                        with conn.cursor() as cur:
                            cur.execute(
                                f"CREATE INDEX {index_name} ON {table_sql} "
                                f"({column_sql}({prefix_length}))"
                            )
                    except Exception as error:
                        logger.warning(
                            "Could not create index on %s.%s: %s",
                            table_name,
                            column,
                            error,
                        )

            conn.commit()
            results[key] = total_rows

        return (
            True,
            f"Successfully migrated {sum(results.values()):,} records into MySQL "
            f"on {host}:{port} (database: '{db_name}').",
        )
    except Exception as error:
        if conn is not None:
            conn.rollback()
        logger.exception("MySQL data migration failed")
        return False, f"Migration error: {error}"
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import the configured beverage CSV files into MySQL."
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Drop and recreate matching MySQL tables (back up important data first).",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        dest="dataset_keys",
        choices=sorted(CSV_FILES),
        help="Migrate only this configured dataset; may be repeated.",
    )
    args = parser.parse_args()

    print(f"Connecting to MySQL on {MYSQL_HOST}:{MYSQL_PORT} as {MYSQL_USER}...")
    success, message = migrate_data_to_mysql(
        replace_existing=args.replace_existing,
        dataset_keys=args.dataset_keys,
    )
    print(message)
    raise SystemExit(0 if success else 1)
