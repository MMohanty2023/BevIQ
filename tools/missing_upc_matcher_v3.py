"""
Missing UPC Identification + Product Row Combination Matching  (v3 - FAST)
===========================================================================
STRATEGY:
  Phase 1 (FAST): Exact UPC lookup for all rows — handles ~60-75% instantly.
  Phase 2 (SMART): Only the truly missing UPCs go through fuzzy matching.
                   Brand-token pre-filter shrinks candidate set per row.
                   rapidfuzz.process.extractOne handles the rest in C-speed.

Usage:
    python tools/missing_upc_matcher_v3.py

Output:
    reports/Missing_UPC_Analysis_<timestamp>.xlsx
"""

import os, sys, re, glob, logging
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from rapidfuzz import fuzz, process as rfprocess

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("upc_v3")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_XL = os.path.join(REPORT_DIR, f"Missing_UPC_Analysis_{TIMESTAMP}.xlsx")

EXACT_SCORE    = 95
PRODUCT_SCORE  = 80
POSSIBLE_SCORE = 60

# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def clean_upc(val) -> str | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip().strip("'\"")
    if not s or s.lower() in ('nan', '{}', 'none', ''):
        return None
    if s.upper().startswith('UPC='):
        s = s[4:]
    if 'E+' in s.upper():
        try:
            s = str(int(float(s)))
        except ValueError:
            return None
    s = re.sub(r'\D', '', s)
    if not s:
        return None
    s = s.zfill(13) if len(s) < 13 else s[-13:]
    return s if len(s) == 13 else None

def extract_upc_from_product(text) -> str | None:
    if not isinstance(text, str):
        return None
    m = re.search(r'-\s*(\d{13})\s*$', text)
    return m.group(1) if m else None

def parse_alt_upcs(val) -> set:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return set()
    s = str(val).strip('{}')
    if not s or s.lower() in ('nan', 'none'):
        return set()
    return {c for p in re.split(r'[,;\s]+', s) if (c := clean_upc(p))}

def ns(v) -> str:
    """Normalise string."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ''
    return re.sub(r'\s+', ' ', str(v).strip().lower())

def brand_token(brand: str) -> str:
    words = [w for w in ns(brand).split() if len(w) > 2]
    return words[0] if words else ns(brand)[:5]

def find_csv(pat: str) -> str:
    hits = [f for f in glob.glob(os.path.join(BASE_DIR, '*.csv'))
            if pat.lower() in os.path.basename(f).lower()]
    if not hits:
        raise FileNotFoundError(f"No CSV matching '{pat}'")
    return hits[0]

# ══════════════════════════════════════════════════════════════════════════════
# Load master
# ══════════════════════════════════════════════════════════════════════════════

def load_master() -> pd.DataFrame:
    path = find_csv('ALLBrand')
    log.info(f"Loading AllBrand: {os.path.basename(path)}")
    df = pd.read_csv(path, sep='|', dtype=str, encoding='utf-8-sig', low_memory=False)
    df.columns = [c.strip("' ") for c in df.columns]
    df['clean_upc']      = df['UPCCode'].apply(clean_upc)
    df['clean_alt_upcs'] = df['AlternateUPCCode'].apply(parse_alt_upcs)
    df['orig_row']       = (df.index + 2).astype(int)
    log.info(f"  {len(df):,} master rows loaded")
    return df

def build_master_indexes(mdf: pd.DataFrame):
    upc_idx = {}     # upc → master integer index
    alt_idx = {}     # alt_upc → master integer index
    brand_bucket = defaultdict(list)  # brand_token → [(df_index, key_str)]

    log.info("Building master indexes ...")
    for i, (idx, row) in enumerate(mdf.iterrows()):
        if row['clean_upc']:
            upc_idx.setdefault(row['clean_upc'], idx)
        for au in row['clean_alt_upcs']:
            alt_idx.setdefault(au, idx)

        key = ' | '.join([
            ns(row.get('BrandName', '')),
            ns(row.get('ProductName', '')),
            ns(row.get('Size', '')),
            ns(row.get('Flavor', '')),
            ns(row.get('ProductCategory', '')),
            ns(row.get('SupplierName', '')),
        ])
        bt = brand_token(str(row.get('BrandName', '') or ''))
        if bt:
            brand_bucket[bt].append((idx, key))

    log.info(f"  Primary UPCs:      {len(upc_idx):,}")
    log.info(f"  Alternate UPCs:    {len(alt_idx):,}")
    log.info(f"  Brand buckets:     {len(brand_bucket):,}")
    return upc_idx, alt_idx, brand_bucket

# ══════════════════════════════════════════════════════════════════════════════
# Cat sheet loaders
# ══════════════════════════════════════════════════════════════════════════════

def _get_upc_from_row(row) -> str | None:
    u = extract_upc_from_product(row.get('Product', ''))
    return u or clean_upc(row.get('UPC 13 digit'))

def _brand_from_cat_row(row) -> str:
    for k in ('Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
              'Final Brand Name', 'Finalized Name September', 'Updated Brand Name'):
        v = ns(row.get(k, ''))
        if v and v not in ('nan', 'none'):
            return v
    return ''

def _size_from_cat_row(row) -> str:
    for k in ('Beer Size Groups Value', 'RTD Size Value',
              'Spirits Sizes Value', 'Size Packages Value'):
        v = ns(row.get(k, ''))
        if v and v not in ('nan', 'none'):
            return v
    return ''

def _cat_key(row) -> str:
    brand   = _brand_from_cat_row(row)
    product = ns(row.get('Product', ''))
    product = re.sub(r'\s*-\s*\d{13}\s*$', '', product).strip()
    size    = _size_from_cat_row(row)
    flavor  = next((ns(row.get(k,'')) for k in
                    ('Beer Mezzo Styles Value','Beer Micro Styles Value',
                     'Spirits Flavors Value','Flavor Groups Value','Flavors Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    cat     = next((ns(row.get(k,'')) for k in
                    ('Beer Category Value','RTD Category Value',
                     'Spirits Category Value','Categories Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    supp    = next((ns(row.get(k,'')) for k in
                    ('Beer Vendors Value','Wine Suppliers Value',
                     'Spirits Suppliers Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    return ' | '.join([brand, product, size, flavor, cat, supp])

def load_cat(name: str, pattern: str) -> pd.DataFrame:
    path = find_csv(pattern)
    log.info(f"Loading {name}: {os.path.basename(path)}")
    df = pd.read_csv(path, sep=',', dtype=str, encoding='utf-8-sig', low_memory=False)
    df['clean_upc']    = df.apply(_get_upc_from_row, axis=1)
    df['source_sheet'] = name
    df['orig_row']     = (df.index + 2).astype(int)
    log.info(f"  {name}: {len(df):,} rows | valid UPCs: {df['clean_upc'].notna().sum():,}")
    return df

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: exact UPC classification (vectorised)
# ══════════════════════════════════════════════════════════════════════════════

STATUS_COLORS = {
    "Exact Match":                 "C6EFCE",
    "Product Match - UPC Missing": "FFEB9C",
    "Possible Match":              "FFCC99",
    "New Product":                 "FFC7CE",
    "No Valid UPC":                "D9D9D9",
}

def classify_score(score: int) -> str:
    if score >= EXACT_SCORE:    return "Exact Match"
    if score >= PRODUCT_SCORE:  return "Product Match - UPC Missing"
    if score >= POSSIBLE_SCORE: return "Possible Match"
    return "New Product"

def _master_fields(m: pd.Series) -> dict:
    return {
        "Master Row":          int(m.get('orig_row', 0)),
        "Master UPC":          str(m.get('UPCCode', '') or ''),
        "Master Alt UPC":      str(m.get('AlternateUPCCode', '') or ''),
        "Master Brand":        str(m.get('BrandName', '') or ''),
        "Master OCR Brand":    str(m.get('OCRBrandName', '') or ''),
        "Master Ext Brand":    str(m.get('ExtendedBrandName', '') or ''),
        "Master Product Name": str(m.get('ProductName', '') or ''),
        "Master Size":         str(m.get('Size', '') or ''),
        "Master Supplier":     str(m.get('SupplierName', '') or ''),
    }

EMPTY_MASTER = {
    "Master Row":'', "Master UPC":'', "Master Alt UPC":'',
    "Master Brand":'', "Master OCR Brand":'', "Master Ext Brand":'',
    "Master Product Name":'', "Master Size":'', "Master Supplier":'',
}

def analyse_sheet(
    cat_df: pd.DataFrame,
    sheet_name: str,
    upc_idx: dict, alt_idx: dict, brand_bucket: dict,
    mdf: pd.DataFrame,
) -> list[dict]:

    log.info(f"  Processing {sheet_name} ({len(cat_df):,} rows) ...")
    records = []

    exact_set = set(upc_idx.keys())
    alt_set   = set(alt_idx.keys())

    # Pre-build all master fuzzy candidates (for rows with no brand match)
    # Only used as absolute last fallback
    all_cands_keys = []
    all_cands_idxs = []
    for idx, row in mdf.iterrows():
        key = ' | '.join([ns(row.get('BrandName','')), ns(row.get('ProductName','')),
                          ns(row.get('Size','')), ns(row.get('Flavor','')),
                          ns(row.get('ProductCategory','')), ns(row.get('SupplierName',''))])
        all_cands_keys.append(key)
        all_cands_idxs.append(idx)

    total   = len(cat_df)
    missing = 0

    for i, (_, crow) in enumerate(cat_df.iterrows()):
        if i % 10000 == 0 and i > 0:
            log.info(f"    {sheet_name}: {i:,}/{total:,} (missing so far: {missing:,})")

        upc     = crow.get('clean_upc')
        src_upc = str(crow.get('UPC 13 digit', '') or '')
        prod_t  = str(crow.get('Product', '') or '')[:200]
        brand_c = _brand_from_cat_row(crow)
        size_c  = _size_from_cat_row(crow)

        base = {
            "Source Sheet":        sheet_name,
            "Source Row":          crow.get('orig_row', ''),
            "Source UPC (raw)":    src_upc,
            "Extracted UPC":       upc or '',
            "Product Text":        prod_t,
            "Brand (Cat Sheet)":   brand_c,
            "Size (Cat Sheet)":    size_c,
            "Match Status":        '',
            "Confidence Score":    '',
            "Suggested UPC":       '',
            "Remarks":             '',
            **EMPTY_MASTER,
        }

        # ── No valid UPC ──────────────────────────────────────────────────────
        if not upc:
            base["Match Status"] = "No Valid UPC"
            base["Remarks"]      = "Could not extract 13-digit UPC"
            records.append(base)
            continue

        # ── Primary UPC exact match ───────────────────────────────────────────
        if upc in exact_set:
            m = mdf.loc[upc_idx[upc]]
            base.update({
                "Match Status":     "Exact Match",
                "Confidence Score": 100,
                "Remarks":          "UPC found in Master primary UPC column",
                **_master_fields(m),
            })
            records.append(base)
            continue

        # ── Alternate UPC exact match ─────────────────────────────────────────
        if upc in alt_set:
            m = mdf.loc[alt_idx[upc]]
            base.update({
                "Match Status":     "Exact Match",
                "Confidence Score": 100,
                "Suggested UPC":    str(m.get('UPCCode', '') or ''),
                "Remarks":          "UPC matched via Master Alternate UPC column",
                **_master_fields(m),
            })
            records.append(base)
            continue

        # ── UPC MISSING — fuzzy product match ─────────────────────────────────
        missing += 1
        cat_key = _cat_key(crow)

        if not cat_key.replace('|', '').strip():
            base["Match Status"]     = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"]          = "No usable fields for product matching"
            records.append(base)
            continue

        # Try brand-token bucket first (fast, narrow)
        bt       = brand_token(brand_c)
        bucket   = brand_bucket.get(bt, [])
        if bucket:
            cand_keys = [k for _, k in bucket]
            cand_idxs = [i for i, _ in bucket]
        else:
            # No brand bucket — fallback to full master (slower but complete)
            cand_keys = all_cands_keys
            cand_idxs = all_cands_idxs

        result = rfprocess.extractOne(
            cat_key, cand_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=POSSIBLE_SCORE - 1,
        )

        if result is None:
            base["Match Status"]     = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"]          = "No similar product found in Master"
            records.append(base)
            continue

        best_key, best_score, best_pos = result
        m     = mdf.loc[cand_idxs[best_pos]]
        status = classify_score(int(best_score))

        base.update({
            "Match Status":     status,
            "Confidence Score": int(best_score),
            **_master_fields(m),
        })

        if status in ("Exact Match", "Product Match - UPC Missing"):
            base["Suggested UPC"] = str(m.get('UPCCode', '') or '')
            base["Remarks"] = (
                f"Product found in Master row {base['Master Row']} "
                f"(score={best_score}). Suggested UPC from Master. "
                f"MANUAL VERIFICATION REQUIRED before applying."
            )
        elif status == "Possible Match":
            base["Remarks"] = (
                f"Partial similarity (score={best_score}). "
                f"Manual verification required — do NOT apply UPC automatically."
            )
        else:
            base["Remarks"] = "No reliable match. Likely a new product."

        records.append(base)

    log.info(f"  {sheet_name}: done — {len(records):,} records ({missing:,} had missing UPC)")
    return records

# ══════════════════════════════════════════════════════════════════════════════
# Excel report
# ══════════════════════════════════════════════════════════════════════════════

def write_excel(records: list[dict], path: str):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.utils import get_column_letter

    log.info(f"Writing Excel report → {path}")
    df = pd.DataFrame(records)

    df_miss = df[df["Match Status"] != "Exact Match"].copy()
    df_ex   = df[df["Match Status"] == "Exact Match"].copy()
    df_prod = df[df["Match Status"] == "Product Match - UPC Missing"].copy()
    df_pos  = df[df["Match Status"] == "Possible Match"].copy()
    df_new  = df[df["Match Status"] == "New Product"].copy()
    df_noupc= df[df["Match Status"] == "No Valid UPC"].copy()

    # Summary
    sum_rows = []
    for s in ['Beer', 'Wine', 'RTD', 'Spirits', 'TOTAL']:
        sub = df if s == 'TOTAL' else df[df["Source Sheet"] == s]
        t   = len(sub)
        sum_rows.append({
            "Sheet":                     s,
            "Total Records":             t,
            "Exact Matches":             int((sub["Match Status"] == "Exact Match").sum()),
            "Product Match-UPC Missing": int((sub["Match Status"] == "Product Match - UPC Missing").sum()),
            "Possible Matches":          int((sub["Match Status"] == "Possible Match").sum()),
            "New Products":              int((sub["Match Status"] == "New Product").sum()),
            "No Valid UPC":              int((sub["Match Status"] == "No Valid UPC").sum()),
            "Missing UPC Count":         int((sub["Match Status"] != "Exact Match").sum()),
            "Missing UPC %":             f"{((sub['Match Status'] != 'Exact Match').sum()/max(t,1))*100:.1f}%",
        })

    all_sheets = [
        ("Summary Report",            pd.DataFrame(sum_rows),  "1F497D"),
        ("Missing UPCs",              df_miss,                 "C00000"),
        ("Exact Product Matches",     df_ex,                   "375623"),
        ("Product Match-UPC Missing", df_prod,                 "7F6000"),
        ("Possible Matches",          df_pos,                  "974706"),
        ("New Products",              df_new,                  "843C0C"),
        ("No Valid UPC",              df_noupc,                "595959"),
    ]

    wb = Workbook()
    wb.remove(wb.active)

    for title, data, hdr_hex in all_sheets:
        ws = wb.create_sheet(title=title[:31])
        if data.empty:
            ws.append(["No records in this category."])
            continue

        for rdata in dataframe_to_rows(data, index=False, header=True):
            ws.append(rdata)

        # Row colouring
        if "Match Status" in data.columns:
            sc_idx = list(data.columns).index("Match Status") + 1
            for r in range(2, ws.max_row + 1):
                cell_val = str(ws.cell(row=r, column=sc_idx).value or '')
                fill = PatternFill("solid", fgColor=STATUS_COLORS.get(cell_val, "FFFFFF"))
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=r, column=c).fill = fill

        # Header style
        hfill = PatternFill("solid", fgColor=hdr_hex)
        for cell in ws[1]:
            cell.fill      = hfill
            cell.font      = Font(bold=True, color="FFFFFF", size=10)
            cell.alignment = Alignment(horizontal='center', wrap_text=True)

        ws.freeze_panes = "A2"

        # Column widths (sample first 300 rows for speed)
        for c in range(1, ws.max_column + 1):
            max_len = max(
                (len(str(ws.cell(row=r, column=c).value or ''))
                 for r in range(1, min(ws.max_row + 1, 301))),
                default=10,
            )
            ws.column_dimensions[get_column_letter(c)].width = min(max(max_len + 2, 12), 55)

    wb.save(path)
    log.info(f"Saved: {path}")

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    log.info("=" * 70)
    log.info("Missing UPC Identification + Product Row Combination Matching v3")
    log.info("=" * 70)

    mdf = load_master()
    upc_idx, alt_idx, brand_bucket = build_master_indexes(mdf)

    cat_sheets = [
        ("Beer",    "Beer"),
        ("Wine",    "Wine"),
        ("RTD",     "RTDs"),
        ("Spirits", "Spirits"),
    ]

    all_records = []
    for name, pat in cat_sheets:
        try:
            cat_df  = load_cat(name, pat)
            records = analyse_sheet(cat_df, name, upc_idx, alt_idx, brand_bucket, mdf)
            all_records.extend(records)
        except Exception as e:
            log.error(f"Error in {name}: {e}", exc_info=True)

    log.info(f"\nTotal: {len(all_records):,} records")
    df_all = pd.DataFrame(all_records)
    for status, cnt in df_all["Match Status"].value_counts().items():
        log.info(f"  {status:<42} {cnt:>8,}")

    write_excel(all_records, OUTPUT_XL)
    print(f"\nReport: {OUTPUT_XL}")
    return OUTPUT_XL

if __name__ == "__main__":
    main()

