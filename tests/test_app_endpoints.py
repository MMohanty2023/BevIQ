import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
import json
import app as app_module

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


def test_upc_audit_returns_stable_csv_export_without_writing(monkeypatch, tmp_path):
    expected = {
        'category': 'BEER',
        'status': 'Product Match - UPC Missing',
        'current_upc': '',
        'suggested_upc': '0012345678905',
        'alternate_upc': '0098765432100',
        'source_product': 'Harbor Light Lager Lemon',
        'master_product': 'Harbor Light Lager Lemon',
        'confidence': 95,
    }
    monkeypatch.setattr(app_module, 'upc_match_engine', type('FakeEngine', (), {'audit': lambda self, category, limit: [expected]})())
    monkeypatch.setattr(app_module, 'REPORTS_DIR', tmp_path)

    res = client.post('/api/upc-audit', json={'category': 'cat_beer', 'limit': 10})

    assert res.status_code == 200
    payload = res.get_json()
    assert payload['record_count'] == 1
    assert payload['download_token']
    assert payload['read_only'] is True
    assert payload['columns'] == list(expected.keys())

    csv_res = client.get(f"/api/export-csv/{payload['download_token']}")
    assert csv_res.status_code == 200
    assert 'suggested_upc' in csv_res.data.decode('utf-8')
    assert '0012345678905' in csv_res.data.decode('utf-8')


def test_index_exposes_upc_first_review_action():
    html = client.get('/').data.decode('utf-8')
    assert 'Product Match' in html
    assert 'Alternate UPC' in html
    assert 'no master product or upc is changed automatically' in html.lower()
    assert 'id="studio-status-filter"' in html
    assert 'onchange="filterStudioTable(false)"' in html
    assert 'Exact Match' in html


def test_comparison_uses_human_category_label():
    response = client.post('/api/compare', json={'type': 'master_vs_beer', 'limit': 1})
    assert response.status_code == 200
    assert response.get_json()['comparison_type'] == 'Master vs Beer'


def test_comparison_search_is_sent_to_server_query(monkeypatch):
    seen = {}

    class FakeComparison:
        def compare_all_missing_in_master(self, limit_per_category, search=None):
            seen['limit'] = limit_per_category
            seen['search'] = search
            return {'comparison_type': 'Missing UPC Audit', 'summary': {}, 'records': []}

    monkeypatch.setattr(app_module, 'comparison_engine', FakeComparison())
    response = client.post('/api/compare', json={'type': 'all_missing', 'limit': 250, 'search': 'barefoot'})

    assert response.status_code == 200
    assert seen == {'limit': 250, 'search': 'barefoot'}


def test_upc_audit_full_review_passes_unbounded_limit(monkeypatch, tmp_path):
    seen = {}

    class FakeEngine:
        def audit(self, category, limit):
            seen['category'] = category
            seen['limit'] = limit
            return []

    monkeypatch.setattr(app_module, 'upc_match_engine', FakeEngine())
    monkeypatch.setattr(app_module, 'REPORTS_DIR', tmp_path)

    res = client.post('/api/upc-audit', json={'category': 'cat_wine', 'full_review': True})

    assert res.status_code == 200
    assert seen == {'category': 'cat_wine', 'limit': None}
