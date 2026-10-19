from werkzeug.security import generate_password_hash
from db import get_cursor

email = "user2@example.com"
password = "1234"

with get_cursor() as cursor:
    cursor.execute(
        'SELECT user_id FROM "USER" WHERE LOWER(email) = LOWER(%s)',
        (email,)
    )

    user = cursor.fetchone()

    if user:
        cursor.execute(
            'UPDATE "USER" SET password_hash = %s WHERE user_id = %s',
            (generate_password_hash(password), user["user_id"])
        )
        print("Test password updated successfully.")
        print("Email:", email)
        print("Password:", password)
    else:
        print("User not found. Check whether the CSV data was imported.")