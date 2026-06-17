import asyncio
import argparse
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from sqlalchemy import select

async def manage_user(username: str, password: str | None, role: str | None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"User '{username}' found. Updating...")
            if password:
                user.hashed_password = get_password_hash(password)
                print(f"  - Password updated.")
            if role:
                try:
                    user.role = UserRole(role)
                    print(f"  - Role updated to '{role}'.")
                except ValueError:
                    print(f"  - Invalid role '{role}', must be 'admin' or 'user'. Skipping role update.")
            
            await session.commit()
            print("User updated successfully.")
        else:
            if not password:
                print("Error: Password is required to create a new user.")
                sys.exit(1)
            if not role:
                role = "user"
            
            print(f"User '{username}' not found. Creating new user...")
            try:
                new_user = User(
                    username=username,
                    hashed_password=get_password_hash(password),
                    role=UserRole(role)
                )
                session.add(new_user)
                await session.commit()
                print(f"User '{username}' created successfully with role '{role}'.")
            except ValueError:
                print(f"Error: Invalid role '{role}', must be 'admin' or 'user'.")
                sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Manage users in the PMS database.")
    parser.add_argument("--username", required=True, help="Username to create or update")
    parser.add_argument("--password", help="Password for the user (required for new users)")
    parser.add_argument("--role", choices=["admin", "user"], help="Role of the user (admin or user)")
    
    args = parser.parse_args()
    asyncio.run(manage_user(args.username, args.password, args.role))

if __name__ == "__main__":
    main()
