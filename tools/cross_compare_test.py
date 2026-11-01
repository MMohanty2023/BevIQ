import pandas as pd
import re
import json

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

print("Loading Master UPCs...")
df_master = pd.read_csv('AIMasterBrandData.csv', sep='|', usecols=['UPCCode', 'AlternateUPCCode', 'BrandName', 'ProductName'], dtype=str)
master_upcs = set()
for _, r in df_master.iterrows():
    u = clean_upc(r['UPCCode'])
    if u: master_upcs.add(u)
    alt = clean_upc(r.get('AlternateUPCCode', ''))
    if alt: master_upcs.add(alt)

print(f"Master total unique primary + alternate UPCs: {len(master_upcs):,}")

cat_files = [
    ('Beer', 'Categorization 2026 - Beer.csv', ','),
    ('RTDs', 'Categorization 2026 - RTDs.csv', ','),
    ('Spirits', 'Categorization 2026 - Spirits.csv', ','),
    ('Wine', 'Categorization 2026 - Wine.csv', ','),
    ('ALLBrand', '$ALLBrand_202610291524.csv', '|')
]

for name, fname, sep in cat_files:
    upc_col = 'UPCCode' if 'Brand' in name else 'UPC 13 digit'
    prod_col = 'ProductName' if 'Brand' in name else 'Product'
    df = pd.read_csv(fname, sep=sep, usecols=[upc_col, prod_col], dtype=str)
    cat_upcs = set()
    for _, r in df.iterrows():
        u = clean_upc(r[upc_col], r[prod_col])
        if u: cat_upcs.add(u)
        
    overlap = master_upcs.intersection(cat_upcs)
    in_cat_not_master = cat_upcs - master_upcs
    in_master_not_cat = master_upcs - cat_upcs
    print(f"\n--- {name} vs AIMaster ---")
    print(f"  {name} Total Unique UPCs: {len(cat_upcs):,}")
    print(f"  Matching (In both): {len(overlap):,} ({(len(overlap)/len(cat_upcs)*100):.1f}%)")
    print(f"  In {name} but MISSING in AIMaster: {len(in_cat_not_master):,}")
