from config import CSV_FILES
from engines.sql_engine import SQLEngine


class MetricsDB:
    def query(self, sql, params=None):
        sql_lower = " ".join(sql.lower().split())
        if "count(*)" in sql_lower and "from `cat_beer`" in sql_lower:
            return [{"total_records": 10, "available_upcs": 8, "distinct_upcs": 7, "missing_upcs": 2, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_wine`" in sql_lower:
            return [{"total_records": 20, "available_upcs": 15, "distinct_upcs": 14, "missing_upcs": 5, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_rtd`" in sql_lower:
            return [{"total_records": 7, "available_upcs": 7, "distinct_upcs": 6, "missing_upcs": 0, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_spirits`" in sql_lower:
            return [{"total_records": 13, "available_upcs": 10, "distinct_upcs": 9, "missing_upcs": 3, "invalid_upcs": 0}]
        if "from `ai_master`" in sql_lower and "master_record_count" in sql_lower:
            return [{
                "master_record_count": 50,
                "unique_brands": 12,
                "unique_master_ids": 48,
                "available_upcs": 40,
                "distinct_upcs": 38,
                "missing_upcs": 10,
            }]
        raise AssertionError(f"Unexpected query: {sql}")


def test_dashboard_metrics_returns_live_category_and_master_brand_quality():
    metrics = SQLEngine(MetricsDB()).get_dashboard_metrics()

    assert metrics["categories"]["beer"]["total_records"] == 10
    assert metrics["categories"]["wine"]["missing_upcs"] == 5
    assert metrics["categories"]["rtd"]["completion_percentage"] == 100.0
    assert metrics["overall_upc"]["available_upcs"] == 40
    assert metrics["overall_upc"]["missing_upcs"] == 10
    assert metrics["master_brand"]["unique_master_ids"] == 48
    assert metrics["master_brand"]["distinct_upcs"] == 38
    assert metrics["categories"]["beer"]["distinct_upcs"] == 7


def test_dashboard_metrics_handles_master_schema_without_normalized_brand_or_id():
    class LegacyMetricsDB(MetricsDB):
        def table_columns(self, table):
            return ["record_id", "BrandName", "clean_upc"]

        def query(self, sql, params=None):
            if "from `ai_master`" in " ".join(sql.lower().split()):
                assert "norm_brand" not in sql
                assert "record_id" in sql
                return [{
                    "master_record_count": 4,
                    "unique_brands": 2,
                    "unique_master_ids": 4,
                    "available_upcs": 3,
                    "missing_upcs": 1,
                }]
            return super().query(sql, params)

    metrics = SQLEngine(LegacyMetricsDB()).get_dashboard_metrics()

    assert metrics["master_brand"]["unique_brands"] == 2


def test_dataset_overview_combines_row_and_distinct_upc_counts():
    class OverviewDB:
        def __init__(self):
            self.queries = []

        def query(self, sql, params=None):
            self.queries.append(sql)
            return [
                {"dataset_key": key, "row_count": 25, "upc_count": 20}
                for key in CSV_FILES
            ]

    database = OverviewDB()
    overview = SQLEngine(database).get_dataset_overview()

    assert len(overview) == 7
    assert len(database.queries) == 1
    assert "UNION ALL" in database.queries[0]
    assert "COUNT(DISTINCT NULLIF(clean_upc, ''))" in database.queries[0]
    assert all(item["total_rows"] == 25 and item["unique_upcs"] == 20 for item in overview)


def test_dataset_overview_retries_tables_individually_when_combined_query_fails():
    class OverviewDB:
        def __init__(self):
            self.queries = []

        def query(self, sql, params=None):
            self.queries.append(sql)
            if "UNION ALL" in sql:
                raise RuntimeError("combined query unsupported")
            return [{"row_count": 25, "upc_count": 20}]

    database = OverviewDB()
    overview = SQLEngine(database).get_dataset_overview()

    assert len(overview) == 7
    assert len(database.queries) == 8
    assert all(item["total_rows"] == 25 and item["unique_upcs"] == 20 for item in overview)


def test_supplier_directory_groups_na_and_returns_brand_summary_and_details():
    class SupplierDB:
        def query(self, sql, params=None):
            normalized = " ".join(sql.lower().split())
            if "group by" in normalized and "supplier" in normalized:
                return [
                    {"supplier": "Acme Imports", "record_count": 3, "brand_count": 2, "upc_count": 2},
                    {"supplier": "NA", "record_count": 2, "brand_count": 1, "upc_count": 0},
                ]
            if "select distinct" in normalized:
                if params == ("NA",):
                    return [{"brand_name": "NA Brand"}]
                return [{"brand_name": "Fizz"}, {"brand_name": "fizz"}, {"brand_name": None}]
            if "limit" in normalized:
                if params == ("NA",):
                    return [{"BrandName": "NA Brand", "ProductName": "NA Product", "clean_upc": ""}]
                return [{"BrandName": "Fizz", "ProductName": "Fizz Original", "clean_upc": "123"}]
            raise AssertionError(f"Unexpected query: {sql}")

    result = SQLEngine(SupplierDB()).get_supplier_directory()

    assert result["total_suppliers"] == 2
    assert result["suppliers"][0]["supplier"] == "Acme Imports"
    assert result["suppliers"][0]["brand_count"] == 2
    assert result["suppliers"][0]["brand_names"] == ["Fizz"]
    assert result["suppliers"][0]["records"]
    assert result["suppliers"][1]["supplier"] == "NA"
    assert result["suppliers"][1]["brand_names"] == ["NA Brand"]
    assert result["suppliers"][1]["records"]


def test_supplier_overview_uses_master_and_trained_brand_data(monkeypatch, tmp_path):
    trained_data = (
        "Id|Class Id|SupplierCode|SupplierName|BrandCode|BrandName|Category (Wine/Spirits/Beer/Non Alcoholic)|ImageCounts|Status|RecordStatus|SKU|Model|Model Id|ImageUrls\n"
        "10|20|A1|Acme|FIZZ|Fizz|Wine|3|1|Active|2|Model A|7|https://images.test/fizz.png\n"
        "13|23|A1|Acme|FIZZ|Fizz|Spirits|2|1|Active|1|Model A2|10|https://images.test/fizz-class2.png\n"
        "11|21|A1|Acme|POP|Pop|Non Alcoholic|5|2|Inactive|4|Model B|8|\n"
        "14|24|A2|ACME|MIX|Mix|Beer|1|1|Active|1|Model D|11|https://images.test/mix.png\n"
        "12|22|B1|Other|OTHER|Other Brand|Beer|1|1|Active|1|Model C|9|\n"
    )
    trained_file = tmp_path / "TrainedBrandsData.csv"
    trained_file.write_text(trained_data, encoding="utf-8")
    monkeypatch.setattr("engines.sql_engine.TRAINED_BRANDS_FILE", trained_file)

    class SupplierOverviewDB:
        def query(self, sql, params=None):
            assert "SELECT DISTINCT SupplierCode AS supplier_code" in sql
            assert "FROM `ai_master`" in sql
            assert "all_brands" not in sql
            return [
                {"supplier_code": "A1", "supplier_name": "Acme", "brand_code": "FIZZ", "brand_name": "Fizz", "product_category": "1"},
                {"supplier_code": "A1", "supplier_name": "Acme", "brand_code": "POP", "brand_name": "Pop", "product_category": "2"},
                {"supplier_code": "A2", "supplier_name": "ACME", "brand_code": "MIX", "brand_name": "Mix", "product_category": "3"},
                {"supplier_code": "B1", "supplier_name": "Other", "brand_code": "OTHER", "brand_name": "Other Brand", "product_category": "1"},
            ]

    engine = SQLEngine(SupplierOverviewDB())
    overview = engine.get_supplier_overview(sort="highest")

    assert overview["total_suppliers"] == 2
    assert overview["total_brands"] == 4
    assert overview["suppliers"][0]["supplier"] == "Acme"
    assert overview["suppliers"][0]["brand_count"] == 3
    assert engine.get_supplier_overview(search="20")["suppliers"][0]["supplier"] == "Acme"
    assert engine.get_supplier_overview(category="Wine")["suppliers"][0]["brand_count"] == 1
    assert engine.get_supplier_overview(status="Inactive")["suppliers"][0]["supplier"] == "Acme"

    acme_brands = engine.get_supplier_brands("name:acme", category="Wine")
    assert acme_brands["total_brand_count"] == 3
    assert acme_brands["brand_count"] == 1
    assert acme_brands["brands"][0]["class_id"] == "20, 23"
    assert acme_brands["brands"][0]["category"] == "Spirits / Wine"
    assert "_trained_rows" not in acme_brands["brands"][0]
    assert engine.get_supplier_brands("name:acme")["brands"][1]["brand_name"] == "Mix"
    assert engine.get_supplier_overview(supplier="code:a2")["suppliers"][0]["supplier"] == "Acme"

    class BrandDetailsDB(SupplierOverviewDB):
        def query(self, sql, params=None):
            if "SELECT id AS master_id" in sql:
                assert "FROM `ai_master`" in sql
                return [
                    {"master_id": "m1", "supplier_code": "A1", "supplier": "Acme", "brand_code": "FIZZ", "brand_name": "Fizz", "product_category": "1", "product_name": "Fizz Original", "upc": "111", "clean_upc": "111", "image_url": "https://images.test/product.png"},
                    {"master_id": "m2", "supplier_code": "A1", "supplier": "Acme", "brand_code": "FIZZ", "brand_name": "Fizz", "product_category": "1", "product_name": "Fizz Zero", "upc": "222", "clean_upc": "222", "image_url": "https://images.test/product.png"},
                ]
            assert "all_brands" not in sql
            return super().query(sql, params)

    details = SQLEngine(BrandDetailsDB()).get_supplier_brand_details(
        supplier_code="A1", brand_code="FIZZ"
    )
    assert details["brand_id"] == "10, 13"
    assert details["class_id"] == "20, 23"
    assert details["model_name"] == "Model A, Model A2"
    assert details["sku"] == "1, 2"
    assert details["image_count"] == "5"
    assert details["images"] == [
        "https://images.test/product.png",
        "https://images.test/fizz.png",
        "https://images.test/fizz-class2.png",
    ]
    assert len(details["products"]) == 2
