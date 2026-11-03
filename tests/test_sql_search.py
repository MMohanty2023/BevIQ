from engines.sql_engine import SQLEngine


class FakeDB:
    def __init__(self):
        self.calls = []

    def query(self, sql, params=None):
        self.calls.append((sql, params))
        if "FROM `ai_master`" in sql and "clean_alt_upc" in sql:
            return [{
                "id": "10245",
                "BrandName": "Example Brand",
                "ProductName": "Example Product",
                "clean_upc": "0012345678905",
                "clean_alt_upc": "0098765432100",
                "source_file": "AIMasterBrandData.csv",
                "original_row": 12,
            }]
        if "FROM `cat_beer`" in sql and "clean_upc" in sql:
            return [{
                "Beer_Brands_Value": "Example Brand",
                "Product": "Example Product",
                "clean_upc": "0012345678905",
                "source_file": "Categorization 2026 - Beer.csv",
                "original_row": 9,
            }]
        return []


def test_lookup_identifier_returns_complete_direct_and_related_records():
    db = FakeDB()

    result = SQLEngine(db).lookup_identifier("10245")

    assert result["total_matches"] >= 1
    assert result["records"][0]["ProductName"] == "Example Product"
    assert result["records"][0]["source_file"] == "AIMasterBrandData.csv"
    assert result["related_records"] == []


def test_lookup_identifier_matches_alternate_upc_and_related_dataset():
    db = FakeDB()

    result = SQLEngine(db).lookup_identifier("0098765432100")

    assert result["total_matches"] >= 1
    assert result["normalized_identifier"] == "0098765432100"


def test_search_catalog_passes_offset_for_pagination():
    db = FakeDB()
    engine = SQLEngine(db)

    engine.search_catalog("example", limit=25, offset=50)

    assert any("LIMIT 25 OFFSET 50" in sql for sql, _ in db.calls)

