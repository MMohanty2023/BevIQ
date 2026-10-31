import json

with open('dataset_full_profile.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"{'File Name':<35} | {'Rows':<9} | {'Cols':<5} | {'Size MB':<8} | {'Valid UPCs':<11} | {'Unique UPCs':<11} | {'Duplicates'}")
print("-" * 105)
for d in data:
    upc_st = d['upc_stats']
    print(f"{d['file_name']:<35} | {d['total_rows']:<9} | {d['total_columns']:<5} | {d['file_size_mb']:<8} | {upc_st['total_valid_upcs']:<11} | {upc_st['unique_upcs']:<11} | {upc_st['duplicate_upc_records']}")
