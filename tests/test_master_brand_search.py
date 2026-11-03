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

