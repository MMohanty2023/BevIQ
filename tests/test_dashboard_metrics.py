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
