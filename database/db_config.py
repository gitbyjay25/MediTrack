# Database configuration
import pymysql
from config import Config

def get_db_connection():
    """Get database connection"""
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='password',
            database='meditrek',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def execute_query(query, params=None):
    """Execute database query"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                connection.commit()
                return cursor.lastrowid
    except Exception as e:
        print(f"Query execution error: {e}")
        return None
    finally:
        connection.close()
