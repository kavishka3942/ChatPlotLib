from ollama import AsyncClient
import requests
import json

async def call_ollama(message: str):
    """
    Asynchronous Ollama caller.
    """
    message_payload = {'role': 'user', 'content': message}
        
    client = AsyncClient(host='http://host.docker.internal:11434') # Points to your local Ollama
    try:
        response = await client.chat(
            model='qwen2.5vl:3b', # Changed to standard qwen2.5:3b (adjust if you specifically need the vl version)
            messages=[message_payload],
            options={
                "num_ctx": 8192,
                "num_predict": 512,
                "temperature": 0.0,
            }
        )
        return response['message']['content']
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running on your host machine."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"