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

    assert len(overview) == 8
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

    assert len(overview) == 8
    assert len(database.queries) == 9
    assert all(item["total_rows"] == 25 and item["unique_upcs"] == 20 for item in overview)


def test_supplier_directory_groups_na_and_returns_brand_summary_and_details():
    class SupplierDB:
        def query(self, sql, params=None):
            normalized = " ".join(sql.lower().split())
            if "select case when" in normalized and "count(distinct" in normalized:
                return [
                    {"supplier": "Acme Imports", "record_count": 3, "brand_count": 2, "upc_count": 2},
                    {"supplier": "NA", "record_count": 2, "brand_count": 1, "upc_count": 0},
                ]
            if "select case when" in normalized and "group by" in normalized:
                return [
                    {"supplier_key": "acme imports", "brand_name": "Fizz", "brand_code": "F1", "brand_id": "B1", "record_count": 2, "categories": "Beer"},
                    {"supplier_key": "NA", "brand_name": "NA Brand", "brand_code": None, "brand_id": None, "record_count": 1, "categories": None},
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


def test_supplier_directory_reports_allmaster_record_count_and_product_categories():
    class AllMasterOnlyDB:
        def query(self, sql, params=None):
            normalized = " ".join(sql.lower().split())
            assert "from `all_brands`" in normalized
            assert "ai_master" not in normalized
            assert "trained_brands" not in normalized
            if "min(brandname)" in normalized:
                assert "supplier_key" in normalized
                assert "group by" in normalized
                return [
                    {"supplier_key": "acme", "brand_name": "Fizz", "brand_code": "F1", "brand_id": "B1", "record_count": 3, "categories": "Beer"},
                    {"supplier_key": "acme", "brand_name": "Wine Star", "brand_code": "W1", "brand_id": "B2", "record_count": 1, "categories": "Wine"},
                ]
            if "group by" in normalized and "supplier" in normalized:
                assert "productcategory" in normalized
                assert "order by case when supplier_key" in normalized or "order by supplier_key" in normalized
                return [{
                    "supplier_key": "acme",
                    "supplier": "Acme Imports",
                    "supplier_code": "S1",
                    "record_count": 4,
                    "brand_count": 2,
                    "upc_count": 4,
                    "categories": "Beer,Beer,Wine",
                    "statuses": "1",
                }]
            if "select distinct brandname" in normalized:
                return [{"brand_name": "Fizz"}, {"brand_name": "Wine Star"}]
            if "select brandname, productname" in normalized:
                return []
            raise AssertionError(f"Unexpected query: {sql}")

    result = SQLEngine(AllMasterOnlyDB()).get_supplier_directory()

    assert result["total_suppliers"] == 1
    supplier = result["suppliers"][0]
    assert supplier["supplier"] == "Acme Imports"
    assert supplier["record_count"] == 4
    assert supplier["brand_count"] == 2
    assert supplier["categories"] == ["Beer", "Wine"]
    assert supplier["brand_details"][0]["categories"] == ["Beer"]
    assert supplier["brand_details"][1]["categories"] == ["Wine"]
