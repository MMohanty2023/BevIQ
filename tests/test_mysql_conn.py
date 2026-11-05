from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import mysql.connector

from config import MYSQL_DB, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


def main():
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        connection_timeout=3,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            print("Connected to configured MySQL server:", cursor.fetchone()[0])
    finally:
        connection.close()


if __name__ == "__main__":
    main()
