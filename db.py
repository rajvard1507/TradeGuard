from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL

@contextmanager
def get_cursor():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
