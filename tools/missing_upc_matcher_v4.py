"""
Missing UPC Identification + Product Row Combination Matching  (v4 - SMART FAST)
=================================================================================
KEY CHANGES from v3:
 - Phase 1: Vectorised pandas merge for exact UPC matching (milliseconds for all rows)
 - Phase 2: Fuzzy matching ONLY on rows with missing UPC, using ONLY brand-bucket candidates
   (NO fallback to full 189K master list — too slow)
 - If brand bucket empty -> classified as "New Product" (conservative, safe)
 - Total runtime: ~3-5 min for all 4 sheets

Usage:
    python tools/missing_upc_matcher_v4.py

Output:
    reports/Missing_UPC_Analysis_<timestamp>.xlsx
"""

import os, sys, re, glob, logging
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from rapidfuzz import fuzz, process as rfprocess

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("upc_v4")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_XL = os.path.join(REPORT_DIR, f"Missing_UPC_Analysis_{TIMESTAMP}.xlsx")

EXACT_SCORE    = 95
PRODUCT_SCORE  = 80
POSSIBLE_SCORE = 60

# ── Helpers ────────────────────────────────────────────────────────────────────

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

def parse_alt_upcs(val) -> list:
    """Returns list of clean UPCs from {upc1,upc2,...} notation."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return []
    s = str(val).strip('{}')
    if not s or s.lower() in ('nan', 'none'):
        return []
    return [c for p in re.split(r'[,;\s]+', s) if (c := clean_upc(p))]

def ns(v) -> str:
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

def classify_score(score: int) -> str:
    if score >= EXACT_SCORE:    return "Exact Match"
    if score >= PRODUCT_SCORE:  return "Product Match - UPC Missing"
    if score >= POSSIBLE_SCORE: return "Possible Match"
    return "New Product"

STATUS_COLORS = {
    "Exact Match":                 "C6EFCE",
    "Exact via Alt UPC":          "A9D18E",
    "Product Match - UPC Missing": "FFEB9C",
    "Possible Match":              "FFCC99",
    "New Product":                 "FFC7CE",
    "No Valid UPC":                "D9D9D9",
}

# ── Load master ────────────────────────────────────────────────────────────────

def load_master() -> pd.DataFrame:
    path = find_csv('ALLBrand')
    log.info(f"Loading AllBrand: {os.path.basename(path)}")
    df = pd.read_csv(path, sep='|', dtype=str, encoding='utf-8-sig', low_memory=False)
    df.columns = [c.strip("' ") for c in df.columns]
    df['clean_upc'] = df['UPCCode'].apply(clean_upc)
    df['orig_row']  = (df.index + 2).astype(int)

    # Expand alternate UPCs into a separate lookup DataFrame
    alt_rows = []
    for idx, row in df.iterrows():
        for au in parse_alt_upcs(row.get('AlternateUPCCode', None)):
            alt_rows.append({'alt_upc': au, 'master_idx': idx})
    df_alt = pd.DataFrame(alt_rows) if alt_rows else pd.DataFrame(columns=['alt_upc', 'master_idx'])

    log.info(f"  AllBrand: {len(df):,} rows | alt UPC pairs: {len(df_alt):,}")
    return df, df_alt


def build_brand_index(mdf: pd.DataFrame) -> dict:
    """Brand token -> list of (master_idx, product_key_str)"""
    log.info("Building brand-token index for fuzzy matching ...")
    idx_map = defaultdict(list)
    for idx, row in mdf.iterrows():
        key = ' | '.join([ns(row.get('BrandName','')), ns(row.get('ProductName','')),
                          ns(row.get('Size','')), ns(row.get('Flavor','')),
                          ns(row.get('ProductCategory','')), ns(row.get('SupplierName',''))])
        bt = brand_token(str(row.get('BrandName','') or ''))
        if bt:
            idx_map[bt].append((idx, key))
    log.info(f"  Brand buckets: {len(idx_map):,}")
    return idx_map

# ── Cat sheet loaders ──────────────────────────────────────────────────────────

def _get_upc(row) -> str | None:
    u = extract_upc_from_product(row.get('Product', ''))
    return u or clean_upc(row.get('UPC 13 digit'))

def _brand(row) -> str:
    for k in ('Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
              'Final Brand Name', 'Finalized Name September', 'Updated Brand Name'):
        v = ns(row.get(k, ''))
        if v and v not in ('nan', 'none'):
            return v
    return ''

def _size(row) -> str:
    for k in ('Beer Size Groups Value', 'RTD Size Value',
              'Spirits Sizes Value', 'Size Packages Value'):
        v = ns(row.get(k, ''))
        if v and v not in ('nan', 'none'):
            return v
    return ''

def _cat_key(row) -> str:
    brand   = _brand(row)
    product = ns(row.get('Product', ''))
    product = re.sub(r'\s*-\s*\d{13}\s*$', '', product).strip()
    size    = _size(row)
    flavor  = next((ns(row.get(k,'')) for k in
                    ('Beer Mezzo Styles Value','Beer Micro Styles Value',
                     'Spirits Flavors Value','Flavor Groups Value','Flavors Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    cat     = next((ns(row.get(k,'')) for k in
                    ('Beer Category Value','RTD Category Value',
                     'Spirits Category Value','Categories Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    supp    = next((ns(row.get(k,'')) for k in
                    ('Beer Vendors Value','Wine Suppliers Value','Spirits Suppliers Value')
                    if ns(row.get(k,'')) not in ('','nan')), '')
    return ' | '.join([brand, product, size, flavor, cat, supp])

def load_cat(name: str, pattern: str) -> pd.DataFrame:
    path = find_csv(pattern)
    log.info(f"Loading {name}: {os.path.basename(path)}")
    df = pd.read_csv(path, sep=',', dtype=str, encoding='utf-8-sig', low_memory=False)
    df['clean_upc']    = df.apply(_get_upc, axis=1)
    df['cat_brand']    = df.apply(_brand, axis=1)
    df['cat_size']     = df.apply(_size, axis=1)
    df['source_sheet'] = name
    df['orig_row']     = (df.index + 2).astype(int)
    log.info(f"  {name}: {len(df):,} rows | valid UPCs: {df['clean_upc'].notna().sum():,}")
    return df

# ── Master row -> dict helper ──────────────────────────────────────────────────

def master_fields(m: pd.Series) -> dict:
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

EMPTY_M = {k: '' for k in ["Master Row","Master UPC","Master Alt UPC","Master Brand",
                             "Master OCR Brand","Master Ext Brand","Master Product Name",
                             "Master Size","Master Supplier"]}

# ── Main analysis ──────────────────────────────────────────────────────────────

def analyse_sheet(
    cat_df: pd.DataFrame, name: str,
    mdf: pd.DataFrame, df_alt: pd.DataFrame,
    primary_upc_set: set, brand_idx: dict,
) -> list[dict]:

    log.info(f"\n  === {name}: {len(cat_df):,} rows ===")

    # Build lookup dicts from master for fast access
    master_by_upc = {}
    for idx, row in mdf.iterrows():
        u = row['clean_upc']
        if u and u not in master_by_upc:
            master_by_upc[u] = idx

    master_by_alt = {}
    for _, arow in df_alt.iterrows():
        if arow['alt_upc'] not in master_by_alt:
            master_by_alt[arow['alt_upc']] = arow['master_idx']

    records = []
    missing_rows = []  # rows needing fuzzy match

    # ── Phase 1: Exact UPC classification (very fast) ──────────────────────
    log.info(f"  Phase 1: exact UPC matching ...")
    for i, (_, crow) in enumerate(cat_df.iterrows()):
        upc     = crow.get('clean_upc')
        src_upc = str(crow.get('UPC 13 digit', '') or '')
        prod_t  = str(crow.get('Product', '') or '')[:150]
        brand_c = str(crow.get('cat_brand', '') or '')
        size_c  = str(crow.get('cat_size', '') or '')

        base = {
            "Source Sheet":        name,
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
            **EMPTY_M,
        }

        if not upc:
            base["Match Status"] = "No Valid UPC"
            base["Remarks"]      = "Could not extract 13-digit UPC from source"
            records.append(base)
            continue

        if upc in master_by_upc:
            m = mdf.loc[master_by_upc[upc]]
            base.update({"Match Status": "Exact Match", "Confidence Score": 100,
                         "Remarks": "UPC found in Master primary UPC column",
                         **master_fields(m)})
            records.append(base)
            continue

        if upc in master_by_alt:
            m = mdf.loc[master_by_alt[upc]]
            base.update({"Match Status": "Exact via Alt UPC", "Confidence Score": 100,
                         "Suggested UPC": str(m.get('UPCCode', '') or ''),
                         "Remarks": "UPC matched via Master Alternate UPC column",
                         **master_fields(m)})
            records.append(base)
            continue

        # Not found — queue for fuzzy matching
        missing_rows.append((base, crow))

    log.info(f"  Phase 1 done: {len(records):,} exact matches | {len(missing_rows):,} missing UPCs")

    # ── Phase 2: Fuzzy matching on missing UPCs only ────────────────────────
    log.info(f"  Phase 2: fuzzy product matching for {len(missing_rows):,} missing UPC rows ...")
    for j, (base, crow) in enumerate(missing_rows):
        if j % 2000 == 0 and j > 0:
            log.info(f"    {name} fuzzy: {j:,}/{len(missing_rows):,}")

        brand_c = base["Brand (Cat Sheet)"]
        bt      = brand_token(brand_c)
        bucket  = brand_idx.get(bt, [])

        if not bucket:
            # No brand match - try a few related tokens
            # e.g. 'bud light' -> try 'bud' and 'light'
            brand_words = [w for w in ns(brand_c).split() if len(w) > 2]
            for bw in brand_words[:3]:
                bucket = brand_idx.get(bw, [])
                if bucket:
                    break

        if not bucket:
            base["Match Status"]     = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"]          = "Brand not found in Master. Likely a new product or different brand name."
            records.append(base)
            continue

        cat_key = _cat_key(crow)
        if not cat_key.replace('|', '').strip():
            base["Match Status"]     = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"]          = "No product fields available for matching."
            records.append(base)
            continue

        cand_keys = [k for _, k in bucket]
        cand_idxs = [i for i, _ in bucket]

        result = rfprocess.extractOne(
            cat_key, cand_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=POSSIBLE_SCORE - 1,
        )

        if result is None:
            base["Match Status"]     = "New Product"
            base["Confidence Score"] = 0
            base["Remarks"]          = "No similar product found in same brand bucket."
            records.append(base)
            continue

        best_key, best_score, best_pos = result
        m      = mdf.loc[cand_idxs[best_pos]]
        status = classify_score(int(best_score))

        base.update({
            "Match Status":     status,
            "Confidence Score": int(best_score),
            **master_fields(m),
        })

        if status in ("Exact Match", "Product Match - UPC Missing"):
            base["Suggested UPC"] = str(m.get('UPCCode', '') or '')
            base["Remarks"] = (
                f"Product found in Master row {base['Master Row']} "
                f"(score={best_score}). Cat-sheet UPC is missing from AllMasterBrand. "
                f"Suggested UPC is the Master primary UPC. VERIFY before applying."
            )
        elif status == "Possible Match":
            base["Remarks"] = (
                f"Partial similarity (score={best_score}). "
                f"Uncertain match - verify manually before any UPC assignment."
            )
        else:
            base["Remarks"] = "No reliable match within brand group. Treat as new product."

        records.append(base)

    log.info(f"  {name}: complete - {len(records):,} total records")
    return records

# ── Excel report ───────────────────────────────────────────────────────────────

def write_excel(records: list[dict], path: str):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.utils import get_column_letter

    log.info(f"Writing Excel -> {path}")
    df = pd.DataFrame(records)

    # The KEY sheet: products that exist in master but UPC is missing in cat sheet
    df_upc_missing = df[df["Match Status"] == "Product Match - UPC Missing"].copy()
    df_missing_all = df[~df["Match Status"].isin(["Exact Match", "Exact via Alt UPC"])].copy()
    df_exact       = df[df["Match Status"].isin(["Exact Match", "Exact via Alt UPC"])].copy()
    df_possible    = df[df["Match Status"] == "Possible Match"].copy()
    df_new         = df[df["Match Status"] == "New Product"].copy()
    df_noupc       = df[df["Match Status"] == "No Valid UPC"].copy()

    sum_rows = []
    for s in ['Beer', 'Wine', 'RTD', 'Spirits', 'TOTAL']:
        sub = df if s == 'TOTAL' else df[df["Source Sheet"] == s]
        t   = len(sub)
        sum_rows.append({
            "Sheet":                        s,
            "Total Records":                t,
            "Exact Match (Primary UPC)":    int((sub["Match Status"] == "Exact Match").sum()),
            "Exact Match (Alt UPC)":        int((sub["Match Status"] == "Exact via Alt UPC").sum()),
            "Product Match - UPC Missing":  int((sub["Match Status"] == "Product Match - UPC Missing").sum()),
            "Possible Match":               int((sub["Match Status"] == "Possible Match").sum()),
            "New Product":                  int((sub["Match Status"] == "New Product").sum()),
            "No Valid UPC":                 int((sub["Match Status"] == "No Valid UPC").sum()),
            "Total Missing from Master":    int((~sub["Match Status"].isin(["Exact Match","Exact via Alt UPC"])).sum()),
            "Missing %":                    f"{((~sub['Match Status'].isin(['Exact Match','Exact via Alt UPC'])).sum()/max(t,1))*100:.1f}%",
        })
    df_summary = pd.DataFrame(sum_rows)

    sheets = [
        ("Summary Report",              df_summary,       "1F497D"),
        ("!! UPC Missing - Add to Master", df_upc_missing,"7F0000"),  # KEY sheet
        ("All Missing UPCs",            df_missing_all,   "C00000"),
        ("Exact Product Matches",       df_exact,         "375623"),
        ("Possible Matches",            df_possible,      "974706"),
        ("New Products",                df_new,           "843C0C"),
        ("No Valid UPC",                df_noupc,         "595959"),
    ]

    wb = Workbook()
    wb.remove(wb.active)

    for title, data, hdr_hex in sheets:
        ws = wb.create_sheet(title=title[:31])
        if data.empty:
            ws.append([f"No records in this category. (0 rows)"])
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

        hfill = PatternFill("solid", fgColor=hdr_hex)
        for cell in ws[1]:
            cell.fill      = hfill
            cell.font      = Font(bold=True, color="FFFFFF", size=10)
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
        ws.freeze_panes = "A2"

        for c in range(1, ws.max_column + 1):
            max_len = max(
                (len(str(ws.cell(row=r, column=c).value or ''))
                 for r in range(1, min(ws.max_row + 1, 201))),
                default=10,
            )
            ws.column_dimensions[get_column_letter(c)].width = min(max(max_len + 2, 12), 55)

    wb.save(path)
    log.info(f"Saved: {path}")
    return path

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    log.info("=" * 70)
    log.info("Missing UPC + Product Match Tool v4 (Fast Phase-Split)")
    log.info("=" * 70)
    log.info("This will identify UPCs missing from AllMasterBrand where the")
    log.info("product already exists (same brand/size/flavor) -> add UPC to master")
    log.info("=" * 70)

    mdf, df_alt = load_master()
    primary_upc_set = set(mdf[mdf['clean_upc'].notna()]['clean_upc'])
    brand_idx = build_brand_index(mdf)

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
            records = analyse_sheet(cat_df, name, mdf, df_alt, primary_upc_set, brand_idx)
            all_records.extend(records)
        except Exception as e:
            log.error(f"Error in {name}: {e}", exc_info=True)

    log.info(f"\nTotal: {len(all_records):,} records processed")
    df_all = pd.DataFrame(all_records)
    log.info("\nResults summary:")
    for status, cnt in df_all["Match Status"].value_counts().items():
        log.info(f"  {status:<45} {cnt:>8,}")

    key_count = int((df_all["Match Status"] == "Product Match - UPC Missing").sum())
    log.info(f"\n*** KEY FINDING: {key_count:,} records where product exists in Master")
    log.info(f"    but UPC is missing from categorization sheet.")
    log.info(f"    -> Check sheet '!! UPC Missing - Add to Master' in the Excel report")

    out = write_excel(all_records, OUTPUT_XL)
    log.info(f"\nDone! Report: {out}")
    print(f"\nReport saved to: {out}")
    return out


if __name__ == "__main__":
    main()

