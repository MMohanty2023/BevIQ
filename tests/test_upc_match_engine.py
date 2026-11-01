from engines.upc_match_engine import UPCMatchEngine


class FakeDB:
    def __init__(self, category_rows, master_rows):
        self.category_rows = category_rows
        self.master_rows = master_rows
        self.writes = 0
        self.master_queries = 0

    def query(self, sql, params=None):
        if "FROM `cat_beer`" in sql:
            return self.category_rows
        if "FROM all_brands" in sql:
            self.master_queries += 1
            return self.master_rows
        raise AssertionError(f"Unexpected SQL: {sql}")


def _category_row(**overrides):
    row = {
        "clean_upc": "",
        "source_file": "Categorization 2026 - Beer.csv",
        "original_row": 7,
        "Beer_Brands_Value": "Harbor Light",
        "Beer_Size_Groups_Value": "12 oz 6 pack",
        "Product": "Harbor Light Lager Lemon",
        "Beer_Category_Value": "Lager",
        "Beer_Mezzo_Styles_Value": "Lemon",
    }
    row.update(overrides)
    return row


def _master_row(**overrides):
    row = {
        "source_file": "$ALLBrand.csv",
        "original_row": 42,
        "clean_upc": "0012345678905",
        "clean_alt_upc": "0098765432100",
        "BrandName": "Harbor Light",
        "ProductName": "Harbor Light Lager Lemon",
        "Size": "12 oz 6 pack",
        "SupplierName": "Example Supplier",
    }
    row.update(overrides)
    return row


def test_exact_upc_is_reported_as_verified_without_writing(monkeypatch):
    category = _category_row(clean_upc="0012345678905")
    fake_db = FakeDB([category], [_master_row()])
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = UPCMatchEngine().audit("cat_beer", limit=10)

    assert len(records) == 1
    assert records[0]["status"] == "Verified UPC in AllBrand"
    assert records[0]["current_upc"] == "0012345678905"
    assert records[0]["suggested_upc"] == ""
    assert fake_db.writes == 0


def test_missing_upc_gets_strong_product_match_and_preserves_leading_zero(monkeypatch):
    fake_db = FakeDB([_category_row()], [_master_row()])
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = UPCMatchEngine().audit("cat_beer", limit=10)

    assert len(records) == 1
    assert records[0]["status"] == "Product Match - UPC Missing"
    assert records[0]["suggested_upc"] == "0012345678905"
    assert records[0]["alternate_upc"] == "0098765432100"
    assert records[0]["confidence"] >= 80
    assert records[0]["source_description"]
    assert records[0]["master_description"]
    assert records[0]["description_match_score"] >= 75


def test_brand_only_match_does_not_suggest_an_upc(monkeypatch):
    fake_db = FakeDB(
        [_category_row(Product="", Beer_Size_Groups_Value="", Beer_Mezzo_Styles_Value="")],
        [_master_row()],
    )
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = UPCMatchEngine().audit("cat_beer", limit=10)

    assert len(records) == 1
    assert records[0]["suggested_upc"] == ""
    assert records[0]["status"] == "Manual Review - Insufficient Product Match"


def test_blank_brand_does_not_scan_unrelated_master_products(monkeypatch):
    fake_db = FakeDB(
        [_category_row(Beer_Brands_Value="", Product="Unknown Lager")],
        [_master_row()],
    )
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = UPCMatchEngine().audit("cat_beer", limit=10)

    assert records[0]["suggested_upc"] == ""
    assert records[0]["status"] == "Manual Review - Insufficient Product Match"


def test_size_conflict_does_not_suggest_an_upc(monkeypatch):
    fake_db = FakeDB(
        [_category_row(Beer_Size_Groups_Value="24 oz 12 pack")],
        [_master_row(Size="12 oz 6 pack")],
    )
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = UPCMatchEngine().audit("cat_beer", limit=10)

    assert len(records) == 1
    assert records[0]["suggested_upc"] == ""
    assert records[0]["status"] == "Manual Review - Size/Pack Conflict"


def test_liter_and_milliliter_sizes_are_compatible(monkeypatch):
    engine = UPCMatchEngine()
    assert engine._size_status("0.75 LT", "750 ML")[0] == "compatible"
    fake_db = FakeDB(
        [_category_row(Beer_Size_Groups_Value="0.75 LT")],
        [_master_row(Size="750 ML")],
    )
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    records = engine.audit("cat_beer", limit=10)

    assert records[0]["status"] == "Product Match - UPC Missing"
    assert records[0]["suggested_upc"] == "0012345678905"


def test_audit_loads_master_candidates_once_for_multiple_rows(monkeypatch):
    rows = [_category_row(original_row=7), _category_row(original_row=8, Beer_Brands_Value="Harbor Light Reserve")]
    fake_db = FakeDB(rows, [_master_row()])
    monkeypatch.setattr("engines.upc_match_engine.db_manager", fake_db)

    UPCMatchEngine().audit("cat_beer", limit=10)

    assert fake_db.master_queries == 1
