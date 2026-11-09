from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.comparison_engine import ComparisonEngine
import app as app_module
from app import app


class UntrainedDB:
    def query(self, sql, params=None):
        if "FROM `all_brands`" in sql:
            return [
                {"upc": "00123", "brand_name": "Alpha", "supplier_name": "Supplier A", "brand_code": "A", "source_file": "AIMasterBrandData.csv", "original_row": 1},
                {"upc": "00456", "brand_name": "Beta", "supplier_name": "Supplier B", "brand_code": "B", "source_file": "AIMasterBrandData.csv", "original_row": 2},
            ]
        if "FROM `trained_brands`" in sql:
            return [{"upc": "00123"}]
        if "FROM `cat_rtd`" in sql:
            return [{"upc": "00789", "brand_name": "Alpha", "supplier_name": "Supplier A", "brand_code": "A", "source_file": "Categorization 2026 - RTDs.csv", "original_row": 4}]
        if "FROM `cat_wine`" in sql:
            return [{"upc": "00456", "brand_name": "Beta", "supplier_name": "Supplier B", "brand_code": "B", "source_file": "Categorization 2026 - Wine.csv", "original_row": 5}]
        if "FROM `cat_beer`" in sql:
            return [{"upc": "00011", "brand_name": "Gamma", "supplier_name": "Supplier C", "brand_code": "C", "source_file": "Categorization 2026 - Beer.csv", "original_row": 6}]
        if "FROM `cat_spirits`" in sql:
            return []
        raise AssertionError(sql)


class NewDatasetDB:
    def query(self, sql, params=None):
        if "FROM `cat_beer`" in sql:
            assert "Dataset" in sql
            return [{"brand_name": "New Beer", "source_file": "beer.csv", "original_row": 1}]
        if "FROM `cat_wine`" in sql:
            assert "needtoverify" in sql.lower()
            return [
                {"brand_name": "New Wine", "source_file": "wine.csv", "original_row": 3},
                {"brand_name": "Verify Wine", "source_file": "wine.csv", "original_row": 4},
            ]
        if "FROM `cat_spirits`" in sql:
            return [{"brand_name": "New Beer", "upc": "311", "source_file": "spirits.csv", "original_row": 4}]
        if "FROM `cat_rtd`" in sql:
            return []
        raise AssertionError(sql)


def test_untrained_dataset_uses_only_new_category_rows_and_does_not_count_records():
    result = ComparisonEngine(NewDatasetDB()).find_untrained_brands()

    assert [record["brand_name"] for record in result["records"]] == ["New Beer", "New Beer", "New Wine", "Verify Wine"]
    assert all("record_count" not in record for record in result["records"])


def test_untrained_comparison_endpoint_returns_read_only_report(monkeypatch):
    class FakeComparison:
        def find_untrained_brands(self, limit=None, search=None):
            assert limit == 250
            return {"summary": {"unique_untrained_brands": 1}, "records": [{"brand_name": "Alpha"}]}

    monkeypatch.setattr(app_module, "comparison_engine", FakeComparison())
    response = app.test_client().post("/api/compare", json={"type": "untrained_brands"})

    assert response.status_code == 200
    assert response.get_json()["records"] == [{"brand_name": "Alpha"}]
    assert response.get_json()["summary"]["unique_untrained_brands"] == 1


def test_untrained_dataset_navigation_endpoint_returns_searchable_report(monkeypatch):
    class FakeComparison:
        def find_untrained_brands(self, limit=None, search=None):
            assert limit == 25
            assert search == "alpha"
            return {
                "summary": {"unique_untrained_brands": 1},
                "records": [{"brand_name": "Alpha"}],
                "export_records": [{"brand_name": "Alpha"}, {"brand_name": "Hidden export row"}],
            }

    class FakeDB:
        def backend_name(self):
            return "sqlite"

    monkeypatch.setattr(app_module, "comparison_engine", FakeComparison())
    monkeypatch.setattr(app_module, "db_manager", FakeDB())
    response = app.test_client().get("/api/untrained-dataset?limit=25&search=alpha")

    assert response.status_code == 200
    assert response.get_json()["records"] == [{"brand_name": "Alpha"}]
    assert "export_records" not in response.get_json()
