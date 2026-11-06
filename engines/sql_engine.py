import csv
import pandas as pd
import logging
from collections import Counter
from config import CSV_FILES, TRAINED_BRANDS_FILE
from database.db_manager import db_manager
from data_ingestion.normalizer import normalize_upc

logger = logging.getLogger("SQLEngine")

class SQLEngine:
    def __init__(self, db=None):
        self.db = db or db_manager
        self._trained_brand_cache = None
        self._trained_brand_cache_mtime = None

    @staticmethod
    def _normalized_supplier_value(value):
        return str(value or "").strip().casefold()

    @staticmethod
    def _category_label(value):
        category = str(value or "").strip()
        normalized = category.casefold().replace("-", " ").replace("_", " ")
        if normalized in {"", "na", "n a", "n/a", "null", "none"}:
            return "Uncategorized"
        if normalized in {"beer", "wine", "spirits"}:
            return normalized.title()
        if "non" in normalized and "alcohol" in normalized:
            return "Non Alcoholic"
        return "Uncategorized" if category.isdigit() else category

    @staticmethod
    def _trained_image_urls(value):
        image_urls = []
        seen = set()
        for item in str(value or "").replace("\r", "\n").splitlines():
            for url in item.split(";"):
                cleaned = url.strip().strip("[]\"'")
                if cleaned and cleaned.casefold() not in seen:
                    seen.add(cleaned.casefold())
                    image_urls.append(cleaned)
        return image_urls

    def _trained_brand_rows(self):
        file_mtime = TRAINED_BRANDS_FILE.stat().st_mtime_ns
        if self._trained_brand_cache is None or file_mtime != self._trained_brand_cache_mtime:
            with TRAINED_BRANDS_FILE.open("r", encoding="utf-8-sig", newline="") as source:
                self._trained_brand_cache = list(csv.DictReader(source, delimiter="|"))
            self._trained_brand_cache_mtime = file_mtime
        return self._trained_brand_cache

    def _trained_brand_indexes(self):
        indexes = {
            "supplier_code_brand_code": {},
            "supplier_code_brand_name": {},
            "supplier_name_brand_code": {},
            "supplier_name_brand_name": {},
        }
        for row in self._trained_brand_rows():
            supplier_code = self._normalized_supplier_value(row.get("SupplierCode"))
            supplier_name = self._normalized_supplier_value(row.get("SupplierName"))
            brand_code = self._normalized_supplier_value(row.get("BrandCode"))
            brand_name = self._normalized_supplier_value(row.get("BrandName"))
            for key, index_name in (
                ((supplier_code, brand_code), "supplier_code_brand_code"),
                ((supplier_code, brand_name), "supplier_code_brand_name"),
                ((supplier_name, brand_code), "supplier_name_brand_code"),
                ((supplier_name, brand_name), "supplier_name_brand_name"),
            ):
                if key[0] and key[1]:
                    indexes[index_name].setdefault(key, []).append(row)
        return indexes

    @staticmethod
    def _matched_trained_rows(indexes, supplier_code, supplier_name, brand_code, brand_name):
        lookups = (
            ("supplier_code_brand_code", supplier_code, brand_code),
            ("supplier_code_brand_name", supplier_code, brand_name),
            ("supplier_name_brand_code", supplier_name, brand_code),
            ("supplier_name_brand_name", supplier_name, brand_name),
        )
        for index_name, first, second in lookups:
            key = (SQLEngine._normalized_supplier_value(first), SQLEngine._normalized_supplier_value(second))
            if key[0] and key[1] and indexes[index_name].get(key):
                return indexes[index_name][key]
        return []

    @staticmethod
    def _supplier_brand_summary(master_brand, trained_rows):
        distinct_rows = {}
        for row in trained_rows:
            key = tuple(str(row.get(field) or "").strip() for field in (
                "Id", "Class Id", "Category (Wine/Spirits/Beer/Non Alcoholic)",
                "Status", "RecordStatus", "SKU", "Model", "Model Id", "ImageCounts",
                "ImageUrls",
            ))
            distinct_rows.setdefault(key, row)
        trained_rows = list(distinct_rows.values())
        categories = sorted({
            SQLEngine._category_label(row.get("Category (Wine/Spirits/Beer/Non Alcoholic)"))
            for row in trained_rows
        }, key=lambda value: value.casefold())
        statuses = set()
        for row in trained_rows:
            status = str(row.get("RecordStatus") or row.get("Status") or "").strip()
            if status == "1":
                status = "Active"
            elif status in {"0", "2"}:
                status = "Inactive"
            if status:
                statuses.add(status)
        statuses = sorted(statuses, key=lambda value: value.casefold())

        def values(field):
            return sorted({
                str(row.get(field) or "").strip()
                for row in trained_rows
                if str(row.get(field) or "").strip()
            }, key=str.casefold)

        image_counts = []
        for row in trained_rows:
            try:
                image_counts.append(int(row.get("ImageCounts") or 0))
            except ValueError:
                continue
        return {
            "brand_name": str(master_brand.get("brand_name") or "").strip(),
            "brand_code": str(master_brand.get("brand_code") or "").strip(),
            "brand_ids": values("Id"),
            "brand_id": ", ".join(values("Id")),
            "class_ids": values("Class Id"),
            "class_id": ", ".join(values("Class Id")),
            "categories": categories or [SQLEngine._category_label(master_brand.get("product_category"))],
            "category": " / ".join(categories) if categories else SQLEngine._category_label(master_brand.get("product_category")),
            "statuses": statuses or ["Unknown"],
            "status": " / ".join(statuses) if statuses else "Unknown",
            "skus": values("SKU"),
            "sku": ", ".join(values("SKU")),
            "image_count": str(sum(image_counts)) if image_counts else "",
            "model_names": values("Model"),
            "model_name": ", ".join(values("Model")),
            "model_ids": values("Model Id"),
            "model_id": ", ".join(values("Model Id")),
            "_trained_rows": trained_rows,
        }

    def _supplier_brand_groups(self):
        trained_indexes = self._trained_brand_indexes()
        suppliers = {}
        table = CSV_FILES["ai_master"]["table"]
        rows = self.db.query(f"""
            SELECT DISTINCT SupplierCode AS supplier_code,
                   SupplierName AS supplier_name,
                   BrandCode AS brand_code,
                   BrandName AS brand_name,
                   ProductCategory AS product_category
            FROM `{table}`
            ORDER BY SupplierName, BrandName
        """)
        for row in rows:
            supplier_code = str(row.get("supplier_code") or "").strip()
            supplier_name = str(row.get("supplier_name") or "").strip() or "NA"
            supplier_name_key = self._normalized_supplier_value(supplier_name)
            supplier_key = f"name:{supplier_name_key}"
            supplier = suppliers.setdefault(supplier_key, {
                "supplier_key": supplier_key,
                "supplier_code": supplier_code,
                "_supplier_codes": [],
                "supplier": supplier_name,
                "brands_by_key": {},
            })
            if supplier_code and supplier_code not in supplier["_supplier_codes"]:
                supplier["_supplier_codes"].append(supplier_code)
            if not supplier.get("supplier_code") and supplier_code:
                supplier["supplier_code"] = supplier_code

            brand_code = str(row.get("brand_code") or "").strip()
            brand_name = str(row.get("brand_name") or "").strip()
            brand_code_key = self._normalized_supplier_value(brand_code)
            brand_name_key = self._normalized_supplier_value(brand_name)
            if not brand_code_key and not brand_name_key:
                continue
            brand_key = f"code:{brand_code_key}" if brand_code_key else f"name:{brand_name_key}"
            brand = supplier["brands_by_key"].setdefault(brand_key, {
                "brand_name": brand_name or brand_code,
                "brand_code": brand_code,
                "product_category": row.get("product_category"),
            })
            if not brand.get("product_category") and row.get("product_category"):
                brand["product_category"] = row.get("product_category")

        for supplier in suppliers.values():
            for brand in supplier["brands_by_key"].values():
                trained_rows = []
                for supplier_code in supplier["_supplier_codes"] or [""]:
                    trained_rows.extend(self._matched_trained_rows(
                        trained_indexes,
                        supplier_code,
                        supplier["supplier"],
                        brand["brand_code"],
                        brand["brand_name"],
                    ))
                brand.update(self._supplier_brand_summary(brand, trained_rows))
            supplier["brands"] = sorted(
                supplier.pop("brands_by_key").values(),
                key=lambda brand: (brand["brand_name"].casefold(), brand["brand_code"].casefold()),
            )
            supplier["brand_count"] = len(supplier["brands"])
        return suppliers

    def get_supplier_overview(self, search="", category="", supplier="", status="", sort="name"):
        """Return deduplicated suppliers with filtered brand counts and search options."""
        suppliers = list(self._supplier_brand_groups().values())
        query = self._normalized_supplier_value(search)
        selected_category = self._normalized_supplier_value(category)
        selected_status = self._normalized_supplier_value(status)
        selected_supplier = self._normalized_supplier_value(supplier)
        filtered = []
        for item in suppliers:
            supplier_codes = {
                self._normalized_supplier_value(code)
                for code in item.get("_supplier_codes", [])
            }
            supplier_text = " ".join((
                item["supplier"],
                *item.get("_supplier_codes", []),
            )).casefold()
            selected_code = selected_supplier[5:] if selected_supplier.startswith("code:") else selected_supplier
            if (
                selected_supplier
                and selected_supplier != item["supplier_key"].casefold()
                and selected_supplier not in supplier_text
                and selected_code not in supplier_codes
            ):
                continue
            matching_brands = [
                brand for brand in item["brands"]
                if (not selected_category or selected_category in {value.casefold() for value in brand["categories"]})
                and (not selected_status or selected_status in {value.casefold() for value in brand["statuses"]})
            ]
            if query:
                supplier_match = query in supplier_text
                matching_brands = [
                    brand for brand in matching_brands
                    if supplier_match or query in " ".join((
                        brand["brand_name"], brand["brand_code"],
                        brand["brand_id"], brand["class_id"],
                    )).casefold()
                ]
                if not supplier_match and not matching_brands:
                    continue
            if (selected_category or selected_status or query) and not matching_brands:
                continue
            filtered.append({
                "supplier_key": item["supplier_key"],
                "supplier_code": item["supplier_code"],
                "supplier": item["supplier"],
                "brand_count": len(matching_brands),
                "total_brand_count": item["brand_count"],
            })

        if sort == "highest":
            filtered.sort(key=lambda item: (-item["brand_count"], item["supplier"].casefold()))
        elif sort == "lowest":
            filtered.sort(key=lambda item: (item["brand_count"], item["supplier"].casefold()))
        else:
            filtered.sort(key=lambda item: item["supplier"].casefold())
        return {
            "total_suppliers": len(suppliers),
            "total_brands": sum(item["brand_count"] for item in suppliers),
            "filtered_suppliers": len(filtered),
            "suppliers": filtered,
        }

    def get_supplier_brands(self, supplier_key, search="", category="", status=""):
        """Return a selected supplier's complete or filtered, deduplicated brand list."""
        suppliers = self._supplier_brand_groups()
        supplier = suppliers.get(str(supplier_key or ""))
        if not supplier:
            return None
        query = self._normalized_supplier_value(search)
        selected_category = self._normalized_supplier_value(category)
        selected_status = self._normalized_supplier_value(status)
        supplier_matches = query and query in " ".join(
            (supplier["supplier"], supplier["supplier_code"])
        ).casefold()
        brands = [
            brand for brand in supplier["brands"]
            if (not selected_category or selected_category in {value.casefold() for value in brand["categories"]})
            and (not selected_status or selected_status in {value.casefold() for value in brand["statuses"]})
            and (
                not query or supplier_matches
                or query in " ".join((
                    brand["brand_name"], brand["brand_code"],
                    brand["brand_id"], brand["class_id"],
                )).casefold()
            )
        ]
        public_brands = [
            {key: value for key, value in brand.items() if key != "_trained_rows"}
            for brand in brands
        ]
        return {
            "supplier": supplier["supplier"],
            "supplier_code": supplier["supplier_code"],
            "total_brand_count": supplier["brand_count"],
            "brand_count": len(public_brands),
            "brands": public_brands,
        }

    def get_supplier_brand_details(self, supplier_code="", supplier_name="", brand_code="", brand_name=""):
        """Return AIMasterBrandData products/images and trained brand metadata."""
        conditions = []
        params = []
        if supplier_name:
            conditions.append("LOWER(TRIM(COALESCE(SupplierName, ''))) = LOWER(TRIM(?))")
            params.append(supplier_name)
        elif supplier_code:
            conditions.append("LOWER(TRIM(COALESCE(SupplierCode, ''))) = LOWER(TRIM(?))")
            params.append(supplier_code)
        if brand_code:
            conditions.append("LOWER(TRIM(COALESCE(BrandCode, ''))) = LOWER(TRIM(?))")
            params.append(brand_code)
        elif brand_name:
            conditions.append("LOWER(TRIM(COALESCE(BrandName, ''))) = LOWER(TRIM(?))")
            params.append(brand_name)
        if not conditions:
            raise ValueError("A supplier and brand identifier are required")
        master_table = CSV_FILES["ai_master"]["table"]
        master_records = self.db.query(f"""
            SELECT id AS master_id, SupplierCode AS supplier_code, SupplierName AS supplier,
                   BrandCode AS brand_code, BrandName AS brand_name, ProductCategory AS product_category,
                   ProductName AS product_name, UPCCode AS upc, clean_upc, ImageURL AS image_url,
                   '' AS high_res_image_url, '' AS mid_res_image_url, '' AS low_res_image_url
            FROM `{master_table}`
            WHERE {" AND ".join(conditions)}
            ORDER BY ProductName
        """, tuple(params))
        records = master_records
        if not records:
            return None

        first = master_records[0] if master_records else records[0]
        trained_indexes = self._trained_brand_indexes()
        trained_rows = self._matched_trained_rows(
            trained_indexes,
            supplier_code or first.get("supplier_code"),
            supplier_name or first.get("supplier"),
            brand_code or first.get("brand_code"),
            brand_name or first.get("brand_name"),
        )
        brand = self._supplier_brand_summary({
            "brand_name": first.get("brand_name"),
            "brand_code": first.get("brand_code"),
            "product_category": first.get("product_category"),
            "record_count": len(records),
        }, trained_rows)
        image_urls = []
        seen_images = set()
        for record in records:
            for image_field in ("image_url", "high_res_image_url", "mid_res_image_url", "low_res_image_url"):
                image_url = str(record.get(image_field) or "").strip()
                if image_url and image_url.casefold() not in seen_images:
                    seen_images.add(image_url.casefold())
                    image_urls.append(image_url)
        for trained in brand["_trained_rows"]:
            for image_url in self._trained_image_urls(trained.get("ImageUrls")):
                if image_url.casefold() not in seen_images:
                    seen_images.add(image_url.casefold())
                    image_urls.append(image_url)
        public_brand = {key: value for key, value in brand.items() if key != "_trained_rows"}
        products_by_key = {}
        for record in records:
            product_name = str(record.get("product_name") or "").strip()
            upc = str(record.get("upc") or record.get("clean_upc") or "").strip()
            product_key = self._normalized_supplier_value(upc or product_name)
            if product_key:
                products_by_key.setdefault(product_key, {
                    "product_name": product_name,
                    "upc": upc,
                })
        return {
            **public_brand,
            "supplier": first.get("supplier") or supplier_name or "NA",
            "supplier_code": first.get("supplier_code") or supplier_code or "",
            "master_id": first.get("master_id") or "",
            "images": image_urls,
            "products": list(products_by_key.values()),
        }

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

    def get_supplier_directory(self, limit=500):
        """Return supplier-wise Master Brand summaries and bounded detail rows."""
        table = CSV_FILES["ai_master"]["table"]
        safe_limit = max(1, min(int(limit), 500))
        supplier_key = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE LOWER(TRIM(SupplierName)) END"
        supplier_label = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE TRIM(SupplierName) END"
        brand_key = "CASE WHEN LOWER(TRIM(COALESCE(BrandName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN NULL ELSE LOWER(TRIM(BrandName)) END"
        upc_key = "CASE WHEN LOWER(TRIM(COALESCE(clean_upc, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na', '0') THEN NULL ELSE LOWER(TRIM(clean_upc)) END"

        summaries = self.db.query(f"""
            SELECT {supplier_key} AS supplier_key,
                   MIN({supplier_label}) AS supplier,
                   COUNT(*) AS record_count,
                   COUNT(DISTINCT {brand_key}) AS brand_count,
                   COUNT(DISTINCT {upc_key}) AS upc_count
            FROM `{table}`
            GROUP BY {supplier_key}
            ORDER BY CASE WHEN {supplier_key} = 'NA' THEN 1 ELSE 0 END, supplier
            LIMIT {safe_limit}
        """)

        suppliers = []
        for summary in summaries:
            key = str(summary.get("supplier_key") or summary.get("supplier") or "NA").strip().lower()
            label = str(summary.get("supplier") or "NA").strip() or "NA"
            if key in {"", "null", "none", "nan", "n/a", "na"}:
                key, label = "NA", "NA"
            where = f"{supplier_key} = ?"
            brand_rows = self.db.query(
                f"SELECT DISTINCT BrandName AS brand_name FROM `{table}` WHERE {where} AND {brand_key} IS NOT NULL ORDER BY brand_name",
                (key,),
            )
            brand_names = []
            seen_brands = set()
            for row in brand_rows:
                name = str(row.get("brand_name") or "").strip()
                if name and name.lower() not in seen_brands:
                    seen_brands.add(name.lower())
                    brand_names.append(name)

            records = self.db.query(
                f"SELECT BrandName, ProductName, clean_upc, source_file, original_row FROM `{table}` WHERE {where} ORDER BY BrandName, ProductName LIMIT 25",
                (key,),
            )
            suppliers.append({
                "supplier": label,
                "record_count": int(summary.get("record_count") or 0),
                "brand_count": int(summary.get("brand_count") or 0),
                "brand_names": brand_names,
                "upc_count": int(summary.get("upc_count") or 0),
                "records": records,
            })

        return {"total_suppliers": len(suppliers), "suppliers": suppliers}

    def get_supplier_dashboard(self):
        """Return complete supplier and brand record counts from Master Brand data."""
        table = CSV_FILES["ai_master"]["table"]
        supplier_key = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE LOWER(TRIM(SupplierName)) END"
        supplier_label = "CASE WHEN LOWER(TRIM(COALESCE(SupplierName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN 'NA' ELSE TRIM(SupplierName) END"
        brand_key = "CASE WHEN LOWER(TRIM(COALESCE(BrandName, ''))) IN ('', 'null', 'none', 'nan', 'n/a', 'na') THEN NULL ELSE LOWER(TRIM(BrandName)) END"
        brand_label = "CASE WHEN {brand_key} IS NULL THEN NULL ELSE TRIM(BrandName) END".format(brand_key=brand_key)
        rows = self.db.query(f"""
            SELECT {supplier_key} AS supplier_key,
                   MIN({supplier_label}) AS supplier,
                   {brand_key} AS brand_key,
                   MIN({brand_label}) AS brand_name,
                   COUNT(*) AS record_count
            FROM `{table}`
            WHERE LOWER(TRIM(COALESCE(SupplierName, ''))) NOT IN ('', 'null', 'none', 'nan', 'n/a', 'na')
            GROUP BY {supplier_key}, {brand_key}
            ORDER BY supplier, brand_name
        """)

        suppliers_by_key = {}
        for row in rows:
            supplier_key_value = str(row.get("supplier_key") or "NA").strip().lower() or "na"
            supplier = suppliers_by_key.setdefault(supplier_key_value, {
                "supplier": str(row.get("supplier") or "NA").strip() or "NA",
                "record_count": 0,
                "brand_count": 0,
                "brands": [],
            })
            record_count = int(row.get("record_count") or 0)
            supplier["record_count"] += record_count
            brand_name = str(row.get("brand_name") or "").strip()
            if row.get("brand_key") is not None and brand_name:
                supplier["brands"].append({
                    "brand_name": brand_name,
                    "record_count": record_count,
                })
                supplier["brand_count"] += 1

        suppliers = sorted(
            suppliers_by_key.values(),
            key=lambda item: (item["supplier"].upper() == "NA", item["supplier"].casefold()),
        )
        return {"total_suppliers": len(suppliers), "suppliers": suppliers}

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
