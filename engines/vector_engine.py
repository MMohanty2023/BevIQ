import os
import re
import math
import pickle
from collections import Counter
from config import INDEX_DIR, CSV_FILES
from database.db_manager import db_manager

class LocalVectorIndex:
    """
    Offline local persistent BM25 / TF-IDF Vector Index for semantic retrieval.
    Zero external API requirements, zero internet, fast sub-second querying.
    """
    def __init__(self, index_name="beverage_vector_index"):
        self.index_name = index_name
        self.index_file = INDEX_DIR / f"{index_name}.pkl"
        self.documents = []  # List of metadata dicts
        self.doc_tokens = []
        self.doc_lens = []
        self.avg_doc_len = 0
        self.df = Counter()  # Document frequency
        self.k1 = 1.5
        self.b = 0.75

    def tokenize(self, text):
        if not text:
            return []
        text = str(text).lower()
        return re.findall(r'[a-z0-9]+', text)

    def build_from_database(self, limit_per_table=10000):
        """Build vector index from SQLite database records."""
        self.documents = []
        self.doc_tokens = []
        self.doc_lens = []
        self.df = Counter()

        # Ingest representative sample across all tables for semantic coverage
        tables = [
            (CSV_FILES['ai_master']['table'], "BrandName, ExtendedBrandName, SupplierName, ProductName, Size, clean_upc, source_file, original_row"),
            (CSV_FILES['cat_beer']['table'], "Beer_Brands_Value as BrandName, Beer_Category_Value as ProductName, Beer_Vendors_Value as SupplierName, Product as Size, clean_upc, source_file, original_row"),
            (CSV_FILES['cat_spirits']['table'], "Spirits_Brands_Value as BrandName, Spirits_Category_Value as ProductName, Spirits_Suppliers_Value as SupplierName, Product as Size, clean_upc, source_file, original_row"),
            (CSV_FILES['cat_wine']['table'], "Brands_Value as BrandName, Categories_Value as ProductName, Wine_Suppliers_Value as SupplierName, Product as Size, clean_upc, source_file, original_row"),
        ]

        total_docs = 0
        for tbl, cols in tables:
            try:
                rows = db_manager.query(f"SELECT {cols} FROM `{tbl}` WHERE clean_upc != '' LIMIT {limit_per_table}")
                for r in rows:
                    brand = r.get('BrandName') or ''
                    supp = r.get('SupplierName') or ''
                    cat = r.get('ProductName') or ''
                    desc = r.get('Size') or ''
                    upc = r.get('clean_upc') or ''
                    doc_text = f"{brand} {supp} {cat} {desc} {upc}"
                    
                    tokens = self.tokenize(doc_text)
                    if not tokens:
                        continue
                    
                    doc_dict = {
                        "id": total_docs,
                        "upc": upc,
                        "brand": brand,
                        "supplier": supp,
                        "category": cat,
                        "description": desc,
                        "source_file": r.get('source_file'),
                        "original_row": r.get('original_row'),
                        "text": doc_text
                    }
                    self.documents.append(doc_dict)
                    self.doc_tokens.append(tokens)
                    self.doc_lens.append(len(tokens))
                    
                    # update df
                    unique_tokens = set(tokens)
                    for t in unique_tokens:
                        self.df[t] += 1
                        
                    total_docs += 1
            except Exception as e:
                print(f"Index build error for {tbl}: {e}")

        if self.doc_lens:
            self.avg_doc_len = sum(self.doc_lens) / len(self.doc_lens)

        self.save()
        return len(self.documents)

    def save(self):
        with open(self.index_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'doc_tokens': self.doc_tokens,
                'doc_lens': self.doc_lens,
                'avg_doc_len': self.avg_doc_len,
                'df': self.df
            }, f)

    def load(self):
        if not os.path.exists(self.index_file):
            return False
        with open(self.index_file, 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.doc_tokens = data['doc_tokens']
            self.doc_lens = data['doc_lens']
            self.avg_doc_len = data['avg_doc_len']
            self.df = data['df']
        return True

    def search(self, query, top_k=10, category_filter=None):
        """Retrieve most semantically relevant documents using BM25 scoring."""
        if not self.documents:
            if not self.load():
                return []

        q_tokens = self.tokenize(query)
        if not q_tokens:
            return []

        N = len(self.documents)
        scores = []

        for idx, tokens in enumerate(self.doc_tokens):
            doc = self.documents[idx]
            if category_filter and category_filter.lower() not in doc.get('category', '').lower():
                continue

            doc_len = self.doc_lens[idx]
            token_counts = Counter(tokens)
            score = 0.0

            for q in q_tokens:
                if q in token_counts:
                    tf = token_counts[q]
                    df = self.df.get(q, 0)
                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * (numerator / denominator)

            if score > 0:
                scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scores[:top_k]]

vector_engine = LocalVectorIndex()
