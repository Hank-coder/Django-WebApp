import mysql.connector

try:
    connection = mysql.connector.connect(
        host='38.60.249.61',
        user='root',
        password='!@cyh1qw23er45T',

    )
    print("Connection successful!")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    if connection.is_connected():
        connection.close()
        print("Connection closed.")
