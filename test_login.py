import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select
from app.core.security import verify_password

async def test_login():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if not user:
            print("User admin not found in DB!")
            return
        
        print("User found. Testing password...")
        try:
            is_valid = verify_password("admin123", user.hashed_password)
            print(f"Password valid: {is_valid}")
        except Exception as e:
            print(f"Exception during verify_password: {e}")

if __name__ == "__main__":
    asyncio.run(test_login())
