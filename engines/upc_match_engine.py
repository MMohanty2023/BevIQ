"""Read-only, UPC-first product matching for category audits."""

import re

from config import CSV_FILES
from database.db_manager import db_manager

try:
    from rapidfuzz.fuzz import token_set_ratio
except ImportError:  # pragma: no cover
    from difflib import SequenceMatcher

    def token_set_ratio(a, b):
        return int(SequenceMatcher(None, a, b).ratio() * 100)


class UPCMatchEngine:
    """Compare category rows with AllBrand without changing any source data."""

    fields = {
        "cat_beer": {"brand": "Beer_Brands_Value", "size": "Beer_Size_Groups_Value", "product": "Product", "category": "Beer_Category_Value", "flavour": "Beer_Mezzo_Styles_Value"},
        "cat_rtd": {"brand": "Brands_Value", "size": "RTD_Size_Value", "product": "Product", "category": "RTD_Category_Value", "flavour": "Flavor_Groups_Value"},
        "cat_spirits": {"brand": "Spirits_Brands_Value", "size": "Spirits_Sizes_Value", "product": "Product", "category": "Spirits_Category_Value", "flavour": "Spirits_Flavors_Value"},
        "cat_wine": {"brand": "Brands_Value", "size": "Size_Packages_Value", "product": "Product", "category": "Categories_Value", "flavour": "Flavors_Value"},
    }
    size_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(oz|ounce|ounces|ml|lt|l|liter|litre|gal|gallon|pack|pk|ct|count)\b", re.IGNORECASE)

    def _norm(self, value):
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def _size_signature(self, value):
        signature = set()
        for number, unit in self.size_pattern.findall(str(value or "")):
            amount = float(number)
            unit = unit.lower()
            if unit in {"l", "lt", "liter", "litre"}:
                amount, unit = amount * 1000, "ml"
            elif unit in {"ounce", "ounces"}:
                unit = "oz"
            elif unit in {"pk", "ct", "count"}:
                unit = "pack"
            signature.add((round(amount, 3), unit))
        return signature

    def _similarity(self, left, right):
        left, right = self._norm(left), self._norm(right)
        return int(token_set_ratio(left, right)) if left and right else 0

    def _size_status(self, source_size, master_size):
        source, master = self._size_signature(source_size), self._size_signature(master_size)
        if source and master and source.isdisjoint(master):
            return "conflict", 0
        if not source or not master:
            return "unknown", 60
        return "compatible", self._similarity(source_size, master_size)

    def _category_rows(self, table, limit):
        if limit is None:
            return db_manager.query(f"SELECT * FROM `{table}` ORDER BY original_row")
        return db_manager.query(f"SELECT * FROM `{table}` ORDER BY original_row LIMIT ?", (int(limit),))

    def _load_master_index(self):
        rows = db_manager.query(
            """SELECT source_file, original_row, clean_upc, clean_alt_upc, BrandName, ProductName, Size, SupplierName
               FROM all_brands WHERE (clean_upc != '' OR clean_alt_upc != '')"""
        )
        index = {}
        for row in rows:
            key = self._norm(row.get("BrandName"))
            if key:
                index.setdefault(key, []).append(row)
        return index

    def _master_candidates(self, brand, cache=None, master_index=None):
        cache_key = self._norm(brand)
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        if master_index is not None:
            candidates = []
            for master_brand, rows in master_index.items():
                if cache_key in master_brand or master_brand in cache_key:
                    candidates.extend(rows)
                    if len(candidates) >= 120:
                        break
            candidates = candidates[:120]
            if cache is not None:
                cache[cache_key] = candidates
            return candidates
        candidates = db_manager.query(
            """SELECT source_file, original_row, clean_upc, clean_alt_upc, BrandName, ProductName, Size, SupplierName
               FROM all_brands WHERE norm_brand LIKE ? AND (clean_upc != '' OR clean_alt_upc != '') LIMIT 120""",
            (f"%{self._norm(brand)}%",),
        )
        if cache is not None:
            cache[cache_key] = candidates
        return candidates

    def _best_candidate(self, row, spec, candidates):
        product = row.get(spec["product"], "")
        if not self._norm(product):
            return None
        source_product = " ".join(self._norm(row.get(spec[key], "")) for key in ("product", "flavour", "category"))
        best = None
        for candidate in candidates:
            product_score = self._similarity(source_product, f"{candidate.get('ProductName', '')} {candidate.get('BrandName', '')}")
            size_status, size_score = self._size_status(row.get(spec["size"]), candidate.get("Size"))
            brand_score = self._similarity(row.get(spec["brand"]), candidate.get("BrandName"))
            if size_status == "conflict" or product_score < 75 or brand_score < 70:
                continue
            # Equivalent normalized sizes (for example 0.75 LT and 750 ML)
            # should receive full size confidence even when their raw text differs.
            if size_status == "compatible" and self._size_signature(row.get(spec["size"])) == self._size_signature(candidate.get("Size")):
                size_score = 100
            score = round((product_score * 0.55) + (max(size_score, 70) * 0.30) + (brand_score * 0.15))
            if best is None or score > best["score"]:
                best = {"score": int(score), "description_score": int(product_score), "candidate": candidate}
        return best if best and best["score"] >= 80 else None

    def _record(self, category, row, spec, candidate=None, status=None, confidence=0, remarks="", description_score=0):
        candidate = candidate or {}
        source_description = " ".join(str(row.get(spec[key]) or "").strip() for key in ("product", "flavour", "category") if str(row.get(spec[key]) or "").strip())
        master_description = str(candidate.get("ProductName") or "").strip()
        return {
            "category": category.replace("cat_", "").upper(), "status": status or "Missing in AllBrand - No Product Match",
            "current_upc": str(row.get("clean_upc") or ""), "suggested_upc": str(candidate.get("clean_upc") or ""), "alternate_upc": str(candidate.get("clean_alt_upc") or ""), "confidence": int(confidence),
            "source_file": row.get("source_file"), "source_row": row.get("original_row"), "source_brand": row.get(spec["brand"]), "source_product": row.get(spec["product"]), "source_flavour": row.get(spec["flavour"]), "source_size": row.get(spec["size"]), "source_category": row.get(spec["category"]),
            "master_brand": candidate.get("BrandName", ""), "master_product": candidate.get("ProductName", ""), "master_size": candidate.get("Size", ""), "master_row": candidate.get("original_row", ""),
            "source_description": source_description, "master_description": master_description, "description_match_score": int(description_score),
            "remarks": remarks or "Review only; no master product or UPC was changed.",
        }

    def audit(self, category=None, limit=100):
        categories = [category] if category in self.fields else list(self.fields)
        output = []
        candidate_cache = {}
        master_index = self._load_master_index()
        for cat_key in categories:
            spec = self.fields[cat_key]
            for row in self._category_rows(CSV_FILES[cat_key]["table"], limit):
                current_upc = str(row.get("clean_upc") or "")
                if not self._norm(row.get(spec["brand"], "")):
                    output.append(self._record(cat_key, row, spec, status="Manual Review - Insufficient Product Match"))
                    continue
                candidates = self._master_candidates(row.get(spec["brand"], ""), candidate_cache, master_index)
                exact = next((c for c in candidates if current_upc and current_upc in {str(c.get("clean_upc") or ""), str(c.get("clean_alt_upc") or "")}), None)
                if exact:
                    verified = self._record(cat_key, row, spec, exact, "Verified UPC in AllBrand", 100, "Exact UPC or known alternate UPC found in AllBrand.", 100)
                    verified["suggested_upc"] = ""
                    output.append(verified)
                    continue
                best = self._best_candidate(row, spec, candidates)
                if best:
                    status = "Product Match - UPC Missing" if not current_upc else "Product Match - UPC Different"
                    output.append(self._record(cat_key, row, spec, best["candidate"], status, best["score"], "Brand, product/flavour, and size/pack are compatible; review suggested UPC before manual update.", best["description_score"]))
                    continue
                if not self._norm(row.get(spec["product"], "")):
                    status = "Manual Review - Insufficient Product Match"
                elif any(self._size_status(row.get(spec["size"]), c.get("Size"))[0] == "conflict" for c in candidates):
                    status = "Manual Review - Size/Pack Conflict"
                else:
                    status = "Missing in AllBrand - No Product Match"
                output.append(self._record(cat_key, row, spec, status=status))
        return output


upc_match_engine = UPCMatchEngine()
