import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import engine
from sqlalchemy import text

async def delete_bad_user():
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM users WHERE username='admin'"))
        print("Deleted bad admin user")

if __name__ == "__main__":
    asyncio.run(delete_bad_user())
