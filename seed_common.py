import asyncio
import sys
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import ssl

from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.models.bug import Bug, BugStatus

async def seed_data():
    DATABASE_URL = settings.DATABASE_URL
    connect_args = {}
    if "azure.com" in DATABASE_URL:
        connect_args["ssl"] = ssl.create_default_context()
        
    engine = create_async_engine(DATABASE_URL, connect_args=connect_args)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    print("Seeding common data (Projects, Tasks, Bugs)...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create a Project
            proj = Project(
                name="Website Redesign 2026",
                description="Overhauling the corporate website with a modern look and better performance.",
                start_date=date.today(),
                status=ProjectStatus.in_progress,
            )
            session.add(proj)
            await session.commit()
            await session.refresh(proj)
            print(f"Created Project: {proj.name} (ID: {proj.id})")
            
            # 2. Create Tasks
            task1 = Task(
                project_id=proj.id,
                name="Design Mockups",
                description="Create Figma mockups for the homepage and about page.",
                status=TaskStatus.resolved,
                assignees=["designer@example.com"]
            )
            task2 = Task(
                project_id=proj.id,
                name="Frontend Implementation",
                description="Implement the design using React and Tailwind.",
                status=TaskStatus.in_progress,
                assignees=["frontend@example.com"]
            )
            session.add_all([task1, task2])
            await session.commit()
            await session.refresh(task1)
            await session.refresh(task2)
            print(f"Created Tasks: '{task1.name}', '{task2.name}'")
            
            # 3. Create Sub-tasks
            subtask = Task(
                project_id=proj.id,
                parent_id=task2.id,
                name="Configure Vite",
                description="Set up Vite with React SWC plugin.",
                status=TaskStatus.closed,
                assignees=["frontend@example.com"]
            )
            session.add(subtask)
            await session.commit()
            
            # 4. Create Bugs
            bug1 = Bug(
                project_id=proj.id,
                task_id=task2.id,
                title="Mobile menu doesn't open",
                description="Clicking the hamburger icon does nothing on mobile resolutions.",
                reporter="qa@example.com",
                status=BugStatus.open,
                assignees=["frontend@example.com"]
            )
            bug2 = Bug(
                project_id=proj.id,
                title="Favicon missing",
                description="The website favicon is returning a 404 error.",
                reporter="manager@example.com",
                status=BugStatus.in_progress,
            )
            session.add_all([bug1, bug2])
            await session.commit()
            print("Created Bugs: Mobile menu issue, Favicon missing")
            
            print("Successfully seeded common data! (Admin user was not touched).")
            
        except Exception as e:
            print(f"Error seeding data: {e}")
            await session.rollback()
        finally:
            await session.close()
            await engine.dispose()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())
