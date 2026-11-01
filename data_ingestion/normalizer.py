import re
import pandas as pd

def normalize_upc(raw_val, product_str=None):
    """
    Standardize beverage UPCs to 13-digit strings with leading zeros preserved.
    Recovers UPC from product description string if raw_val suffered Excel truncation.
    """
    # 1. Check if product string has trailing 11-14 digit UPC
    if product_str and isinstance(product_str, str):
        m = re.search(r'-\s*(\d{11,14})\s*$', product_str.strip())
        if m:
            digits = m.group(1)
            return digits.zfill(13) if len(digits) in [11, 12] else digits

    if pd.isna(raw_val):
        return ""

    s = str(raw_val).strip()
    if not s or s.lower() in ['nan', 'null', 'none']:
        return ""

    # 2. Remove 'UPC=' or similar prefixes
    s = s.replace('UPC=', '').replace('upc=', '').strip()

    # 3. Handle scientific notation (e.g. 6.19947E+11)
    if 'e+' in s.lower() or 'e-' in s.lower():
        try:
            s = f"{int(float(s))}"
        except Exception:
            pass

    # 4. Remove trailing decimals (e.g. 18200967151.0)
    if '.' in s:
        parts = s.split('.')
        if len(parts) == 2 and (parts[1] == '0' or parts[1] == ''):
            s = parts[0]

    # 5. Extract only digits
    digits = re.sub(r'\D', '', s)
    if not digits:
        return ""

    # Standard 13-digit UPC formatting with leading zeros
    if len(digits) in [11, 12]:
        return digits.zfill(13)
    return digits

def clean_text(val):
    """Clean string values, handling nulls, multiple spaces, and special quotes."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in ['nan', 'null', 'none', '#n/a', 'na']:
        return ""
    # normalize internal whitespace
    s = re.sub(r'\s+', ' ', s)
    return s

