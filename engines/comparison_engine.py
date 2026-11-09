import pandas as pd
import json
import logging
import re
from config import CSV_FILES, REPORTS_DIR
from database.db_manager import db_manager

logger = logging.getLogger("ComparisonEngine")

class ComparisonEngine:
    def __init__(self, db=None):
        self.db = db or db_manager

    def compare_master_vs_categorization(self, cat_key='cat_beer', limit=500, search=None):
        """
        Compare AIMasterBrandData vs a Categorization Sheet (Beer, RTDs, Spirits, or Wine).
        Classifies records into Exact Match, Partial Match, Mismatch, Missing in Master, Duplicate.
        """
        master_table = CSV_FILES['ai_master']['table']
        cat_table = CSV_FILES.get(cat_key, {}).get('table', 'cat_beer')
        cat_file = CSV_FILES.get(cat_key, {}).get('file', cat_key)

        # 1. Total counts
        master_count = self.db.query(f"SELECT COUNT(*) as c FROM `{master_table}`")[0]['c']
        cat_count = self.db.query(f"SELECT COUNT(*) as c FROM `{cat_table}`")[0]['c']

        # 2. Overlap query (matching UPCs)
        search_clause = ""
        search_params = ()
        if search:
            search_clause = " AND (LOWER(COALESCE(m.BrandName,'')) LIKE ? OR LOWER(COALESCE(c.norm_brand,'')) LIKE ? OR LOWER(COALESCE(c.Product,'')) LIKE ? OR c.clean_upc LIKE ?)"
            needle = f"%{search.lower()}%"
            search_params = (needle, needle, needle, f"%{search}%")
        match_sql = f"""
        SELECT 
            c.clean_upc AS upc,
            m.source_file AS master_file,
            m.original_row AS master_row,
            m.BrandName AS master_brand,
            m.SupplierName AS master_supplier,
            m.ProductName AS master_product_type,
            c.source_file AS cat_file,
            c.original_row AS cat_row,
            c.norm_brand AS cat_brand,
            COALESCE(c.Product, c.clean_upc) AS cat_product_desc
        FROM `{cat_table}` c
        JOIN `{master_table}` m ON c.clean_upc = m.clean_upc
        WHERE c.clean_upc != ''{search_clause}
        LIMIT {limit}
        """
        matches = self.db.query(match_sql, search_params)

        # Classify each match
        records = []
        exact_matches = 0
        partial_matches = 0
        brand_mismatches = 0

        for r in matches:
            m_brand = (r.get('master_brand') or '').strip().upper()
            c_brand = (r.get('cat_brand') or '').strip().upper()

            if m_brand == c_brand:
                status = "Exact Match"
                reason = "UPC and Brand Name align perfectly"
                exact_matches += 1
            elif m_brand in c_brand or c_brand in m_brand:
                status = "Partial Match"
                reason = f"Brand variation: Master='{r.get('master_brand')}' vs Sheet='{r.get('cat_brand')}'"
                partial_matches += 1
            else:
                status = "Mismatch"
                reason = f"Brand discrepancy: Master='{r.get('master_brand')}' vs Sheet='{r.get('cat_brand')}'"
                brand_mismatches += 1

            records.append({
                "upc": r.get('upc'),
                "status": status,
                "reason": reason,
                "master_brand": r.get('master_brand'),
                "cat_brand": r.get('cat_brand'),
                "master_file": r.get('master_file'),
                "master_row": r.get('master_row'),
                "cat_file": r.get('cat_file'),
                "cat_row": r.get('cat_row'),
                "product_desc": r.get('cat_product_desc')
            })

        # 3. Missing in Master (present in Cat Sheet but missing from Master)
        missing_search_clause = ""
        missing_search_params = ()
        if search:
            missing_search_clause = " AND (LOWER(COALESCE(c.norm_brand,'')) LIKE ? OR LOWER(COALESCE(c.Product,'')) LIKE ? OR c.clean_upc LIKE ?)"
            needle = f"%{search.lower()}%"
            missing_search_params = (needle, needle, f"%{search}%")
        missing_in_master_sql = f"""
        SELECT 
            c.clean_upc AS upc,
            c.source_file AS cat_file,
            c.original_row AS cat_row,
            c.norm_brand AS cat_brand,
            COALESCE(c.Product, c.clean_upc) AS cat_product_desc
        FROM `{cat_table}` c
        LEFT JOIN `{master_table}` m ON c.clean_upc = m.clean_upc
        WHERE m.clean_upc IS NULL AND c.clean_upc != ''{missing_search_clause}
        LIMIT {min(limit, 200)}
        """
        missing_rows = self.db.query(missing_in_master_sql, missing_search_params)
        for r in missing_rows:
            records.append({
                "upc": r.get('upc'),
                "status": "Missing Record",
                "reason": f"UPC exists in {cat_file} but is completely missing from Master",
                "master_brand": "MISSING",
                "cat_brand": r.get('cat_brand'),
                "master_file": "AIMasterBrandData.csv",
                "master_row": "N/A",
                "cat_file": r.get('cat_file'),
                "cat_row": r.get('cat_row'),
                "product_desc": r.get('cat_product_desc')
            })

        # 4. Aggregated stats
        total_matched_count = self.db.query(f"""
            SELECT COUNT(DISTINCT c.clean_upc) as c
            FROM `{cat_table}` c
            JOIN `{master_table}` m ON c.clean_upc = m.clean_upc
            WHERE c.clean_upc != ''
        """)[0]['c']

        total_cat_upcs = self.db.query(f"SELECT COUNT(DISTINCT clean_upc) as c FROM `{cat_table}` WHERE clean_upc != ''")[0]['c']
        missing_from_master_total = total_cat_upcs - total_matched_count

        category_labels = {
            "cat_beer": "Beer",
            "cat_rtd": "RTD",
            "cat_spirits": "Spirits",
            "cat_wine": "Wine",
        }
        return {
            "comparison_type": f"Master vs {category_labels.get(cat_key, cat_key)}",
            "summary": {
                "master_total_records": master_count,
                "categorization_total_records": cat_count,
                "categorization_unique_upcs": total_cat_upcs,
                "matching_upcs_in_both": total_matched_count,
                "missing_from_master_total": missing_from_master_total,
                "match_rate_pct": round((total_matched_count / total_cat_upcs * 100), 2) if total_cat_upcs else 0,
                "sample_analyzed": len(records),
                "exact_matches_in_sample": exact_matches,
                "partial_matches_in_sample": partial_matches,
                "mismatches_in_sample": brand_mismatches,
                "missing_in_sample": len(missing_rows)
            },
            "records": records
        }

    def compare_allbrand_vs_supplier(self, limit=500):
        """
        Compare AllBrand / AIMaster with Supplier master sheet ($Supplier_202610291521.csv).
        Checks for supplier name mismatches, missing suppliers, and inactive/orphan codes.
        """
        master_table = CSV_FILES['ai_master']['table']
        supplier_table = CSV_FILES['suppliers']['table']

        # Join on SupplierCode
        sql = f"""
        SELECT 
            m.SupplierCode AS supplier_code,
            m.SupplierName AS master_supplier_name,
            m.BrandName AS brand_name,
            m.source_file AS master_file,
            m.original_row AS master_row,
            s.SupplierName AS official_supplier_name,
            s.RecordStatusId AS supplier_status,
            s.source_file AS supplier_file,
            s.original_row AS supplier_row
        FROM `{master_table}` m
        LEFT JOIN `{supplier_table}` s ON m.SupplierCode = s.SupplierCode
        WHERE m.SupplierCode IS NOT NULL AND m.SupplierCode != ''
        LIMIT {limit}
        """
        rows = self.db.query(sql)

        records = []
        exact = 0
        mismatch = 0
        missing = 0

        for r in rows:
            m_supp = (r.get('master_supplier_name') or '').strip().upper()
            o_supp = (r.get('official_supplier_name') or '').strip().upper()

            if not o_supp:
                status = "Missing Record"
                reason = f"SupplierCode {r.get('supplier_code')} in Brand sheet not found in Supplier master"
                missing += 1
            elif m_supp == o_supp:
                status = "Exact Match"
                reason = "Supplier name matches official master"
                exact += 1
            else:
                status = "Mismatch"
                reason = f"Supplier name discrepancy: Brand='{r.get('master_supplier_name')}' vs Master='{r.get('official_supplier_name')}'"
                mismatch += 1

            records.append({
                "supplier_code": r.get('supplier_code'),
                "status": status,
                "reason": reason,
                "brand_name": r.get('brand_name'),
                "brand_supplier_name": r.get('master_supplier_name'),
                "official_supplier_name": r.get('official_supplier_name') or "MISSING",
                "master_file": r.get('master_file'),
                "master_row": r.get('master_row'),
                "supplier_file": r.get('supplier_file') or "$Supplier_202610291521.csv",
                "supplier_row": r.get('supplier_row') or "N/A"
            })

        return {
            "comparison_type": "AllBrand vs Supplier Sheet",
            "summary": {
                "records_analyzed": len(records),
                "exact_matches": exact,
                "mismatches": mismatch,
                "missing_in_supplier_sheet": missing
            },
            "records": records
        }

    def compare_beer_vs_rtd(self, limit=500):
        """
        Compare Beer vs RTD categorization.
        Flags products that cross both categories and checks for classification discrepancies.
        """
        beer_table = CSV_FILES['cat_beer']['table']
        rtd_table = CSV_FILES['cat_rtd']['table']

        sql = f"""
        SELECT 
            b.clean_upc AS upc,
            b.Beer_Brands_Value AS beer_brand,
            b.Beer_Category_Value AS beer_category,
            b.Beer_Segments_Value AS beer_segment,
            b.source_file AS beer_file,
            b.original_row AS beer_row,
            r.Brands_Value AS rtd_brand,
            r.RTD_Category_Value AS rtd_category,
            r.RTD_Alcohol_Base_Value AS rtd_alcohol_base,
            r.RTD_Segment_Value AS rtd_segment,
            r.source_file AS rtd_file,
            r.original_row AS rtd_row
        FROM `{beer_table}` b
        JOIN `{rtd_table}` r ON b.clean_upc = r.clean_upc
        WHERE b.clean_upc != ''
        LIMIT {limit}
        """
        rows = self.db.query(sql)

        records = []
        for r in rows:
            rtd_cat = (r.get('rtd_category') or '').strip().upper()
            rtd_base = (r.get('rtd_alcohol_base') or '').strip().upper()
            
            if 'NON RTD' in rtd_cat or 'NON RTD' in rtd_base:
                status = "Exact Match"
                reason = "Correctly categorized as Beer and flagged as NON RTD in RTD dataset"
            elif 'FAB' in rtd_cat or 'SELTZER' in rtd_base or 'MALT' in rtd_base:
                status = "Requires Verification"
                reason = f"Dual Classification: Listed as '{r.get('beer_category')}' in Beer but '{r.get('rtd_category')}' in RTD"
            else:
                status = "Mismatch"
                reason = f"Category conflict: Beer='{r.get('beer_category')}' vs RTD='{r.get('rtd_category')}'"

            records.append({
                "upc": r.get('upc'),
                "status": status,
                "reason": reason,
                "beer_brand": r.get('beer_brand'),
                "beer_category": r.get('beer_category'),
                "beer_segment": r.get('beer_segment'),
                "rtd_brand": r.get('rtd_brand'),
                "rtd_category": r.get('rtd_category'),
                "rtd_base": r.get('rtd_alcohol_base'),
                "beer_file": r.get('beer_file'),
                "beer_row": r.get('beer_row'),
                "rtd_file": r.get('rtd_file'),
                "rtd_row": r.get('rtd_row')
            })

        return {
            "comparison_type": "Beer vs RTD Categorization Validation",
            "summary": {
                "overlapping_sample": len(records),
                "verified_non_rtd": sum(1 for x in records if x['status'] == 'Exact Match'),
                "requires_verification": sum(1 for x in records if x['status'] == 'Requires Verification'),
                "mismatches": sum(1 for x in records if x['status'] == 'Mismatch')
            },
            "records": records
        }

    def find_duplicate_upcs_across_all(self, limit=100):
        """Find UPCs appearing in multiple distinct datasets."""
        # Query distinct UPC count across tables
        union_sql = f"""
        SELECT clean_upc, source_file, original_row, norm_brand FROM `{CSV_FILES['ai_master']['table']}` WHERE clean_upc != ''
        UNION ALL
        SELECT clean_upc, source_file, original_row, norm_brand FROM `{CSV_FILES['cat_beer']['table']}` WHERE clean_upc != ''
        UNION ALL
        SELECT clean_upc, source_file, original_row, norm_brand FROM `{CSV_FILES['cat_rtd']['table']}` WHERE clean_upc != ''
        UNION ALL
        SELECT clean_upc, source_file, original_row, norm_brand FROM `{CSV_FILES['cat_spirits']['table']}` WHERE clean_upc != ''
        UNION ALL
        SELECT clean_upc, source_file, original_row, norm_brand FROM `{CSV_FILES['cat_wine']['table']}` WHERE clean_upc != ''
        """
        
        dup_query = f"""
        WITH all_records AS ({union_sql})
        SELECT clean_upc, COUNT(DISTINCT source_file) AS file_count, GROUP_CONCAT(DISTINCT source_file) AS files, GROUP_CONCAT(DISTINCT norm_brand) AS brands, COUNT(*) as total_occurrences
        FROM all_records
        GROUP BY clean_upc
        HAVING file_count > 1
        ORDER BY total_occurrences DESC
        LIMIT {limit}
        """
        dups = self.db.query(dup_query)
        
        results = []
        for d in dups:
            results.append({
                "upc": d.get('clean_upc'),
                "status": "Duplicate Record",
                "file_count": d.get('file_count'),
                "files_present": d.get('files'),
                "brands": d.get('brands'),
                "total_occurrences": d.get('total_occurrences'),
                "reason": f"UPC appears across {d.get('file_count')} different files"
            })

        return {
            "comparison_type": "Cross-File Duplicate UPC Audit",
            "summary": {
                "duplicates_found_in_sample": len(results)
            },
            "records": results
        }

    def compare_all_missing_in_master(self, limit_per_category=200, search=None):
        """
        Compare all 4 categorization sheets (Beer, Wine, RTD, Spirits) against AIMasterBrandData.
        Identifies all UPCs that exist in categorization sheets but are missing from Master Brands.
        """
        categories = [
            ("Beer", CSV_FILES['cat_beer']['table'], "Beer_Brands_Value", "Product", "Categorization 2026 - Beer.csv"),
            ("Wine", CSV_FILES['cat_wine']['table'], "Brands_Value", "Product", "Categorization 2026 - Wine.csv"),
            ("RTD", CSV_FILES['cat_rtd']['table'], "Brands_Value", "Product", "Categorization 2026 - RTDs.csv"),
            ("Spirits", CSV_FILES['cat_spirits']['table'], "Spirits_Brands_Value", "Product", "Categorization 2026 - Spirits.csv")
        ]

        master_table = CSV_FILES['ai_master']['table']
        category_summaries = []
        all_missing_records = []
        total_unique_cat_upcs = 0
        total_matched_upcs = 0
        total_missing_upcs = 0

        for cat_name, tbl, brand_col, prod_col, fname in categories:
            total_cat = self.db.query(f"SELECT COUNT(DISTINCT clean_upc) as c FROM `{tbl}` WHERE clean_upc != ''")[0]['c']
            matched_count = self.db.query(f"""
                SELECT COUNT(DISTINCT c.clean_upc) as c 
                FROM `{tbl}` c 
                JOIN `{master_table}` m ON c.clean_upc = m.clean_upc 
                WHERE c.clean_upc != ''
            """)[0]['c']
            missing_count = total_cat - matched_count
            pct_missing = round((missing_count / total_cat * 100), 1) if total_cat else 0

            total_unique_cat_upcs += total_cat
            total_matched_upcs += matched_count
            total_missing_upcs += missing_count

            category_summaries.append({
                "category": cat_name,
                "total_upcs": total_cat,
                "matched_in_master": matched_count,
                "missing_from_master": missing_count,
                "pct_missing": f"{pct_missing}%",
                "source_file": fname
            })

            # Retrieve sample missing records
            search_clause = ""
            search_params = ()
            if search:
                search_clause = f" AND (LOWER(COALESCE(c.{brand_col},'')) LIKE ? OR LOWER(COALESCE(c.{prod_col},'')) LIKE ? OR c.clean_upc LIKE ?)"
                needle = f"%{search.lower()}%"
                search_params = (needle, needle, f"%{search}%")
            missing_sql = f"""
            SELECT 
                '{cat_name}' AS category,
                c.clean_upc AS upc,
                COALESCE(c.{brand_col}, 'N/A') AS brand,
                COALESCE(c.{prod_col}, 'N/A') AS product,
                c.source_file AS source_file,
                c.original_row AS original_row,
                'Missing Record' AS status,
                'UPC exists in {fname} but is missing from Master Brands' AS reason
            FROM `{tbl}` c
            LEFT JOIN `{master_table}` m ON c.clean_upc = m.clean_upc
            WHERE m.clean_upc IS NULL AND c.clean_upc != ''{search_clause}
            LIMIT {limit_per_category}
            """
            rows = self.db.query(missing_sql, search_params)
            all_missing_records.extend(rows)

        return {
            "comparison_type": "Missing UPC Audit: Beer, Wine, RTD & Spirits vs Master",
            "summary": {
                "categories": category_summaries,
                "total_categorization_upcs": total_unique_cat_upcs,
                "total_matched_in_master": total_matched_upcs,
                "total_missing_from_master": total_missing_upcs,
                "overall_missing_pct": round((total_missing_upcs / total_unique_cat_upcs * 100), 1) if total_unique_cat_upcs else 0,
                "sample_missing_records": len(all_missing_records)
            },
            "records": all_missing_records
        }

    def find_untrained_brands(self, limit=None, search=None):
        """Return brands marked as ``New`` or ``NeedToVerify`` in category datasets.

        This intentionally does not compare UPCs or trained records. The
        category sheet's Dataset column is the source of truth for whether a
        brand belongs in the untrained dataset.
        """
        category_sheets = [
            ('Beer', CSV_FILES['cat_beer']['table'], 'Beer_Brands_Value'),
            ('Wine', CSV_FILES['cat_wine']['table'], 'Brands_Value'),
            ('Spirits', CSV_FILES['cat_spirits']['table'], 'Spirits_Brands_Value'),
            ('RTD', CSV_FILES['cat_rtd']['table'], 'Brands_Value'),
        ]

        records = []
        for category, table, brand_column in category_sheets:
            rows = self.db.query(f"""
                SELECT COALESCE({brand_column}, '') AS brand_name,
                       source_file,
                       original_row
                FROM `{table}`
                WHERE LOWER(REPLACE(TRIM(COALESCE(Dataset, '')), ' ', ''))
                      IN ('new', 'needtoverify')
            """)
            for row in rows:
                brand_name = str(row.get('brand_name') or '').strip()
                if not brand_name:
                    continue
                records.append({
                    'brand_name': brand_name,
                    'category': category,
                    'source': str(row.get('source_file') or '').strip(),
                })

        records.sort(key=lambda item: item['brand_name'].lower())
        if search:
            needle = str(search).strip().lower()
            records = [item for item in records if needle in item['brand_name'].lower()]
        export_records = records[:]
        if limit is not None:
            records = records[:max(1, min(int(limit), 50000))]

        return {
            'comparison_type': 'Untrained Brands: New/NeedToVerify rows from Beer, Wine, Spirits & RTD datasets',
            'process': [
                'Beer Dataset = New or NeedToVerify',
                'Wine Dataset = New or NeedToVerify',
                'Spirits Dataset = New or NeedToVerify',
                'RTD Dataset = New or NeedToVerify',
                'Keep every New or NeedToVerify brand row; no deduplication',
            ],
            'records': records,
            'export_records': export_records,
        }

comparison_engine = ComparisonEngine()
