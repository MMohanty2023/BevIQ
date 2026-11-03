from engines.sql_engine import SQLEngine


class MetricsDB:
    def query(self, sql, params=None):
        sql_lower = " ".join(sql.lower().split())
        if "count(*)" in sql_lower and "from `cat_beer`" in sql_lower:
            return [{"total_records": 10, "available_upcs": 8, "missing_upcs": 2, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_wine`" in sql_lower:
            return [{"total_records": 20, "available_upcs": 15, "missing_upcs": 5, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_rtd`" in sql_lower:
            return [{"total_records": 7, "available_upcs": 7, "missing_upcs": 0, "invalid_upcs": 0}]
        if "count(*)" in sql_lower and "from `cat_spirits`" in sql_lower:
            return [{"total_records": 13, "available_upcs": 10, "missing_upcs": 3, "invalid_upcs": 0}]
        if "from `ai_master`" in sql_lower and "master_record_count" in sql_lower:
            return [{
                "master_record_count": 50,
                "unique_brands": 12,
                "unique_master_ids": 48,
                "available_upcs": 40,
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
