import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

import ssl
ssl_ctx = ssl.create_default_context()
engine = create_async_engine('mysql+aiomysql://fsadmin:123%40suse%40project%212026@suse-db.mysql.database.azure.com:3306/pms', connect_args={'ssl': ssl_ctx})

async def test():
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            res = await conn.execute(text('SHOW TABLES;'))
            print("Connected to DB successfully! Tables:", res.fetchall())
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
