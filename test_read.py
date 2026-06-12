import asyncio
import httpx

async def t():
    r = await httpx.AsyncClient().get('http://localhost:8000/api/v1/tasks/5')
    print('GET:', r.status_code, r.text)

asyncio.run(t())
