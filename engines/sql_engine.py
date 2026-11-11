import pandas as pd
import logging
import re
from collections import Counter
from config import CSV_FILES
from database.db_manager import db_manager
from data_ingestion.normalizer import normalize_upc

logger = logging.getLogger("SQLEngine")

class SQLEngine:
    def __init__(self, db=None):
        self.db = db or db_manager

    def lookup_upc(self, upc_query):
        """
        Exact search for a UPC across Master and Categorization tables.
        Returns matching records with source files and original rows.
        """
        clean = normalize_upc(upc_query)
        results = []

        # 1. Search in AIMaster
        master_table = CSV_FILES['ai_master']['table']
        m_rows = self.db.query(f"""
            SELECT 'AIMaster' as source, source_file, original_row, clean_upc, clean_alt_upc, BrandName, ExtendedBrandName, SupplierName, ProductName, Size, Price, Segment
            FROM `{master_table}`
            WHERE clean_upc = ? OR clean_alt_upc = ?
        """, (clean, clean))
        results.extend(m_rows)

        # 2. Search in AllBrand if not in Master
        allbrand_table = CSV_FILES['all_brands']['table']
        ab_rows = self.db.query(f"""
            SELECT 'AllBrand' as source, source_file, original_row, clean_upc, clean_alt_upc, BrandName, ExtendedBrandName, SupplierName, ProductName, Size, Price, Remarks
            FROM `{allbrand_table}`
            WHERE clean_upc = ? OR clean_alt_upc = ?
        """, (clean, clean))
        results.extend(ab_rows)

        # 3. Search in Beer
        beer_table = CSV_FILES['cat_beer']['table']
        b_rows = self.db.query(f"""
            SELECT 'Beer' as source, source_file, original_row, clean_upc, Beer_Brands_Value as BrandName, Beer_Category_Value as Category, Beer_Vendors_Value as SupplierName, Product, Status
            FROM `{beer_table}`
            WHERE clean_upc = ?
        """, (clean,))
        results.extend(b_rows)

        # 4. Search in RTDs
        rtd_table = CSV_FILES['cat_rtd']['table']
        r_rows = self.db.query(f"""
            SELECT 'RTD' as source, source_file, original_row, clean_upc, Brands_Value as BrandName, RTD_Category_Value as Category, RTD_Alcohol_Base_Value as AlcoholBase, Product, PD_Status
            FROM `{rtd_table}`
            WHERE clean_upc = ?
        """, (clean,))
        results.extend(r_rows)

        # 5. Search in Spirits
        spirits_table = CSV_FILES['cat_spirits']['table']
        s_rows = self.db.query(f"""
            SELECT 'Spirits' as source, source_file, original_row, clean_upc, Spirits_Brands_Value as BrandName, Spirits_Category_Value as Category, Spirits_Suppliers_Value as SupplierName, Product, PD_Status
            FROM `{spirits_table}`
            WHERE clean_upc = ?
        """, (clean,))
        results.extend(s_rows)

        # 6. Search in Wine
        wine_table = CSV_FILES['cat_wine']['table']
        w_rows = self.db.query(f"""
            SELECT 'Wine' as source, source_file, original_row, clean_upc, Brands_Value as BrandName, Categories_Value as Category, Wine_Suppliers_Value as SupplierName, Product, PD_Status
            FROM `{wine_table}`
            WHERE clean_upc = ?
        """, (clean,))
        results.extend(w_rows)

        return {
            "query_upc": upc_query,
            "normalized_upc": clean,
            "total_matches": len(results),
            "found_in_files": list(set([r['source_file'] for r in results])),
            "records": results
        }

    def search_brand(self, brand_query, limit=50):
        """Search products by brand name across master and categorization datasets."""
        term = f"%{brand_query.strip().upper()}%"
        master_table = CSV_FILES['ai_master']['table']
        rows = self.db.query(f"""
            SELECT source_file, original_row, clean_upc, BrandName, ExtendedBrandName, SupplierName, ProductName, Size, Price, Segment
            FROM `{master_table}`
            WHERE norm_brand LIKE ?
            LIMIT {limit}
        """, (term,))

        return {
            "query_brand": brand_query,
            "total_matches": len(rows),
            "records": rows
        }

    def search_master_brands(self, query="", master_id=None, brand=None, upc=None, product=None, limit=100):
        """Search the Master Brand table using real columns and exact identifiers."""
        table = CSV_FILES["ai_master"]["table"]
        columns = [column for column in self.db.table_columns(table) if column]
        column_lookup = {column.lower(): column for column in columns}
        id_column = next((column_lookup[name] for name in (
            "id", "record_id", "masterbrandid", "master_brand_id", "master_id"
        ) if name in column_lookup), None)
        brand_column = column_lookup.get("norm_brand") or column_lookup.get("brandname")
        product_column = column_lookup.get("productname") or column_lookup.get("product")
        clean_upc_column = next((column_lookup[name] for name in ("clean_upc", "upccode", "upc_13_digit", "upc 13 digit", "upc13digit") if name in column_lookup), None)
        clean_alt_column = next((column_lookup[name] for name in ("clean_alt_upc", "alternateupccode", "alternate upc code", "alternateupccode") if name in column_lookup), None)

        master_id = master_id or query if query and not (brand or upc or product) else master_id
        conditions = []
        params = []
        if master_id and id_column:
            conditions.append(f"`{id_column}` = ?")
            params.append(str(master_id).strip())
        if upc and clean_upc_column:
            normalized = normalize_upc(upc)
            upc_conditions = [f"`{clean_upc_column}` = ?"]
            upc_params = [normalized]
            if clean_alt_column:
                upc_conditions.append(f"`{clean_alt_column}` = ?")
                upc_params.append(normalized)
            conditions.append("(" + " OR ".join(upc_conditions) + ")")
            params.extend(upc_params)
        if brand and brand_column:
            conditions.append(f"LOWER(COALESCE(`{brand_column}`, '')) LIKE LOWER(?)")
            params.append(f"%{brand.strip()}%")
        if product and product_column:
            conditions.append(f"LOWER(COALESCE(`{product_column}`, '')) LIKE LOWER(?)")
            params.append(f"%{product.strip()}%")
        if not conditions:
            return {"columns": columns, "records": [], "total_matches": 0, "id_column": id_column}

        safe_limit = max(1, min(int(limit), 500))
        where_sql = f"FROM `{table}` WHERE {' AND '.join(conditions)}"
        count_rows = self.db.query(f"SELECT COUNT(*) AS total_matches {where_sql}", tuple(params))
        rows = self.db.query(
            f"SELECT * FROM `{table}` WHERE {' AND '.join(conditions)} LIMIT {safe_limit}",
            tuple(params),
        )
        result_columns = list(rows[0].keys()) if rows else columns
        total_matches = int((count_rows[0].get("total_matches") or 0)) if count_rows and "total_matches" in count_rows[0] else len(rows)
        return {
            "columns": result_columns,
            "records": rows,
            "total_matches": total_matches,
            "id_column": id_column,
        }

    def lookup_identifier(self, identifier, limit=200):
        """Return complete source rows for an exact ID, UPC, or alternate UPC."""
        requested = str(identifier or "").strip()
        if not requested:
            return {"normalized_identifier": "", "total_matches": 0,
                    "records": [], "related_records": [], "source_files": []}

        normalized = normalize_upc(requested) if requested.isdigit() and 10 <= len(requested) <= 14 else requested
        datasets = [
            ("all_brands", "Id"),
            ("suppliers", "SupplierId"),
            ("ai_master", "id"),
            ("cat_beer", None),
            ("cat_rtd", None),
            ("cat_spirits", None),
            ("cat_wine", None),
        ]
        records = []
        seen = set()
        safe_limit = max(1, min(int(limit), 1000))
        for table, id_column in datasets:
            id_clause = f"CAST(`{id_column}` AS CHAR) = ? OR " if id_column else ""
            params = (requested, normalized, normalized) if id_column else (normalized, normalized)
            rows = self.db.query(
                f"SELECT * FROM `{table}` WHERE ({id_clause}clean_upc = ? OR clean_alt_upc = ?) LIMIT {safe_limit}",
                params,
            )
            for row in rows:
                key = (table, row.get("original_row"), row.get("clean_upc"), row.get("clean_alt_upc"))
                if key not in seen:
                    seen.add(key)
                    row.setdefault("_dataset", table)
                    records.append(row)

        related_upcs = {r.get("clean_upc") for r in records if r.get("clean_upc")}
        related = []
        for table, _ in datasets:
            for upc in related_upcs:
                rows = self.db.query(
                    f"SELECT * FROM `{table}` WHERE clean_upc = ? OR clean_alt_upc = ? LIMIT {safe_limit}",
                    (upc, upc),
                )
                for row in rows:
                    key = (table, row.get("original_row"), row.get("clean_upc"), row.get("clean_alt_upc"))
                    if key not in seen:
                        seen.add(key)
                        row.setdefault("_dataset", table)
                        related.append(row)

        source_files = sorted({r.get("source_file") for r in records + related if r.get("source_file")})
        return {
            "normalized_identifier": normalized,
            "total_matches": len(records),
            "records": records,
            "related_records": related,
            "source_files": source_files,
        }

    def search_catalog(self, query, limit=100, offset=0):
        """Search brand names and product descriptions across every beverage sheet."""
        term = f"%{query.strip()}%"
        safe_limit = max(1, min(int(limit), 1000))
        safe_offset = max(0, int(offset))
        datasets = [
            ("Master", CSV_FILES['ai_master']['table'], "norm_brand, BrandName, ProductName, Flavor, Flavor_1, Size, SupplierName, Appellation, clean_upc, source_file, original_row", "ProductName"),
            ("Beer", CSV_FILES['cat_beer']['table'], "norm_brand, Beer_Brands_Value, Product, Beer_Mezzo_Styles_Value, Beer_Size_Groups_Value, Beer_Vendors_Value, Beer_DomVsImp_Value, clean_upc, source_file, original_row", "Product"),
            ("Wine", CSV_FILES['cat_wine']['table'], "norm_brand, Brands_Value, Product, Flavor_Groups_Value, Flavors_Value, Size_Packages_Value, Wine_Suppliers_Value, DomVsImp_Value, clean_upc, source_file, original_row", "Product"),
            ("RTD", CSV_FILES['cat_rtd']['table'], "norm_brand, Brands_Value, Product, RTD_Size_Value, clean_upc, source_file, original_row", "Product"),
            ("Spirits", CSV_FILES['cat_spirits']['table'], "norm_brand, Spirits_Brands_Value, Product, Spirits_Flavors_Value, Spirits_Flavor_Scents_Value, Spirits_Sizes_Value, Spirits_Suppliers_Value, Spirits_DomVsImp_Value, clean_upc, source_file, original_row", "Product"),
        ]
        results = []
        for category, table, columns, product_column in datasets:
            rows = self.db.query(
                f"SELECT {columns} FROM `{table}` WHERE norm_brand LIKE ? OR LOWER(COALESCE({product_column}, '')) LIKE LOWER(?) LIMIT {safe_limit} OFFSET {safe_offset}",
                (term, term)
            )
            for row in rows:
                if category == "Master":
                    brand, product, flavour, size = row.get("BrandName"), row.get("ProductName"), " / ".join(str(row.get(k) or "") for k in ("Flavor", "Flavor_1") if str(row.get(k) or "").strip()), row.get("Size")
                    supplier, origin = row.get("SupplierName"), row.get("Appellation")
                elif category == "Beer":
                    brand, product, flavour, size = row.get("Beer_Brands_Value"), row.get("Product"), row.get("Beer_Mezzo_Styles_Value"), row.get("Beer_Size_Groups_Value")
                    supplier, origin = row.get("Beer_Vendors_Value"), row.get("Beer_DomVsImp_Value")
                elif category == "Wine":
                    brand, product, flavour, size = row.get("Brands_Value"), row.get("Product"), " / ".join(str(row.get(k) or "") for k in ("Flavor_Groups_Value", "Flavors_Value") if str(row.get(k) or "").strip()), row.get("Size_Packages_Value")
                    supplier, origin = row.get("Wine_Suppliers_Value"), row.get("DomVsImp_Value")
                elif category == "RTD":
                    brand, product, flavour, size = row.get("Brands_Value"), row.get("Product"), "", row.get("RTD_Size_Value")
                    supplier, origin = "", ""
                else:
                    brand, product, flavour, size = row.get("Spirits_Brands_Value"), row.get("Product"), " / ".join(str(row.get(k) or "") for k in ("Spirits_Flavors_Value", "Spirits_Flavor_Scents_Value") if str(row.get(k) or "").strip()), row.get("Spirits_Sizes_Value")
                    supplier, origin = row.get("Spirits_Suppliers_Value"), row.get("Spirits_DomVsImp_Value")
                results.append({
                    "category": category, "brand": brand or "", "product_description": product or "",
                    "flavour": flavour or "", "size": size or "", "supplier": supplier or "",
                    "origin": origin or "", "upc": row.get("clean_upc") or "",
                    "source_file": row.get("source_file"), "original_row": row.get("original_row")
                })
                if len(results) >= safe_limit:
                    return {"query": query, "total_matches": len(results), "records": results}
        return {"query": query, "total_matches": len(results), "records": results}

    def brand_profile(self, brand_query, limit=500):
        """Return brand facts across the master and all categorization sheets."""
        term = f"%{brand_query.strip().upper()}%"
        datasets = [
            ("Master", CSV_FILES['ai_master']['table'],
             "norm_brand, BrandName, ProductCategory, Flavor, Flavor_1, Size, SupplierName, Appellation, ProductName, clean_upc, source_file, original_row"),
            ("Beer", CSV_FILES['cat_beer']['table'],
             "norm_brand, Beer_Brands_Value, Beer_Mezzo_Styles_Value, Beer_Size_Groups_Value, Beer_Vendors_Value, Beer_DomVsImp_Value, Product, clean_upc, source_file, original_row"),
            ("Wine", CSV_FILES['cat_wine']['table'],
             "norm_brand, Brands_Value, Flavor_Groups_Value, Flavors_Value, Size_Packages_Value, Wine_Suppliers_Value, DomVsImp_Value, Product, clean_upc, source_file, original_row"),
            ("RTD", CSV_FILES['cat_rtd']['table'],
             "norm_brand, Brands_Value, RTD_Size_Value, Product, clean_upc, source_file, original_row"),
            ("Spirits", CSV_FILES['cat_spirits']['table'],
             "norm_brand, Spirits_Brands_Value, Spirits_Flavors_Value, Spirits_Flavor_Scents_Value, Spirits_Sizes_Value, Spirits_Suppliers_Value, Spirits_DomVsImp_Value, Product, clean_upc, source_file, original_row"),
        ]

        records = []
        for category, table, columns in datasets:
            rows = self.db.query(
                f"SELECT {columns} FROM `{table}` WHERE norm_brand LIKE ? LIMIT {int(limit)}",
                (term,)
            )
            for row in rows:
                if category == "Master":
                    flavour = " / ".join(str(row.get(k) or "") for k in ("Flavor", "Flavor_1") if str(row.get(k) or "").strip())
                    brand = row.get("BrandName")
                    size = row.get("Size")
                    supplier = row.get("SupplierName")
                    origin = row.get("Appellation")
                    product = row.get("ProductName")
                elif category == "Beer":
                    flavour = row.get("Beer_Mezzo_Styles_Value")
                    brand = row.get("Beer_Brands_Value")
                    size = row.get("Beer_Size_Groups_Value")
                    supplier = row.get("Beer_Vendors_Value")
                    origin = row.get("Beer_DomVsImp_Value")
                    product = row.get("Product")
                elif category == "Wine":
                    flavour = " / ".join(str(row.get(k) or "") for k in ("Flavor_Groups_Value", "Flavors_Value") if str(row.get(k) or "").strip())
                    brand = row.get("Brands_Value")
                    size = row.get("Size_Packages_Value")
                    supplier = row.get("Wine_Suppliers_Value")
                    origin = row.get("DomVsImp_Value")
                    product = row.get("Product")
                elif category == "RTD":
                    flavour = ""
                    brand = row.get("Brands_Value")
                    size = row.get("RTD_Size_Value")
                    supplier = ""
                    origin = ""
                    product = row.get("Product")
                else:
                    flavour = " / ".join(str(row.get(k) or "") for k in ("Spirits_Flavors_Value", "Spirits_Flavor_Scents_Value") if str(row.get(k) or "").strip())
                    brand = row.get("Spirits_Brands_Value")
                    size = row.get("Spirits_Sizes_Value")
                    supplier = row.get("Spirits_Suppliers_Value")
                    origin = row.get("Spirits_DomVsImp_Value")
                    product = row.get("Product")
                records.append({
                    "category": category, "brand": brand or brand_query, "flavour": flavour,
                    "size": size, "supplier": supplier, "origin": origin,
                    "product": product, "upc": row.get("clean_upc"),
                    "source_file": row.get("source_file"), "original_row": row.get("original_row")
                })

        def values(key):
            return sorted({str(r[key]).strip() for r in records if str(r.get(key) or "").strip()})

        return {
            "query_brand": brand_query,
            "total_records": len(records),
            "unique_brand_count": len({str(r.get("brand") or "").strip().upper() for r in records if str(r.get("brand") or "").strip()}),
            "unique_flavour_count": len(values("flavour")),
            "unique_size_count": len(values("size")),
            "unique_upc_count": len({str(r.get("upc") or "").strip() for r in records if str(r.get("upc") or "").strip()}),
            "categories": [{"category": name, "count": count} for name, count in Counter(r["category"] for r in records).most_common()],
            "flavours": values("flavour"), "sizes": values("size"),
            "suppliers": values("supplier"), "origins": values("origin"),
            "records": records,
        }

    def search_supplier(self, supplier_query, limit=50):
        """Search products and supplier details by supplier name."""
        term = f"%{supplier_query.strip().upper()}%"
        master_table = CSV_FILES['ai_master']['table']
        rows = self.db.query(f"""
            SELECT source_file, original_row, clean_upc, BrandName, ExtendedBrandName, SupplierName, SupplierCode, ProductName, Price
            FROM `{master_table}`
            WHERE norm_supplier LIKE ?
            LIMIT {limit}
        """, (term,))

        return {
            "query_supplier": supplier_query,
            "total_matches": len(rows),
            "records": rows
        }

    def count_master_brands(self):
        """Return the distinct normalized brand count from the master catalog."""
        return self.count_brands()

    def count_brands(self, category=None):
        """Return distinct brand count for the master or requested category sheet."""
        table = CSV_FILES.get(category or 'ai_master', CSV_FILES['ai_master'])['table']
        rows = self.db.query(
            f"SELECT COUNT(DISTINCT norm_brand) AS brand_count FROM `{table}` "
            "WHERE TRIM(COALESCE(norm_brand, '')) != ''"
        )
        return int(rows[0].get('brand_count') or 0) if rows else 0

    def count_by_category(self):
        """Aggregates product counts by category across Master and Categorization tables."""
        master_table = CSV_FILES['ai_master']['table']
        m_counts = self.db.query(f"""
            SELECT ProductName as category, COUNT(*) as product_count
            FROM `{master_table}`
            GROUP BY ProductName
            ORDER BY product_count DESC
        """)

        beer_table = CSV_FILES['cat_beer']['table']
        b_counts = self.db.query(f"""
            SELECT Beer_Category_Value as category, COUNT(*) as product_count
            FROM `{beer_table}`
            GROUP BY Beer_Category_Value
            ORDER BY product_count DESC
        """)

        rtd_table = CSV_FILES['cat_rtd']['table']
        r_counts = self.db.query(f"""
            SELECT RTD_Category_Value as category, COUNT(*) as product_count
            FROM `{rtd_table}`
            GROUP BY RTD_Category_Value
            ORDER BY product_count DESC
        """)

        return {
            "master_categories": m_counts,
            "beer_categories": b_counts,
            "rtd_categories": r_counts
        }

    def get_dataset_overview(self):
        """Returns row counts and metrics for each active table."""
        datasets = list(CSV_FILES.items())
        overview_query = " UNION ALL ".join(
            f"SELECT '{key}' AS dataset_key, COUNT(*) AS row_count, "
            f"COUNT(DISTINCT NULLIF(clean_upc, '')) AS upc_count "
            f"FROM `{conf['table']}`"
            for key, conf in datasets
        )
        try:
            counts_by_dataset = {
                row["dataset_key"]: row
                for row in self.db.query(overview_query)
            }
        except Exception:
            logger.exception("Combined dataset overview query failed; retrying tables individually")
            counts_by_dataset = {}

        stats = []
        for key, conf in datasets:
            counts = counts_by_dataset.get(key)
            if counts is None:
                try:
                    counts = self.db.query(
                        f"SELECT COUNT(*) AS row_count, "
                        f"COUNT(DISTINCT NULLIF(clean_upc, '')) AS upc_count "
                        f"FROM `{conf['table']}`"
                    )[0]
                except Exception:
                    logger.exception("Dataset overview query failed for %s", conf["table"])
                    counts = {"row_count": 0, "upc_count": 0}
            stats.append({
                "dataset_key": key,
                "file_name": conf['file'],
                "table_name": conf['table'],
                "total_rows": counts["row_count"],
                "unique_upcs": counts["upc_count"],
            })
        return stats

    def get_dashboard_metrics(self):
        """Return live category, UPC-quality, and Master Brand dashboard metrics."""
        category_keys = ("beer", "wine", "rtd", "spirits")
        categories = {
            key: self._table_upc_metrics(CSV_FILES[f"cat_{key}"]["table"])
            for key in category_keys
        }
        master_columns = self.db.table_columns(CSV_FILES['ai_master']['table']) if hasattr(self.db, 'table_columns') else []
        master_column_lookup = {column.lower(): column for column in master_columns if column}
        master_id_column = (
            master_column_lookup.get('id')
            or master_column_lookup.get('record_id')
            or master_column_lookup.get('masterbrandid')
            or master_column_lookup.get('master_brand_id')
        )
        master_brand_column = master_column_lookup.get('norm_brand') or master_column_lookup.get('brandname') or master_column_lookup.get('extendedbrandname')
        master_upc_column = next((master_column_lookup.get(name) for name in ('clean_upc', 'upccode', 'upc_13_digit', 'upc 13 digit', 'upc13digit') if master_column_lookup.get(name)), None)
        id_expression = f"`{master_id_column}`" if master_id_column else "NULL"
        brand_expression = f"`{master_brand_column}`" if master_brand_column else "NULL"
        upc_expression = f"`{master_upc_column}`" if master_upc_column else "NULL"
        master = self.db.query(f"""
            SELECT
                COUNT(*) AS master_record_count,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE({brand_expression}, '')), '')) AS unique_brands,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE({id_expression}, '')), '')) AS unique_master_ids,
                SUM(CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) NOT IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN 1 ELSE 0 END) AS available_upcs,
                SUM(CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN 1 ELSE 0 END) AS missing_upcs,
                COUNT(DISTINCT CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) NOT IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN TRIM({upc_expression}) END) AS distinct_upcs
            FROM `{CSV_FILES['ai_master']['table']}`
        """)[0]

        overall_total = sum(item["total_records"] for item in categories.values())
        overall_available = sum(item["available_upcs"] for item in categories.values())
        overall_missing = sum(item["missing_upcs"] for item in categories.values())
        return {
            "categories": categories,
            "overall_upc": self._quality_summary(overall_total, overall_available, overall_missing),
            "master_brand": {
                "total_records": int(master.get("master_record_count") or 0),
                "unique_brands": int(master.get("unique_brands") or 0),
                "unique_master_ids": int(master.get("unique_master_ids") or 0),
                "records_with_upc": int(master.get("available_upcs") or 0),
                "records_without_upc": int(master.get("missing_upcs") or 0),
                "distinct_upcs": int(master.get("distinct_upcs") or 0),
            },
        }

    def get_supplier_directory(self, limit=500, include_records=True):
        """Return supplier-wise Master Brand summaries and bounded detail rows."""
        table = CSV_FILES["all_brands"]["table"]
        safe_limit = max(1, min(int(limit), 500))
        supplier_key = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE LOWER(TRIM(SupplierName)) END"
        supplier_label = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE TRIM(SupplierName) END"
        brand_key = "CASE WHEN LOWER(TRIM(COALESCE(BrandName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN NULL ELSE LOWER(TRIM(BrandName)) END"
        upc_key = "CASE WHEN LOWER(TRIM(COALESCE(clean_upc, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN NULL ELSE LOWER(TRIM(clean_upc)) END"

        summaries = self.db.query(f"""
            SELECT {supplier_key} AS supplier_key,
                   MIN({supplier_label}) AS supplier,
                   MIN(SupplierCode) AS supplier_code,
                   COUNT(*) AS record_count,
                   COUNT(DISTINCT {brand_key}) AS brand_count,
                   COUNT(DISTINCT {upc_key}) AS upc_count,
                   GROUP_CONCAT(DISTINCT ProductCategory) AS categories,
                   GROUP_CONCAT(DISTINCT RecordStatusId) AS statuses
            FROM `{table}`
            GROUP BY {supplier_key}
            ORDER BY CASE WHEN supplier_key = 'NA' THEN 1 ELSE 0 END, supplier
            LIMIT {safe_limit}
        """)

        def unique_values(value):
            values = []
            seen = set()
            for item in str(value or "").split(","):
                item = item.strip()
                key = item.casefold()
                if item and key not in seen:
                    seen.add(key)
                    values.append(item)
            return values

        all_brand_detail_rows = self.db.query(
            f"""SELECT {supplier_key} AS supplier_key,
                              MIN(BrandName) AS brand_name,
                              MIN(BrandCode) AS brand_code,
                              MIN(Id) AS brand_id,
                              COUNT(*) AS record_count,
                              GROUP_CONCAT(DISTINCT ProductCategory) AS categories
                       FROM `{table}`
                      WHERE {brand_key} IS NOT NULL
                      GROUP BY {supplier_key}, {brand_key}
                      ORDER BY supplier_key, brand_name"""
        )
        brand_details_by_supplier = {}
        for row in all_brand_detail_rows:
            brand_name = str(row.get("brand_name") or "").strip()
            if not brand_name:
                continue
            raw_key = str(row.get("supplier_key") or "NA").strip().lower() or "NA"
            key = "NA" if raw_key in {"", "null", "none", "nan", "n/a", "na"} else raw_key
            brand_details_by_supplier.setdefault(key, []).append({
                "brand_name": brand_name,
                "brand_code": str(row.get("brand_code") or "").strip() or None,
                "brand_id": str(row.get("brand_id") or "").strip() or None,
                "record_count": int(row.get("record_count") or 0),
                "categories": unique_values(row.get("categories")),
            })

        suppliers = []
        for summary in summaries:
            key = str(summary.get("supplier_key") or summary.get("supplier") or "NA").strip().lower()
            label = str(summary.get("supplier") or "NA").strip() or "NA"
            if key in {"", "null", "none", "nan", "n/a", "na"}:
                key, label = "NA", "NA"
            where = f"{supplier_key} = ?"
            brand_details = brand_details_by_supplier.get(key, [])
            brand_names = [detail["brand_name"] for detail in brand_details]
            records = []
            if include_records:
                records = self.db.query(
                    f"SELECT BrandName, ProductName, clean_upc, source_file, original_row FROM `{table}` WHERE {where} ORDER BY BrandName, ProductName LIMIT 25",
                    (key,),
                )
            suppliers.append({
                "supplier": label,
                "supplier_code": str(summary.get("supplier_code") or "").strip() or None,
                "categories": unique_values(summary.get("categories")),
                "statuses": [value.strip() for value in str(summary.get("statuses") or "").split(",") if value.strip()],
                "record_count": int(summary.get("record_count") or 0),
                "brand_count": int(summary.get("brand_count") or 0),
                "brand_names": brand_names,
                "brand_details": brand_details,
                "upc_count": int(summary.get("upc_count") or 0),
                "records": records,
            })

        return {"total_suppliers": len(suppliers), "suppliers": suppliers}

    def get_supplier_brand_details(self, supplier, brand):
        """Return de-duplicated product records for one supplier/brand pair."""
        table = CSV_FILES["all_brands"]["table"]
        supplier_key = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE LOWER(TRIM(SupplierName)) END"
        brand_key = "CASE WHEN LOWER(TRIM(COALESCE(BrandName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN NULL ELSE LOWER(TRIM(BrandName)) END"
        rows = self.db.query(
            f"""SELECT DISTINCT Id, SupplierCode, SupplierName, BrandCode, BrandName,
                              ProductCategory, ProductName, Category, UPCCode, clean_upc,
                              RecordStatusId, HighResImageURL, MidResImageURL,
                              LowResImageURL, S3ImageURL, S3ImageThumURL
                       FROM `{table}`
                      WHERE {supplier_key} = ? AND {brand_key} = ?
                      ORDER BY ProductName, Id""",
            (supplier.strip().lower() or "NA", brand.strip().lower()),
        )
        records = []
        for row in rows:
            images = [
                str(row.get(column) or '').strip()
                for column in ('HighResImageURL', 'MidResImageURL', 'LowResImageURL', 'S3ImageURL', 'S3ImageThumURL')
                if str(row.get(column) or '').strip()
            ]
            records.append({
                "brand_name": row.get("BrandName"),
                "brand_id": row.get("Id"),
                "class_id": row.get("BrandCode"),
                "brand_code": row.get("BrandCode"),
                "category": row.get("ProductCategory") or row.get("Category"),
                "category_image_url": None,
                "supplier_name": row.get("SupplierName"),
                "supplier_code": row.get("SupplierCode"),
                "sku": row.get("clean_upc") or row.get("UPCCode"),
                "image_count": len(images),
                "model_name": row.get("ProductName"),
                "model_id": row.get("Id"),
                "status": row.get("RecordStatusId"),
                "available_images": images,
            })
        return {"supplier": supplier, "brand": brand, "records": records}

    @staticmethod
    def _trained_image_urls(value):
        if value is None:
            return []
        raw = str(value).strip().strip('"')
        if not raw or raw.lower() in {"null", "none", "nan", "n/a", "na", "0", "{}"}:
            return []
        urls = []
        for item in re.split(r"[,|;\n]+", raw):
            url = item.strip().strip('"')
            if url.startswith(("http://", "https://")) and url not in urls:
                urls.append(url)
        return urls

    def _trained_where(self, filters=None):
        filters = filters or {}
        conditions, params = [], []
        fields = ["Id", "Class_Id", "SupplierCode", "SupplierName", "BrandCode", "BrandName",
                  "Category_Wine_Spirits_Beer_Non_Alcoholic", "SKU", "Model", "Model_Id"]
        query = str(filters.get("query") or "").strip()
        if query:
            conditions.append("(" + " OR ".join(f"LOWER(COALESCE(`{field}`, '')) LIKE LOWER(?)" for field in fields) + ")")
            params.extend([f"%{query}%"] * len(fields))
        for field, key in (("Category_Wine_Spirits_Beer_Non_Alcoholic", "category"), ("SupplierName", "supplier"), ("BrandName", "brand"), ("Model", "model")):
            value = str(filters.get(key) or "").strip()
            if value:
                conditions.append(f"LOWER(COALESCE(`{field}`, '')) LIKE LOWER(?)")
                params.append(f"%{value}%")
        status = str(filters.get("status") or "").strip().lower()
        if status:
            if status in {"active", "1"}:
                conditions.append("(LOWER(COALESCE(`Status`, '')) = '1' OR LOWER(COALESCE(`RecordStatus`, '')) = 'active')")
            elif status in {"inactive", "0", "2"}:
                conditions.append("(LOWER(COALESCE(`Status`, '')) <> '1' AND LOWER(COALESCE(`RecordStatus`, '')) <> 'active')")
            else:
                conditions.append("LOWER(COALESCE(`RecordStatus`, '')) LIKE LOWER(?)")
                params.append(f"%{status}%")
        min_images = filters.get("min_images")
        max_images = filters.get("max_images")
        if min_images not in (None, ""):
            conditions.append(f"{self._trained_numeric_cast('COALESCE(`ImageCounts`, 0)')} >= ?")
            params.append(int(min_images))
        if max_images not in (None, ""):
            conditions.append(f"{self._trained_numeric_cast('COALESCE(`ImageCounts`, 0)')} <= ?")
            params.append(int(max_images))
        missing_conditions = {
            "missing_sku": "LOWER(COALESCE(`SKU`, '')) IN ('', '0', 'null', 'none', 'nan', 'n/a', 'na')",
            "missing_images": "LOWER(COALESCE(`ImageUrls`, '')) IN ('', '""', 'null', 'none', 'nan', 'n/a', 'na', '0', '{}')",
            "missing_model_id": "LOWER(COALESCE(`Model_Id`, '')) IN ('', '0', 'null', 'none', 'nan', 'n/a', 'na')",
        }
        for key, expression in missing_conditions.items():
            if filters.get(key) in (True, "true", "1", 1):
                conditions.append(expression)
        return (" WHERE " + " AND ".join(conditions)) if conditions else "", params

    def _trained_numeric_cast(self, expression):
        """Return a numeric CAST expression valid for the active SQL backend."""
        backend = getattr(self.db, "backend_name", lambda: "sqlite")()
        cast_type = "SIGNED" if str(backend).lower() == "mysql" else "INTEGER"
        return f"CAST({expression} AS {cast_type})"

    @staticmethod
    def _trained_record(row):
        image_urls = SQLEngine._trained_image_urls(row.get("ImageUrls"))
        sku = str(row.get("SKU") or "").strip()
        model_id = str(row.get("Model_Id") or "").strip()
        status = str(row.get("Status") or "").strip()
        record_status = str(row.get("RecordStatus") or "").strip()
        return {
            "id": row.get("Id"), "class_id": row.get("Class_Id"),
            "supplier_code": row.get("SupplierCode"), "supplier_name": row.get("SupplierName"),
            "brand_code": row.get("BrandCode"), "brand_name": row.get("BrandName"),
            "category": row.get("Category_Wine_Spirits_Beer_Non_Alcoholic"),
            "image_count": int(float(row.get("ImageCounts") or 0)),
            "avg_trained_photos": float(row.get("AvgTrainedPhotos") or 0),
            "sku": row.get("SKU"), "status": status, "record_status": record_status,
            "model": row.get("Model"), "model_id": row.get("Model_Id"),
            "image_urls": image_urls, "missing_sku": not sku or sku == "0",
            "missing_images": not image_urls, "missing_model_id": not model_id or model_id == "0",
        }

    @staticmethod
    def _supplier_count_key(value):
        """Normalize obvious supplier-name variants without fuzzy-merging brands."""
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()
        if normalized in {"", "null", "none", "nan", "n a", "na"}:
            return None
        suffixes = {"inc", "incorporated", "llc", "ltd", "limited", "co", "company", "corp", "corporation", "plc", "lp", "llp"}
        parts = normalized.split()
        while parts and parts[-1] in suffixes:
            parts.pop()
        return " ".join(parts) or None

    def search_trained_brands(self, page=1, page_size=50, sort_by="BrandName", sort_dir="asc", **filters):
        table = CSV_FILES["trained_brands"]["table"]
        where, params = self._trained_where(filters)
        allowed_sort = {"Id", "Class_Id", "SupplierName", "BrandName", "ImageCounts", "AvgTrainedPhotos", "Model", "Status"}
        sort_column = sort_by if sort_by in allowed_sort else "BrandName"
        direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
        page_size = max(1, min(int(page_size), 200))
        page = max(1, int(page))
        total = self.db.query(f"SELECT COUNT(*) AS total_matches FROM `{table}`{where}", tuple(params))
        rows = self.db.query(
            f"SELECT * FROM `{table}`{where} ORDER BY `{sort_column}` {direction}, `Id` LIMIT {page_size} OFFSET {(page - 1) * page_size}",
            tuple(params),
        )
        return {"records": [self._trained_record(row) for row in rows], "total_matches": int(total[0].get("total_matches") or 0) if total else 0, "page": page, "page_size": page_size}

    def get_trained_dataset_summary(self, filters=None):
        table = CSV_FILES["trained_brands"]["table"]
        where, params = self._trained_where(filters)
        supplier_rows = self.db.query(
            f"SELECT DISTINCT SupplierName FROM `{table}`{where}", tuple(params)
        )
        supplier_keys = {
            key for row in supplier_rows
            if (key := self._supplier_count_key(row.get("SupplierName"))) is not None
        }
        row = self.db.query(f"""SELECT COUNT(DISTINCT NULLIF(BrandCode, '')) AS total_brands,
                COALESCE(SUM({self._trained_numeric_cast('COALESCE(ImageCounts, 0)')}), 0) AS total_trained_images,
                COUNT(DISTINCT CASE WHEN Status = '1' OR LOWER(COALESCE(RecordStatus, '')) = 'active' THEN BrandCode END) AS active_brands,
                COUNT(DISTINCT CASE WHEN Status <> '1' AND LOWER(COALESCE(RecordStatus, '')) <> 'active' THEN BrandCode END) AS inactive_brands,
                COUNT(DISTINCT NULLIF(Model_Id, '')) AS total_unique_models,
                COUNT(DISTINCT NULLIF(Category_Wine_Spirits_Beer_Non_Alcoholic, '')) AS total_categories,
                SUM(CASE WHEN LOWER(COALESCE(SKU, '')) IN ('', '0', 'null', 'none', 'nan', 'n/a', 'na')
                    OR LOWER(COALESCE(ImageUrls, '')) IN ('', '""', 'null', 'none', 'nan', 'n/a', 'na', '0', '{{}}')
                    OR LOWER(COALESCE(Model_Id, '')) IN ('', '0', 'null', 'none', 'nan', 'n/a', 'na') THEN 1 ELSE 0 END) AS missing_data_records
                FROM `{table}`{where}""", tuple(params))
        row = row[0] if row else {}
        summary = {key: int(row.get(key) or 0) for key in ("total_brands", "total_trained_images", "active_brands", "inactive_brands", "total_unique_models", "total_categories", "missing_data_records")}
        summary["total_suppliers"] = len(supplier_keys)
        return summary

    def get_trained_dataset_analytics(self, filters=None):
        table = CSV_FILES["trained_brands"]["table"]
        where, params = self._trained_where(filters)
        def grouped(select, group, order, limit=10, group_sql=None):
            group_clause = group_sql or f"`{group}`"
            return self.db.query(f"SELECT {select} FROM `{table}`{where} GROUP BY {group_clause} ORDER BY {order} LIMIT {limit}", tuple(params))
        status_expression = "CASE WHEN Status = '1' OR LOWER(COALESCE(RecordStatus, '')) = 'active' THEN 'Active' ELSE 'Inactive' END"
        return {
            "category_brands": grouped("Category_Wine_Spirits_Beer_Non_Alcoholic AS category, COUNT(DISTINCT BrandCode) AS brand_count", "Category_Wine_Spirits_Beer_Non_Alcoholic", "brand_count DESC"),
            "top_suppliers": grouped("SupplierName AS supplier, COUNT(DISTINCT BrandCode) AS brand_count", "SupplierName", "brand_count DESC"),
            "top_brands": grouped(f"BrandName AS brand, SUM({self._trained_numeric_cast('COALESCE(ImageCounts, 0)')}) AS image_count", "BrandName", "image_count DESC"),
            "active_inactive": grouped(f"{status_expression} AS status, COUNT(DISTINCT BrandCode) AS brand_count", "status", "brand_count DESC", 2, status_expression),
            "model_brands": grouped("Model AS model, COUNT(DISTINCT BrandCode) AS brand_count", "Model", "brand_count DESC"),
            "category_images": grouped(f"Category_Wine_Spirits_Beer_Non_Alcoholic AS category, SUM({self._trained_numeric_cast('COALESCE(ImageCounts, 0)')}) AS image_count", "Category_Wine_Spirits_Beer_Non_Alcoholic", "image_count DESC", 20),
        }

    def get_trained_brand_detail(self, record_id):
        table = CSV_FILES["trained_brands"]["table"]
        rows = self.db.query(f"SELECT * FROM `{table}` WHERE Id = ? LIMIT 1", (str(record_id),))
        return {"record": self._trained_record(rows[0]) if rows else None}

    @staticmethod
    def _quality_summary(total_records, available_upcs, missing_upcs, invalid_upcs=0, distinct_upcs=None):
        total_records = int(total_records or 0)
        available_upcs = int(available_upcs or 0)
        missing_upcs = int(missing_upcs or 0)
        invalid_upcs = int(invalid_upcs or 0)
        distinct_upcs = int(available_upcs if distinct_upcs is None else distinct_upcs or 0)
        return {
            "total_records": total_records,
            "available_upcs": available_upcs,
            "missing_upcs": missing_upcs,
            "invalid_upcs": invalid_upcs,
            "distinct_upcs": distinct_upcs,
            "completion_percentage": round((available_upcs / total_records) * 100, 2) if total_records else 0.0,
        }

    def _table_upc_metrics(self, table):
        columns = {column.lower(): column for column in (self.db.table_columns(table) if hasattr(self.db, 'table_columns') else [])}
        upc_column = next((columns.get(name) for name in ('clean_upc', 'upccode', 'upc_13_digit', 'upc 13 digit', 'upc13digit') if columns.get(name)), None)
        upc_expression = f"`{upc_column}`" if upc_column else "NULL"
        row = self.db.query(f"""
            SELECT
                COUNT(*) AS total_records,
                SUM(CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) NOT IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN 1 ELSE 0 END) AS available_upcs,
                SUM(CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN 1 ELSE 0 END) AS missing_upcs,
                COUNT(DISTINCT CASE WHEN LOWER(TRIM(COALESCE({upc_expression}, ''))) NOT IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN TRIM({upc_expression}) END) AS distinct_upcs
            FROM `{table}`
        """)[0]
        return self._quality_summary(
            row.get("total_records"),
            row.get("available_upcs"),
            row.get("missing_upcs"),
            distinct_upcs=row.get("distinct_upcs"),
        )

sql_engine = SQLEngine()
