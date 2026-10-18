import psycopg2
from config import DATABASE_URL

try:
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()

    cursor.execute("SELECT current_database(), current_user, version();")
    result = cursor.fetchone()

    print("Connection successful!")
    print("Database:", result[0])
    print("User:", result[1])
    print("PostgreSQL:", result[2])

    cursor.close()
    connection.close()

except Exception as error:
    print("Connection failed:", error)