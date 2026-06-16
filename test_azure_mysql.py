import asyncio
import aiomysql
import ssl
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_conn():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = await aiomysql.connect(
            host='suse-db.mysql.database.azure.com',
            port=3306,
            user='fsadmin',
            password='123@suse@project!2026',
            db='pms',
            ssl=ctx
        )
        print("Successfully connected!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_conn())
