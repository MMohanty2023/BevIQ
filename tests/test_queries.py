import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding='utf-8')
from engines.rag_orchestrator import rag_orchestrator
import json

def main():
    test_questions = [
        "Find all UPCs available in Master but missing in Beer.",
        "Show duplicate UPCs across all files.",
        "Compare All Brand Sheet with Supplier Sheet.",
        "Find a product using its UPC 0852955008021",
        "Compare Beer and RTD categorization.",
        "Count total products in each category",
        "Show all products belonging to brand Michelob Ultra"
    ]

    print("=" * 70)
    print("TESTING NATURAL LANGUAGE QUERIES IN BEVERAGE DATA ASSISTANT")
    print("=" * 70)

    for q in test_questions:
        print(f"\n>>> USER QUESTION: \"{q}\"")
        res = rag_orchestrator.route_and_execute(q)
        print("--- ASSISTANT ANSWER ---")
        print(res['answer'])
        print(f"--- SOURCES: {res['source_files']} | RECORDS RETRIEVED: {res['record_count']} | TOKEN: {res['download_token']} ---")
        if res['records']:
            print("SAMPLE FIRST RECORD:", json.dumps(res['records'][0], default=str))
        print("-" * 70)


if __name__ == '__main__':
    main()
