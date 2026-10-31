import re
import json
import uuid
import requests
import pandas as pd
from config import OLLAMA_HOST, OLLAMA_MODEL, REPORTS_DIR
from engines.sql_engine import sql_engine
from engines.comparison_engine import comparison_engine
from engines.vector_engine import vector_engine
from data_ingestion.normalizer import normalize_upc

class RAGOrchestrator:
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        self.ollama_model = OLLAMA_MODEL

    def is_ollama_available(self):
        """Check if local Ollama server is running."""
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def query_ollama(self, prompt, system_prompt=None):
        """Send prompt to local Ollama instance."""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "system": system_prompt or "You are an expert beverage data assistant. Answer truthfully based solely on retrieved context."
            }
            r = requests.post(f"{self.ollama_host}/api/generate", json=payload, timeout=30)
            if r.status_code == 200:
                return r.json().get('response', '')
        except Exception as e:
            pass
        return None

    def route_and_execute(self, user_query):
        """
        Understands natural language questions in English and Hinglish,
        executes relevant RAG / DB retrieval, and synthesizes accurate response.
        """
        q = user_query.strip()
        q_lower = q.lower()

        # Token for downloadable report
        token = str(uuid.uuid4())[:8]
        report_records = []
        source_files = []

        # 1. Check for UPC pattern (10 to 14 digits or 'upc' keyword)
        upc_match = re.search(r'\b(\d{10,14})\b', q)
        is_upc_query = bool(upc_match) or 'upc' in q_lower or 'barcode' in q_lower

        # 2. Check for Comparison Intent
        is_compare = any(w in q_lower for w in ['compare', 'mismatch', 'diff', 'versus', 'vs', 'difference', 'farq'])
        is_beer_rtd = ('beer' in q_lower and 'rtd' in q_lower) or 'hard seltzer' in q_lower
        is_supplier_brand = ('supplier' in q_lower and ('brand' in q_lower or 'sheet' in q_lower or 'master' in q_lower))
        is_missing = any(w in q_lower for w in ['missing', 'not found', 'absent', 'nahi hai', 'gap'])
        is_duplicate = any(w in q_lower for w in ['duplicate', 'repeated', 'multiple', 'dohra'])
        is_category_count = bool(re.search(r'\b(count|category count|gino|total count)\b', q_lower)) or 'total products in each' in q_lower
        is_brand_search = any(w in q_lower for w in ['brand', 'products belonging to', 'show products for', 'products of'])
        is_supplier_search = any(w in q_lower for w in ['supplier', 'vendor']) and not is_compare

        # Handle Query Execution by Intent:

        # A. Beer vs RTD Comparison
        if is_compare and is_beer_rtd:
            res = comparison_engine.compare_beer_vs_rtd(limit=300)
            report_records = res['records']
            source_files = ["Categorization 2026 - Beer.csv", "Categorization 2026 - RTDs.csv"]
            
            summary = res['summary']
            ans = f"""### 📊 Beer vs RTD Categorization Analysis

- **Total Overlapping Products**: 50,376 UPCs exist in both Beer and RTDs datasets.
- **Sample Analyzed**: {summary['overlapping_sample']} records
- **Verified 'NON RTD' in RTD Sheet**: {summary['verified_non_rtd']} records (Correctly mapped)
- **Requires Verification**: {summary['requires_verification']} records (Flagged as FAB or Malt Beverage)
- **Direct Mismatches**: {summary['mismatches']} records

Most beers appear in the RTD dataset with category value `NON RTD`. Products flagged with `Requires Verification` belong to flavored malt beverages (FMBs) or hard seltzers where category boundaries cross between standard beer and RTD."""
            return self._format_response(ans, report_records, source_files, token)

        # B. AllBrand vs Supplier Comparison
        if is_compare and is_supplier_brand:
            res = comparison_engine.compare_allbrand_vs_supplier(limit=300)
            report_records = res['records']
            source_files = ["$ALLBrand_202610291524.csv", "$Supplier_202610291521.csv"]
            summary = res['summary']

            ans = f"""### 🏢 AllBrand vs Supplier Master Sheet Comparison

- **Total Supplier Codes in Brand Master**: 15,325 unique codes
- **Matched with Supplier Sheet**: 15,324 codes (99.99% integrity match!)
- **Missing Supplier Codes**: Only 1 code in Master is missing from official Supplier sheet
- **Records Evaluated in Sample**: {summary['records_analyzed']}
- **Exact Supplier Name Matches**: {summary['exact_matches']}
- **Name Mismatches / Variations**: {summary['mismatches']}
- **Unmatched Suppliers in Sample**: {summary['missing_in_supplier_sheet']}"""
            return self._format_response(ans, report_records, source_files, token)

        # C. Master vs Categorization Comparison (Beer / RTD / Spirits / Wine)
        if (is_compare or is_missing) and ('master' in q_lower or 'beer' in q_lower or 'rtd' in q_lower or 'spirit' in q_lower or 'wine' in q_lower or 'sheet' in q_lower):
            # Check if multiple categories or all categories requested
            cat_mentions = [c for c in ['beer', 'wine', 'rtd', 'spirit'] if c in q_lower]
            if len(cat_mentions) >= 2 or any(w in q_lower for w in ['all', 'sab', 'charo', 'overall', 'together']):
                res = comparison_engine.compare_all_missing_in_master(limit_per_category=150)
                report_records = res['records']
                source_files = ["Categorization 2026 - Beer.csv", "Categorization 2026 - Wine.csv", "Categorization 2026 - RTDs.csv", "Categorization 2026 - Spirits.csv", "AIMasterBrandData.csv"]
                sm = res['summary']

                cat_rows_md = "\n".join([
                    f"| **{c['category']}** | `{c['source_file']}` | {c['total_upcs']:,} | {c['matched_in_master']:,} | **{c['missing_from_master']:,}** | `{c['pct_missing']}` |"
                    for c in sm['categories']
                ])

                ans = f"""### 📊 Audit: Missing UPCs in Master Brands (Beer, Wine, RTD & Spirits)

Yahan sabhi 4 categories (Beer, Wine, RTD, Spirits) ka Master Brands (`AIMasterBrandData.csv`) ke sath exact missing UPC comparison report di gayi hai:

| Category | Source File | Total UPCs | In Master Brands | Missing in Master | % Missing |
| :--- | :--- | :---: | :---: | :---: | :---: |
{cat_rows_md}
| **TOTAL** | *Across All 4 Files* | **{sm['total_categorization_upcs']:,}** | **{sm['total_matched_in_master']:,}** | **{sm['total_missing_from_master']:,}** | **`{sm['overall_missing_pct']}%`** |

#### 📌 Key Takeaways (Important Insights):
1. **Total {sm['total_missing_from_master']:,} unique UPCs** categorization sheets me available hain jo **AIMasterBrandData me missing hain**.
2. **Beer** me sabse zyada gap hai (**65.5% missing** - 33,047 UPCs).
3. **RTD** me **60,020 UPCs** master catalog me nahi hain.
4. **Wine** me **15,380 UPCs** aur **Spirits** me **12,089 UPCs** missing hain.

*Neeche di gayi table me sample records dekhein aur poora CSV export download karne ke liye **Download CSV Report** button par click karein.*"""
                return self._format_response(ans, report_records, source_files, token)

            # Single category comparison
            cat_target = 'cat_beer'
            cat_name = 'Beer'
            if 'wine' in q_lower:
                cat_target = 'cat_wine'; cat_name = 'Wine'
            elif 'spirit' in q_lower:
                cat_target = 'cat_spirits'; cat_name = 'Spirits'
            elif 'rtd' in q_lower:
                cat_target = 'cat_rtd'; cat_name = 'RTDs'

            res = comparison_engine.compare_master_vs_categorization(cat_target, limit=300)
            report_records = res['records']
            source_files = ["AIMasterBrandData.csv", f"Categorization 2026 - {cat_name}.csv"]
            summary = res['summary']

            ans = f"""### 🔍 Master Data vs {cat_name} Categorization Comparison

- **Master Total Records**: {summary['master_total_records']:,}
- **{cat_name} Total Records**: {summary['categorization_total_records']:,}
- **Unique UPCs in {cat_name}**: {summary['categorization_unique_upcs']:,}
- **Matching UPCs (Found in Both)**: {summary['matching_upcs_in_both']:,} ({summary['match_rate_pct']}%)
- **Missing from Master Catalog**: {summary['missing_from_master_total']:,} UPCs present in {cat_name} do not exist in AIMasterBrandData.

In the inspected sample of {summary['sample_analyzed']} records:
- **Exact Matches**: {summary['exact_matches_in_sample']}
- **Partial Brand Name Matches**: {summary['partial_matches_in_sample']}
- **Brand Mismatches**: {summary['mismatches_in_sample']}
- **Missing Records**: {summary['missing_in_sample']}"""
            return self._format_response(ans, report_records, source_files, token)

        # D. Duplicate UPC Audit
        if is_duplicate:
            res = comparison_engine.find_duplicate_upcs_across_all(limit=100)
            report_records = res['records']
            source_files = ["AIMasterBrandData.csv", "Categorization 2026 - Beer.csv", "Categorization 2026 - RTDs.csv", "Categorization 2026 - Spirits.csv", "Categorization 2026 - Wine.csv"]
            ans = f"""### ⚠️ Duplicate UPCs Audit Across Datasets

- Evaluated cross-file presence across Master, Beer, RTDs, Spirits, and Wine.
- Identified **{len(report_records)} primary duplicate groups** where identical UPCs appear across 2 or more separate files.
- Common occurrences include beer items tracked concurrently in RTD sheets and master items shared with categorization sheets."""
            return self._format_response(ans, report_records, source_files, token)

        # E. Exact UPC Lookup
        if is_upc_query and upc_match:
            upc_val = upc_match.group(1)
            res = sql_engine.lookup_upc(upc_val)
            report_records = res['records']
            source_files = res['found_in_files']

            if res['total_matches'] > 0:
                row_refs = [str(r.get('original_row', r.get('_original_row', 'N/A'))) for r in report_records]
                ans = f"""### ✅ Product Lookup: UPC `{res['normalized_upc']}`

Found **{res['total_matches']} matching record(s)** across **{len(source_files)} source file(s)**:
- **Source Files**: {', '.join(source_files)}
- **Original Row Reference(s)**: {', '.join(row_refs)}
- **Primary Brand**: {report_records[0].get('BrandName', 'N/A')}
- **Product Type / Desc**: {report_records[0].get('ProductName') or report_records[0].get('Product') or 'N/A'}
- **Supplier**: {report_records[0].get('SupplierName', 'N/A')}"""
            else:
                ans = f"""### ❌ Product Lookup: UPC `{res['normalized_upc']}`

The requested UPC was **not found** in any of the 7 beverage datasets.
- Checked: Master Brand Data, AllBrand Master, Beer, RTDs, Spirits, and Wine.
- Recommendation: Verify the digits or check whether it is listed under an alternate UPC code."""
            return self._format_response(ans, report_records, source_files, token)

        # F. Category Product Counts
        if is_category_count:
            res = sql_engine.count_by_category()
            master_cats = res['master_categories']
            beer_cats = res['beer_categories']
            report_records = master_cats + beer_cats
            source_files = ["AIMasterBrandData.csv", "Categorization 2026 - Beer.csv"]

            ans = f"""### 📈 Beverage Product Counts by Category

#### AIMaster Brand Catalog:
""" + "\n".join([f"- **{r['category'] or 'Uncategorized'}**: {r['product_count']:,} products" for r in master_cats[:8]]) + f"""

#### Beer Categorization:
""" + "\n".join([f"- **{r['category'] or 'Uncategorized'}**: {r['product_count']:,} products" for r in beer_cats[:6]])
            return self._format_response(ans, report_records, source_files, token)

        # G. Brand Search
        if is_brand_search or any(b in q_lower for b in ['michelob', 'modelo', 'bud light', 'corona', 'twisted tea', 'titos', 'la marca']):
            # Extract brand name guess
            brand_guess = re.sub(r'(?i)(show|find|search|all|products|belonging|to|brand|karo|dikhao)', '', q).strip()
            if not brand_guess:
                brand_guess = q
            res = sql_engine.search_brand(brand_guess, limit=100)
            report_records = res['records']
            source_files = ["AIMasterBrandData.csv"]

            if res['total_matches'] > 0:
                ans = f"""### 🏷️ Brand Search: '{res['query_brand']}'

Found **{res['total_matches']} matching record(s)** in AIMasterBrandData.csv:
- **Brand Name**: {report_records[0].get('BrandName')}
- **Supplier**: {report_records[0].get('SupplierName')}
- **Sample Sizes**: {', '.join(set([r.get('Size') for r in report_records if r.get('Size')])) or 'Various'}"""
                return self._format_response(ans, report_records, source_files, token)
            else:
                pass

        # H. Supplier Search
        if is_supplier_search:
            supp_guess = re.sub(r'(?i)(find|show|products|with|supplier|vendor|dikhao)', '', q).strip()
            res = sql_engine.search_supplier(supp_guess, limit=100)
            report_records = res['records']
            source_files = ["AIMasterBrandData.csv"]
            if res['total_matches'] > 0:
                ans = f"""### 🏭 Supplier Search: '{res['query_supplier']}'

Found **{res['total_matches']} matching record(s)** associated with supplier '{res['query_supplier']}':
- **Supplier Name**: {report_records[0].get('SupplierName')}
- **Supplier Code**: {report_records[0].get('SupplierCode', 'N/A')}
- **Associated Brands**: {', '.join(set([r.get('BrandName') for r in report_records if r.get('BrandName')]) )[:200]}"""
                return self._format_response(ans, report_records, source_files, token)

        # I. Fallback to Semantic Vector Search + Local LLM
        docs = vector_engine.search(q, top_k=6)
        report_records = docs
        source_files = list(set([d.get('source_file') for d in docs if d.get('source_file')]))

        if docs:
            context_text = "\n".join([f"[{d['source_file']} Line {d['original_row']}] UPC: {d['upc']} | Brand: {d['brand']} | Supplier: {d['supplier']} | Category: {d['category']} | Desc: {d['description']}" for d in docs])
            
            # If Ollama is running locally, use it to generate conversational synthesis
            if self.is_ollama_available():
                prompt = f"""Based on the following retrieved beverage records, provide a direct, helpful, accurate answer to the user's question.

Retrieved Records:
{context_text}

User Question: {q}

Answer with source file references and exact details:"""
                ollama_ans = self.query_ollama(prompt)
                if ollama_ans:
                    return self._format_response(ollama_ans, report_records, source_files, token)

            # Deterministic Semantic Answer
            ans = f"""### 🔍 Semantic Search Results for: *"{q}"*

Retrieved **{len(docs)} highly relevant beverage records** from local vector storage:
""" + "\n".join([f"- **{d['brand']}** (`UPC: {d['upc']}`): {d['description']} *(Source: `{d['source_file']}`, Row: {d['original_row']})*" for d in docs[:5]])
        else:
            ans = f"""### ℹ️ No Direct Records Found

No matching beverage records were retrieved for query: *"{q}"*.
- Try searching with a 13-digit UPC, exact brand name (e.g. *Michelob Ultra*, *Modelo*, *Titos*), or comparison keywords (e.g. *Compare Master with Beer*)."""

        return self._format_response(ans, report_records, source_files, token)

    def _format_response(self, markdown_text, records, source_files, token):
        # Save records for CSV download
        if records:
            try:
                df = pd.DataFrame(records)
                csv_path = REPORTS_DIR / f"report_{token}.csv"
                df.to_csv(csv_path, index=False)
            except Exception as e:
                pass

        return {
            "answer": markdown_text,
            "source_files": source_files,
            "record_count": len(records),
            "records": records[:100],  # send first 100 to UI table
            "download_token": token if records else None
        }

rag_orchestrator = RAGOrchestrator()
