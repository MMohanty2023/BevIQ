from engines.rag_orchestrator import RAGOrchestrator


def test_ollama_availability_check_is_cached(monkeypatch):
    calls = {'count': 0}

    class FakeResponse:
        status_code = 200

    def fake_get(*args, **kwargs):
        calls['count'] += 1
        return FakeResponse()

    monkeypatch.setattr('engines.rag_orchestrator.requests.get', fake_get)
    orchestrator = RAGOrchestrator()

    assert orchestrator.is_ollama_available() is True
    assert orchestrator.is_ollama_available() is True
    assert calls['count'] == 1


def test_master_brand_count_uses_direct_sql_count(monkeypatch):
    orchestrator = RAGOrchestrator()
    called = {'count': 0, 'vector': 0}

    class FakeSQL:
        def count_master_brands(self):
            called['count'] += 1
            return 12345

    class FakeVector:
        def search(self, *args, **kwargs):
            called['vector'] += 1
            return []

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    monkeypatch.setattr('engines.rag_orchestrator.vector_engine', FakeVector())
    result = orchestrator.route_and_execute('How many brands are present in the master sheet?')

    assert called['count'] == 1
    assert called['vector'] == 0
    assert '12,345' in result['answer']


def test_hinglish_master_brand_count_gets_hinglish_answer(monkeypatch):
    class FakeSQL:
        def count_master_brands(self):
            return 12345

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute('master sheet mein kitne brands hain?')

    assert 'master sheet mein' in result['answer'].lower()
    assert '12,345' in result['answer']


def test_short_english_brand_count_question_gets_master_count(monkeypatch):
    class FakeSQL:
        def count_master_brands(self):
            return 12345

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute('How many brands present in this?')

    assert '12,345' in result['answer']
    assert 'unique brands' in result['answer']


def test_category_brand_count_uses_requested_sheet(monkeypatch):
    class FakeSQL:
        def count_brands(self, category=None):
            assert category == 'cat_beer'
            return 456

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute('How many beer brands present?')

    assert '456' in result['answer']
    assert 'beer' in result['answer'].lower()
    assert 'master sheet contains' not in result['answer'].lower()


def test_flexible_joke_request_returns_a_joke():
    result = RAGOrchestrator().route_and_execute('tell me about joke')

    assert 'Joke' in result['answer']
    assert 'coffee' in result['answer'].lower()


def test_brand_profile_query_returns_sheet_details_in_hinglish(monkeypatch):
    class FakeSQL:
        def brand_profile(self, brand):
            assert brand.lower() == 'barefoot'
            return {
                'query_brand': brand,
                'total_records': 12,
                'unique_brand_count': 1,
                'unique_flavour_count': 2,
                'unique_size_count': 2,
                'unique_upc_count': 12,
                'categories': [{'category': 'Wine', 'count': 12}],
                'flavours': ['Moscato', 'Merlot'],
                'sizes': ['750 ML', '1.5 L'],
                'suppliers': ['Gallo'],
                'origins': ['Imported'],
                'records': [{'category': 'Wine', 'brand': 'Barefoot', 'flavour': 'Moscato'}],
            }

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute(
        'Barefoot ke kitne flavour, size, supplier aur origin hain?'
    )

    assert 'Barefoot' in result['answer']
    assert 'Moscato' in result['answer']
    assert 'Gallo' in result['answer']
    assert 'unique brand names' in result['answer'].lower()
    assert 'flavours (2 distinct)' in result['answer'].lower()
    assert 'sizes / packs (2 distinct)' in result['answer'].lower()


def test_brand_or_product_description_search_uses_all_sheet_catalog(monkeypatch):
    class FakeSQL:
        def search_catalog(self, query, limit=100):
            assert query == '100 Percent Honest'
            return {
                'query': query,
                'total_matches': 1,
                'records': [{
                    'category': 'Wine', 'brand': '100 Percent Honest',
                    'product_description': '100 Percent Honest Chardonnay 750 ML Bottle',
                    'flavour': 'Chardonnay', 'size': '750 ML',
                    'supplier': 'Example Supplier', 'origin': 'California',
                    'upc': '0854764004481', 'source_file': 'Wine.csv',
                    'original_row': 2,
                }],
            }

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute('search 100 Percent Honest')

    assert '100 Percent Honest Chardonnay' in result['answer']
    assert result['record_count'] == 1
    assert result['record_count'] == 1


def test_hinglish_missing_category_query_gets_hinglish_summary(monkeypatch):
    class FakeComparison:
        def compare_master_vs_categorization(self, category, limit):
            return {
                'records': [],
                'summary': {
                    'master_total_records': 10,
                    'categorization_total_records': 5,
                    'categorization_unique_upcs': 5,
                    'matching_upcs_in_both': 3,
                    'match_rate_pct': 60,
                    'missing_from_master_total': 2,
                    'sample_analyzed': 5,
                    'exact_matches_in_sample': 3,
                    'partial_matches_in_sample': 0,
                    'mismatches_in_sample': 0,
                    'missing_in_sample': 2,
                },
            }

    monkeypatch.setattr('engines.rag_orchestrator.comparison_engine', FakeComparison())
    result = RAGOrchestrator().route_and_execute('beer ka missing upc dikhao')

    assert 'master' in result['answer'].lower()
    assert 'missing' in result['answer'].lower()
    assert 'beer sheet' in result['answer'].lower()


def test_product_audit_chat_requests_full_category_review(monkeypatch):
    seen = {}

    class FakeEngine:
        def audit(self, category, limit):
            seen['category'] = category
            seen['limit'] = limit
            return []

    monkeypatch.setattr('engines.upc_match_engine.upc_match_engine', FakeEngine())
    monkeypatch.setattr(RAGOrchestrator, 'is_ollama_available', lambda self: False)

    response = RAGOrchestrator().route_and_execute(
        'Check Wine products where brand flavour size match AllMasterBrand but UPC is missing'
    )

    assert seen == {'category': 'cat_wine', 'limit': None}
    assert response['read_only'] is True


def test_supplier_question_uses_supplier_search_without_brand_profile(monkeypatch):
    class FakeSQL:
        def search_supplier(self, supplier, limit=100):
            assert supplier == 'Gallo'
            return {'query_supplier': supplier, 'total_matches': 1, 'records': [
                {'SupplierName': 'Gallo', 'BrandName': 'Example', 'SupplierCode': 'S1'}
            ]}

        def brand_profile(self, brand):
            raise AssertionError('supplier-only query must not use brand_profile')

    monkeypatch.setattr('engines.rag_orchestrator.sql_engine', FakeSQL())
    result = RAGOrchestrator().route_and_execute('Find products with supplier Gallo')

    assert 'Supplier Search' in result['answer']
    assert result['record_count'] == 1
