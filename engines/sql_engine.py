import pandas as pd
import logging
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
            "id", "masterbrandid", "master_brand_id", "masterbrandid", "master_id"
        ) if name in column_lookup), None)
        brand_column = column_lookup.get("norm_brand") or column_lookup.get("brandname")
        product_column = column_lookup.get("productname") or column_lookup.get("product")
        clean_upc_column = column_lookup.get("clean_upc")
        clean_alt_column = column_lookup.get("clean_alt_upc")

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
        rows = self.db.query(
            f"SELECT * FROM `{table}` WHERE {' AND '.join(conditions)} LIMIT {safe_limit}",
            tuple(params),
        )
        result_columns = list(rows[0].keys()) if rows else columns
        return {
            "columns": result_columns,
            "records": rows,
            "total_matches": len(rows),
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
        stats = []
        for key, conf in CSV_FILES.items():
            tbl = conf['table']
            try:
                row_count = self.db.query(f"SELECT COUNT(*) as c FROM `{tbl}`")[0]['c']
                upc_count = self.db.query(f"SELECT COUNT(DISTINCT clean_upc) as c FROM `{tbl}` WHERE clean_upc != ''")[0]['c']
            except Exception:
                row_count = 0
                upc_count = 0
            stats.append({
                "dataset_key": key,
                "file_name": conf['file'],
                "table_name": tbl,
                "total_rows": row_count,
                "unique_upcs": upc_count
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
        master_id_column = master_column_lookup.get('id') or master_column_lookup.get('masterbrandid') or master_column_lookup.get('master_brand_id')
        id_expression = f"`{master_id_column}`" if master_id_column else "NULL"
        master = self.db.query(f"""
            SELECT
                COUNT(*) AS master_record_count,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE(norm_brand, '')), '')) AS unique_brands,
                COUNT(DISTINCT NULLIF(TRIM(COALESCE({id_expression}, '')), '')) AS unique_master_ids,
                SUM(CASE WHEN TRIM(COALESCE(clean_upc, '')) != '' THEN 1 ELSE 0 END) AS available_upcs,
                SUM(CASE WHEN TRIM(COALESCE(clean_upc, '')) = '' THEN 1 ELSE 0 END) AS missing_upcs
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
            },
        }

    @staticmethod
    def _quality_summary(total_records, available_upcs, missing_upcs, invalid_upcs=0):
        total_records = int(total_records or 0)
        available_upcs = int(available_upcs or 0)
        missing_upcs = int(missing_upcs or 0)
        invalid_upcs = int(invalid_upcs or 0)
        return {
            "total_records": total_records,
            "available_upcs": available_upcs,
            "missing_upcs": missing_upcs,
            "invalid_upcs": invalid_upcs,
            "completion_percentage": round((available_upcs / total_records) * 100, 2) if total_records else 0.0,
        }

    def _table_upc_metrics(self, table):
        row = self.db.query(f"""
            SELECT
                COUNT(*) AS total_records,
                SUM(CASE WHEN TRIM(COALESCE(clean_upc, '')) != '' THEN 1 ELSE 0 END) AS available_upcs,
                SUM(CASE WHEN TRIM(COALESCE(clean_upc, '')) = '' THEN 1 ELSE 0 END) AS missing_upcs
            FROM `{table}`
        """)[0]
        return self._quality_summary(
            row.get("total_records"),
            row.get("available_upcs"),
            row.get("missing_upcs"),
        )

sql_engine = SQLEngine()
