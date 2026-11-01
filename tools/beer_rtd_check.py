import pandas as pd
import re

def clean_upc(val, product_str=None):
    if product_str and isinstance(product_str, str):
        m = re.search(r'-\s*(\d{11,14})\s*$', product_str)
        if m:
            digits = m.group(1)
            return digits.zfill(13) if len(digits) in [11, 12] else digits
    if pd.isna(val): return ""
    digits = re.sub(r'\D', '', str(val))
    return digits.zfill(13) if len(digits) in [11, 12] else digits

beer = pd.read_csv('Categorization 2026 - Beer.csv', dtype=str)
rtd = pd.read_csv('Categorization 2026 - RTDs.csv', dtype=str)

beer['clean_upc'] = beer.apply(lambda r: clean_upc(r['UPC 13 digit'], r['Product']), axis=1)
rtd['clean_upc'] = rtd.apply(lambda r: clean_upc(r['UPC 13 digit'], r['Product']), axis=1)

beer_upcs = set(beer['clean_upc'])
rtd_upcs = set(rtd['clean_upc'])

overlap = beer_upcs.intersection(rtd_upcs)
print(f"Overlap between Beer and RTD: {len(overlap):,} UPCs exist in BOTH Beer and RTD!")

if overlap:
    sample_overlap_upc = list(overlap)[0]
    print(f"\nSample overlapping UPC: {sample_overlap_upc}")
    beer_match = beer[beer['clean_upc'] == sample_overlap_upc].iloc[0]
    rtd_match = rtd[rtd['clean_upc'] == sample_overlap_upc].iloc[0]
    print("  In Beer -> Brand:", beer_match.get('Beer Brands Value'), "| Category:", beer_match.get('Beer Category Value'), "| Segment:", beer_match.get('Beer Segments Value'))
    print("  In RTD  -> Brand:", rtd_match.get('Brands Value'), "| Category:", rtd_match.get('RTD Category Value'), "| Base:", rtd_match.get('RTD Alcohol Base Value'))
