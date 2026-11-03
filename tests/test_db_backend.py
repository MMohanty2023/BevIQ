from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module
from app import app
from database.db_manager import DBManager


def test_db_manager_reports_sqlite_until_mysql_is_enabled():
    manager = DBManager()

    assert manager.backend_name() == "sqlite"
    manager.set_mysql_backend(True)

    assert manager.backend_name() == "mysql"


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


def test_configure_db_keeps_sqlite_after_failed_mysql_connection(monkeypatch):
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
    assert manager.active_backend == "sqlite"


def test_query_falls_back_to_sqlite_when_mysql_query_fails(monkeypatch):
    manager = DBManager(use_mysql=True)

    class Cursor:
        def execute(self, sql, params):
            return None

        def fetchall(self):
            return []

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            return None

    monkeypatch.setattr(manager, "test_mysql_connection", lambda password=None: (True, "ok"))
    monkeypatch.setattr(manager, "get_mysql_connection", lambda: (_ for _ in ()).throw(RuntimeError("mysql dropped")))
    monkeypatch.setattr(manager, "get_sqlite_connection", lambda: Connection())

    assert manager.query("SELECT 1") == []
    assert manager.backend_name() == "sqlite"


def test_database_status_reports_safe_sqlite_and_mysql_fields(monkeypatch):
    from database.db_manager import DBManager

    manager = DBManager()
    monkeypatch.setattr(manager, "test_mysql_connection", lambda password=None: (False, "not configured"))

    status = manager.database_status()

    assert status["sqlite_connected"] is True
    assert status["mysql_connected"] is False
    assert status["active_backend"] == "sqlite"
    assert "password" not in str(status).lower()

