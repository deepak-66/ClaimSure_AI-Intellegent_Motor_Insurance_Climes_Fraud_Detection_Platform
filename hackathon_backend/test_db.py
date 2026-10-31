import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="claimssure_ai"
    )

    if conn.is_connected():
        print("MySQL Connected Successfully!")

    conn.close()

except mysql.connector.Error as err:
    print("Connection Error:", err)