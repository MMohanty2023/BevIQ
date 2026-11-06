from engines.sql_engine import SQLEngine


class MasterDB:
    def table_columns(self, table):
        assert table == "ai_master"
        return ["id", "BrandName", "ProductName", "clean_upc", "clean_alt_upc", "norm_brand", "Size"]

    def query(self, sql, params=None):
        assert "FROM `ai_master`" in sql
        assert params
        if params[0] == "64836d6479db3373669996ae":
            return [{
                "id": "64836d6479db3373669996ae",
                "BrandName": "Kingfisher",
                "ProductName": "Kingfisher Lager",
                "clean_upc": "08901234567890",
                "clean_alt_upc": "",
                "norm_brand": "KINGFISHER",
                "Size": "650 ML",
            }]
        return []


def test_master_brand_search_returns_exact_alphanumeric_id_and_all_fields():
    result = SQLEngine(MasterDB()).search_master_brands(master_id="64836d6479db3373669996ae")

    assert result["total_matches"] == 1
    assert result["records"][0]["BrandName"] == "Kingfisher"
    assert "ProductName" in result["columns"]


def test_master_brand_search_supports_record_id_and_reports_full_match_count():
    class LegacyDB:
        def table_columns(self, table):
            return ["record_id", "BrandName", "ProductName", "UPCCode"]

        def query(self, sql, params=None):
            rows = [
                {"record_id": "a-1", "BrandName": "Test", "ProductName": "One", "UPCCode": "1"},
                {"record_id": "a-2", "BrandName": "Test", "ProductName": "Two", "UPCCode": "2"},
            ]
            if params and params[0] == "%Test%":
                return rows
            if params and params[0] == "a-1":
                return [rows[0]]
            return []

    result = SQLEngine(LegacyDB()).search_master_brands(brand="Test", limit=1)
    assert result["total_matches"] == 2
    assert len(result["records"]) >= 1


def test_master_brand_metrics_falls_back_to_source_upc_column():
    class SourceUPCDB:
        def table_columns(self, table):
            if table == "ai_master":
                return ["id", "BrandName", "UPCCode"]
            return ["UPC 13 digit"]

        def query(self, sql, params=None):
            if "ai_master" in sql:
                return [{"master_record_count": 1, "unique_brands": 1, "unique_master_ids": 1, "available_upcs": 1, "missing_upcs": 0}]
            return [{"total_records": 1, "available_upcs": 1, "missing_upcs": 0}]

    metrics = SQLEngine(SourceUPCDB()).get_dashboard_metrics()
    assert metrics["master_brand"]["records_with_upc"] == 1

