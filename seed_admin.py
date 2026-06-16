import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select

async def seed_admin():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            print("Creating initial admin user...")
            new_admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.admin
            )
            session.add(new_admin)
            await session.commit()
            print("Admin user created (admin / admin123)")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
