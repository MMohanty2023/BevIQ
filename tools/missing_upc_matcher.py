"""
Missing UPC Identification + Product Row Combination Matching
=============================================================
Compares All Master Brand (AllBrand) with Beer, Wine, RTD, Spirits sheets.
For every missing UPC, attempts multi-field product matching to classify as:
  1. Exact Match
  2. Product Match - UPC Missing
  3. Possible Match
  4. New Product

Outputs a multi-sheet Excel report.
"""

import os
import sys
import re
import glob
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from rapidfuzz import fuzz

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("missing_upc_matcher")

# ── Constants ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)

REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_XL  = os.path.join(REPORT_DIR, f"Missing_UPC_Analysis_{TIMESTAMP}.xlsx")

# Match thresholds
EXACT_MATCH_THRESHOLD   = 95   # fuzzy score ≥ 95 on combined key
PRODUCT_MATCH_THRESHOLD = 80   # fuzzy score 80-94
POSSIBLE_MATCH_THRESHOLD = 60  # fuzzy score 60-79


# ══════════════════════════════════════════════════════════════════════════════
# 1.  UPC normalisation helpers
# ══════════════════════════════════════════════════════════════════════════════

def clean_upc(val) -> str | None:
    """
    Convert any representation of a UPC to a zero-padded 13-digit string.
    Handles:
      - scientific notation  (6.19947E+11 → 619947000031 → 0619947000031)
      - bare integers         (85000017731 → 0085000017731)
      - 'UPC=...' prefix
      - already correct 13-digit strings
    Returns None for empty / invalid values.
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip().strip("'\"")
    if not s or s in ('nan', 'NaN', '{}', 'None'):
        return None

    # Strip UPC= prefix (master data)
    if s.upper().startswith('UPC='):
        s = s[4:]

    # Expand scientific notation
    if 'E+' in s.upper() or 'e+' in s:
        try:
            s = str(int(float(s)))
        except ValueError:
            return None

    # Keep only digits
    s = re.sub(r'\D', '', s)
    if not s:
        return None

    # Pad to 13 digits
    if len(s) < 13:
        s = s.zfill(13)
    elif len(s) > 13:
        # Trim leading zeros if over-long
        s = s[-13:]

    # Sanity check: must be 13 digits
    if len(s) != 13:
        return None
    return s


def extract_upc_from_product_text(text) -> str | None:
    """
    Pull the 13-digit UPC embedded at the end of cat-sheet Product strings.
    Pattern: '... - 0619947000031'
    """
    if not isinstance(text, str):
        return None
    m = re.search(r'-\s*(\d{13})\s*$', text)
    if m:
        return m.group(1)
    return None


def parse_alternate_upc_set(val) -> set:
    """
    Parse AllBrand AlternateUPCCode field which looks like:
      {0033072815291,0033072815001,0633072815001}
    Returns a set of clean 13-digit strings.
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return set()
    s = str(val).strip().strip('{}')
    if not s or s in ('nan', 'NaN'):
        return set()
    parts = re.split(r'[,;\s]+', s)
    result = set()
    for p in parts:
        cleaned = clean_upc(p)
        if cleaned:
            result.add(cleaned)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Load CSVs
# ══════════════════════════════════════════════════════════════════════════════

def find_csv(pattern: str) -> str:
    csvs = glob.glob(os.path.join(BASE_DIR, '*.csv'))
    matches = [f for f in csvs if pattern.lower() in os.path.basename(f).lower()]
    if not matches:
        raise FileNotFoundError(f"No CSV matching pattern '{pattern}' in {BASE_DIR}")
    return matches[0]


def load_allbrand() -> pd.DataFrame:
    path = find_csv('ALLBrand')
    log.info(f"Loading AllBrand: {os.path.basename(path)}")
    df = pd.read_csv(path, sep='|', dtype=str, encoding='utf-8-sig', low_memory=False)
    df.columns = [c.strip("' ") for c in df.columns]

    # Normalise UPCs
    df['clean_upc']     = df['UPCCode'].apply(clean_upc)
    df['clean_alt_upc'] = df['AlternateUPCCode'].apply(lambda v: parse_alternate_upc_set(v))

    # Build ALL UPCs per row (primary + alternates)
    def all_upcs(row):
        s = set()
        if row['clean_upc']:
            s.add(row['clean_upc'])
        s.update(row['clean_alt_upc'])
        return s

    df['all_upcs'] = df.apply(all_upcs, axis=1)
    df['orig_row'] = df.index + 2  # 1-based + header row
    log.info(f"  AllBrand rows: {len(df):,}")
    return df


def load_cat_sheet(sheet_name: str, filename_pattern: str) -> pd.DataFrame:
    path = find_csv(filename_pattern)
    log.info(f"Loading {sheet_name}: {os.path.basename(path)}")
    df = pd.read_csv(path, sep=',', dtype=str, encoding='utf-8-sig', low_memory=False)

    # Extract UPC — prefer Product text, fallback to column value
    def get_upc(row):
        # Try embedding in Product text first (most reliable for cat sheets)
        upc = extract_upc_from_product_text(row.get('Product', ''))
        if upc:
            return upc
        # Fallback to UPC column
        return clean_upc(row.get('UPC 13 digit', None))

    df['clean_upc'] = df.apply(get_upc, axis=1)
    df['source_sheet'] = sheet_name
    df['orig_row'] = df.index + 2
    log.info(f"  {sheet_name} rows: {len(df):,}  |  valid UPCs: {df['clean_upc'].notna().sum():,}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Build Master UPC lookup structures
# ══════════════════════════════════════════════════════════════════════════════

def build_master_upc_index(master_df: pd.DataFrame):
    """
    Returns:
      upc_to_rows  : dict[str, list[int]] — clean_upc → master row indices
      alt_upc_map  : dict[str, list[int]] — alt upc   → master row indices
    """
    upc_to_rows = {}
    alt_upc_map = {}

    for idx, row in master_df.iterrows():
        primary = row['clean_upc']
        if primary:
            upc_to_rows.setdefault(primary, []).append(idx)
        for alt in row['clean_alt_upc']:
            alt_upc_map.setdefault(alt, []).append(idx)

    log.info(f"  Master primary UPC index: {len(upc_to_rows):,} unique UPCs")
    log.info(f"  Master alternate UPC index: {len(alt_upc_map):,} unique alt UPCs")
    return upc_to_rows, alt_upc_map


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Multi-field product matching
# ══════════════════════════════════════════════════════════════════════════════

def build_product_key(brand, product_name, size, flavor, category, supplier) -> str:
    """Combine fields into a normalised comparison key."""
    parts = [brand, product_name, size, flavor, category, supplier]
    cleaned = [str(p).strip().lower() if pd.notna(p) and str(p).strip() not in ('nan', '') else ''
               for p in parts]
    return ' | '.join(cleaned)


def build_master_product_keys(master_df: pd.DataFrame) -> pd.Series:
    return master_df.apply(
        lambda r: build_product_key(
            r.get('BrandName', ''),
            r.get('ProductName', ''),
            r.get('Size', ''),
            r.get('Flavor', ''),
            r.get('ProductCategory', ''),
            r.get('SupplierName', ''),
        ),
        axis=1,
    )


def cat_row_product_key(cat_row: pd.Series, sheet_name: str) -> str:
    """
    Extract brand, size, etc. from cat-sheet row.
    Column names differ per sheet — try all known variants.
    """
    def pick(*keys):
        for k in keys:
            v = cat_row.get(k, None)
            if v and str(v).strip().lower() not in ('nan', '', 'none'):
                return str(v).strip()
        return ''

    brand = pick('Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
                 'Wine Brands Value', 'RTD Brands Value',
                 'Final Brand Name', 'Finalized Name September', 'Updated Brand Name')
    size  = pick('Beer Size Groups Value', 'RTD Size Value', 'Spirits Sizes Value',
                 'Size Packages Value', 'Size')
    flavor = pick('Beer Mezzo Styles Value', 'Beer Micro Styles Value',
                  'Spirits Flavors Value', 'Spirits Flavor Scents Value',
                  'Flavor Groups Value', 'Flavors Value')
    category = pick('Beer Category Value', 'RTD Category Value',
                    'Spirits Category Value', 'Categories Value')
    supplier = pick('Beer Vendors Value', 'Wine Suppliers Value',
                    'Spirits Suppliers Value', 'RTD Suppliers Value')
    product = pick('Product', 'ProductName')

    # Clean product text — remove trailing UPC
    if product:
        product = re.sub(r'\s*-\s*\d{13}\s*$', '', product).strip()

    return build_product_key(brand, product, size, flavor, category, supplier)


def fuzzy_match_to_master(
    cat_key: str,
    master_keys: pd.Series,
    master_df: pd.DataFrame,
    top_n: int = 3,
):
    """
    Find top-N master rows by fuzzy token-sort ratio against cat_key.
    Returns list of (master_idx, score, master_row) sorted by score desc.
    """
    if not cat_key.replace('|', '').strip():
        return []

    scores = master_keys.apply(lambda mk: fuzz.token_sort_ratio(cat_key, mk))
    top_idx = scores.nlargest(top_n).index.tolist()

    results = []
    for idx in top_idx:
        score = int(scores[idx])
        if score >= POSSIBLE_MATCH_THRESHOLD:
            results.append((idx, score, master_df.loc[idx]))
    return results


def classify_match(score: int) -> str:
    if score >= EXACT_MATCH_THRESHOLD:
        return "Exact Match"
    elif score >= PRODUCT_MATCH_THRESHOLD:
        return "Product Match - UPC Missing"
    elif score >= POSSIBLE_MATCH_THRESHOLD:
        return "Possible Match"
    else:
        return "New Product"


# ══════════════════════════════════════════════════════════════════════════════
# 5.  Main analysis loop
# ══════════════════════════════════════════════════════════════════════════════

def analyse_sheet(
    cat_df: pd.DataFrame,
    sheet_name: str,
    upc_to_rows: dict,
    alt_upc_map: dict,
    master_df: pd.DataFrame,
    master_keys: pd.Series,
) -> list[dict]:

    records = []
    total = len(cat_df)
    log.info(f"  Analysing {sheet_name} ({total:,} rows)...")

    for i, (_, cat_row) in enumerate(cat_df.iterrows()):
        if i % 10000 == 0 and i > 0:
            log.info(f"    {sheet_name}: processed {i:,}/{total:,}")

        upc = cat_row.get('clean_upc', None)
        product_text = str(cat_row.get('Product', '')).strip()
        brand_col = next(
            (str(cat_row.get(c, '')) for c in
             ['Beer Brands Value', 'Brands Value', 'Spirits Brands Value',
              'Final Brand Name', 'Finalized Name September']
             if pd.notna(cat_row.get(c, None)) and str(cat_row.get(c, '')).strip() not in ('nan', '')),
            ''
        )
        size_col = next(
            (str(cat_row.get(c, '')) for c in
             ['Beer Size Groups Value', 'RTD Size Value', 'Spirits Sizes Value', 'Size Packages Value']
             if pd.notna(cat_row.get(c, None)) and str(cat_row.get(c, '')).strip() not in ('nan', '')),
            ''
        )

        base_rec = {
            "Source Sheet":         sheet_name,
            "Source Row":           cat_row.get('orig_row', ''),
            "Source UPC":           cat_row.get('UPC 13 digit', ''),
            "Extracted UPC":        upc or '',
            "Product Text":         product_text[:200],
            "Brand (Cat Sheet)":    brand_col,
            "Size (Cat Sheet)":     size_col,
            # Master fields filled in below
            "Master Row":           '',
            "Master UPC":           '',
            "Master Alt UPC":       '',
            "Master Brand":         '',
            "Master Product Name":  '',
            "Master Size":          '',
            "Master Supplier":      '',
            "Master OCR Brand":     '',
            "Master Ext Brand":     '',
            "Match Status":         '',
            "Confidence Score":     '',
            "Suggested UPC":        '',
            "Remarks":              '',
        }

        if not upc:
            base_rec["Match Status"] = "No Valid UPC"
            base_rec["Remarks"]      = "Could not extract 13-digit UPC from source"
            records.append(base_rec)
            continue

        # ── Check primary UPC in master ──────────────────────────────────────
        if upc in upc_to_rows:
            master_idxs = upc_to_rows[upc]
            m = master_df.loc[master_idxs[0]]
            base_rec["Match Status"]       = "Exact Match"
            base_rec["Confidence Score"]   = 100
            base_rec["Master Row"]         = int(m.get('orig_row', ''))
            base_rec["Master UPC"]         = m.get('UPCCode', '')
            base_rec["Master Brand"]       = m.get('BrandName', '')
            base_rec["Master Product Name"]= m.get('ProductName', '')
            base_rec["Master Size"]        = m.get('Size', '')
            base_rec["Master Supplier"]    = m.get('SupplierName', '')
            base_rec["Master OCR Brand"]   = m.get('OCRBrandName', '')
            base_rec["Master Ext Brand"]   = m.get('ExtendedBrandName', '')
            base_rec["Remarks"]            = "UPC found in Master primary UPC column"
            records.append(base_rec)
            continue

        # ── Check alternate UPC in master ─────────────────────────────────────
        if upc in alt_upc_map:
            master_idxs = alt_upc_map[upc]
            m = master_df.loc[master_idxs[0]]
            base_rec["Match Status"]       = "Exact Match"
            base_rec["Confidence Score"]   = 100
            base_rec["Master Row"]         = int(m.get('orig_row', ''))
            base_rec["Master UPC"]         = m.get('UPCCode', '')
            base_rec["Master Alt UPC"]     = m.get('AlternateUPCCode', '')
            base_rec["Master Brand"]       = m.get('BrandName', '')
            base_rec["Master Product Name"]= m.get('ProductName', '')
            base_rec["Master Size"]        = m.get('Size', '')
            base_rec["Master Supplier"]    = m.get('SupplierName', '')
            base_rec["Master OCR Brand"]   = m.get('OCRBrandName', '')
            base_rec["Master Ext Brand"]   = m.get('ExtendedBrandName', '')
            base_rec["Suggested UPC"]      = m.get('UPCCode', '')
            base_rec["Remarks"]            = "UPC matched via Master Alternate UPC"
            records.append(base_rec)
            continue

        # ── UPC is MISSING from master — attempt product matching ─────────────
        cat_key = cat_row_product_key(cat_row, sheet_name)
        matches = fuzzy_match_to_master(cat_key, master_keys, master_df, top_n=3)

        if not matches:
            base_rec["Match Status"] = "New Product"
            base_rec["Confidence Score"] = 0
            base_rec["Remarks"] = "No match found in Master; likely a new product"
            records.append(base_rec)
            continue

        best_idx, best_score, best_m = matches[0]
        status = classify_match(best_score)

        base_rec["Match Status"]        = status
        base_rec["Confidence Score"]    = best_score
        base_rec["Master Row"]          = int(best_m.get('orig_row', ''))
        base_rec["Master UPC"]          = best_m.get('UPCCode', '')
        base_rec["Master Alt UPC"]      = best_m.get('AlternateUPCCode', '')
        base_rec["Master Brand"]        = best_m.get('BrandName', '')
        base_rec["Master Product Name"] = best_m.get('ProductName', '')
        base_rec["Master Size"]         = best_m.get('Size', '')
        base_rec["Master Supplier"]     = best_m.get('SupplierName', '')
        base_rec["Master OCR Brand"]    = best_m.get('OCRBrandName', '')
        base_rec["Master Ext Brand"]    = best_m.get('ExtendedBrandName', '')

        if status == "Product Match - UPC Missing":
            base_rec["Suggested UPC"] = best_m.get('UPCCode', '')
            base_rec["Remarks"] = (
                f"Product found in Master (row {base_rec['Master Row']}) but UPC is missing "
                f"in cat sheet. Suggested UPC is from Master. Score={best_score}. "
                f"MANUAL VERIFICATION REQUIRED."
            )
        elif status == "Exact Match":
            base_rec["Suggested UPC"] = best_m.get('UPCCode', '')
            base_rec["Remarks"] = f"High-confidence product match (score={best_score}). Verify before applying."
        elif status == "Possible Match":
            base_rec["Suggested UPC"] = ''
            base_rec["Remarks"] = (
                f"Partial product similarity (score={best_score}). Uncertain match — "
                f"manual verification required before any UPC assignment."
            )
        else:
            base_rec["Suggested UPC"] = ''
            base_rec["Remarks"] = "No reliable match found; treat as New Product."

        records.append(base_rec)

    return records


# ══════════════════════════════════════════════════════════════════════════════
# 6.  Excel report generation
# ══════════════════════════════════════════════════════════════════════════════

def _style_sheet(ws, header_color="366092"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill("solid", fgColor=header_color)
    header_font = Font(bold=True, color="FFFFFF", size=10)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )

    # Style header row
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        cell.border = thin_border

    # Auto-width columns
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
            for cell in row:
                try:
                    max_len = max(max_len, len(str(cell.value or '')))
                except Exception:
                    pass
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 45)

    # Freeze header row
    ws.freeze_panes = "A2"


def _status_fill_color(status: str) -> str:
    COLOR_MAP = {
        "Exact Match":                  "C6EFCE",  # green
        "Product Match - UPC Missing":  "FFEB9C",  # yellow
        "Possible Match":               "FFCC99",  # orange
        "New Product":                  "FFC7CE",  # red-pink
        "No Valid UPC":                 "D9D9D9",  # grey
    }
    return COLOR_MAP.get(status, "FFFFFF")


def write_excel_report(all_records: list[dict], output_path: str):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.utils import get_column_letter

    log.info(f"Writing Excel report → {output_path}")
    df_all = pd.DataFrame(all_records)

    # ── Partition into category DataFrames ───────────────────────────────────
    missing_mask  = ~df_all["Match Status"].isin(["Exact Match"])
    df_missing    = df_all[missing_mask].copy()

    df_exact      = df_all[df_all["Match Status"] == "Exact Match"].copy()
    df_prod_match = df_all[df_all["Match Status"] == "Product Match - UPC Missing"].copy()
    df_possible   = df_all[df_all["Match Status"] == "Possible Match"].copy()
    df_new        = df_all[df_all["Match Status"] == "New Product"].copy()

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_rows = []
    for sheet in ['Beer', 'Wine', 'RTD', 'Spirits', 'ALL']:
        sub = df_all if sheet == 'ALL' else df_all[df_all["Source Sheet"] == sheet]
        summary_rows.append({
            "Sheet": sheet,
            "Total Records":             len(sub),
            "Exact Matches":             (sub["Match Status"] == "Exact Match").sum(),
            "Product Match-UPC Missing": (sub["Match Status"] == "Product Match - UPC Missing").sum(),
            "Possible Matches":          (sub["Match Status"] == "Possible Match").sum(),
            "New Products":              (sub["Match Status"] == "New Product").sum(),
            "No Valid UPC":              (sub["Match Status"] == "No Valid UPC").sum(),
            "Missing UPC %":             f"{((sub['Match Status'] != 'Exact Match').sum() / max(len(sub), 1) * 100):.1f}%",
        })
    df_summary = pd.DataFrame(summary_rows)

    wb = Workbook()
    wb.remove(wb.active)   # remove default empty sheet

    sheets = [
        ("Summary Report",              df_summary,    "1F497D"),
        ("Missing UPCs",                df_missing,    "C00000"),
        ("Exact Product Matches",        df_exact,      "375623"),
        ("Product Match-UPC Missing",   df_prod_match, "7F6000"),
        ("Possible Matches",            df_possible,   "974706"),
        ("New Products",                df_new,        "843C0C"),
    ]

    for sheet_name, df_sheet, hdr_color in sheets:
        ws = wb.create_sheet(title=sheet_name[:31])

        if df_sheet.empty:
            ws.append(["No records in this category."])
            continue

        # Write header + rows
        rows = dataframe_to_rows(df_sheet, index=False, header=True)
        for r_idx, row in enumerate(rows, start=1):
            ws.append(row)

        # Colour data rows by status
        if "Match Status" in df_sheet.columns:
            status_col_idx = list(df_sheet.columns).index("Match Status") + 1
            for r_idx in range(2, ws.max_row + 1):
                status_cell = ws.cell(row=r_idx, column=status_col_idx)
                fill_color = _status_fill_color(str(status_cell.value or ''))
                fill = PatternFill("solid", fgColor=fill_color)
                for c_idx in range(1, ws.max_column + 1):
                    ws.cell(row=r_idx, column=c_idx).fill = fill

        _style_sheet(ws, header_color=hdr_color)

    wb.save(output_path)
    log.info(f"Report saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info("Missing UPC Identification + Product Row Combination Matching")
    log.info("=" * 70)

    # ── Load master data ──────────────────────────────────────────────────────
    master_df = load_allbrand()
    upc_to_rows, alt_upc_map = build_master_upc_index(master_df)
    log.info("Building master product keys for fuzzy matching...")
    master_keys = build_master_product_keys(master_df)
    log.info("  Master product keys built.")

    # ── Load cat sheets ───────────────────────────────────────────────────────
    cat_sheets = [
        ("Beer",    "Beer"),
        ("Wine",    "Wine"),
        ("RTD",     "RTDs"),
        ("Spirits", "Spirits"),
    ]

    all_records = []
    for sheet_name, pattern in cat_sheets:
        try:
            cat_df = load_cat_sheet(sheet_name, pattern)
            records = analyse_sheet(
                cat_df, sheet_name,
                upc_to_rows, alt_upc_map,
                master_df, master_keys,
            )
            log.info(f"  {sheet_name}: {len(records):,} records processed")
            all_records.extend(records)
        except Exception as e:
            log.error(f"  ERROR processing {sheet_name}: {e}")

    log.info(f"\nTotal records analysed: {len(all_records):,}")

    # ── Quick summary to console ──────────────────────────────────────────────
    df_all = pd.DataFrame(all_records)
    for status, count in df_all["Match Status"].value_counts().items():
        log.info(f"  {status:35s}: {count:,}")

    # ── Write report ──────────────────────────────────────────────────────────
    write_excel_report(all_records, OUTPUT_XL)
    log.info(f"\nDone!  Report → {OUTPUT_XL}")
    return OUTPUT_XL


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()

