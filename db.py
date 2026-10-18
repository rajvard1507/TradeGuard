from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL


@contextmanager
def get_cursor():
    connection = psycopg2.connect(DATABASE_URL)

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()