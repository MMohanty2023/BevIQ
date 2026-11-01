"""
Missing UPC Identification + Product Row Combination Matching  (v2 - OPTIMISED)
===============================================================================
OPTIMISATIONS vs v1:
 - Only rows whose UPC is NOT in master go through fuzzy matching (skip exact matches early)
 - rapidfuzz.process.extractOne() on pre-built list of master keys (10-50x faster than per-row apply)
 - BrandName pre-filter: only fuzzy-match against master rows sharing the same first brand token
   → reduces search space from 189K → ~hundreds per row
 - Parallel processing of cat sheets sequentially (Beer → Wine → RTD → Spirits)

Usage:
    python tools/missing_upc_matcher_v2.py
"""

import os
import sys
import re
import glob
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from rapidfuzz import fuzz, process as rfprocess

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("missing_upc_v2")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_XL = os.path.join(REPORT_DIR, f"Missing_UPC_Analysis_{TIMESTAMP}.xlsx")

# ── Thresholds ────────────────────────────────────────────────────────────────
EXACT_SCORE   = 95
PRODUCT_SCORE = 80
POSSIBLE_SCORE= 60


# ══════════════════════════════════════════════════════════════════════════════
# 1.  UPC utilities
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


def norm_str(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ''
    return re.sub(r'\s+', ' ', str(v).strip().lower())


def brand_token(brand_str: str) -> str:
    """First meaningful word of brand for pre-filtering."""
    t = norm_str(brand_str)
    words = [w for w in t.split() if len(w) > 2 and w not in ('the', 'and', 'for', 'of')]
    return words[0] if words else t[:6]


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Load data
# ══════════════════════════════════════════════════════════════════════════════

def find_csv(pattern: str) -> str:
    csvs = glob.glob(os.path.join(BASE_DIR, '*.csv'))
    matches = [f for f in csvs if pattern.lower() in os.path.basename(f).lower()]
    if not matches:
        raise FileNotFoundError(f"No CSV matching '{pattern}' in {BASE_DIR}")
    return matches[0]


def load_allbrand() -> pd.DataFrame:
    path = find_csv('ALLBrand')
    log.info(f"Loading AllBrand: {os.path.basename(path)}")
    df = pd.read_csv(path, sep='|', dtype=str, encoding='utf-8-sig', low_memory=False)
    df.columns = [c.strip("' ") for c in df.columns]
    df['clean_upc']     = df['UPCCode'].apply(clean_upc)
    df['clean_alt_upcs']= df['AlternateUPCCode'].apply(parse_alt_upcs)
    df['orig_row']      = (df.index + 2).astype(int)
    log.info(f"  AllBrand: {len(df):,} rows loaded")
    return df


def load_cat_sheet(name: str, pattern: str) -> pd.DataFrame:
    path = find_csv(pattern)
    log.info(f"Loading {name}: {os.path.basename(path)}")
    df = pd.read_csv(path, sep=',', dtype=str, encoding='utf-8-sig', low_memory=False)

    def get_upc(row):
        u = extract_upc_from_product(row.get('Product', ''))
        return u or clean_upc(row.get('UPC 13 digit', None))

    df['clean_upc']  = df.apply(get_upc, axis=1)
    df['source_sheet'] = name
    df['orig_row']   = (df.index + 2).astype(int)
    log.info(f"  {name}: {len(df):,} rows  |  valid UPCs: {df['clean_upc'].notna().sum():,}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Master indexes
# ══════════════════════════════════════════════════════════════════════════════

def build_indexes(master_df: pd.DataFrame):
    """Returns upc_idx, alt_idx, brand_token_idx, master_keys_list, master_keys_series"""
    upc_idx   = {}  # clean_upc → master df index
    alt_idx   = {}  # alt_upc → master df index
    brand_idx = defaultdict(list)  # brand_token → list of (master_df_index, key_str)

    log.info("Building master UPC + brand indexes ...")
    keys_list = []

    for idx, row in master_df.iterrows():
        # UPC indexes
        if row['clean_upc']:
            upc_idx.setdefault(row['clean_upc'], idx)
        for au in row['clean_alt_upcs']:
            alt_idx.setdefault(au, idx)

        # Product key
        key = ' | '.join([
            norm_str(row.get('BrandName',      '')),
            norm_str(row.get('ProductName',    '')),
            norm_str(row.get('Size',           '')),
            norm_str(row.get('Flavor',         '')),
            norm_str(row.get('ProductCategory','')),
            norm_str(row.get('SupplierName',   '')),
        ])
        keys_list.append((idx, key))

        bt = brand_token(str(row.get('BrandName', '') or ''))
        if bt:
            brand_idx[bt].append((idx, key))

    master_keys_series = pd.Series(
        {idx: key for idx, key in keys_list},
        name='product_key',
    )

    log.info(f"  Primary UPCs: {len(upc_idx):,}")
    log.info(f"  Alternate UPCs: {len(alt_idx):,}")
    log.info(f"  Brand token buckets: {len(brand_idx):,}")
    return upc_idx, alt_idx, brand_idx, keys_list, master_keys_series


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Cat-sheet product key extraction
# ══════════════════════════════════════════════════════════════════════════════

def cat_product_key(row: pd.Series) -> str:
    def pick(*keys):
        for k in keys:
            v = row.get(k)
            if v and norm_str(v) not in ('', 'nan', 'none'):
                return norm_str(v)
        return ''

    brand = pick(
        'Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
        'Final Brand Name', 'Finalized Name September', 'Updated Brand Name'
    )
    product = pick('Product', 'ProductName')
    if product:
        product = re.sub(r'\s*-\s*\d{13}\s*$', '', product).strip().lower()

    size     = pick('Beer Size Groups Value', 'RTD Size Value',
                    'Spirits Sizes Value', 'Size Packages Value', 'Size')
    flavor   = pick('Beer Mezzo Styles Value', 'Beer Micro Styles Value',
                    'Spirits Flavors Value', 'Flavor Groups Value', 'Flavors Value')
    category = pick('Beer Category Value', 'RTD Category Value',
                    'Spirits Category Value', 'Categories Value')
    supplier = pick('Beer Vendors Value', 'Wine Suppliers Value',
                    'Spirits Suppliers Value')

    return ' | '.join([brand, product, size, flavor, category, supplier])


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Main analysis
# ══════════════════════════════════════════════════════════════════════════════

def classify(score: int) -> str:
    if score >= EXACT_SCORE:   return "Exact Match"
    if score >= PRODUCT_SCORE: return "Product Match - UPC Missing"
    if score >= POSSIBLE_SCORE:return "Possible Match"
    return "New Product"


def analyse_sheet(
    cat_df: pd.DataFrame,
    sheet_name: str,
    upc_idx: dict,
    alt_idx: dict,
    brand_idx: dict,
    keys_list: list,
    master_df: pd.DataFrame,
) -> list[dict]:

    records  = []
    total    = len(cat_df)
    log.info(f"  Analysing {sheet_name}: {total:,} rows ...")

    # Pre-compute: which rows are UPC-missing (skip exact UPC matches cheaply)
    exact_upcs  = set(upc_idx.keys())
    alt_upcs    = set(alt_idx.keys())

    # Build full master keys list for fallback (no brand filter)
    all_master_choices = [(idx, key) for idx, key in keys_list]

    for i, (_, crow) in enumerate(cat_df.iterrows()):
        if i % 5000 == 0 and i > 0:
            log.info(f"    {sheet_name}: {i:,}/{total:,}")

        upc       = crow.get('clean_upc')
        src_upc   = str(crow.get('UPC 13 digit', '') or '')
        product_t = str(crow.get('Product', '') or '')[:200]

        base = {
            "Source Sheet":         sheet_name,
            "Source Row":           crow.get('orig_row', ''),
            "Source UPC (raw)":     src_upc,
            "Extracted UPC":        upc or '',
            "Product Text":         product_t,
            "Brand (Cat Sheet)":    '',
            "Size (Cat Sheet)":     '',
            "Master Row":           '',
            "Master UPC":           '',
            "Master Alt UPC":       '',
            "Master Brand":         '',
            "Master OCR Brand":     '',
            "Master Ext Brand":     '',
            "Master Product Name":  '',
            "Master Size":          '',
            "Master Supplier":      '',
            "Match Status":         '',
            "Confidence Score":     '',
            "Suggested UPC":        '',
            "Remarks":              '',
        }

        # Fill cat-sheet brand/size for readability
        def pick(*keys):
            for k in keys:
                v = crow.get(k)
                if v and norm_str(v) not in ('', 'nan', 'none'):
                    return norm_str(v)
            return ''

        base["Brand (Cat Sheet)"] = pick(
            'Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
            'Final Brand Name', 'Finalized Name September', 'Updated Brand Name'
        )
        base["Size (Cat Sheet)"] = pick(
            'Beer Size Groups Value', 'RTD Size Value',
            'Spirits Sizes Value', 'Size Packages Value'
        )

        # ── No valid UPC ──────────────────────────────────────────────────────
        if not upc:
            base["Match Status"] = "No Valid UPC"
            base["Remarks"]      = "Could not extract 13-digit UPC"
            records.append(base)
            continue

        # ── Exact primary UPC match ───────────────────────────────────────────
        if upc in exact_upcs:
            m_idx = upc_idx[upc]
            m = master_df.loc[m_idx]
            base.update({
                "Match Status":        "Exact Match",
                "Confidence Score":    100,
                "Master Row":          int(m.get('orig_row', 0)),
                "Master UPC":          m.get('UPCCode', ''),
                "Master Brand":        m.get('BrandName', ''),
                "Master OCR Brand":    m.get('OCRBrandName', ''),
                "Master Ext Brand":    m.get('ExtendedBrandName', ''),
                "Master Product Name": m.get('ProductName', ''),
                "Master Size":         m.get('Size', ''),
                "Master Supplier":     m.get('SupplierName', ''),
                "Remarks":             "UPC matched in Master primary UPC column",
            })
            records.append(base)
            continue

        # ── Alternate UPC match ───────────────────────────────────────────────
        if upc in alt_upcs:
            m_idx = alt_idx[upc]
            m = master_df.loc[m_idx]
            base.update({
                "Match Status":        "Exact Match",
                "Confidence Score":    100,
                "Master Row":          int(m.get('orig_row', 0)),
                "Master UPC":          m.get('UPCCode', ''),
                "Master Alt UPC":      m.get('AlternateUPCCode', ''),
                "Master Brand":        m.get('BrandName', ''),
                "Master OCR Brand":    m.get('OCRBrandName', ''),
                "Master Ext Brand":    m.get('ExtendedBrandName', ''),
                "Master Product Name": m.get('ProductName', ''),
                "Master Size":         m.get('Size', ''),
                "Master Supplier":     m.get('SupplierName', ''),
                "Suggested UPC":       m.get('UPCCode', ''),
                "Remarks":             "UPC matched via Master Alternate UPC column",
            })
            records.append(base)
            continue

        # ── UPC MISSING — fuzzy product match ─────────────────────────────────
        cat_key = cat_product_key(crow)

        if not cat_key.replace('|', '').strip():
            base["Match Status"] = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"] = "No usable product fields for matching"
            records.append(base)
            continue

        # Pre-filter by brand token (much faster)
        bt = brand_token(base["Brand (Cat Sheet)"])
        candidate_choices = brand_idx.get(bt, []) or all_master_choices

        # Use rapidfuzz.process.extractOne (C-speed)
        choices_keys  = [key for _, key in candidate_choices]
        choices_idxs  = [idx for idx, _ in candidate_choices]

        result = rfprocess.extractOne(
            cat_key, choices_keys,
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
        m_idx = choices_idxs[best_pos]
        m     = master_df.loc[m_idx]
        status = classify(int(best_score))

        base.update({
            "Match Status":        status,
            "Confidence Score":    int(best_score),
            "Master Row":          int(m.get('orig_row', 0)),
            "Master UPC":          m.get('UPCCode', ''),
            "Master Alt UPC":      m.get('AlternateUPCCode', ''),
            "Master Brand":        m.get('BrandName', ''),
            "Master OCR Brand":    m.get('OCRBrandName', ''),
            "Master Ext Brand":    m.get('ExtendedBrandName', ''),
            "Master Product Name": m.get('ProductName', ''),
            "Master Size":         m.get('Size', ''),
            "Master Supplier":     m.get('SupplierName', ''),
        })

        if status == "Exact Match":
            base["Suggested UPC"] = m.get('UPCCode', '')
            base["Remarks"] = f"High-confidence product match (score={best_score}). Verify UPC before applying."
        elif status == "Product Match - UPC Missing":
            base["Suggested UPC"] = m.get('UPCCode', '')
            base["Remarks"] = (
                f"Product exists in Master (row {base['Master Row']}) but UPC absent in cat sheet. "
                f"Suggested UPC from Master. Score={best_score}. MANUAL VERIFICATION REQUIRED."
            )
        elif status == "Possible Match":
            base["Suggested UPC"] = ''
            base["Remarks"] = (
                f"Partial similarity (score={best_score}). Uncertain — manual verification "
                f"required before any UPC assignment."
            )
        else:
            base["Remarks"] = "No reliable match. Treat as new product."

        records.append(base)

    log.info(f"  {sheet_name}: {len(records):,} records classified")
    return records


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Excel report
# ══════════════════════════════════════════════════════════════════════════════

STATUS_COLORS = {
    "Exact Match":                  "C6EFCE",
    "Product Match - UPC Missing":  "FFEB9C",
    "Possible Match":               "FFCC99",
    "New Product":                  "FFC7CE",
    "No Valid UPC":                 "D9D9D9",
}


def write_excel(all_records: list[dict], path: str):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.utils import get_column_letter

    log.info(f"Writing Excel: {path}")
    df = pd.DataFrame(all_records)

    df_missing    = df[~df["Match Status"].isin(["Exact Match"])].copy()
    df_exact      = df[df["Match Status"] == "Exact Match"].copy()
    df_prod       = df[df["Match Status"] == "Product Match - UPC Missing"].copy()
    df_possible   = df[df["Match Status"] == "Possible Match"].copy()
    df_new        = df[df["Match Status"] == "New Product"].copy()

    # Summary
    rows = []
    for sheet in ['Beer', 'Wine', 'RTD', 'Spirits', 'TOTAL']:
        sub = df if sheet == 'TOTAL' else df[df["Source Sheet"] == sheet]
        t = len(sub)
        rows.append({
            "Sheet":                     sheet,
            "Total Records":             t,
            "Exact Matches":             int((sub["Match Status"] == "Exact Match").sum()),
            "Product Match-UPC Missing": int((sub["Match Status"] == "Product Match - UPC Missing").sum()),
            "Possible Matches":          int((sub["Match Status"] == "Possible Match").sum()),
            "New Products":              int((sub["Match Status"] == "New Product").sum()),
            "No Valid UPC":              int((sub["Match Status"] == "No Valid UPC").sum()),
            "Missing UPC Count":         int((sub["Match Status"] != "Exact Match").sum()),
            "Missing UPC %":             f"{((sub['Match Status'] != 'Exact Match').sum() / max(t,1)) * 100:.1f}%",
        })
    df_summary = pd.DataFrame(rows)

    sheets_to_write = [
        ("Summary Report",             df_summary,  "1F497D"),
        ("Missing UPCs",               df_missing,  "C00000"),
        ("Exact Product Matches",      df_exact,    "375623"),
        ("Product Match-UPC Missing",  df_prod,     "7F6000"),
        ("Possible Matches",           df_possible, "974706"),
        ("New Products",               df_new,      "843C0C"),
    ]

    wb = Workbook()
    wb.remove(wb.active)

    for sheet_title, data, hdr_color in sheets_to_write:
        ws = wb.create_sheet(title=sheet_title[:31])

        if data.empty:
            ws.append(["No records in this category."])
            continue

        for r_idx, row_data in enumerate(dataframe_to_rows(data, index=False, header=True), start=1):
            ws.append(row_data)

        # Colour rows by status
        status_cols = [c for c in (data.columns.tolist() if not data.empty else [])
                       if c == "Match Status"]
        if status_cols:
            s_col_idx = list(data.columns).index("Match Status") + 1
            for r in range(2, ws.max_row + 1):
                sc = ws.cell(row=r, column=s_col_idx)
                fill = PatternFill("solid", fgColor=STATUS_COLORS.get(str(sc.value or ''), "FFFFFF"))
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=r, column=c).fill = fill

        # Header style
        hfill = PatternFill("solid", fgColor=hdr_color)
        hfont = Font(bold=True, color="FFFFFF", size=10)
        for cell in ws[1]:
            cell.fill  = hfill
            cell.font  = hfont
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
        ws.freeze_panes = "A2"

        # Column widths
        for col_idx in range(1, ws.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_len = max(
                (len(str(ws.cell(row=r, column=col_idx).value or ''))
                 for r in range(1, min(ws.max_row + 1, 200))),
                default=10,
            )
            ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 50)

    wb.save(path)
    log.info(f"Report saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    log.info("=" * 70)
    log.info("Missing UPC Identification + Product Match  [v2 OPTIMISED]")
    log.info("=" * 70)

    master_df = load_allbrand()
    upc_idx, alt_idx, brand_idx, keys_list, _ = build_indexes(master_df)

    cat_sheets = [
        ("Beer",    "Beer"),
        ("Wine",    "Wine"),
        ("RTD",     "RTDs"),
        ("Spirits", "Spirits"),
    ]

    all_records = []
    for name, pattern in cat_sheets:
        try:
            cat_df  = load_cat_sheet(name, pattern)
            records = analyse_sheet(cat_df, name, upc_idx, alt_idx,
                                    brand_idx, keys_list, master_df)
            all_records.extend(records)
        except Exception as e:
            log.error(f"ERROR in {name}: {e}", exc_info=True)

    log.info(f"\nTotal records: {len(all_records):,}")
    df = pd.DataFrame(all_records)
    for status, cnt in df["Match Status"].value_counts().items():
        log.info(f"  {status:<40} {cnt:>8,}")

    write_excel(all_records, OUTPUT_XL)
    print(f"\nReport: {OUTPUT_XL}")


if __name__ == "__main__":
    main()

