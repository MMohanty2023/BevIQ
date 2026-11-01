import sqlite3
import pandas as pd

conn = sqlite3.connect('db_storage/beverage_data.sqlite3')

cats = [
    ('Beer', 'cat_beer', 'Beer_Brands_Value', 'Product', 'Categorization 2026 - Beer.csv'),
    ('Wine', 'cat_wine', 'Brands_Value', 'Product', 'Categorization 2026 - Wine.csv'),
    ('RTD', 'cat_rtd', 'Brands_Value', 'Product', 'Categorization 2026 - RTDs.csv'),
    ('Spirits', 'cat_spirits', 'Spirits_Brands_Value', 'Product', 'Categorization 2026 - Spirits.csv')
]

summary = []
all_missing = []

for name, tbl, brand_col, prod_col, fname in cats:
    total_upcs = conn.execute(f"SELECT COUNT(DISTINCT clean_upc) FROM `{tbl}` WHERE clean_upc != ''").fetchone()[0]
    
    matched_sql = f"""
    SELECT COUNT(DISTINCT c.clean_upc) 
    FROM `{tbl}` c 
    JOIN `ai_master` m ON c.clean_upc = m.clean_upc 
    WHERE c.clean_upc != ''
    """
    matched = conn.execute(matched_sql).fetchone()[0]
    missing = total_upcs - matched
    pct_missing = (missing / total_upcs * 100) if total_upcs else 0
    
    summary.append({
        'Category': name,
        'Total_UPCs': total_upcs,
        'Matched_In_Master': matched,
        'Missing_From_Master': missing,
        'Pct_Missing': f"{pct_missing:.1f}%"
    })
    
    missing_sql = f"""
    SELECT 
        '{name}' AS category,
        c.clean_upc AS upc,
        COALESCE(c.{brand_col}, 'N/A') AS brand,
        COALESCE(c.{prod_col}, 'N/A') AS product,
        c.source_file AS source_file,
        c.original_row AS original_row,
        'Missing in Master' AS status
    FROM `{tbl}` c
    LEFT JOIN `ai_master` m ON c.clean_upc = m.clean_upc
    WHERE m.clean_upc IS NULL AND c.clean_upc != ''
    LIMIT 250
    """
    df_missing = pd.read_sql(missing_sql, conn)
    all_missing.append(df_missing)

print(pd.DataFrame(summary).to_string(index=False))
total_combined_missing = sum(s['Missing_From_Master'] for s in summary)
print(f"\nTotal Combined Missing UPCs across all 4 categories: {total_combined_missing:,}")

