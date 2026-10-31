import pandas as pd
import logging
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

sql_engine = SQLEngine()
