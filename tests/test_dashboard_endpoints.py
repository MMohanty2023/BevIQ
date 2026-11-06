import sqlite3
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app
from config import CSV_FILES
from engines.sql_engine import SQLEngine


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


def test_supplier_dashboard_returns_unique_suppliers_and_brand_record_counts(monkeypatch):
    class FakeDB:
        def query(self, sql, params=None):
            assert f"`{CSV_FILES['ai_master']['table']}`" in sql
            assert "GROUP BY" in sql
            return [
                {"supplier_key": "acme", "supplier": "Acme", "brand_key": "fizz", "brand_name": "Fizz", "record_count": 3},
                {"supplier_key": "acme", "supplier": "Acme", "brand_key": "soda", "brand_name": "Soda", "record_count": 2},
                {"supplier_key": "acme", "supplier": "Acme", "brand_key": None, "brand_name": None, "record_count": 1},
                {"supplier_key": "other", "supplier": "Other", "brand_key": "fizz", "brand_name": "Fizz", "record_count": 4},
            ]

    class FakeDBManager:
        def backend_name(self):
            return "sqlite"

    monkeypatch.setattr(app_module, "sql_engine", SQLEngine(db=FakeDB()))
    monkeypatch.setattr(app_module, "db_manager", FakeDBManager())

    response = app.test_client().get("/api/suppliers/dashboard")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["total_suppliers"] == 2
    assert payload["backend"] == "sqlite"
    acme = payload["suppliers"][0]
    assert acme["brand_count"] == 2
    assert acme["record_count"] == 6
    assert acme["brands"] == [
        {"brand_name": "Fizz", "record_count": 3},
        {"brand_name": "Soda", "record_count": 2},
    ]


def test_supplier_dashboard_sql_groups_case_insensitive_brands_and_ignores_missing_suppliers():
    table = CSV_FILES["ai_master"]["table"]
    connection = sqlite3.connect(":memory:")
    connection.execute(f'CREATE TABLE "{table}" (SupplierName TEXT, BrandName TEXT)')
    connection.executemany(
        f'INSERT INTO "{table}" (SupplierName, BrandName) VALUES (?, ?)',
        [
            ("Acme", "Fizz"),
            ("ACME", " fizz "),
            ("Acme", "Pop"),
            ("Acme", "Pop"),
            ("Acme", ""),
            ("", "Unassigned"),
        ],
    )

    class SQLiteDB:
        def query(self, sql, params=None):
            cursor = connection.execute(sql, params or ())
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    try:
        payload = SQLEngine(db=SQLiteDB()).get_supplier_dashboard()
    finally:
        connection.close()

    assert payload["total_suppliers"] == 1
    supplier = payload["suppliers"][0]
    assert supplier["supplier"] == "ACME"
    assert supplier["brand_count"] == 2
    assert supplier["record_count"] == 5
    assert supplier["brands"] == [
        {"brand_name": "Fizz", "record_count": 2},
        {"brand_name": "Pop", "record_count": 2},
    ]


def test_supplier_overview_endpoint_passes_search_filters_and_sort(monkeypatch):
    class FakeSQL:
        def get_supplier_overview(self, **filters):
            assert filters == {
                "search": "AB12", "category": "Wine", "supplier": "code:ab12",
                "status": "Active", "sort": "highest",
            }
            return {
                "total_suppliers": 1,
                "total_brands": 2,
                "filtered_suppliers": 1,
                "suppliers": [{"supplier": "Acme", "supplier_code": "AB12", "brand_count": 2}],
                "supplier_options": [],
            }

    class FakeDB:
        def backend_name(self):
            return "sqlite"

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    monkeypatch.setattr(app_module, "db_manager", FakeDB())
    response = app.test_client().get(
        "/api/suppliers/overview?q=AB12&category=Wine&supplier=code%3Aab12&status=Active&sort=highest"
    )

    assert response.status_code == 200
    assert response.get_json()["suppliers"][0]["supplier_code"] == "AB12"


def test_supplier_overview_rejects_unknown_sort():
    response = app.test_client().get("/api/suppliers/overview?sort=random")
    assert response.status_code == 400


def test_supplier_brand_endpoints_validate_and_return_not_found(monkeypatch):
    class FakeSQL:
        def get_supplier_brands(self, **filters):
            return None

        def get_supplier_brand_details(self, **filters):
            return None

    monkeypatch.setattr(app_module, "sql_engine", FakeSQL())
    client = app.test_client()

    assert client.get("/api/suppliers/brands").status_code == 400
    assert client.get("/api/suppliers/brands?supplier_key=code%3Amissing").status_code == 404
    assert client.get("/api/suppliers/brand-details").status_code == 400
    assert client.get(
        "/api/suppliers/brand-details?supplier_code=1&brand_code=missing"
    ).status_code == 404


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
