import sqlite3
import mysql.connector
from mysql.connector import errorcode
import pandas as pd
import logging
from datetime import datetime, timezone
from config import SQLITE_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, CSV_FILES

logger = logging.getLogger("DBManager")

class DBManager:
    def __init__(self, use_mysql=True, mysql_password=None):
        self.use_mysql = use_mysql
        self._active_backend = "mysql" if use_mysql else "sqlite"
        self.mysql_password = mysql_password if mysql_password is not None else MYSQL_PASSWORD
        self.sqlite_path = str(SQLITE_PATH)
        self.last_mysql_check = None
        self.last_sqlite_check = None

    def set_mysql_backend(self, enabled):
        """Enable or disable MySQL preference; SQLite remains the fallback."""
        self.use_mysql = bool(enabled)
        self._active_backend = "mysql" if self.use_mysql else "sqlite"

    def backend_name(self):
        """Return the backend currently selected for application queries."""
        return self._active_backend

    def test_mysql_connection(self, password=None):
        """Test if the configured MySQL server is reachable and authenticates."""
        pwd = password if password is not None else self.mysql_password
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=pwd,
                connection_timeout=3,
            )
            version = None
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
            conn.close()
            self.last_mysql_check = datetime.now(timezone.utc).isoformat()
            return True, f"Connected to MySQL {version} on {MYSQL_HOST}:{MYSQL_PORT}"
        except Exception as e:
            self.last_mysql_check = datetime.now(timezone.utc).isoformat()
            return False, str(e)

    def get_mysql_connection(self, create_db=True):
        """Obtain a Connector/Python connection to the configured MySQL server."""
        connection_options = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": self.mysql_password,
            "database": MYSQL_DB,
            "charset": "utf8mb4",
            "connection_timeout": 5,
        }
        try:
            return mysql.connector.connect(**connection_options)
        except mysql.connector.Error as exc:
            if not create_db or exc.errno != errorcode.ER_BAD_DB_ERROR:
                raise

        server_options = {key: value for key, value in connection_options.items() if key != "database"}
        server_conn = mysql.connector.connect(**server_options)
        try:
            with server_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            server_conn.close()
        return mysql.connector.connect(**connection_options)

    def get_sqlite_connection(self):
        """Obtain high-performance local SQLite connection."""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 100000")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def table_columns(self, table):
        """Return column names for a configured table on the active backend."""
        if self.use_mysql:
            try:
                conn = self.get_mysql_connection()
            except Exception as exc:
                logger.warning("MySQL connection unavailable; using SQLite fallback: %s", exc)
                self._active_backend = "sqlite"
            else:
                try:
                    with conn.cursor(dictionary=True) as cur:
                        cur.execute(f"SHOW COLUMNS FROM `{table}`")
                        rows = cur.fetchall()
                finally:
                    conn.close()
                self._active_backend = "mysql"
                return [row.get("Field") or row.get("field") for row in rows]
        conn = self.get_sqlite_connection()
        try:
            rows = conn.execute(f"PRAGMA table_info(`{table}`)").fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    def mysql_schema_status(self):
        """Check that MySQL has the normalized tables this application queries."""
        required = {entry["table"] for entry in CSV_FILES.values()}
        try:
            conn = self.get_mysql_connection(create_db=False)
            try:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute("SHOW TABLES")
                    rows = cur.fetchall()
            finally:
                conn.close()
            available = {next(iter(row.values())) for row in rows}
            missing = sorted(required - available)
            if missing:
                return False, f"MySQL is reachable but normalized beverage tables are missing: {', '.join(missing)}"
            return True, "MySQL normalized beverage schema is ready"
        except Exception as exc:
            return False, f"MySQL schema check failed: {exc}"

    def database_status(self):
        """Return safe connection state without exposing credentials."""
        sqlite_ok = False
        sqlite_message = "Unavailable"
        try:
            conn = self.get_sqlite_connection()
            conn.close()
            sqlite_ok = True
            sqlite_message = "SQLite database is available"
            self.last_sqlite_check = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            sqlite_message = str(exc)

        mysql_ok, mysql_message = self.test_mysql_connection()
        mysql_schema_ready, mysql_schema_message = self.mysql_schema_status() if mysql_ok else (False, "MySQL schema was not checked because the server is unavailable")
        if self.use_mysql:
            self._active_backend = "mysql" if mysql_ok else "sqlite"
        return {
            "sqlite_connected": sqlite_ok,
            "sqlite_message": sqlite_message,
            "mysql_connected": mysql_ok,
            "mysql_message": mysql_message,
            "mysql_schema_ready": mysql_schema_ready,
            "mysql_schema_message": mysql_schema_message,
            "active_backend": self.backend_name(),
            "primary_backend": "mysql" if self.use_mysql else "sqlite",
            "database_name": MYSQL_DB if self._active_backend == "mysql" else "beverage_data.sqlite3",
            "last_sqlite_check": self.last_sqlite_check,
            "last_mysql_check": self.last_mysql_check,
        }

    def get_connection(self):
        """Returns MySQL connection if configured and available, otherwise SQLite."""
        if self.use_mysql:
            try:
                conn = self.get_mysql_connection()
            except Exception as exc:
                logger.warning("MySQL connection unavailable; using SQLite fallback: %s", exc)
                self._active_backend = "sqlite"
            else:
                self._active_backend = "mysql"
                return conn
        return self.get_sqlite_connection()

    def query(self, sql, params=None):
        """Execute query and return list of dicts."""
        if self.use_mysql:
            try:
                conn = self.get_mysql_connection()
            except Exception as exc:
                logger.warning("MySQL query failed; using SQLite fallback: %s", exc)
                self._active_backend = "sqlite"
            else:
                self._active_backend = "mysql"
                try:
                    with conn.cursor(dictionary=True) as cur:
                        cur.execute(sql.replace("?", "%s"), params or ())
                        return cur.fetchall()
                finally:
                    conn.close()

        conn = self.get_sqlite_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def query_df(self, sql, params=None):
        """Execute query and return Pandas DataFrame."""
        if self.use_mysql:
            try:
                conn = self.get_mysql_connection()
            except Exception as exc:
                logger.warning("MySQL dataframe query failed; using SQLite fallback: %s", exc)
                self._active_backend = "sqlite"
            else:
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql.replace("?", "%s"), params or ())
                        columns = [column[0] for column in cur.description]
                        result = pd.DataFrame(cur.fetchall(), columns=columns)
                    self._active_backend = "mysql"
                    return result
                finally:
                    conn.close()

        conn = self.get_sqlite_connection()
        try:
            return pd.read_sql(sql, conn, params=params)
        finally:
            conn.close()

# The application is MySQL-primary for the beverage task. Every query still
# falls back to SQLite if MySQL becomes unavailable, so local development and
# offline usage remain safe without silently making SQLite the intended source.
db_manager = DBManager(use_mysql=True)
