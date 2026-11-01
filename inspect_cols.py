import pandas as pd
import glob

csvs = glob.glob('*.csv')
allbrand_file = [f for f in csvs if 'ALLBrand' in f][0]

# Check sample rows for UPC format
df = pd.read_csv(allbrand_file, sep='|', nrows=10, dtype=str, encoding='utf-8-sig')
df.columns = [c.strip("'") for c in df.columns]

print("UPCCode samples:")
print(df['UPCCode'].tolist())

print("\nAlternateUPCCode samples:")
print(df['AlternateUPCCode'].tolist())

print("\nProductName samples:")
print(df['ProductName'].tolist())

print("\nBrandName samples:")
print(df['BrandName'].tolist())

print("\nProductCategory samples:")
print(df['ProductCategory'].tolist())

print("\nSize samples:")
print(df['Size'].tolist())

# Check beer categorization UPC format
beer_file = [f for f in csvs if 'Beer' in f][0]
beer_df = pd.read_csv(beer_file, sep=',', nrows=10, dtype=str, encoding='utf-8-sig')
print("\n\n=== BEER UPC 13 digit samples ===")
print(beer_df['UPC 13 digit'].tolist())
print("\nBeer Product samples:")
print(beer_df['Product'].tolist()[:5])

# Check wine
wine_file = [f for f in csvs if 'Wine' in f][0]
wine_df = pd.read_csv(wine_file, sep=',', nrows=10, dtype=str, encoding='utf-8-sig')
print("\n\n=== WINE UPC 13 digit samples ===")
print(wine_df['UPC 13 digit'].tolist())

# Check spirits
spirits_file = [f for f in csvs if 'Spirits' in f][0]
spirits_df = pd.read_csv(spirits_file, sep=',', nrows=10, dtype=str, encoding='utf-8-sig')
print("\n\n=== SPIRITS UPC 13 digit samples ===")
print(spirits_df['UPC 13 digit'].tolist())

# Check RTD
rtd_file = [f for f in csvs if 'RTDs' in f][0]
rtd_df = pd.read_csv(rtd_file, sep=',', nrows=10, dtype=str, encoding='utf-8-sig')
print("\n\n=== RTD UPC 13 digit samples ===")
print(rtd_df['UPC 13 digit'].tolist())

