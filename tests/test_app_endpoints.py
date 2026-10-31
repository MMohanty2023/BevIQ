import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
import json

client = app.test_client()

def test_all_endpoints():
    print("Testing Flask Web Application Endpoints...")

    # 1. Test Index
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("[PASS] GET / -> HTTP 200 OK")

    # 2. Test Stats
    res = client.get('/api/stats')
    assert res.status_code == 200
    stats = res.get_json()
    assert stats['total_records'] == 702207, f"Expected 702207 total records, got {stats['total_records']}"
    print(f"[PASS] GET /api/stats -> HTTP 200 OK (Total records: {stats['total_records']:,})")

    # 3. Test DB Status
    res = client.get('/api/db-status')
    assert res.status_code == 200
    db_st = res.get_json()
    print(f"[PASS] GET /api/db-status -> HTTP 200 OK (MySQL Port: {db_st['mysql_port']}, DBeaver URL: {db_st['dbeaver_url']})")

    # 4. Test Chat API
    chat_payload = {"message": "Find UPC 0852955008021"}
    res = client.post('/api/chat', json=chat_payload)
    assert res.status_code == 200
    chat_resp = res.get_json()
    assert chat_resp['record_count'] > 0
    token = chat_resp['download_token']
    print(f"[PASS] POST /api/chat -> HTTP 200 OK (Matches: {chat_resp['record_count']}, Token: {token})")

    # 5. Test Export CSV
    if token:
        res = client.get(f'/api/export-csv/{token}')
        assert res.status_code == 200
        assert 'text/csv' in res.content_type
        print(f"[PASS] GET /api/export-csv/{token} -> HTTP 200 OK (Content-Type: {res.content_type}, Size: {len(res.data)} bytes)")

    # 6. Test Compare API (Master vs Beer)
    comp_payload = {"type": "master_vs_beer", "limit": 100}
    res = client.post('/api/compare', json=comp_payload)
    assert res.status_code == 200
    comp_resp = res.get_json()
    assert len(comp_resp['records']) > 0
    print(f"[PASS] POST /api/compare (master_vs_beer) -> HTTP 200 OK (Records: {len(comp_resp['records'])})")

    # 7. Test Compare API (Beer vs RTD)
    comp_payload = {"type": "beer_vs_rtd", "limit": 100}
    res = client.post('/api/compare', json=comp_payload)
    assert res.status_code == 200
    comp_resp = res.get_json()
    assert len(comp_resp['records']) > 0
    print(f"[PASS] POST /api/compare (beer_vs_rtd) -> HTTP 200 OK (Records: {len(comp_resp['records'])})")

    # 8. Test Compare API (AllBrand vs Supplier)
    comp_payload = {"type": "allbrand_vs_supplier", "limit": 100}
    res = client.post('/api/compare', json=comp_payload)
    assert res.status_code == 200
    comp_resp = res.get_json()
    assert len(comp_resp['records']) > 0
    print(f"[PASS] POST /api/compare (allbrand_vs_supplier) -> HTTP 200 OK (Records: {len(comp_resp['records'])})")

    print("\nALL FLASK ENDPOINT INTEGRATION TESTS PASSED SUCCESSFULLY! 100% SUCCESS.")

if __name__ == '__main__':
    test_all_endpoints()
