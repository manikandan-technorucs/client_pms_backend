import sys
import asyncio
import uvicorn

if sys.platform == 'win32':
    # Fix for aiomysql SSL connection issues on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, loop="none")
