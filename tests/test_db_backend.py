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

