import sys
import asyncio
import uvicorn
from fastapi import FastAPI
from app.database import engine

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI()

@app.on_event("startup")
async def startup():
    print(f"Current loop: {type(asyncio.get_event_loop())}")
    try:
        async with engine.connect() as conn:
            print("Successfully connected to DB within FastAPI!")
    except Exception as e:
        print(f"Failed to connect within FastAPI: {e}")
    sys.exit(0)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, loop="none")
