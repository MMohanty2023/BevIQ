import pandas as pd

df_supp = pd.read_csv('$Supplier_202610291521.csv', sep='|', dtype=str)
print("Supplier sheet total rows:", len(df_supp))
supp_codes = set(df_supp['SupplierCode'].dropna().str.strip())
supp_names = set(df_supp['SupplierName'].dropna().str.strip().str.upper())

df_master = pd.read_csv('AIMasterBrandData.csv', sep='|', usecols=['SupplierCode', 'SupplierName', 'BrandName'], dtype=str)
master_supp_codes = set(df_master['SupplierCode'].dropna().str.strip())
master_supp_names = set(df_master['SupplierName'].dropna().str.strip().str.upper())

print("Supplier sheet unique SupplierCodes:", len(supp_codes))
print("AIMaster unique SupplierCodes:", len(master_supp_codes))

matched_codes = supp_codes.intersection(master_supp_codes)
missing_in_supp = master_supp_codes - supp_codes
supp_unused = supp_codes - master_supp_codes

print(f"SupplierCodes matched: {len(matched_codes):,} ({len(matched_codes)/len(master_supp_codes)*100:.1f}%)")
print(f"SupplierCodes in AIMaster but MISSING in Supplier sheet: {len(missing_in_supp):,}")
print(f"SupplierCodes in Supplier sheet but unused in AIMaster: {len(supp_unused):,}")
