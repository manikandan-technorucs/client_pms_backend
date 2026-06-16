import asyncio
import asyncmy
import ssl

async def test_conn():
    try:
        ssl_ctx = ssl.create_default_context()
        conn = await asyncmy.connect(
            host='suse-db.mysql.database.azure.com',
            port=3306,
            user='fsadmin',
            password='123@suse@project!2026',
            database='pms',
            ssl=ssl_ctx
        )
        print("Successfully connected with asyncmy!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_conn())
