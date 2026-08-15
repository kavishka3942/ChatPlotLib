import asyncio
import httpx

async def test_endpoint(message: str):
    print(f"\n--- Testing: {message} ---")
    async with httpx.AsyncClient() as client:
        payload = {
            "messages": [{"role": "user", "content": message}],
            "filename": "",
            "dataset_schema": ""
        }
        async with client.stream("POST", "http://localhost:8000/chat", json=payload, timeout=30.0) as response:
            async for chunk in response.aiter_text():
                print(chunk, end="", flush=True)
            print()

async def run_tests():
    # 1. Chat intent
    await test_endpoint("hello, what is your name?")
    
    # 2. Execute intent
    await test_endpoint("what is 2 + 2?")
    
    # 3. Code intent
    await test_endpoint("write a python script to calculate the factorial of 5")

if __name__ == "__main__":
    asyncio.run(run_tests())
