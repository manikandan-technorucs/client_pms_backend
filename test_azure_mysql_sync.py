import pymysql
import ssl

def test_conn():
    try:
        ssl_ctx = ssl.create_default_context()
        conn = pymysql.connect(
            host='suse-db.mysql.database.azure.com',
            port=3306,
            user='fsadmin',
            password='123@suse@project!2026',
            ssl=ssl_ctx,
            connect_timeout=10
        )
        print("Successfully connected with pymysql!")
        
        with conn.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS pms;")
            print("Database 'pms' created successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

test_conn()
