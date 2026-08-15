import asyncio
import httpx

async def test_stream():
    async with httpx.AsyncClient() as client:
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "filename": "",
            "dataset_schema": ""
        }
        async with client.stream("POST", "http://localhost:8000/chat", json=payload, timeout=10.0) as response:
            print("Status:", response.status_code)
            async for chunk in response.aiter_text():
                print(f"CHUNK: {repr(chunk)}")

if __name__ == "__main__":
    asyncio.run(test_stream())
