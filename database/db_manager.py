import sqlite3
import pymysql
import pandas as pd
import logging
from config import SQLITE_PATH, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

logger = logging.getLogger("DBManager")

class DBManager:
    def __init__(self, use_mysql=False, mysql_password=None):
        self.use_mysql = use_mysql
        self._active_backend = "mysql" if use_mysql else "sqlite"
        self.mysql_password = mysql_password if mysql_password is not None else MYSQL_PASSWORD
        self.sqlite_path = str(SQLITE_PATH)

    def set_mysql_backend(self, enabled):
        """Select MySQL as primary or return to the local SQLite fallback."""
        self.use_mysql = bool(enabled)
        self._active_backend = "mysql" if self.use_mysql else "sqlite"

    def backend_name(self):
        """Return the backend currently selected for application queries."""
        return self._active_backend

    def test_mysql_connection(self, password=None):
        """Test if MySQL server on port 3307 is reachable and authenticates."""
        pwd = password if password is not None else self.mysql_password
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=pwd,
                connect_timeout=3
            )
            version = None
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
            conn.close()
            return True, f"Connected to MySQL {version} on {MYSQL_HOST}:{MYSQL_PORT}"
        except Exception as e:
            return False, str(e)

    def get_mysql_connection(self, create_db=True):
        """Obtain PyMySQL connection to MySQL 3307."""
        if create_db:
            # First connect without DB to ensure DB exists
            root_conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=self.mysql_password,
                connect_timeout=5
            )
            with root_conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            root_conn.close()

        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=self.mysql_password,
            database=MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def get_sqlite_connection(self):
        """Obtain high-performance local SQLite connection."""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 100000")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def get_connection(self):
        """Returns MySQL connection if configured and available, otherwise SQLite."""
        if self.use_mysql:
            ok, _ = self.test_mysql_connection()
            if ok:
                return self.get_mysql_connection()
            self.set_mysql_backend(False)
        return self.get_sqlite_connection()

    def query(self, sql, params=None):
        """Execute query and return list of dicts."""
        if self.use_mysql:
            try:
                if self.test_mysql_connection()[0]:
                    conn = self.get_mysql_connection()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(sql, params or ())
                            return cur.fetchall()
                    finally:
                        conn.close()
                self.set_mysql_backend(False)
            except Exception as exc:
                logger.warning("MySQL query failed; using SQLite fallback: %s", exc)
                self.set_mysql_backend(False)

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
                if self.test_mysql_connection()[0]:
                    conn = self.get_mysql_connection()
                    try:
                        return pd.read_sql(sql, conn, params=params)
                    finally:
                        conn.close()
                self.set_mysql_backend(False)
            except Exception as exc:
                logger.warning("MySQL dataframe query failed; using SQLite fallback: %s", exc)
                self.set_mysql_backend(False)

        conn = self.get_sqlite_connection()
        try:
            return pd.read_sql(sql, conn, params=params)
        finally:
            conn.close()

# Global default instance
db_manager = DBManager()

