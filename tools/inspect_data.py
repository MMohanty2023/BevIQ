import os
import glob
import csv
import json
import pandas as pd

def inspect_csv(file_path):
    print(f"\n==========================================")
    print(f"Inspecting: {file_path}")
    print(f"File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
    
    # Detect encoding
    encoding = 'utf-8'
    sample_bytes = min(100000, os.path.getsize(file_path))
    for enc in ['utf-8', 'latin-1', 'cp1252', 'utf-8-sig']:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(sample_bytes)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
            
    print(f"Encoding detected: {encoding}")
    
    # Read first few lines to check delimiter
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        first_line = f.readline()
        second_line = f.readline()
        
    delimiter = ','
    if '\t' in first_line and first_line.count('\t') > first_line.count(','):
        delimiter = '\t'
    elif ';' in first_line and first_line.count(';') > first_line.count(','):
        delimiter = ';'
    elif '|' in first_line and first_line.count('|') > first_line.count(','):
        delimiter = '|'
    print(f"Delimiter: {repr(delimiter)}")

    # Read with pandas (first 100 rows for quick inspection, dtype=str for UPCs)
    df_sample = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, nrows=100, dtype=str)
    print(f"Number of columns: {len(df_sample.columns)}")
    print(f"Columns: {list(df_sample.columns)}")
    
    # Count rows by streaming
    row_count = 0
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        reader = csv.reader(f, delimiter=delimiter)
        try:
            header = next(reader)
            for _ in reader:
                row_count += 1
        except Exception as e:
            print(f"Error streaming rows: {e}")
            
    print(f"Total row count (excluding header): {row_count}")
    
    # Sample row dictionary
    if not df_sample.empty:
        print("\nFirst row sample:")
        sample_dict = df_sample.iloc[0].dropna().to_dict()
        for k, v in list(sample_dict.items())[:10]:
            print(f"  {k}: {repr(v)}")
            
    return {
        'file_name': os.path.basename(file_path),
        'file_size_mb': round(os.path.getsize(file_path) / (1024*1024), 2),
        'encoding': encoding,
        'delimiter': delimiter,
        'columns': list(df_sample.columns),
        'total_rows': row_count
    }

if __name__ == '__main__':
    csv_files = sorted(glob.glob('*.csv'))
    results = []
    for f in csv_files:
        info = inspect_csv(f)
        results.append(info)
        
    with open('inspection_summary.json', 'w', encoding='utf-8') as out:
        json.dump(results, out, indent=2)
    print("\n\nAll files inspected successfully. Summary saved to inspection_summary.json")
