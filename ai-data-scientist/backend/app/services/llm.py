from langchain_ollama import ChatOllama
import requests
import os

async def call_ollama(message: str):
    """
    Asynchronous Ollama caller using LangChain's ChatOllama.
    """
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5vl:3b")
    
    llm = ChatOllama(
        base_url=ollama_url,
        model=ollama_model,
        temperature=0.0,
        num_ctx=8192,
        num_predict=512,
    )
    
    try:
        response = await llm.ainvoke(message)
        return response.content
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running on your host machine."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"