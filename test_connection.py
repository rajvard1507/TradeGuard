from db import get_cursor

with get_cursor() as cursor:
    cursor.execute('SELECT COUNT(*) AS total FROM "RISK_RULE"')
    result = cursor.fetchone()
    print("Database connected successfully.")
    print("Risk rules:", result["total"])