from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app
import database.db_manager as db_manager_module
from database.db_manager import DBManager


def test_db_manager_prefers_mysql_by_default():
    manager = DBManager()

    assert manager.backend_name() == "mysql"
    assert manager.use_mysql is True
    manager.set_mysql_backend(False)

    assert manager.backend_name() == "sqlite"


def test_mysql_connection_does_not_run_database_ddl_for_existing_database(monkeypatch):
    manager = DBManager()
    connection = object()
    calls = []

    def connect(**kwargs):
        calls.append(kwargs)
        return connection

    monkeypatch.setattr(db_manager_module.mysql.connector, "connect", connect)
    assert manager.get_mysql_connection() is connection
    assert len(calls) == 1
    assert calls[0]["database"] == db_manager_module.MYSQL_DB


def test_configure_db_switches_to_mysql_after_success(monkeypatch):
    class FakeManager:
        mysql_password = ""
        active_backend = "sqlite"

        def test_mysql_connection(self, password=None):
            return True, "ok"

        def set_mysql_backend(self, enabled):
            self.active_backend = "mysql" if enabled else "sqlite"

        def backend_name(self):
            return self.active_backend

    manager = FakeManager()
    monkeypatch.setattr(app_module, "db_manager", manager)

    response = app.test_client().post("/api/configure-db", json={"password": "secret"})

    assert response.status_code == 200
    assert manager.active_backend == "mysql"
    assert response.get_json()["backend"] == "mysql"


def test_configure_db_only_replaces_tables_when_requested(monkeypatch):
    class FakeManager:
        mysql_password = ""

        def test_mysql_connection(self, password):
            return True, "ok"

        def set_mysql_backend(self, enabled):
            return None

        def backend_name(self):
            return "mysql"

    calls = {}

    def fake_migrate(**kwargs):
        calls.update(kwargs)
        return True, "migrated"

    monkeypatch.setattr(app_module, "db_manager", FakeManager())
    monkeypatch.setattr(app_module, "migrate_data_to_mysql", fake_migrate)

    response = app.test_client().post(
        "/api/configure-db",
        json={"password": "secret", "migrate": True, "replace_existing": True},
    )

    assert response.status_code == 200
    assert calls["replace_existing"] is True


def test_configure_db_keeps_mysql_as_preferred_backend_after_temporary_failure(monkeypatch):
    class FakeManager:
        mysql_password = ""
        active_backend = "sqlite"

        def test_mysql_connection(self, password=None):
            return False, "connection refused"

        def set_mysql_backend(self, enabled):
            self.active_backend = "mysql" if enabled else "sqlite"

        def backend_name(self):
            return self.active_backend

    manager = FakeManager()
    monkeypatch.setattr(app_module, "db_manager", manager)

    response = app.test_client().post("/api/configure-db", json={"password": "secret"})

    assert response.status_code == 400
    assert manager.active_backend == "mysql"


def test_query_falls_back_to_sqlite_when_mysql_query_fails(monkeypatch):
    manager = DBManager(use_mysql=True)

    class Cursor:
        def execute(self, sql, params):
            return None

        def fetchall(self):
            return []

    class Connection:
        def cursor(self, **kwargs):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(manager, "test_mysql_connection", lambda password=None: (True, "ok"))
    monkeypatch.setattr(manager, "get_mysql_connection", lambda: (_ for _ in ()).throw(RuntimeError("mysql dropped")))
    monkeypatch.setattr(manager, "get_sqlite_connection", lambda: Connection())

    assert manager.query("SELECT 1") == []
    assert manager.backend_name() == "sqlite"
    assert manager.use_mysql is True


def test_mysql_fallback_retries_mysql_on_the_next_query(monkeypatch):
    manager = DBManager(use_mysql=True)
    attempts = {"count": 0}

    class Cursor:
        def execute(self, sql, params):
            return None

        def fetchall(self):
            return [{"result": 1}]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Connection:
        def cursor(self, **kwargs):
            return Cursor()

        def close(self):
            return None

    class SQLiteCursor:
        def execute(self, sql, params):
            return None

        def fetchall(self):
            return []

    class SQLiteConnection:
        def cursor(self):
            return SQLiteCursor()

        def close(self):
            return None

    def connect():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporarily unavailable")
        return Connection()

    monkeypatch.setattr(manager, "get_mysql_connection", connect)
    monkeypatch.setattr(manager, "get_sqlite_connection", lambda: SQLiteConnection())

    assert manager.query("SELECT 1") == []
    assert manager.backend_name() == "sqlite"
    assert manager.query("SELECT 1") == [{"result": 1}]
    assert manager.backend_name() == "mysql"
    assert attempts["count"] == 2


def test_mysql_query_errors_are_not_hidden_by_sqlite_fallback(monkeypatch):
    manager = DBManager(use_mysql=True)

    class Cursor:
        def execute(self, sql, params):
            raise RuntimeError("unknown table")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class Connection:
        def cursor(self, **kwargs):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(manager, "get_mysql_connection", lambda: Connection())
    monkeypatch.setattr(
        manager,
        "get_sqlite_connection",
        lambda: (_ for _ in ()).throw(AssertionError("query error must not fall back")),
    )

    try:
        manager.query("SELECT * FROM missing_table")
    except RuntimeError as error:
        assert "unknown table" in str(error)
    else:
        raise AssertionError("MySQL query error should be reported")


def test_database_status_reports_safe_sqlite_and_mysql_fields(monkeypatch):
    from database.db_manager import DBManager

    manager = DBManager()
    monkeypatch.setattr(manager, "test_mysql_connection", lambda password=None: (False, "not configured"))

    status = manager.database_status()

    assert status["sqlite_connected"] is True
    assert status["mysql_connected"] is False
    assert status["active_backend"] == "sqlite"
    assert status["primary_backend"] == "mysql"


def test_mysql_schema_readiness_is_explicit(monkeypatch):
    manager = DBManager()
    monkeypatch.setattr(manager, "test_mysql_connection", lambda password=None: (True, "connected"))
    monkeypatch.setattr(manager, "mysql_schema_status", lambda: (False, "MySQL is reachable but the normalized beverage tables are missing"))

    status = manager.database_status()

    assert status["mysql_connected"] is True
    assert status["mysql_schema_ready"] is False
    assert "normalized beverage tables" in status["mysql_schema_message"]
    assert "password" not in str(status).lower()
