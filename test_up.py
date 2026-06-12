import asyncio
import httpx

async def t():
    data = {'assignees': '["Charlie"]', 'name': 'Updated name'}
    r = await httpx.AsyncClient().put('http://localhost:8000/api/v1/tasks/5', data=data)
    print('PUT:', r.status_code, r.text)

asyncio.run(t())
