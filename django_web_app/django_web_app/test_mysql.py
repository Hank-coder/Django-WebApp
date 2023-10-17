import mysql.connector
from mysql.connector import Error


def test_connection(host, database, user, password):
    """Test MySQL database connection."""
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print(f"You're connected to database: {record[0]}")
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed.")


if __name__ == "__main__":
    HOST = "38.60.203.214"
    DATABASE = "mysql"
    USER = "root"
    PASSWORD = "!@cyh1qw23er45T"

    test_connection(HOST, DATABASE, USER, PASSWORD)
