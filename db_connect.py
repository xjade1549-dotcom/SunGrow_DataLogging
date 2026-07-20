import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "ems_executed_decision",
    "user": "jade",
    "password": "password",
    "host": "localhost",
    "port": 12345
}

@contextmanager
def get_db_cursor():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

