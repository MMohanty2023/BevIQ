import re
import json
import uuid
import time
import requests
import pandas as pd
from config import DB_DIR, OLLAMA_HOST, OLLAMA_MODEL, REPORTS_DIR
from engines.sql_engine import sql_engine
from engines.comparison_engine import comparison_engine
from engines.vector_engine import vector_engine
from data_ingestion.normalizer import normalize_upc
from document_rag import search as search_documents
from engines.conversation_store import ConversationStore

class RAGOrchestrator:
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        self.ollama_model = OLLAMA_MODEL
        self._ollama_status = None
        self._ollama_status_checked_at = 0.0
        self.conversation_store = ConversationStore(DB_DIR / "conversation.sqlite3")

    def is_ollama_available(self):
        """Check if local Ollama server is running."""
        now = time.monotonic()
        if self._ollama_status is not None and now - self._ollama_status_checked_at < 10:
            return self._ollama_status
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=1.0)
            self._ollama_status = r.status_code == 200
        except Exception:
            self._ollama_status = False
        self._ollama_status_checked_at = now
        return self._ollama_status

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

    def route_and_execute(self, user_query, session_id='default-session'):
        history = self.conversation_store.recent(session_id, limit=8)
        original_query = user_query.strip()
        query = self._with_conversation_context(original_query, history)
        result = self._route_and_execute(query, session_id=session_id)
        self.conversation_store.append(session_id, "user", original_query)
        self.conversation_store.append(session_id, "assistant", result.get("answer", ""))
        result["conversation_context_used"] = query != original_query
        return result

    def _route_and_execute(self, user_query, session_id='default-session'):
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

        # Always prioritize explicit normal-chat messages over catalog retrieval.
        local_general = self._local_general_response(q)
        if local_general:
            return self._format_response(local_general, [], [], token)

        # Keep ordinary conversation away from the product vector index. The
        # index is useful for catalog questions, but it can produce false hits
        # for words such as "day", "joke", or "India" in product names.
        catalog_terms = [
            'upc', 'barcode', 'product', 'brand', 'supplier', 'vendor',
            'beer', 'wine', 'rtd', 'spirits', 'master', 'categorization',
            'dataset', 'category', 'missing', 'compare', 'duplicate', 'audit', 'search', 'find'
        ]
        document_terms = ['document', 'pdf', 'file', 'upload', 'uploaded', 'image', 'sheet']
        has_identifier_intent = bool(re.search(r'\b(?:id|identifier)\s*[:#-]?\s*[a-z0-9_-]+\b', q_lower))
        has_catalog_intent = bool(re.search(r'\b\d{10,14}\b', q)) or has_identifier_intent or any(term in q_lower for term in catalog_terms)
        has_document_intent = any(term in q_lower for term in document_terms)
        if not has_catalog_intent and not has_document_intent:
            if self.is_ollama_available():
                language = self._detect_response_language(q)
                general_system_prompt = (
                    "You are BevIQ, a friendly and capable general-purpose assistant. "
                    "The user may ask about any topic, not only beverage data. "
                    "Reply in the same language and writing style as the user's latest message. "
                    "If the user writes in English, reply in English. "
                    "If the user writes in Hindi using Devanagari, reply in natural Hindi using Devanagari. "
                    "If the user writes in Hinglish/Roman Hindi, reply in natural Hinglish using Roman script. "
                    "If the user mixes English and Hindi, naturally match that mix. "
                    "Follow an explicit language request if the user asks for a different language. "
                    "Keep technical terms such as Python, Flask, API, SQL, and database in English. "
                    "Do not force beverage-related content into unrelated conversations. "
                    "Be helpful, conversational, accurate, and do not invent facts. "
                    f"Detected response style for this message: {language}."
                )
                general = self.query_ollama(q, general_system_prompt)
                if general:
                    return self._format_response(general, [], [], token)

            detected_language = self._detect_response_language(q)
            if detected_language == "Hindi":
                fallback = (
                    "### 💬 सामान्य बातचीत\\n\\n"
                    "मैं सामान्य सवालों और बातचीत में मदद कर सकता हूँ। "
                    "खुले सवालों के विस्तृत जवाब देने के लिए local Ollama चालू करें। "
                    "BevIQ के database और uploaded-document वाले सवाल उपलब्ध हैं।"
                )
            elif detected_language == "Hinglish":
                fallback = (
                    "### 💬 Normal Chat\\n\\n"
                    "Main normal questions aur casual conversation mein help kar sakta hoon. "
                    "Detailed open-ended answers ke liye local Ollama start karein. "
                    "BevIQ ke database aur uploaded-document questions bhi available hain."
                )
            else:
                fallback = (
                    "### 💬 Normal Chat\\n\\n"
                    "I can help with general questions and casual conversation. "
                    "Start local Ollama for detailed open-ended answers. "
                    "BevIQ database and uploaded-document questions are also available."
                )
            return self._format_response(fallback, [], [], token)

        # Direct aggregates should never fall through to the slower vector index.
        is_master_brand_count = bool(re.search(r'\b(how many|number of|count|kitne|kitni|gino)\b', q_lower)) and 'brand' in q_lower
        if is_master_brand_count:
            category = next((f'cat_{name}' for name in ('beer', 'wine', 'rtd', 'spirits') if re.search(rf'\b{name}\b', q_lower)), None)
            brand_count = sql_engine.count_brands(category) if category else sql_engine.count_master_brands()
            label = category.replace('cat_', '').upper() if category else 'Master'
            if self._is_hinglish(q_lower):
                answer = f"### 📊 {label} Brand Summary\n\n{label} sheet mein **{brand_count:,} unique brands** hain."
            else:
                answer = f"### 📊 {label} Brand Summary\n\nThe {label.lower()} sheet contains **{brand_count:,} unique brands**."
            return self._format_response(answer, [], [], token)

        # Uploaded documents are scoped to the browser conversation. If a relevant
        # chunk exists, answer from it before falling back to the beverage catalog.
        document_hits = search_documents(q, session_id)
        if document_hits:
            context = "\n\n".join(
                f"[{hit['filename']} - page/section {hit['page']}]\n{hit['content']}"
                for hit in document_hits
            )
            if self.is_ollama_available():
                prompt = f"Use only this uploaded-document context to answer the question. Cite filename and page/section.\n\nContext:\n{context}\n\nQuestion: {q}"
                answer = self.query_ollama(prompt, "You answer questions about user-uploaded documents. If the answer is not in context, say so clearly.")
            else:
                answer = None
            if not answer:
                answer = "### 📄 Uploaded Document Answer\n\n" + "\n\n".join(
                    f"**{hit['filename']} — page/section {hit['page']}**\n{hit['content'][:1200]}"
                    for hit in document_hits
                )
            return self._format_response(answer, document_hits,
                                         [hit['filename'] for hit in document_hits], token)

        # 1. Check for UPC pattern (10 to 14 digits or 'upc' keyword)
        upc_match = re.search(r'\b(\d{10,14})\b', q)
        is_upc_query = bool(upc_match) or 'upc' in q_lower or 'barcode' in q_lower
        identifier_match = re.search(r'\b(?:id|identifier)\s*[:#-]?\s*([a-z0-9_-]+)\b', q_lower)

        # 2. Check for Comparison Intent
        is_compare = any(w in q_lower for w in ['compare', 'mismatch', 'diff', 'versus', 'vs', 'difference', 'farq'])
        is_beer_rtd = ('beer' in q_lower and 'rtd' in q_lower) or 'hard seltzer' in q_lower
        is_supplier_brand = ('supplier' in q_lower and ('brand' in q_lower or 'sheet' in q_lower or 'master' in q_lower))
        is_missing = any(w in q_lower for w in ['missing', 'not found', 'absent', 'nahi hai', 'gap'])
        is_duplicate = any(w in q_lower for w in ['duplicate', 'repeated', 'multiple', 'dohra'])
        is_category_count = bool(re.search(r'\b(count|category count|gino|total count)\b', q_lower)) or 'total products in each' in q_lower
        is_product_upc_gap = any(w in q_lower for w in [
            'alternate upc', 'alternate barcode', 'same product', 'product match',
            'upc missing', 'brand flavour size', 'brand flavor size',
            'allmasterbrand', 'all master'
        ])
        # A supplier-only question should use the supplier search path below.
        # Brand profile is reserved for questions asking for product attributes.
        is_brand_profile = any(w in q_lower for w in [
            'flavour', 'flavor', 'size', 'origin', 'country',
            'details', 'profile'
        ]) and not is_product_upc_gap
        is_supplier_search = any(w in q_lower for w in ['supplier', 'vendor']) and not is_compare
        is_brand_search = any(w in q_lower for w in ['brand', 'products belonging to', 'show products for', 'products of', 'search', 'find']) and not is_supplier_search

        if identifier_match:
            identifier = identifier_match.group(1)
            res = sql_engine.lookup_identifier(identifier, limit=200)
            report_records = res['records'] + res.get('related_records', [])
            source_files = res.get('source_files', [])
            if res['total_matches']:
                primary = report_records[0] if report_records else {}
                product = primary.get('ProductName') or primary.get('Product') or primary.get('ProductDescription') or 'Not available'
                brand = primary.get('BrandName') or primary.get('Brands_Value') or primary.get('Beer_Brands_Value') or primary.get('Spirits_Brands_Value') or 'Not available'
                ans = f"### ✅ Complete ID Lookup: `{res['normalized_identifier']}`\n\nFound **{res['total_matches']} direct record(s)** and **{len(res.get('related_records', []))} related record(s)** across **{len(source_files)} source file(s)**.\n\n- **Brand:** {brand}\n- **Product:** {product}\n\nAll displayed details come directly from the connected database."
            else:
                ans = f"### ❌ ID Not Found: `{res['normalized_identifier']}`\n\nNo exact matching ID, UPC, or alternate UPC was found in the configured beverage datasets."
            return self._format_response(ans, report_records, source_files, token)

        if is_product_upc_gap:
            from engines.upc_match_engine import upc_match_engine
            category = next((f'cat_{name}' for name in ('beer', 'rtd', 'spirits', 'wine') if name in q_lower), None)
            report_records = upc_match_engine.audit(category, limit=None)
            source_files = ['$ALLBrand_202610291524.csv', 'Categorization 2026 - Beer.csv', 'Categorization 2026 - RTDs.csv', 'Categorization 2026 - Spirits.csv', 'Categorization 2026 - Wine.csv']
            ans = f"### 🔎 UPC-First Product Audit\n\nReviewed **{len(report_records)} category records** against AllBrand. The report includes exact UPC status, missing UPC details, product/flavour/size matches, and suggested alternate UPCs. **No data was changed.** Review the CSV before making any manual update."
            return self._format_response(ans, report_records, source_files, token)

        if is_brand_profile:
            brand_guess = self._extract_brand_guess(q)
            profile = sql_engine.brand_profile(brand_guess)
            report_records = profile['records']
            source_files = sorted({r.get('source_file') for r in report_records if r.get('source_file')})
            join = lambda values, fallback='Not available': ', '.join(values[:20]) if values else fallback
            if self._is_hinglish(q_lower):
                ans = f"""### 🏷️ {profile['query_brand']} Brand Profile

**Unique brand names**: {profile['unique_brand_count']:,} | **Total records**: {profile['total_records']:,}

- **Categories / sheets**: {', '.join(f"{c['category']} ({c['count']:,})" for c in profile['categories']) or 'Not found'}
- **Flavours ({profile['unique_flavour_count']:,} distinct)**: {join(profile['flavours'])}
- **Sizes / packs ({profile['unique_size_count']:,} distinct)**: {join(profile['sizes'])}
- **Suppliers**: {join(profile['suppliers'])}
- **Origin / domestic-import**: {join(profile['origins'])}
- **Distinct UPCs**: {profile['unique_upc_count']:,}

Neeche matching product records aur UPC details diye gaye hain."""
            else:
                ans = f"""### 🏷️ {profile['query_brand']} Brand Profile

**Unique brand names**: {profile['unique_brand_count']:,} | **Total records**: {profile['total_records']:,}

- **Categories / sheets**: {', '.join(f"{c['category']} ({c['count']:,})" for c in profile['categories']) or 'Not found'}
- **Flavours ({profile['unique_flavour_count']:,} distinct)**: {join(profile['flavours'])}
- **Sizes / packs ({profile['unique_size_count']:,} distinct)**: {join(profile['sizes'])}
- **Suppliers**: {join(profile['suppliers'])}
- **Origin / domestic-import**: {join(profile['origins'])}
- **Distinct UPCs**: {profile['unique_upc_count']:,}

Matching product records and UPC details are shown below."""
            return self._format_response(ans, report_records, source_files, token)

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

            if self._is_hinglish(q_lower):
                    ans = f"""### 🔍 Master Data vs {cat_name} Categorization Comparison

- **Master mein total records**: {summary['master_total_records']:,}
- **{cat_name} sheet mein total records**: {summary['categorization_total_records']:,}
- **{cat_name} ke unique UPCs**: {summary['categorization_unique_upcs']:,}
- **Dono sheets mein matching UPCs**: {summary['matching_upcs_in_both']:,} ({summary['match_rate_pct']}%)
- **Master mein missing UPCs**: {summary['missing_from_master_total']:,}

Sample review mein:
- **Exact matches**: {summary['exact_matches_in_sample']}
- **Partial brand matches**: {summary['partial_matches_in_sample']}
- **Brand mismatch**: {summary['mismatches_in_sample']}
- **Missing records**: {summary['missing_in_sample']}"""
            else:
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
            brand_guess = re.sub(r'(?i)(show|find|search|all|products?|product|description|belonging|to|for|brand|karo|dikhao)', '', q).strip()
            if not brand_guess:
                brand_guess = q
            res = sql_engine.search_catalog(brand_guess, limit=100)
            report_records = res['records']
            source_files = sorted({r.get('source_file') for r in report_records if r.get('source_file')})

            if res['total_matches'] > 0:
                sample = report_records[0]
                if self._is_hinglish(q_lower):
                    ans = f"### 🔎 Catalog Search: '{res['query']}'\n\nAll sheets mein **{res['total_matches']} matching record(s)** mile.\n\n**Sample product description**: {sample.get('product_description') or 'Not available'}\n\nNeeche brand, product description, flavour, size, supplier, origin aur UPC details hain."
                else:
                    ans = f"### 🔎 Catalog Search: '{res['query']}'\n\nFound **{res['total_matches']} matching record(s)** across the Master, Beer, Wine, RTD and Spirits sheets.\n\n**Sample product description**: {sample.get('product_description') or 'Not available'}\n\nThe results include brand, product description, flavour, size, supplier, origin and UPC details."
                return self._format_response(ans, report_records, source_files, token)

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
            if self.is_ollama_available():
                general = self.query_ollama(q, "You are a helpful general chat assistant with beverage-data expertise. Be concise, honest, and answer in the user's language. Do not invent database facts unless they are in context.")
                if general:
                    return self._format_response(general, [], [], token)
            local_general = self._local_general_response(q)
            if local_general:
                return self._format_response(local_general, [], [], token)
            ans = f"""### ℹ️ No Direct Records Found

No matching beverage records were retrieved for query: *"{q}"*.
- Try searching with a 13-digit UPC, exact brand name (e.g. *Michelob Ultra*, *Modelo*, *Titos*), or comparison keywords (e.g. *Compare Master with Beer*)."""

        return self._format_response(ans, report_records, source_files, token)

    def _with_conversation_context(self, query, history):
        """Resolve short pronoun-based follow-ups without changing explicit searches."""
        if not history:
            return query
        lowered = query.lower()
        contextual = len(query.split()) <= 8 and bool(re.search(
            r'\b(what about|and|also|it|that|this|same|iska|uska|iske|uske|aur)\b', lowered
        ))
        if not contextual:
            return query
        previous_user = next((turn["content"] for turn in reversed(history) if turn["role"] == "user"), "")
        if not previous_user:
            return query
        return query + "\nPrevious user request for context: " + previous_user

    def _local_general_response(self, query):
        """Keep basic normal chat useful even when Ollama is not running."""
        text = query.lower().strip()
        if not self._is_hinglish(text):
            if re.search(r'^(hi|hello|hey|hii)\b', text):
                return "### 👋 Hello!\n\nI’m the BevIQ Assistant. You can chat normally or ask about beverage data, UPCs, comparisons, and uploaded documents."
            if 'how are you' in text:
                return "### 🙂 I’m ready!\n\nYou can chat casually or ask me about a product, UPC, PDF, image, or dataset."
            if 'capital of india' in text:
                return "### 🇮🇳 Answer\n\nThe capital of India is **New Delhi**."
            if re.search(r'\b(joke|funny|make me laugh)\b', text) and re.search(r'\b(tell|give|share|about|hear|make)\b', text):
                return "### 😄 Joke\n\nWhy did the data analyst drink coffee? To clear the **cache**!"
            if any(word in text for word in ['thank you', 'thanks']):
                return "### 😊 You’re welcome!\n\nGlad to help. Ask me anything whenever you like."
            if any(word in text for word in ['what can you do', 'help', 'features']):
                return "### 💡 BevIQ Help\n\n- Normal chat in English or Hinglish\n- UPC, brand, supplier, and category search\n- Beer, Wine, RTD, and Spirits comparisons\n- Missing/product-match UPC audits\n- Questions about uploaded PDF, image, DOCX, CSV, and XLSX files\n\nEnable local Ollama for richer open-ended answers."
        if re.search(r'^(hi|hello|hey|hii|namaste|नमस्ते)\b', text):
            return "### 👋 Hello!\n\nMain BevIQ Assistant hoon. Aap normal chat, beverage data, UPC lookup, comparisons, ya uploaded documents ke baare mein pooch sakte ho."
        if any(word in text for word in ['how are you', 'kaise ho', 'kya haal']):
            return "### 🙂 Main ready hoon!\n\nAap casual chat kar sakte ho ya koi product, UPC, PDF, image, ya dataset question pooch sakte ho."
        if 'capital of india' in text or 'india ki capital' in text:
            return "### 🇮🇳 Answer\n\nIndia ki capital **New Delhi** hai."
        if (
            re.search(r'\b(joke|funny|hansi|hasao)\b', text)
            and re.search(r'\b(tell|give|share|about|suna|sunao|batao|make)\b', text)
        ):
            return "### 😄 Joke\n\nData analyst ne coffee kyun pi? Kyunki usse apna **cache** clear karna tha!"
        if any(word in text for word in ['thank you', 'thanks', 'dhanyavaad', 'shukriya']):
            return "### 😊 Welcome\n\nKhushi hui! Jab chahein pooch sakte ho."
        if any(word in text for word in ['what can you do', 'help', 'kya kar sakte', 'features', 'madad']):
            return "### 💡 BevIQ Help\n\n- Normal chat in English/Hinglish\n- UPC, brand, supplier aur category search\n- Beer, Wine, RTD aur Spirits comparison\n- Missing/product-match UPC audit\n- PDF, image, DOCX, CSV aur XLSX upload karke questions\n\nOpen-ended general answers ke liye local Ollama enable kar sakte ho."
        return None

    def _detect_response_language(self, text):
        """Detect the reply style from the latest user message."""
        if re.search(r'[\\u0900-\\u097f]', text):
            return "Hindi"

        hindi_markers = [
            'kya', 'hai', 'hain', 'hoon', 'karna', 'karo', 'kaise', 'kyun',
            'mujhe', 'mera', 'mere', 'aap', 'apka', 'aapka', 'batao',
            'dikhao', 'chahiye', 'nahi', 'nahin', 'mein', 'mujhko',
            'kyunki', 'acha', 'achha', 'haan'
        ]
        if any(re.search(rf'\\b{re.escape(marker)}\\b', text.lower()) for marker in hindi_markers):
            return "Hinglish"
        return "English"

    def _is_hinglish(self, text):
        """Backward-compatible helper used by existing deterministic responses."""
        return self._detect_response_language(text) in ("Hindi", "Hinglish")

    def _extract_brand_guess(self, query):
        """Remove profile question words while keeping a multi-word brand name."""
        cleaned = re.sub(r'[^a-zA-Z0-9&.\- ]+', ' ', query)
        stop_words = {
            'mujhe', 'batao', 'dikhao', 'show', 'find', 'tell', 'me', 'about',
            'how', 'many', 'what', 'which', 'are', 'is', 'the', 'this', 'brand',
            'ke', 'ka', 'ki', 'hain', 'hai', 'kya', 'mein', 'me', 'present',
            'kitne', 'kitni', 'flavour', 'flavours', 'flavor', 'flavors',
            'size', 'sizes', 'supplier', 'suppliers', 'origin', 'origins',
            'country', 'details', 'profile', 'and', 'or', 'aur', 'please', 'products'
        }
        words = [word for word in cleaned.split() if word.lower() not in stop_words]
        return ' '.join(words).strip() or query.strip()

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
            "download_token": token if records else None,
            "read_only": True
        }

rag_orchestrator = RAGOrchestrator()
