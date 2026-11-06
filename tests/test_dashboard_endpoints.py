import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app


def test_dashboard_overview_returns_live_kpis(monkeypatch):
    class FakeSQL:
        def get_dataset_overview(self):
            return [{"dataset_key": "ai_master", "total_rows": 10, "unique_upcs": 8}]

    class FakeDB:
        def backend_name(self):
            return "mysql"

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    monkeypatch.setattr(app_module, "db_manager", FakeDB())

    response = app.test_client().get("/api/dashboard/overview")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["backend"] == "mysql"
    assert payload["kpis"]["total_records"] == 10
    assert payload["kpis"]["total_unique_upcs"] == 8


def test_dashboard_suppliers_returns_supplier_directory(monkeypatch):
    class FakeSQL:
        def get_supplier_directory(self, limit=500):
            assert limit == 500
            return {
                "total_suppliers": 1,
                "suppliers": [{
                    "supplier": "Acme Imports",
                    "record_count": 2,
                    "brand_count": 1,
                    "brand_names": ["Fizz"],
                    "upc_count": 2,
                    "records": [],
                }],
            }

    class FakeDB:
        def backend_name(self):
            return "sqlite"

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    monkeypatch.setattr(app_module, "db_manager", FakeDB())

    response = app.test_client().get("/api/dashboard/suppliers")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["backend"] == "sqlite"
    assert payload["total_suppliers"] == 1
    assert payload["suppliers"][0]["brand_names"] == ["Fizz"]


def test_dashboard_missing_upc_is_bounded(monkeypatch):
    class FakeComparison:
        def compare_all_missing_in_master(self, limit_per_category, search=None):
            assert limit_per_category == 50
            return {"summary": {"total_missing_from_master": 4}, "records": [{"upc": "1"}]}

    monkeypatch.setattr(app_module, "comparison_engine", FakeComparison())

    response = app.test_client().get("/api/dashboard/missing-upc?limit=50&search=brand")

    assert response.status_code == 200
    assert response.get_json()["summary"]["total_missing_from_master"] == 4


def test_dashboard_export_rejects_unknown_dataset():
    response = app.test_client().get("/api/dashboard/export/not-a-dataset")

    assert response.status_code == 400


def test_dashboard_export_returns_csv(monkeypatch):
    class FakeDB:
        def query(self, sql, params=None):
            return [{"id": "1", "BrandName": "Example"}]

    monkeypatch.setattr(app_module, "db_manager", FakeDB())

    response = app.test_client().get("/api/dashboard/export/ai_master?limit=10")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "BrandName" in response.data.decode("utf-8")
