import os
import glob
import re
import csv
import json
import pandas as pd
from collections import Counter

files_info = [
    {"name": "$ALLBrand_202610291524.csv", "sep": "|"},
    {"name": "$Supplier_202610291521.csv", "sep": "|"},
    {"name": "AIMasterBrandData.csv", "sep": "|"},
    {"name": "Categorization 2026 - Beer.csv", "sep": ","},
    {"name": "Categorization 2026 - RTDs.csv", "sep": ","},
    {"name": "Categorization 2026 - Spirits.csv", "sep": ","},
    {"name": "Categorization 2026 - Wine.csv", "sep": ","},
]

def clean_upc(val, product_str=None):
    if product_str and isinstance(product_str, str):
        m = re.search(r'-\s*(\d{11,14})\s*$', product_str)
        if m:
            digits = m.group(1)
            return digits.zfill(13) if len(digits) in [11, 12] else digits
    if pd.isna(val):
        return ""
    s = str(val).strip()
    s = s.replace("UPC=", "").strip()
    if 'e+' in s.lower() or 'e-' in s.lower():
        try:
            s = f"{int(float(s))}"
        except:
            pass
    digits = re.sub(r'\D', '', s)
    if not digits:
        return ""
    return digits.zfill(13) if len(digits) in [11, 12] else digits

def analyze_dataset(item):
    fname = item["name"]
    sep = item["sep"]
    print(f"Profiling {fname}...")
    size_mb = os.path.getsize(fname) / (1024 * 1024)
    
    # Read chunk by chunk for stats
    total_rows = 0
    col_nulls = Counter()
    col_types = {}
    sample_rows = []
    upc_col = None
    alt_upc_col = None
    product_col = None
    brand_col = None
    supplier_col = None
    category_col = None

    # Detect key columns
    header = pd.read_csv(fname, sep=sep, nrows=0).columns.tolist()
    for col in header:
        clower = col.lower()
        if 'upc' in clower and 'alt' not in clower and upc_col is None:
            upc_col = col
        elif 'alt' in clower and 'upc' in clower:
            alt_upc_col = col
        elif clower in ['product', 'productname'] and product_col is None:
            product_col = col
        elif 'brand' in clower and brand_col is None:
            brand_col = col
        elif 'supplier' in clower or 'vendor' in clower and supplier_col is None:
            supplier_col = col
        elif 'category' in clower and category_col is None:
            category_col = col

    unique_upcs = set()
    total_valid_upcs = 0
    duplicate_upcs_count = 0

    chunksize = 50000
    for chunk in pd.read_csv(fname, sep=sep, chunksize=chunksize, dtype=str, on_bad_lines='skip'):
        total_rows += len(chunk)
        for col in chunk.columns:
            col_nulls[col] += chunk[col].isna().sum() + (chunk[col].str.strip() == '').sum()
        
        if len(sample_rows) < 3:
            sample_rows.extend(chunk.head(3 - len(sample_rows)).to_dict(orient='records'))
            
        if upc_col and upc_col in chunk.columns:
            for idx, r in chunk.iterrows():
                p_val = r.get(product_col, None) if product_col else None
                u_val = clean_upc(r[upc_col], p_val)
                if u_val:
                    total_valid_upcs += 1
                    if u_val in unique_upcs:
                        duplicate_upcs_count += 1
                    else:
                        unique_upcs.add(u_val)

    # Infer column data types from sample
    sample_df = pd.DataFrame(sample_rows)
    for col in header:
        col_types[col] = "string (text/categorical)"

    return {
        "file_name": fname,
        "file_size_mb": round(size_mb, 2),
        "delimiter": sep,
        "total_rows": total_rows,
        "total_columns": len(header),
        "columns": header,
        "key_mappings": {
            "upc_col": upc_col,
            "alt_upc_col": alt_upc_col,
            "product_col": product_col,
            "brand_col": brand_col,
            "supplier_col": supplier_col,
            "category_col": category_col
        },
        "upc_stats": {
            "total_valid_upcs": total_valid_upcs,
            "unique_upcs": len(unique_upcs),
            "duplicate_upc_records": duplicate_upcs_count
        },
        "null_counts": dict(col_nulls),
        "sample_records": sample_rows[:2]
    }

if __name__ == '__main__':
    all_profiles = []
    for f in files_info:
        p = analyze_dataset(f)
        all_profiles.append(p)
        
    def default_serializer(obj):
        if hasattr(obj, 'item'):
            return obj.item()
        return str(obj)

    with open('dataset_full_profile.json', 'w', encoding='utf-8') as out:
        json.dump(all_profiles, out, indent=2, default=default_serializer)
    print("\nDataset profiling complete! Saved to dataset_full_profile.json")
