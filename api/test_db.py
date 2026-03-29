import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'NewsHub'
}

try:
    print("Connecting to MySQL...")
    conn = mysql.connector.connect(**db_config)
    print("Connection successful!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interests;")
    rows = cursor.fetchall()
    print("Interests table content:", rows)
    
    cursor.close()
    conn.close()
except Exception as e:
    print("Error:", e)
