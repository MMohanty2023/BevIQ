import os
import glob
import pandas as pd
import json

def normalize_upc(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if not s or s.lower() == 'nan' or s.lower() == 'null':
        return ""
    # Check scientific notation e.g. 6.19947E+11
    if 'e+' in s.lower() or 'e-' in s.lower():
        try:
            f = float(s)
            s = f"{int(f)}"
        except:
            pass
    elif '.' in s:
        # e.g. "85000017731.0"
        try:
            parts = s.split('.')
            if parts[1] == '0' or parts[1] == '':
                s = parts[0]
        except:
            pass
    # strip non-digits
    digits = ''.join(c for c in s if c.isdigit())
    if not digits:
        return s
    # Standardize to 13 digits with leading zero if 12 digits, or 14, etc.
    # Keep string representation
    return digits.zfill(12) if len(digits) <= 12 else digits

def analyze_upcs():
    print("Analyzing UPC columns across files...")
    files = {
        'ALLBrand': ('$ALLBrand_202610291524.csv', '|', 'UPCCode', 'AlternateUPCCode'),
        'AIMaster': ('AIMasterBrandData.csv', '|', 'UPCCode', 'AlternateUPCCode'),
        'Beer': ('Categorization 2026 - Beer.csv', ',', 'UPC 13 digit', None),
        'RTDs': ('Categorization 2026 - RTDs.csv', ',', 'UPC 13 digit', None),
        'Spirits': ('Categorization 2026 - Spirits.csv', ',', 'UPC 13 digit', None),
        'Wine': ('Categorization 2026 - Wine.csv', ',', 'UPC 13 digit', None),
    }

    upc_sets = {}
    stats = {}

    for name, (fname, delim, upc_col, alt_col) in files.items():
        print(f"\nProcessing {name} ({fname})...")
        df = pd.read_csv(fname, sep=delim, usecols=[upc_col] if not alt_col else [upc_col, alt_col], dtype=str, on_bad_lines='skip')
        
        total_rows = len(df)
        raw_upcs = df[upc_col].dropna().astype(str)
        norm_upcs = raw_upcs.apply(normalize_upc)
        norm_upcs = norm_upcs[norm_upcs != ""]
        
        unique_upcs = set(norm_upcs)
        duplicates = len(norm_upcs) - len(unique_upcs)
        sci_not_count = raw_upcs.str.contains('E\\+|e\\+', regex=True).sum()
        
        upc_sets[name] = unique_upcs
        
        stats[name] = {
            'total_rows': total_rows,
            'non_null_upcs': len(norm_upcs),
            'unique_upcs': len(unique_upcs),
            'duplicate_upc_rows': int(duplicates),
            'scientific_notation_count': int(sci_not_count),
        }
        
        if alt_col and alt_col in df.columns:
            alt_raw = df[alt_col].dropna().astype(str)
            alt_norm = alt_raw.apply(normalize_upc)
            alt_norm = alt_norm[alt_norm != ""]
            stats[name]['unique_alt_upcs'] = len(set(alt_norm))

        print(f"  {name}: Rows={total_rows:,}, Unique UPCs={len(unique_upcs):,}, Duplicates={duplicates:,}, Sci Notation={sci_not_count:,}")

    # Cross file overlap
    print("\nCross-file UPC overlap with AIMaster:")
    master_set = upc_sets.get('AIMaster', set())
    for name in ['Beer', 'RTDs', 'Spirits', 'Wine', 'ALLBrand']:
        if name in upc_sets:
            overlap = len(master_set.intersection(upc_sets[name]))
            missing_in_cat = len(master_set - upc_sets[name])
            cat_missing_in_master = len(upc_sets[name] - master_set)
            print(f"  AIMaster & {name}: Shared={overlap:,} | In {name} but not Master={cat_missing_in_master:,}")

    with open('deep_analysis_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

if __name__ == '__main__':
    analyze_upcs()
