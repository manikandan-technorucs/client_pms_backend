import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiomysql
from app.core.config import settings

async def test_db():
    try:
        import ssl
        ssl_ctx = ssl.create_default_context()
        conn = await aiomysql.connect(
            host='suse-db.mysql.database.azure.com',
            port=3306,
            user='fsadmin',
            password='123@suse@project!2026',
            db='pms',
            ssl=ssl_ctx
        )
        print("Raw aiomysql connected!")
        conn.close()
    except Exception as e:
        print(f"Raw aiomysql failed: {e}")

    try:
        from app.database import engine
        async with engine.connect() as conn:
            print("SQLAlchemy connected!")
    except Exception as e:
        print(f"SQLAlchemy failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
