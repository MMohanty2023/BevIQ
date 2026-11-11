from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app
from engines.sql_engine import SQLEngine
from engines.rag_orchestrator import RAGOrchestrator


class TrainedDB:
    def table_columns(self, table):
        assert table == "trained_brands"
        return ["Id", "Class_Id", "SupplierCode", "SupplierName", "BrandCode", "BrandName",
                "Category_Wine_Spirits_Beer_Non_Alcoholic", "ImageCounts", "Status", "RecordStatus",
                "SKU", "Model", "Model_Id", "AvgTrainedPhotos", "ImageUrls"]

    def query(self, sql, params=None):
        if "COUNT(*) AS total_matches" in sql:
            return [{"total_matches": 1}]
        if "COUNT(DISTINCT" in sql:
            return [{"total_brands": 2, "total_suppliers": 1, "total_trained_images": 70,
                     "active_brands": 1, "inactive_brands": 1, "total_unique_models": 1,
                     "total_categories": 1, "missing_data_records": 1}]
        if "GROUP BY" in sql:
            return [{"category": "Spirits", "brand_count": 2, "image_count": 70}]
        return [{
            "Id": "10973", "Class_Id": "299", "SupplierCode": "13454", "SupplierName": "Winebow Inc",
            "BrandCode": "TULLIBARDINE", "BrandName": "Tullibardine",
            "Category_Wine_Spirits_Beer_Non_Alcoholic": "Spirits", "ImageCounts": "39", "Status": "1",
            "RecordStatus": "Active", "SKU": "0", "Model": "Winebow_WineGroup_v8_24062025",
            "Model_Id": "317", "AvgTrainedPhotos": "39", "ImageUrls": '""',
        }]


def test_trained_search_maps_actual_fields_and_missing_images():
    result = SQLEngine(TrainedDB()).search_trained_brands(query="299", page=1, page_size=50)

    assert result["total_matches"] == 1
    record = result["records"][0]
    assert record["class_id"] == "299"
    assert record["brand_name"] == "Tullibardine"
    assert record["image_urls"] == []
    assert record["missing_sku"] is True
    assert record["missing_images"] is True


def test_trained_summary_uses_dynamic_counts():
    summary = SQLEngine(TrainedDB()).get_trained_dataset_summary()

    assert summary["total_brands"] == 2
    assert summary["total_trained_images"] == 70
    assert summary["missing_data_records"] == 1


def test_trained_summary_counts_supplier_names_across_supplier_codes():
    captured_queries = []

    class SupplierNameDB(TrainedDB):
        def query(self, sql, params=None):
            if "SELECT DISTINCT SupplierName" in sql:
                captured_queries.append(sql)
                return [{"SupplierName": "Acme Imports"}, {"SupplierName": "ACME IMPORTS"}]
            return super().query(sql, params)

    summary = SQLEngine(SupplierNameDB()).get_trained_dataset_summary()

    assert summary["total_suppliers"] == 1
    assert "SupplierCode" not in captured_queries[0]


def test_trained_summary_merges_obvious_supplier_name_variants():
    captured_queries = []

    class AliasDB(TrainedDB):
        def query(self, sql, params=None):
            if "SELECT DISTINCT SupplierName" in sql:
                captured_queries.append(sql)
                return [
                    {"SupplierName": "Acme Imports, LLC."},
                    {"SupplierName": "ACME IMPORTS LLC"},
                    {"SupplierName": "Acme Imports Inc."},
                ]
            return super().query(sql, params)

    summary = SQLEngine(AliasDB()).get_trained_dataset_summary()

    assert captured_queries
    assert summary["total_suppliers"] == 1


def test_trained_mysql_queries_use_mysql_numeric_casts():
    captured_queries = []

    class MySQLTrainedDB(TrainedDB):
        def backend_name(self):
            return "mysql"

        def query(self, sql, params=None):
            assert "AS INTEGER" not in sql
            captured_queries.append(sql)
            return super().query(sql, params)

    engine = SQLEngine(MySQLTrainedDB())

    engine.get_trained_dataset_summary()
    engine.get_trained_dataset_analytics()
    engine.search_trained_brands(min_images=10)

    active_query = next(query for query in captured_queries if "AS status" in query)
    assert "GROUP BY CASE WHEN" in active_query


def test_trained_records_endpoint_supports_pagination(monkeypatch):
    class FakeSQL:
        def search_trained_brands(self, **kwargs):
            assert kwargs["page"] == 2
            assert kwargs["page_size"] == 100
            return {"records": [{"id": "1"}], "total_matches": 101, "page": 2, "page_size": 100}

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    response = app.test_client().get("/api/trained-dataset/records?page=2&page_size=100")

    assert response.status_code == 200
    assert response.get_json()["records"][0]["id"] == "1"


def test_trained_detail_endpoint_uses_existing_chat_backend(monkeypatch):
    class FakeSQL:
        def get_trained_brand_detail(self, record_id):
            assert record_id == "10973"
            return {"record": {"id": "10973", "brand_name": "Tullibardine"}}

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    response = app.test_client().get("/api/trained-dataset/detail/10973")

    assert response.status_code == 200
    assert response.get_json()["record"]["brand_name"] == "Tullibardine"


def test_existing_ai_assistant_routes_trained_class_id_queries(monkeypatch):
    class FakeSQL:
        def search_trained_brands(self, **kwargs):
            assert kwargs["query"] == "299"
            return {"records": [{"id": "10973", "class_id": "299", "brand_name": "Tullibardine"}], "total_matches": 1}

    assistant = RAGOrchestrator()
    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: False)

    result = assistant.route_and_execute("Find complete details for Class ID 299", session_id="trained-test")

    assert result["record_count"] == 1
    assert "Trained" in result["answer"]
