from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database.mysql_migrator as migrator


def _source_config(filename="brands.csv"):
    return {
        "brands": {
            "file": filename,
            "delimiter": "|",
            "table": "all_brands",
            "upc_col": "UPCCode",
            "alt_upc_col": None,
            "brand_col": "BrandName",
            "supplier_col": "SupplierName",
        }
    }


def test_missing_source_files_fail_before_connecting_to_mysql(tmp_path, monkeypatch):
    monkeypatch.setattr(migrator, "DATA_DIR", tmp_path)
    monkeypatch.setattr(migrator, "CSV_FILES", _source_config())
    monkeypatch.setattr(
        migrator.mysql.connector,
        "connect",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not connect")),
    )

    success, message = migrator.migrate_data_to_mysql()

    assert success is False
    assert "source file not found" in message


def test_existing_tables_are_not_replaced_without_explicit_opt_in(tmp_path, monkeypatch):
    (tmp_path / "brands.csv").write_text(
        "UPCCode|BrandName|SupplierName\n0012345678905|Example|Supplier\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(migrator, "DATA_DIR", tmp_path)
    monkeypatch.setattr(migrator, "CSV_FILES", _source_config())
    executed_sql = []

    class Cursor:
        def execute(self, query, params=None):
            executed_sql.append(query)

        def fetchone(self):
            return (1,)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Connection:
        def cursor(self, **kwargs):
            return Cursor()

        def close(self):
            return None

    connections = [Connection(), Connection()]
    monkeypatch.setattr(
        migrator.mysql.connector,
        "connect",
        lambda **kwargs: connections.pop(0),
    )

    success, message = migrator.migrate_data_to_mysql()

    assert success is False
    assert "already exist" in message
    assert not any("DROP TABLE" in query for query in executed_sql)
    assert not any("CREATE TABLE" in query for query in executed_sql)


def test_prepare_sources_can_select_only_trained_dataset(tmp_path, monkeypatch):
    (tmp_path / "trained.csv").write_text(
        "Id|BrandName|ImageUrls\n1|Example|https://example.test/image.png\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(migrator, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        migrator,
        "CSV_FILES",
        {
            "trained_brands": {
                "file": "trained.csv",
                "delimiter": "|",
                "table": "trained_brands",
                "upc_col": None,
                "alt_upc_col": None,
                "brand_col": "BrandName",
                "supplier_col": None,
            },
            "other": _source_config()["brands"],
        },
    )

    sources = migrator._prepare_sources(["trained_brands"])

    assert list(sources) == ["trained_brands"]
    assert sources["trained_brands"]["path"].name == "trained.csv"


def test_prepare_sources_rejects_unknown_dataset_selection(monkeypatch):
    monkeypatch.setattr(migrator, "CSV_FILES", _source_config())

    try:
        migrator._prepare_sources(["trained_brands"])
    except ValueError as error:
        assert "unknown dataset key" in str(error)
    else:
        raise AssertionError("unknown dataset key should fail preflight")
